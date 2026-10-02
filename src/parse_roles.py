"""Algorithm 1 line 4, role-annotated -- driver for `prompts_parse_v2`.

WRITES A SEPARATE DIRECTORY. `parsed_tuning18/` is read by the scorer (`eval_assets.
load_closed`), by `validate_primary`, and by every decision cell in the v2 notebook. Every
run recorded in ABLATION_LOG_V2.md was validated against it. Re-annotating in place would
silently change the closed set under all of them, so this module reads that directory and
writes `parsed_roles_tuning18/`.

THE CLOSED SET IS COPIED, NOT RE-DERIVED. `rtl_parse.parse_rtl_file` is deliberately NOT
called here. The element list -- entity, name, type, dir -- is taken verbatim from the
cached parse, and only the annotation fields are new. `verify_against_cache()` asserts the
(entity, name) sets are identical and is called on every write. That makes the arm a change
of ANNOTATION only: if the two directories disagreed by even one element, an emission delta
could be a closed-set delta instead, and the arm would measure nothing.

`_issues` -- the per-module record of parse defects -- is a TOP-LEVEL key and therefore
never reaches the prompt: `build_asset_user` serialises `parsed["ports"]` and
`parsed["signals"]` and nothing else. It is on disk so `role_report()` can aggregate it.

WHAT COMES BACK, per element, on top of the cached fields:
    function      <= 12 words, as before -- so INPUT_BLOCKS["function"] still means something
    roles         1-3 labels, roles[0] is the LEAD role
    relationship  {"verb", "object"} or null
    evidence      <= 15 words of RTL justification

READ THE REPORT BEFORE PAYING FOR A GENERATION RUN. `role_report()` prints the positive-role
rate over the closed set. The v1 log records twice that a free-standing checklist becomes a
generator; here the checklist is shown to the parser rather than to LLMasset, so it cannot
directly inflate emission -- but if it marks most of the closed set positive, the asset
stage is handed a design in which everything looks security-relevant, and the arm's emission
delta will be about the parser rather than about the closed set. The ground truth's own rate
over the 15 scored modules is 7.2% (113 of 1572), and the taxonomy's negative section exists
precisely so the annotator can say "ordinary". A positive rate far above the low tens of
percent is a defect in the parse, not a finding about the design.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from prompts_parse_v2 import (ALL_ROLES, NEGATIVE_ROLES, POSITIVE_ROLES, RELATIONSHIPS,
                              PARSE_PORTS_ROLES_SYSTEM, PARSE_SIGNALS_ROLES_SYSTEM)

CACHE_DIR = Path("parsed_tuning18")
ROLES_DIR = Path("parsed_roles_tuning18")

# Assigned when the annotator returns no label this module recognises. NOT a member of the
# taxonomy on purpose: it must be visible in the report rather than blending into the
# negative roles, because "the parse failed here" and "this element is ordinary" are
# different facts and only one of them is about the design.
FALLBACK_ROLE = "UNCLASSIFIED"

_ROLE_SET = set(ALL_ROLES)
_POS_SET = set(POSITIVE_ROLES)
_NEG_SET = set(NEGATIVE_ROLES)
_VERB_SET = set(RELATIONSHIPS)


def _loads(txt):
    """Same salvage path as the notebook's parser: a truncated tail should cost one batch,
    not one module."""
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def _annot_user(stem, entity, rtl, elems, key):
    """The user message.

    NO REAL IDENTIFIER APPEARS HERE. `prompts._annot_user`'s equivalent quotes
    'ctrl.buf_req' and 'host_req_i.stb' as dotted-name examples; both are declared in the
    evaluation set (cache and bus respectively), and this stage feeds the asset stage, so
    the v1 standing rule applies. The dot convention is stated instead of demonstrated.
    """
    return (f"MODULE: {stem}\nENTITY: {entity}\n\n"
            f"AUTHORITATIVE {key.upper()} of entity '{entity}' -- ground truth from the RTL. "
            f"Annotate all, add none, drop none. A name containing a dot is a field of a "
            f"record-typed element and must be reproduced with the dot exactly as given:\n"
            f"{json.dumps(elems, indent=2)}\n\n"
            f"VHDL SOURCE:\n{rtl}\n\n"
            f"Return the annotated {key} as a JSON object using the required schema.")


def _clean_roles(raw, issues, where):
    """-> list of 1-3 known labels. Unknown labels are dropped and counted, never guessed at.

    An unknown label is a parse defect and must not be smuggled into the asset stage: the
    RP arm's prompt tells the model that roles beginning ORDINARY_/GENERIC_ carry a specific
    meaning, and an invented label would be read against that rule.
    """
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raw = []
    out = []
    for r in raw:
        if not isinstance(r, str):
            continue
        r = r.strip().upper()
        if r in _ROLE_SET:
            if r not in out:
                out.append(r)
        elif r:
            issues["unknown_role"][r] += 1
    if not out:
        issues["fallback"][where] += 1
        return [FALLBACK_ROLE]
    if len(out) > 3:
        issues["over_three"][where] += 1
        out = out[:3]
    return out


def _clean_rel(raw, roles, issues, where):
    """-> {"verb","object"} or None. A negative lead role forces None: the taxonomy defines
    the relationship as a link to a security-relevant object, so an element the annotator
    judged ordinary has nothing to link to, and letting both through would put a
    self-contradicting pair in front of the asset stage."""
    if roles and roles[0] in _NEG_SET:
        if isinstance(raw, dict) and raw.get("verb"):
            issues["rel_on_negative"][where] += 1
        return None
    if not isinstance(raw, dict):
        return None
    verb = str(raw.get("verb", "")).strip().upper()
    obj = str(raw.get("object", "")).strip()
    if verb not in _VERB_SET:
        if verb:
            issues["unknown_verb"][verb] += 1
        return None
    if not obj:
        return None
    return {"verb": verb, "object": obj}


def _annotate(complete, system, stem, entity, rtl, elems, key, issues,
              batch=40, max_tokens=16384):
    """Annotate in batches so a large record-expanded list cannot overflow the output and
    truncate the JSON. Batch 40 rather than the v1 stage's 50: this schema returns roles,
    a relationship and evidence per element, roughly four times the v1 payload."""
    ann = {}
    for i in range(0, len(elems), batch):
        chunk = elems[i:i + batch]
        txt = complete(system, _annot_user(stem, entity, rtl, chunk, key),
                       max_tokens=max_tokens)
        got = _loads(txt).get(key, [])
        for a in got:
            if isinstance(a, dict) and "name" in a:
                ann[a["name"]] = a
        if not got:
            issues["dead_batch"][f"{stem}/{entity}/{key}"] += 1
            print(f"    [annot warn] {stem}/{entity} {key} batch {i // batch}: "
                  f"{len(chunk)} elems left unannotated")
    return ann


def annotate_module(complete, stem, rtl_path, overwrite=False):
    """Read the cached closed set, annotate it, write parsed_roles_tuning18/<stem>.json."""
    ROLES_DIR.mkdir(exist_ok=True)
    outp = ROLES_DIR / f"{stem}.json"
    if outp.exists() and not overwrite:
        return json.loads(outp.read_text(encoding="utf-8"))

    cached = json.loads((CACHE_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    # Comments are KEPT: both parser prompts are told to infer function from name,
    # in-source comments and usage. This is the one stage that must not see stripped RTL.
    rtl = Path(rtl_path).read_text(encoding="utf-8", errors="ignore")

    issues = {k: Counter() for k in ("unknown_role", "unknown_verb", "fallback",
                                     "over_three", "rel_on_negative", "dead_batch")}
    by_entity = {}
    for e in cached["ports"] + cached["signals"]:
        by_entity.setdefault(e["entity"], {"ports": [], "signals": []})
    for e in cached["ports"]:
        by_entity[e["entity"]]["ports"].append(e)
    for e in cached["signals"]:
        by_entity[e["entity"]]["signals"].append(e)

    ports_out, signals_out = [], []
    for entity, groups in by_entity.items():
        # The annotator is shown name/type/dir only. `function` from the v1 parse is
        # deliberately withheld: showing it would anchor this annotation to the old one and
        # the roles would describe that sentence rather than the RTL.
        pin = [{k: v for k, v in e.items() if k in ("name", "dir", "type")}
               for e in groups["ports"]]
        sin = [{k: v for k, v in e.items() if k in ("name", "type")}
               for e in groups["signals"]]
        pa = _annotate(complete, PARSE_PORTS_ROLES_SYSTEM, stem, entity, rtl, pin,
                       "ports", issues) if pin else {}
        sa = _annotate(complete, PARSE_SIGNALS_ROLES_SYSTEM, stem, entity, rtl, sin,
                       "signals", issues) if sin else {}

        for e in groups["ports"]:
            a = pa.get(e["name"], {})
            where = f"{stem}/{e['name']}"
            roles = _clean_roles(a.get("roles"), issues, where)
            ports_out.append({**e,
                              "function": a.get("function", "unclear from RTL"),
                              "roles": roles,
                              "relationship": _clean_rel(a.get("relationship"), roles,
                                                         issues, where),
                              "evidence": a.get("evidence", "")})
        for e in groups["signals"]:
            a = sa.get(e["name"], {})
            where = f"{stem}/{e['name']}"
            roles = _clean_roles(a.get("roles"), issues, where)
            signals_out.append({**e,
                                "kind": a.get("kind", e.get("kind", "signal")),
                                "function": a.get("function", "unclear from RTL"),
                                "roles": roles,
                                "relationship": _clean_rel(a.get("relationship"), roles,
                                                           issues, where),
                                "evidence": a.get("evidence", "")})

    parsed = {"module": stem, "entities": cached["entities"],
              "ports": ports_out, "signals": signals_out,
              "_issues": {k: dict(v) for k, v in issues.items() if v}}
    verify_against_cache(parsed, cached, stem)
    outp.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    return parsed


def annotate_all(complete, modules, overwrite=False):
    """-> {stem: parsed}. `modules` is the notebook's [(stem, path), ...].

    Per-module try/except mirrors the v1 parse cell: one module whose annotation fails
    should not cost the other seventeen, and a module that raises simply has no entry, so
    a later `load_all()` reports it as missing rather than as empty.
    """
    out = {}
    for stem, path in modules:
        try:
            p = annotate_module(complete, stem, path, overwrite=overwrite)
            out[stem] = p
            npos = sum(1 for e in p["ports"] + p["signals"] if e["roles"][0] in _POS_SET)
            n = len(p["ports"]) + len(p["signals"])
            print(f"[ok  ] {stem:24s} {len(p['ports'])}p / {len(p['signals'])}s   "
                  f"positive lead role {npos}/{n} ({100 * npos / n if n else 0:.0f}%)")
        except Exception as e:
            print(f"[err ] {stem:24s} {type(e).__name__}: {e}")
    return out


def load_all(modules, roles_dir=None):
    """-> {stem: parsed} from disk, no API calls. Use this to hand `parsed_all` to the
    generation cell on a re-run."""
    d = Path(roles_dir or ROLES_DIR)
    out = {}
    for stem, _ in modules:
        f = d / f"{stem}.json"
        if f.exists():
            out[stem] = json.loads(f.read_text(encoding="utf-8"))
        else:
            print(f"[miss] {stem}: no {f}")
    return out


def verify_against_cache(parsed, cached, stem):
    """The invariant the whole arm rests on: same elements, same order, same fields.

    Raises rather than warns. A drift here turns an annotation arm into an
    annotation-plus-closed-set arm, and no amount of downstream care recovers the
    attribution once the run is paid for.
    """
    for key in ("ports", "signals"):
        a = [(e["entity"], e["name"]) for e in cached[key]]
        b = [(e["entity"], e["name"]) for e in parsed[key]]
        assert a == b, (
            f"{stem}: {key} closed set differs from {CACHE_DIR}/{stem}.json -- "
            f"{len(a)} cached vs {len(b)} annotated; "
            f"missing {sorted(set(a) - set(b))[:5]}, extra {sorted(set(b) - set(a))[:5]}")
    for key in ("ports", "signals"):
        for c, p in zip(cached[key], parsed[key]):
            for f in ("type", "dir"):
                if f in c:
                    assert c[f] == p.get(f), \
                        f"{stem}: {c['name']} field {f!r} changed: {c[f]!r} -> {p.get(f)!r}"


# ------------------------------------------------------------------- report ---

def role_report(stems=None, roles_dir=None):
    """The gate. Print the positive-role rate and everything that would explain it.

    Read this BEFORE running the RP arm. What each line is for:

      positive rate   the share of the closed set carrying a positive LEAD role. The
                      reference's own asset rate over the 15 scored modules is 7.2%.
                      A rate in the high tens of percent means the annotator treated the
                      vocabulary as a menu to fill, and the RP arm would measure that.
      dotted-port     the same rate restricted to dotted PORT fields -- 58.1% of the closed
                      set, and holding 0 of the 30 dotted ground-truth assets. A-03's rule
                      forbids emitting any of them, so a high positive rate here is pure
                      noise handed to the asset stage.
      vocabulary use  how many of the 152 positive labels ever fire. A handful of labels
                      doing all the work means most of the prompt is dead weight; a long
                      flat tail means the annotator is reaching for specificity it cannot
                      support from the RTL.
      issues          parse defects, not findings. Any non-zero `fallback` or `dead_batch`
                      count means elements reached the asset stage unannotated.
    """
    d = Path(roles_dir or ROLES_DIR)
    files = sorted(d.glob("*.json")) if stems is None else [d / f"{s}.json" for s in stems]
    if not files:
        print(f"no annotated parses in {d}/ -- run annotate_module() first")
        return

    tot = Counter()
    lead = Counter()
    per_module = []
    issues = Counter()
    for f in files:
        p = json.loads(f.read_text(encoding="utf-8"))
        n = pos = dot_p = dot_p_pos = rel = 0
        for kind, elems in (("port", p["ports"]), ("signal", p["signals"])):
            for e in elems:
                n += 1
                r0 = e["roles"][0]
                lead[r0] += 1
                for r in e["roles"]:
                    tot[r] += 1
                is_pos = r0 in _POS_SET
                pos += is_pos
                rel += e.get("relationship") is not None
                if kind == "port" and "." in e["name"]:
                    dot_p += 1
                    dot_p_pos += is_pos
        for k, v in (p.get("_issues") or {}).items():
            issues[k] += sum(v.values())
        per_module.append((f.stem, n, pos, dot_p, dot_p_pos, rel))

    N = sum(r[1] for r in per_module)
    P = sum(r[2] for r in per_module)
    DP = sum(r[3] for r in per_module)
    DPP = sum(r[4] for r in per_module)
    R = sum(r[5] for r in per_module)

    print(f"{'module':28} {'elems':>6} {'pos':>6} {'pos%':>6} {'dotP':>6} {'dotP+':>6} {'rel%':>6}")
    for stem, n, pos, dp, dpp, rel in per_module:
        print(f"{stem:28} {n:6} {pos:6} {100*pos/n if n else 0:6.1f} "
              f"{dp:6} {dpp:6} {100*rel/n if n else 0:6.1f}")
    print(f"{'TOTAL':28} {N:6} {P:6} {100*P/N if N else 0:6.1f} "
          f"{DP:6} {DPP:6} {100*R/N if N else 0:6.1f}")

    print(f"\npositive LEAD role : {P}/{N} = {100*P/N if N else 0:.1f}%"
          f"   (ground-truth asset rate over the 15 scored modules: 7.2%)")
    print(f"dotted PORT fields : {DPP}/{DP} = {100*DPP/DP if DP else 0:.1f}% positive"
          f"   (0 of 30 dotted ground-truth assets are port fields)")
    used_pos = {r for r in lead if r in _POS_SET}
    print(f"vocabulary in use  : {len(used_pos)}/{len(POSITIVE_ROLES)} positive labels "
          f"appear as a LEAD role; {len({r for r in lead if r in _NEG_SET})}/"
          f"{len(NEGATIVE_ROLES)} negative labels do")
    if lead.get(FALLBACK_ROLE):
        print(f"UNCLASSIFIED       : {lead[FALLBACK_ROLE]} element(s) came back without a "
              f"usable label -- re-run those modules before generating")
    print("\ntop 12 LEAD roles:")
    for r, c in lead.most_common(12):
        tag = "+" if r in _POS_SET else ("-" if r in _NEG_SET else "?")
        print(f"  {tag} {r:44} {c:5}  {100*c/N if N else 0:5.1f}%")
    if issues:
        print("\nparse issues (defects, not findings):")
        for k, v in sorted(issues.items()):
            print(f"  {k:18} {v}")
