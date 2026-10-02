export const meta = {
  name: 'review-run6-tags-roles',
  description: 'Independent review of SITE tags and Roles in run 6 (trng/cache), then adversarial verification of every finding',
  phases: [
    { title: 'Review', detail: 'one reviewer per entity chunk: tags and Roles against the rulebook and the source' },
    { title: 'Verify', detail: 'one skeptic per chunk re-derives every finding from source and rulebook' },
  ],
}

const REPO = 'E:/jobs/ff/test/Prepoison_subset/bahavioral_patterns_of_assets'
const RULEBOOK = REPO + '/annotation_pack_elements/occurrence_prompts_v2/rulebook.json'
const RULES = REPO + '/annotation_pack_elements/occurrence_prompts_v2/annotate_rules.md'
const DIR = '<session scratchpad>/run6/review'

const CATEGORIES = ['tag_wrong', 'tag_missing', 'role_contradicts_tags', 'role_wrong_fact', 'role_missing_required_detail',
  'role_purpose_word', 'role_line_number', 'role_does_not_tell_apart', 'rulebook_ambiguity']

const FINDINGS = {
  type: 'object',
  properties: {
    entries_reviewed: { type: 'integer' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          element: { type: 'string' },
          id: { type: 'integer' },
          line: { type: 'integer' },
          category: { type: 'string', enum: CATEGORIES },
          found: { type: 'string' },
          expected: { type: 'string' },
          rule_quote: { type: 'string', description: 'the deciding rulebook or annotate_rules sentence, word for word' },
          source_quote: { type: 'string', description: 'the source line(s) with line numbers' },
        },
        required: ['element', 'id', 'line', 'category', 'found', 'expected', 'rule_quote', 'source_quote'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['entries_reviewed', 'findings', 'notes'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          element: { type: 'string' },
          id: { type: 'integer' },
          line: { type: 'integer' },
          category: { type: 'string' },
          verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'RULEBOOK_AMBIGUOUS'] },
          verified_category: { type: 'string', enum: CATEGORIES.concat(['none']) },
          corrected_expected: { type: 'string' },
          reason: { type: 'string' },
        },
        required: ['element', 'id', 'line', 'category', 'verdict', 'verified_category', 'corrected_expected', 'reason'],
      },
    },
  },
  required: ['verdicts'],
}

const COMMON = `
You are checking the output of an LLM annotator of VHDL (the NEORV32 processor). Each entry is one occurrence of one
closed-set element (a port, a signal, or a field written <base>.<field>) with a list of SITE tags and a short Role.

Files (read them with your tools; do not guess their content):
  - Annotation rules: ${RULES}  (read section F SITE-DISAMBIGUATION RULES, section G STRUCTURE AND ROLE, section H,
    and section M CHECKS; section D is about structures, which you do not review)
  - Rulebook, the source of truth for tags: ${RULEBOOK}  (SITE_RULES: trigger, required_structure, context, exclusion,
    kind primary/add-on; CONFLICT_RULES)
  - VHDL source: the file and line range named below. The line numbers in the entries are the file's own line numbers.

Already checked by a program, so do NOT report: the Structure field (not given to you), which occurrences exist,
missing occurrences, and Occurrence IDs.

Decisions already made by the project owner (apply them; do not report them as ambiguity):
  - A slice that is the whole right-hand side of a signal assignment gets PART_SELECT alone (no DIRR_ASS, no RHS_OPERAND).
    This holds for a record field too.
  - An element that gives a position inside the parentheses of an assignment target, as in
    <array>(<element>) <= <expression>, is not the target: it gets no LHS_PROC and no LHS_CONC. Its add-on SITEs
    (INDEX, PART_SELECT where sliced, ATTR_PREFIX where written <element>'<attribute>) are written alone.
  - FIELD_USE belongs only to a record base written <base>.<field>, and is written alone there. The field element itself
    gets the SITEs any other element would get (LHS_PROC, RHS_OPERAND, IF_COND, DIRR_ASS, ...), never FIELD_USE.
  - A component's port clause and a name left of => give no entry.
  - The Role must not say what a signal or a branch is for (for example reset, clock, enable, initialization, defaults,
    handshake, bypass, valid flag, state machine). It names only syntax. Using an element's own name is fine.
  - Bit ranges such as (31 downto 28) in a Role are code text, not line numbers.
  - Where the rulebook genuinely does not decide a case, use category rulebook_ambiguity and say which rules conflict.
`

function reviewPrompt(c) {
  return COMMON + `
YOUR CHUNK
  entries file: ${DIR}/${c.file}  (JSON: module, entity, elements, entries [element, id, line, line_text,
  written_on_line (the names as written on that line, one per occurrence), SITE Tagged, Role])
  source: ${REPO}/data/RTL_data/${c.module}.vhd, entity ${c.entity}, lines ${c.lo}-${c.hi}

TASK
Review EVERY entry (${c.n} entries). For each, read the source line and enough of its statement, then decide from the
rulebook alone:
  1. SITE Tagged: exactly one primary SITE where one matches, plus every add-on SITE this occurrence itself matches
     (FIELD_USE, INDEXED_NAME, INDEX, ATTR_PREFIX, PART_SELECT); add-ons alone where no primary matches. Report a tag
     that should not be there (tag_wrong) or one that is missing (tag_missing).
  2. Role (section G): it names the statement and the element's position; FIELD_USE names the field reached; DECL_FIELD
     says whether the record type is declared in this source or outside it; an actual names its formal; PART_SELECT
     gives the range; several occurrences on one line are told apart. Report a Role that states a false syntactic fact
     (role_wrong_fact), describes a position that implies different tags (role_contradicts_tags), lacks a required
     detail (role_missing_required_detail), says what something is for (role_purpose_word), holds a line number
     (role_line_number), or does not tell apart occurrences on one line (role_does_not_tell_apart).
Be exact and literal. Quote the deciding rule word for word and the source line with its number. Report only real
defects; a correct entry gets no finding. Set entries_reviewed to the number of entries you actually checked.`
}

function verifyPrompt(c, review) {
  return COMMON + `
YOUR CHUNK
  entries file: ${DIR}/${c.file}
  source: ${REPO}/data/RTL_data/${c.module}.vhd, entity ${c.entity}, lines ${c.lo}-${c.hi}

A reviewer reported the findings below. Try to REFUTE each one. For every finding, independently re-read the source
line and its statement, find the entry in the entries file (element, id, line), and re-derive the correct tags or Role
requirement from the rulebook and annotate_rules.md alone. Do not trust the reviewer's quotes: check that each quoted
rule exists and says what is claimed.
  - CONFIRMED: the entry really has this defect. Give verified_category and corrected_expected.
  - REFUTED: the entry is correct, or the claimed rule does not exist or does not apply. verified_category "none".
  - RULEBOOK_AMBIGUOUS: the rulebook really does not decide it (name the conflicting rules). The owner decisions above
    are not ambiguous.
If uncertain between CONFIRMED and REFUTED, choose REFUTED. One verdict per finding, same order.

FINDINGS (${review.findings.length}):
${JSON.stringify(review.findings, null, 1)}`
}

const CHUNKS = args
log(`${CHUNKS.length} chunks, ${CHUNKS.reduce((a, c) => a + c.n, 0)} entries`)

const results = await pipeline(
  CHUNKS,
  c => agent(reviewPrompt(c), { label: `review:${c.file}`, phase: 'Review', schema: FINDINGS, effort: 'high' }),
  (review, c) => {
    if (!review) return { chunk: c.file, review: null, verdicts: [] }
    if (!review.findings.length) return { chunk: c.file, review, verdicts: [] }
    return agent(verifyPrompt(c, review), { label: `verify:${c.file}`, phase: 'Verify', schema: VERDICTS, effort: 'high' })
      .then(v => ({ chunk: c.file, review, verdicts: v ? v.verdicts : null }))
  },
)
return { results }
