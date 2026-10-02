from relation_stage import (
    MIRROR, LHS, RHS, ADDON, SINGLE_BIT, _frames, _key, _occs, _rhs,
    _collapse_bits, _single_bit, _names_re, _same_stmt, _edge_arms,
)

import re
from collections import namedtuple


_CPToken = namedtuple('_CPToken', 'value line column')
_CP_ID = re.compile(r'(?:[a-z_]\w*|\\[^\\\n]+\\)\Z', re.I)
_CP_LEX = re.compile(
    r'''--[^\n]*|"(?:[^"\n]|"")*"|'(?:[^'\n]|'')'|\\[^\\\n]+\\|'''
    r'''\d[\d_]*(?:\#[0-9a-f_.]+\#|\.[\d_]+)?(?:e[+-]?[\d_]+)?|'''
    r'''[a-z_]\w*|<=|>=|/=|:=|=>|\*\*|<>|\S''', re.I
)
_CP_PRIORITY = {t: i for i, t in enumerate(
    ('SEQUENCES', 'RESETS', 'SELECTS', 'CONSTRAINS', 'GATES', 'CARRIES', 'SOURCES')
)}
_CP_LOGIC = {'and', 'or', 'nand', 'nor', 'xor', 'xnor'}
_CP_COMPARE = {'=', '/=', '<', '<=', '>', '>='}
_CP_FORBIDDEN = {
    'DECL_PORT', 'DECL_SIGNAL', 'DECL_FIELD', 'PROCESS_TRIG',
    'CASE_COND', 'FIELD_USE', 'ASSOC_ACTUAL',
}


def _cp_name(value):
    return re.sub(r'\s*\.\s*', '.', value.strip()).lower()


def _cp_tokens(src):
    if isinstance(src, str):
        lines = src.splitlines()
    elif isinstance(src, (list, tuple)):
        lines = [s for s in src if isinstance(s, str)]
    else:
        return []
    numbered = any(re.match(r'^\s*\d+\s*\|', s) for s in lines)
    result = []
    for fallback, text in enumerate(lines, 1):
        m = re.match(r'^\s*(\d+)\s*\|(.*)$', text)
        if m:
            line, text = int(m.group(1)), m.group(2)
        elif numbered:
            continue
        else:
            line = fallback
        for m in _CP_LEX.finditer(text):
            value = m.group()
            if value.startswith('--'):
                break
            result.append(_CPToken(value.lower(), line, m.start()))
    return result


def _cp_lines(value):
    if isinstance(value, int):
        return value, value
    if isinstance(value, (list, tuple)):
        numbers = []
        for item in value:
            bounds = _cp_lines(item)
            if bounds:
                numbers.extend(bounds)
    elif isinstance(value, str):
        numbers = [int(s) for s in re.findall(r'\d+', value)]
    else:
        return None
    return (min(numbers), max(numbers)) if numbers else None


def _cp_occurrences(ent):
    """Isolate malformed profile rows instead of losing the whole entity."""
    result = []
    profile = ent.get('profile', {})
    if not isinstance(profile, dict):
        return result
    for name, rows in profile.items():
        if not isinstance(name, str) or not isinstance(rows, (list, tuple)):
            continue
        for row in rows:
            try:
                if not isinstance(row, dict):
                    continue
                row = dict(row)
                sites = row.get('SITE Tagged') or []
                if isinstance(sites, str):
                    sites = [sites]
                row['SITE Tagged'] = [s for s in sites if isinstance(s, str)]
                row['Context'] = row.get('Context') if isinstance(row.get('Context'), str) else ''
                row['Line Text'] = row.get('Line Text') or ''
                bounds = _cp_lines(row.get('Occurrence Lines'))
                if bounds is None:
                    continue
                hash(row['Occurrence ID'])
                occurrence = _occs({'profile': {name: [row]}})[0]
                occurrence['bounds'] = bounds
                occurrence['name'] = _cp_name(name)
                result.append(occurrence)
            except Exception:
                continue
    def order(o):
        ident = o['id']
        try:
            ident = (0, int(ident))
        except (TypeError, ValueError, OverflowError):
            ident = (1, str(ident))
        return o['bounds'], o['name'], ident
    return sorted(result, key=order)


class _CPWriter:
    """Token-based statement/control model; profile occurrences remain the endpoints.

    Source coordinates distinguish statements and repeated reads. For profile rows
    without columns, occurrences of the same element/site on a line are consumed
    in Occurrence-ID order, after Context has disambiguated their branches.
    """

    def __init__(self, ent):
        self.tokens = _cp_tokens(ent.get('src', ''))
        self.v = [t.value for t in self.tokens]
        self.n = len(self.v)
        self.close = {}
        stack = []
        for i, value in enumerate(self.v):
            if value == '(':
                stack.append(i)
            elif value == ')' and stack:
                self.close[stack.pop()] = i
        self.occ = _cp_occurrences(ent)
        self.types = {}
        for collection in ('ports', 'signals'):
            rows = ent.get(collection, [])
            if not isinstance(rows, (list, tuple)):
                continue
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get('name'), str):
                    typ = row.get('type')
                    self.types[_cp_name(row['name'])] = typ.lower().strip() if isinstance(typ, str) else ''
        for o in self.occ:
            self.types.setdefault(o['name'], '')
        self.variables = {}
        self.constants = set()
        self.generics = set()
        self.parameters = set()
        self.groups = []
        self.statements = []
        self.references = []
        self.best = {}
        self._declaration_names()

    def _top(self, lo, hi):
        i = lo
        while i < hi:
            yield i
            j = self.close.get(i)
            i = j + 1 if self.v[i] == '(' and j is not None and j < hi else i + 1

    def _find(self, lo, words, hi=None):
        for i in self._top(lo, self.n if hi is None else hi):
            if self.v[i] in words:
                return i
        return None

    def _strip(self, lo, hi):
        while lo < hi and self.v[lo] == '(' and self.close.get(lo) == hi - 1:
            lo, hi = lo + 1, hi - 1
        return lo, hi

    def _declaration_names(self):
        for i, value in enumerate(self.v):
            if value == 'constant':
                j = self._find(i + 1, {':', ';'})
                if j is not None and self.v[j] == ':':
                    self.constants.update(v for v in self.v[i + 1:j] if _CP_ID.fullmatch(v))
            elif value == 'generic' and i + 1 in self.close:
                end = self.close[i + 1]
                start = i + 2
                while start < end:
                    colon = self._find(start, {':', ';'}, end)
                    if colon is None:
                        break
                    if self.v[colon] == ':':
                        self.generics.update(v for v in self.v[start:colon] if _CP_ID.fullmatch(v))
                    semi = self._find(colon + 1, {';'}, end)
                    start = end if semi is None else semi + 1

    def _chain(self, start, hi):
        if start >= hi or not _CP_ID.fullmatch(self.v[start]):
            return None
        parts, indexes = [self.v[start]], []
        i, attr, last_index = start + 1, None, False
        while i < hi:
            if self.v[i] == '.' and i + 1 < hi and _CP_ID.fullmatch(self.v[i + 1]):
                parts.append(self.v[i + 1])
                i += 2
                last_index = False
            elif self.v[i] == '(' and i in self.close and self.close[i] < hi:
                end = self.close[i]
                indexes.append((i + 1, end))
                i = end + 1
                last_index = True
            elif self.v[i] == "'" and i + 1 < hi:
                if _CP_ID.fullmatch(self.v[i + 1]):
                    attr = self.v[i + 1]
                    i += 2
                    if i in self.close:
                        i = self.close[i] + 1
                    break
                if self.v[i + 1] == '(' and i + 1 in self.close:
                    end = self.close[i + 1]
                    indexes.append((i + 2, end))
                    i = end + 1
                    break
                break
            else:
                break
        return i, '.'.join(parts), indexes, attr, last_index

    @staticmethod
    def _locals(scopes):
        return {g['param'] for g, _ in scopes if g.get('param')}

    def _resolve(self, path, pid, local):
        root = path.split('.')[0]
        if root in local or root in self.generics:
            return None
        variables = self.variables.get(pid, {})
        if root in variables:
            return 'variable', path, variables[root] if path == root else ''
        parts = path.split('.')
        for count in range(len(parts), 0, -1):
            name = '.'.join(parts[:count])
            if name in self.types:
                return 'element', name, self.types[name]
        return None

    def _read(self, lo, hi, pid, local, index=False):
        result = []
        i = lo
        while i < hi:
            chain = self._chain(i, hi)
            if chain is None:
                i += 1
                continue
            end, path, indexes, attr, last_index = chain
            resolved = self._resolve(path, pid, local)
            if attr and attr != 'event':
                i = end
                continue  # Shape attributes do not read their prefixes' values.
            if resolved:
                kind, name, typ = resolved
                last_slice = bool(indexes and any(self.v[k] in {'to', 'downto'}
                                  for k in self._top(*indexes[-1])))
                result.append({
                    'kind': kind, 'name': name, 'path': path, 'type': typ,
                    'pos': i, 'end': end, 'index': index, 'indexed': bool(indexes),
                    'bit_index': last_index and not last_slice, 'attr': attr,
                    'exact': path == name and not indexes and attr is None,
                    'occ': None,
                })
            indexed_object = resolved is not None or path.split('.')[0] in self.constants
            for a, b in indexes:
                result.extend(self._read(a, b, pid, local, index or indexed_object))
            i = end
        return result

    def _expr(self, lo, hi, pid, role, scopes):
        expr = {'lo': lo, 'hi': hi, 'pid': pid, 'role': role, 'scopes': tuple(scopes)}
        try:
            refs = self._read(lo, hi, pid, self._locals(scopes))
        except (RecursionError, IndexError):
            refs = []
        expr['refs'] = refs
        for r in refs:
            r['expr'] = expr
            r['role'] = role
            r['scopes'] = expr['scopes']
        self.references.extend(refs)
        return expr

    def _bare_span(self, expr, lo, hi, allow_not=False):
        lo, hi = self._strip(lo, hi)
        if allow_not and lo < hi and self.v[lo] == 'not':
            lo, hi = self._strip(lo + 1, hi)
        return next((r for r in expr['refs'] if r['pos'] == lo and r['end'] == hi), None)

    def _bare(self, expr, allow_not=False):
        return self._bare_span(expr, expr['lo'], expr['hi'], allow_not)

    @staticmethod
    def _bit(ref):
        return ref['type'].strip() in SINGLE_BIT or ref['bit_index']

    def _gates(self, expr):
        if 'gates' in expr:
            return expr['gates']
        lo, hi = self._strip(expr['lo'], expr['hi'])
        operators = [i for i in self._top(lo, hi) if self.v[i] in _CP_LOGIC]
        result = set()
        if operators and len({self.v[i] for i in operators}) == 1 and self.v[operators[0]] in {'and', 'or', 'nand', 'nor'}:
            start = lo
            for end in operators + [hi]:
                r = self._bare_span(expr, start, end, True)
                if r is not None:
                    result.add(r['pos'])
                start = end + 1
        expr['gates'] = result
        return result

    def _literal(self, lo, hi):
        lo, hi = self._strip(lo, hi)
        if lo < hi and self.v[lo] in {'+', '-'}:
            lo += 1
        if hi - lo == 2 and self.v[lo] in {'b', 'o', 'x', 'd', 'ub', 'uo', 'ux', 'sb', 'so', 'sx'}:
            lo += 1
        return hi - lo == 1 and bool(re.match(r'''^(?:\d|'|\")''', self.v[lo]))

    def _fixed(self, lo, hi, pid, local):
        lo, hi = self._strip(lo, hi)
        if self._literal(lo, hi):
            return True
        if hi - lo == 1 and _CP_ID.fullmatch(self.v[lo]):
            name = self.v[lo]
            return name not in local and name not in self.generics and self._resolve(name, pid, local) is None
        separators = [i for i in self._top(lo, hi) if self.v[i] == ',']
        arrows = [i for i in self._top(lo, hi) if self.v[i] == '=>']
        if separators or arrows:
            start = lo
            for end in separators + [hi]:
                arrow = self._find(start, {'=>'}, end)
                if not self._fixed(start if arrow is None else arrow + 1, end, pid, local):
                    return False
                start = end + 1
            return True
        return False

    def _edges(self, expr):
        if 'edges' in expr:
            return expr['edges']
        lo, hi, refs = expr['lo'], expr['hi'], expr['refs']
        negative = []
        for i in range(lo, hi):
            if self.v[i] != 'not':
                continue
            j = i + 1
            while j < hi and self.v[j] == 'not':
                j += 1
            if j < hi and self.v[j] == '(' and j in self.close:
                end = self.close[j] + 1
            else:
                chain = self._chain(j, hi)
                end = chain[0] if chain else min(j + 1, hi)
            negative.append((i, end))
        def negated(pos):
            return any(a <= pos < b for a, b in negative)
        active, blocked, present = set(), set(), False
        for i in range(lo, hi - 1):
            if self.v[i] not in {'rising_edge', 'falling_edge'} or self.v[i + 1] != '(':
                continue
            end = self.close.get(i + 1)
            if end is None or end >= hi:
                continue
            positions = {r['pos'] for r in refs if i + 1 < r['pos'] < end}
            blocked.update(positions)
            if not negated(i):
                active.update(positions)
                present = True
        for event in (r for r in refs if r['attr'] == 'event'):
            blocked.add(event['pos'])
            containers = [(lo, hi)] + [(i + 1, j) for i, j in self.close.items()
                          if lo <= i < event['pos'] < j < hi]
            for a, b in sorted(containers, key=lambda p: p[1] - p[0]):
                a, b = self._strip(a, b)
                ops = [k for k in self._top(a, b) if self.v[k] in _CP_LOGIC]
                if not ops or any(self.v[k] != 'and' for k in ops):
                    continue
                start = a
                matches = []
                for end in ops + [b]:
                    c, d = self._strip(start, end)
                    eq = self._find(c, {'='}, d)
                    if eq is not None:
                        left = self._bare_span(expr, c, eq)
                        right = self._bare_span(expr, eq + 1, d)
                        if left and left['name'] == event['name'] and self._literal(eq + 1, d):
                            matches.append(left)
                        if right and right['name'] == event['name'] and self._literal(c, eq):
                            matches.append(right)
                    start = end + 1
                if matches:
                    blocked.update(r['pos'] for r in matches)
                    if not negated(event['pos']) and all(not negated(r['pos']) for r in matches):
                        active.add(event['pos'])
                        active.update(r['pos'] for r in matches)
                        present = True
                    break
        expr['edges'] = active, blocked, present
        return expr['edges']

    def _condition(self, expr):
        if 'condition' in expr:
            return expr['condition']
        active, blocked, _ = self._edges(expr)
        refs = [r for r in expr['refs'] if r['kind'] == 'element']
        result = {}
        for r in refs:
            p = r['pos']
            if p in active:
                result[p] = 'SEQUENCES'
            elif p in blocked:
                continue
            else:
                result[p] = 'SELECTS' if r['index'] else 'GATES'
        def visit(lo, hi):
            lo, hi = self._strip(lo, hi)
            if lo >= hi:
                return
            logical = [i for i in self._top(lo, hi) if self.v[i] in _CP_LOGIC]
            if logical:
                start = lo
                for end in logical + [hi]:
                    visit(start, end)
                    start = end + 1
                return
            comparison = self._find(lo, _CP_COMPARE, hi)
            if comparison is not None:
                left = [r for r in refs if lo <= r['pos'] < comparison and r['pos'] not in blocked]
                right = [r for r in refs if comparison < r['pos'] < hi and r['pos'] not in blocked]
                if left and right and len({r['name'] for r in left + right}) > 1:
                    for r in left + right:
                        if result.get(r['pos']) == 'GATES':
                            result[r['pos']] = 'CONSTRAINS'
                return
            if self.v[lo] == 'not':
                visit(lo + 1, hi)
            else:
                for i in self._top(lo, hi):
                    if self.v[i] == '(' and i in self.close:
                        visit(i + 1, self.close[i])
        visit(expr['lo'], expr['hi'])
        expr['condition'] = result
        return result

    @staticmethod
    def _pid(scopes):
        return next((g['start'] for g, _ in reversed(scopes) if g['kind'] == 'process'), None)

    def _new_group(self, kind, start, scopes, **extra):
        g = {'kind': kind, 'start': start, 'end': self.n - 1, 'pid': self._pid(scopes)}
        g.update(extra)
        self.groups.append(g)
        return g

    def _process_variables(self, lo, hi):
        result = {}
        for i in range(lo, hi):
            if self.v[i] != 'variable':
                continue
            colon = self._find(i + 1, {':', ';'}, hi)
            if colon is None or self.v[colon] != ':':
                continue
            end = self._find(colon + 1, {':=', ';'}, hi)
            if end is None:
                continue
            typ = ''.join(self.v[colon + 1:end])
            for name in self.v[i + 1:colon]:
                if _CP_ID.fullmatch(name):
                    result[name] = typ
        return result

    def _assignment(self, start, scopes, selector=None):
        chain = self._chain(start, self.n)
        if chain is None:
            return None
        op, path, _, _, _ = chain
        pid = self._pid(scopes)
        resolved = self._resolve(path, pid, self._locals(scopes))
        if resolved is None or op >= self.n or self.v[op] not in {'<=', ':='}:
            return None
        if (self.v[op] == ':=') != (resolved[0] == 'variable'):
            return None
        end = self._find(op + 1, {';'})
        if end is None:
            return None
        target = self._expr(start, op, pid, 'target', scopes)
        root = next((r for r in target['refs'] if r['pos'] == start), None)
        if root is None:
            return None
        stmt = {
            'start': start, 'end': end, 'pid': pid, 'scopes': tuple(scopes),
            'target': target, 'root': root, 'values': [], 'guards': [],
            'selector': None, 'rhs': (op + 1, end),
        }
        if selector is not None:
            stmt['selector'] = self._expr(*selector, pid, 'with', scopes)
        role = 'variable_rhs' if root['kind'] == 'variable' else 'rhs'
        cursor = op + 1
        if selector is not None:
            while cursor < end:
                when = self._find(cursor, {'when'}, end)
                if when is None:
                    break
                stmt['values'].append(self._expr(cursor, when, pid, role, scopes))
                comma = self._find(when + 1, {','}, end)
                cursor = end if comma is None else comma + 1
        else:
            while cursor < end:
                when = self._find(cursor, {'when'}, end)
                if when is None:
                    stmt['values'].append(self._expr(cursor, end, pid, role, scopes))
                    break
                stmt['values'].append(self._expr(cursor, when, pid, role, scopes))
                otherwise = self._find(when + 1, {'else'}, end)
                if otherwise is None:
                    stmt['guards'].append(self._expr(when + 1, end, pid, 'when', scopes))
                    break
                stmt['guards'].append(self._expr(when + 1, otherwise, pid, 'when', scopes))
                cursor = otherwise + 1
        for expr in [target] + stmt['values'] + stmt['guards'] + ([stmt['selector']] if stmt['selector'] else []):
            for r in expr['refs']:
                r['stmt'] = stmt
                if expr is target and r is not root:
                    r['role'] = 'lhs_index'
        self.statements.append(stmt)
        return end + 1

    def scan(self):
        scopes = []
        i = 0
        while i < self.n:
            value = self.v[i]
            if value == 'end':
                word = self.v[i + 1] if i + 1 < self.n else ''
                kind = {'if': 'if', 'case': 'case', 'loop': 'loop', 'generate': 'generate', 'process': 'process'}.get(word)
                semi = self._find(i + 1, {';'})
                if kind:
                    for k in range(len(scopes) - 1, -1, -1):
                        g, arm = scopes[k]
                        if g['kind'] == kind:
                            g['end'] = i if semi is None else semi
                            if kind == 'if':
                                g['arms'][arm]['end'] = i - 1
                            del scopes[k:]
                            break
                i = i + 1 if semi is None else semi + 1
                continue
            if value in {'function', 'procedure'}:
                # Do not interpret a subprogram's local statements as process flow.
                semi = self._find(i + 1, {';'})
                is_pos = self._find(i + 1, {'is', ';'})
                if is_pos is not None and self.v[is_pos] == 'is':
                    closing = next((k for k in range(is_pos + 1, self.n - 1)
                                    if self.v[k] == 'end' and self.v[k + 1] == value), None)
                    if closing is not None:
                        semi = self._find(closing + 2, {';'})
                i = i + 1 if semi is None else semi + 1
                continue
            if value == 'process':
                begin = self._find(i + 1, {'begin'})
                if begin is not None:
                    self.variables[i] = self._process_variables(i + 1, begin)
                    g = self._new_group('process', i, scopes)
                    scopes.append((g, 0))
                    i = begin + 1
                    continue
            if value == 'with':
                select = self._find(i + 1, {'select', ';'})
                if select is not None and self.v[select] == 'select':
                    end = self._assignment(select + 1, scopes, (i + 1, select))
                    if end is not None:
                        i = end
                        continue
            if value == 'if':
                then = self._find(i + 1, {'then', 'generate', ';'})
                if then is not None and self.v[then] in {'then', 'generate'}:
                    if self.v[then] == 'generate':
                        scopes.append((self._new_group('generate', i, scopes), 0))
                    else:
                        g = self._new_group('if', i, scopes, arms=[])
                        scopes.append((g, 0))
                        cond = self._expr(i + 1, then, g['pid'], 'if', scopes)
                        g['arms'].append({'tag': 'then', 'start': i, 'end': self.n - 1, 'expr': cond})
                    i = then + 1
                    continue
            if value in {'elsif', 'else'} and scopes and scopes[-1][0]['kind'] == 'if':
                g, old = scopes[-1]
                g['arms'][old]['end'] = i - 1
                arm = len(g['arms'])
                scopes[-1] = g, arm
                if value == 'elsif':
                    then = self._find(i + 1, {'then', ';'})
                    if then is None or self.v[then] != 'then':
                        i += 1
                        continue
                    cond = self._expr(i + 1, then, g['pid'], 'if', scopes)
                    end = then + 1
                else:
                    cond, end = None, i + 1
                g['arms'].append({'tag': value, 'start': i, 'end': self.n - 1, 'expr': cond})
                i = end
                continue
            if value == 'case':
                is_pos = self._find(i + 1, {'is', 'generate', ';'})
                if is_pos is not None and self.v[is_pos] == 'is':
                    g = self._new_group('case', i, scopes)
                    scopes.append((g, 0))
                    g['expr'] = self._expr(i + 1, is_pos, g['pid'], 'case', scopes)
                    i = is_pos + 1
                    continue
            if value == 'when' and scopes and scopes[-1][0]['kind'] == 'case':
                arrow = self._find(i + 1, {'=>', ';'})
                if arrow is not None and self.v[arrow] == '=>':
                    g, arm = scopes[-1]
                    scopes[-1] = g, arm + 1
                    i = arrow + 1
                    continue
            if value in {'for', 'while', 'loop'}:
                opening = i if value == 'loop' else self._find(i + 1, {'loop', 'generate', ';'})
                if opening is not None and self.v[opening] in {'loop', 'generate'}:
                    kind = 'loop' if self.v[opening] == 'loop' else 'generate'
                    param = self.v[i + 1] if value == 'for' and i + 1 < opening else None
                    if param:
                        self.parameters.add(param)
                    scopes.append((self._new_group(kind, i, scopes, param=param), 0))
                    i = opening + 1
                    continue
            if value in {'assert', 'report', 'wait', 'return', 'exit', 'next'}:
                semi = self._find(i + 1, {';'})
                if semi is not None:
                    i = semi + 1
                    continue
            end = self._assignment(i, scopes)
            if end is not None:
                i = end
            elif value == '(' and i in self.close:
                i = self.close[i] + 1
            else:
                i += 1

    def _context_matches(self, o, ref):
        # Source offsets distinguish same-line then/else arms; Context supplies
        # the branch identity. End-line padding may include blank source lines.
        for kind, first, last in o['fr']:
            if kind.startswith('branch:'):
                tag = kind.split(':', 1)[1]
                if not any(g['kind'] == 'if' and arm < len(g['arms'])
                           and g['arms'][arm]['tag'] == tag
                           and self.tokens[g['arms'][arm]['start']].line == first
                           for g, arm in ref['scopes']):
                    return False
            elif kind == 'case':
                if not any(g['kind'] == 'case' and self.tokens[g['start']].line == first
                           and self.tokens[g['end']].line == last
                           for g, _ in ref['scopes']):
                    return False
        return True

    @staticmethod
    def _site_matches(o, ref):
        sites, role = o['sites'], ref['role']
        if sites & _CP_FORBIDDEN:
            return False
        if 'ATTR_PREFIX' in sites and ref['attr'] != 'event':
            return False
        if role == 'target':
            stmt = ref.get('stmt')
            return bool(sites & LHS) or bool(not sites and stmt and (stmt['selector'] or stmt['guards']))
        if sites & LHS:
            return False
        if role == 'if':
            return bool(sites & {'IF_COND', 'EDGE_CHECK'}) or ('INDEX' in sites and ref['index'])
        if role == 'when':
            return 'WHEN_COND' in sites or ('INDEX' in sites and ref['index'])
        if role == 'case':
            return 'CASE_EXPR' in sites or ('INDEX' in sites and ref['index'])
        if role == 'with':
            return not bool(sites & {'CASE_COND', 'WHEN_EXPR', 'WHEN_COND'})
        if role == 'lhs_index':
            return 'INDEX' in sites
        if role == 'variable_rhs':
            return not sites or bool(sites & (RHS | ADDON | {'VAR_RHS_OPERAND'}))
        return bool(sites & (RHS | ADDON))

    def bind(self):
        by_name = {}
        for ref in self.references:
            if ref['kind'] == 'element':
                by_name.setdefault(ref['name'], []).append(ref)
        seen = set()
        for o in self.occ:
            identity = o['el'], o['id']
            if identity in seen:
                continue
            lo, hi = o['bounds']
            candidates = [r for r in by_name.get(o['name'], [])
                          if r['occ'] is None and lo <= self.tokens[r['pos']].line <= hi
                          and self._site_matches(o, r) and self._context_matches(o, r)]
            if candidates:
                ref = min(candidates, key=lambda r: r['pos'])
                ref['occ'] = o
                seen.add(identity)

    def _add(self, ref, target, typ):
        y, x = ref.get('occ'), target['root'].get('occ')
        if y is None or x is None:
            return
        key = y['el'], y['id'], x['el'], x['id']
        old = self.best.get(key)
        if old is None or _CP_PRIORITY[typ] < _CP_PRIORITY[old]:
            self.best[key] = typ

    def _controls(self, stmt, target, seen):
        for g, arm in stmt['scopes']:
            if g['kind'] == 'case':
                for r in g['expr']['refs']:
                    if r['kind'] == 'element' and not r['attr']:
                        self._add(r, target, 'SELECTS')
            elif g['kind'] == 'if':
                arms = g['arms']
                edge_arms = {i for i, a in enumerate(arms)
                             if a['expr'] is not None and self._edges(a['expr'])[2]}
                for i, a in enumerate(arms[:arm + 1]):
                    expr = a['expr']
                    if expr is None:
                        continue
                    reset_arm = any(j > i for j in edge_arms)
                    if i != arm and reset_arm:
                        continue  # Negated reset arms never become gates.
                    fixed = reset_arm and i == arm and self._fixed(
                        *stmt['rhs'], stmt['pid'], self._locals(stmt['scopes']))
                    types = self._condition(expr)
                    for r in expr['refs']:
                        typ = types.get(r['pos'])
                        if typ is None or (typ == 'SEQUENCES' and i != arm):
                            continue
                        if fixed and typ != 'SEQUENCES':
                            typ = 'RESETS'
                        self._add(r, target, typ)
        for expr in stmt['guards']:
            types = self._condition(expr)
            for r in expr['refs']:
                typ = types.get(r['pos'])
                if typ is not None:
                    self._add(r, target, typ)
        if stmt['selector'] is not None:
            for r in stmt['selector']['refs']:
                if r['kind'] == 'element' and not r['attr']:
                    self._add(r, target, 'SELECTS')
        for r in stmt['target']['refs']:
            if r is stmt['root']:
                continue
            if r['kind'] == 'variable':
                self._forward(r, stmt, target, 'select', seen)
            elif not r['attr']:
                self._add(r, target, 'SELECTS')

    @staticmethod
    def _prefix(a, b):
        return a == b or b.startswith(a + '.')

    @staticmethod
    def _branches(stmt):
        return {g['start']: arm for g, arm in stmt['scopes'] if g['kind'] in {'if', 'case'}}

    @staticmethod
    def _loops(stmt):
        return {g['start'] for g, _ in stmt['scopes'] if g['kind'] == 'loop'}

    def _definitions(self, ref, consumer):
        candidates = []
        consumer_branches = self._branches(consumer)
        consumer_loops = self._loops(consumer)
        for stmt in self.statements:
            root = stmt['root']
            if root['kind'] != 'variable' or stmt['pid'] != consumer['pid']:
                continue
            if not (self._prefix(ref['path'], root['path']) or self._prefix(root['path'], ref['path'])):
                continue
            common_loop = bool(consumer_loops & self._loops(stmt))
            if stmt['start'] >= consumer['start'] and not common_loop:
                continue
            branches = self._branches(stmt)
            if not common_loop and any(k in consumer_branches and consumer_branches[k] != v for k, v in branches.items()):
                continue
            candidates.append(stmt)
        result = []
        for stmt in candidates:
            killed = False
            for later in candidates:
                if not stmt['start'] < later['start'] < consumer['start']:
                    continue
                if self._loops(stmt) or self._loops(later) or later['root']['indexed']:
                    continue  # Every loop-body definition remains a contributor.
                if not self._prefix(later['root']['path'], stmt['root']['path']):
                    continue
                if all(consumer_branches.get(k) == v for k, v in self._branches(later).items()):
                    killed = True
                    break
            if not killed:
                result.append(stmt)
        return result

    def _forward(self, ref, consumer, target, mode, seen):
        for definition in self._definitions(ref, consumer):
            key = definition['start'], mode
            if key in seen:
                continue
            next_seen = seen | {key}
            self._controls(definition, target, next_seen)
            self._values(definition, target, mode, True, next_seen)

    def _values(self, stmt, target, mode='top', forwarded=False, seen=frozenset()):
        ordinary = stmt['selector'] is None and not stmt['guards'] and len(stmt['values']) == 1
        target_bit = self._bit(target['root'])
        for expr in stmt['values']:
            bare = self._bare(expr)
            bare_not = self._bare(expr, True)
            gates = self._gates(expr) if ordinary else set()
            for ref in expr['refs']:
                if ref['attr']:
                    continue
                select = mode == 'select' or ref['index']
                gate = ordinary and target_bit and (
                    (mode == 'top' and ref['pos'] in gates) or
                    (mode == 'gate' and ref is bare_not)
                )
                if ref['kind'] == 'variable':
                    if select:
                        child_mode = 'select'
                    elif gate:
                        child_mode = 'gate'
                    elif ordinary and ref is bare and mode == 'top':
                        child_mode = 'top'
                    else:
                        child_mode = 'nested'
                    self._forward(ref, stmt, target, child_mode, seen)
                    continue
                if select:
                    typ = 'SELECTS'
                elif gate and self._bit(ref):
                    typ = 'GATES'
                elif not forwarded and ordinary and mode == 'top' and ref is bare and ref['exact']:
                    typ = 'CARRIES'
                else:
                    typ = 'SOURCES'
                self._add(ref, target, typ)

    def write(self):
        for stmt in self.statements:
            if stmt['root']['kind'] != 'element' or stmt['root']['occ'] is None:
                continue
            try:
                self._controls(stmt, stmt, frozenset())
                self._values(stmt, stmt)
            except Exception:
                # A malformed expression must not discard other statements.
                continue
        return {key + (typ,) for key, typ in self.best.items()}


def code_pairs(ent) -> set:
    """Return (Y, y_occurrence_id, X, x_occurrence_id, DRIVING_TYPE).

    No source/profile mutation and no I/O. Unparseable or unbound occurrences
    produce no invented endpoints. Selection of one type is per occurrence pair,
    not per element pair, and self-relationships are retained.
    """
    writer = None
    try:
        if not isinstance(ent, dict):
            return set()
        writer = _CPWriter(ent)
        writer.scan()
        writer.bind()
        return writer.write()
    except Exception:
        return set() if writer is None else {key + (typ,) for key, typ in writer.best.items()}


def self_test():
    """Opt-in synthetic regressions; no files, printing, or import-time execution."""
    def fixture(source, types, rows):
        lines = source.splitlines()
        ent = {
            'src': '\n'.join(f'{i} | {line}' for i, line in enumerate(lines, 1)),
            'ports': [{'name': n, 'type': t} for n, t in types.items()],
            'signals': [], 'profile': {},
        }
        for name, ident, line, sites in rows:
            ent['profile'].setdefault(name, []).append({
                'Occurrence ID': ident, 'Occurrence Lines': line,
                'Line Text': lines[line - 1], 'SITE Tagged': sites,
                'Context': '', 'Path': [],
            })
        return ent

    bit = 'std_ulogic'
    vector = 'std_ulogic_vector(7 downto 0)'
    ent = fixture('a <= x; b <= y;', {n: bit for n in ('a', 'b', 'x', 'y')}, [
        ('a', 1, 1, ['LHS_CONC']), ('b', 1, 1, ['LHS_CONC']),
        ('x', 1, 1, ['DIRR_ASS']), ('y', 1, 1, ['DIRR_ASS']),
    ])
    assert code_pairs(ent) == {('x', 1, 'a', 1, 'CARRIES'), ('y', 1, 'b', 1, 'CARRIES')}

    ent = fixture('q <= en and (\n  a xor b);', {n: bit for n in ('q', 'en', 'a', 'b')}, [
        ('q', 1, 1, ['LHS_CONC']), ('en', 1, 1, ['RHS_OPERAND']),
        ('a', 1, 2, ['RHS_OPERAND']), ('b', 1, 2, ['RHS_OPERAND']),
    ])
    assert code_pairs(ent) == {
        ('en', 1, 'q', 1, 'GATES'), ('a', 1, 'q', 1, 'SOURCES'), ('b', 1, 'q', 1, 'SOURCES'),
    }

    ent = fixture("process(all) begin\nif s = '0' then q <= R; else q <= T; end if;\nend process;",
                  {'s': bit, 'q': vector}, [
        ('s', 1, 2, ['IF_COND']), ('q', 1, 2, ['LHS_PROC']), ('q', 2, 2, ['LHS_PROC']),
    ])
    assert code_pairs(ent) == {('s', 1, 'q', 1, 'GATES'), ('s', 1, 'q', 2, 'GATES')}

    ent = fixture("q <= '1' when ((a and b) = c) and (arr(to_integer(idx)) = '1') else '0';",
                  {'q': bit, 'a': vector, 'b': vector, 'c': vector, 'arr': vector, 'idx': vector}, [
        ('q', 1, 1, ['LHS_CONC']), ('a', 1, 1, ['WHEN_COND']),
        ('b', 1, 1, ['WHEN_COND']), ('c', 1, 1, ['WHEN_COND']),
        ('arr', 1, 1, ['WHEN_COND']), ('idx', 1, 1, ['WHEN_COND', 'INDEX']),
    ])
    pairs = code_pairs(ent)
    assert ('a', 1, 'q', 1, 'CONSTRAINS') in pairs
    assert ('b', 1, 'q', 1, 'CONSTRAINS') in pairs
    assert ('c', 1, 'q', 1, 'CONSTRAINS') in pairs
    assert ('arr', 1, 'q', 1, 'GATES') in pairs
    assert ('idx', 1, 'q', 1, 'SELECTS') in pairs

    ent = fixture('process(all)\nvariable v : std_ulogic_vector(7 downto 0);\nbegin\n'
                  'v := a;\nfor i in 0 to 7 loop\nv := v or b;\nend loop;\n'
                  'if v = ZERO then z <= ZERO; end if;\nq <= v;\nend process;',
                  {n: vector for n in ('a', 'b', 'q', 'z')}, [
        ('a', 1, 4, []), ('b', 1, 6, ['VAR_RHS_OPERAND']),
        ('z', 1, 8, ['LHS_PROC']), ('q', 1, 9, ['LHS_PROC']),
    ])
    assert code_pairs(ent) == {('a', 1, 'q', 1, 'SOURCES'), ('b', 1, 'q', 1, 'SOURCES')}

    ent = fixture("process(clk, rst) begin\nif rst = '0' then q <= '0';\n"
                  "elsif rising_edge(clk) then\nif en = '1' then q <= '0'; end if;\n"
                  'end if;\nend process;', {n: bit for n in ('clk', 'rst', 'en', 'q')}, [
        ('rst', 1, 2, ['IF_COND']), ('q', 1, 2, ['LHS_PROC']),
        ('clk', 1, 3, ['EDGE_CHECK']), ('en', 1, 4, ['IF_COND']), ('q', 2, 4, ['LHS_PROC']),
    ])
    assert code_pairs(ent) == {
        ('rst', 1, 'q', 1, 'RESETS'), ('clk', 1, 'q', 2, 'SEQUENCES'), ('en', 1, 'q', 2, 'GATES'),
    }

    ent = fixture('with sel select\nq <= a when ZERO,\nb when others;',
                  {n: bit for n in ('sel', 'q', 'a', 'b')}, [
        ('sel', 1, 1, []), ('q', 1, 2, ['LHS_CONC']),
        ('a', 1, 2, ['WHEN_EXPR']), ('b', 1, 3, ['WHEN_EXPR']),
    ])
    assert code_pairs(ent) == {
        ('sel', 1, 'q', 1, 'SELECTS'), ('a', 1, 'q', 1, 'SOURCES'), ('b', 1, 'q', 1, 'SOURCES'),
    }
    assert code_pairs(None) == set()
    assert code_pairs({'profile': {'broken': [None, {}]}, 'src': None}) == set()
    return True
