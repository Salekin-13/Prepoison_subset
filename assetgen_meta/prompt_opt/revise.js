export const meta = {
  name: 'opt-revise',
  description: 'Prompt optimization: analyse the errors of one version, write the next version (general edits only), review it for leakage and repeated failures',
  phases: [{ title: 'Analyse' }, { title: 'Edit' }, { title: 'Review' }],
}
const R = 'E:/jobs/ff/test/Prepoison_subset'
const O = `${R}/assetgen_meta/prompt_opt`
const { cur, next } = args
const RULES = `Rules for every prompt change (the user's and the project's):
- Change the prompt only from observed error patterns, worded GENERALLY so it would apply to any RTL module: no module name, entity name, signal, port, field or constant name of this processor or of any evaluated module; no statement that only fits one module; no reference answer; no numeric quota or proportion ("at most N", "N%", "N assets").
- Basis (project rule, ${R}/assetgen_meta/ASSET_DEFINITION.md section 5): every prompt edit must cite a "Prompt" row of that file's section 3 table, or a paper with page; the exact record test may be pattern only. An edit must not contradict a "Prompt" row or an unchanged definition of the prompt (for example: state, setting and decision elements are primary in their own right). A rule whose only support is a count from the reference does not go into the prompt: name it as an evaluation-layer code filter instead.
- Word every rule by record shape and structural situation only. Do not name kinds of structure that single out an evaluated module (memories, arrays, caches, FIFOs, interrupt controllers, buses of this processor).
- Read the log for withdrawn edits and their reasons; do not propose them again.
- Prefer one to three focused edits over a rewrite. Keep every rule the log marks as measured-useful unless the evidence shows it causes the error.
- Known failures from earlier experiments (do not repeat): a sentence that only tells the model to leave something out is usually ignored; a sentence that redirects the model to report a named kind of element ("report the decision elements instead") turns into a licence and adds false positives; a second output list for non-reported elements absorbs real assets; per-value security questions inside this call cost recall; numeric caps become quotas. A positive, testable criterion tied to the evidence the model already cites (map records, occurrence lines, storage, boundary, connections) is the form that has worked.
- The worked examples at the end of the prompt are fixed (their decisions are checked by code). If an edit contradicts what an example shows, say so in the change note instead of editing the example.`

const ANALYSE = `You are the error analyst of a prompt-optimization loop for an LLM that lists the primary security assets of RTL modules. Read-only: do not edit any file; return your analysis as your final text.

Read:
- ${O}/${cur}/eval_r0.md and ${O}/${cur}/eval_r0.json : precision / recall of version ${cur} on 15 modules (111 reference entries), every false positive (kind, the role the model gave it) and every false negative (kind, and where it ended up in the model's output: nowhere, only in a flow, only in a concept's text, ...), and the change against the previous version if any.
- ${O}/${cur}/instructions.md : the prompt's instructions (the worked examples are not needed).
- ${O}/OPTIMIZATION_LOG.md : what has been tried and what happened.
- The executor outputs ${R}/assets_opt_${cur}_r0/_nested/<module>.json and, when you need to check an RTL fact, the module inputs ${R}/assetgen_meta/traced_inputs_v2/tuning/<module>.txt.

Find the RECURRING error patterns that cost the most precision and recall. For each pattern give: a general description (what kind of element, in what structural situation, and what the model did), the count (false positives and false negatives it explains), two or three examples (module/element, for this analysis only), the prompt wording or missing guidance that produces it, and a candidate GENERAL fix with its expected effect on both precision and recall (estimate how many false positives it removes and how many true positives it risks). Separate patterns the prompt can plausibly fix from errors that are inconsistencies of the reference itself (the same kind of element listed in some modules and not in others): mark the latter "reference inconsistency" and do not propose prompt fixes for them. Rank by expected net F1 gain. Be concrete and brief.

${RULES}`

const EDIT = (analysis) => `You are the prompt editor of a prompt-optimization loop. Write version ${next} of the instructions from version ${cur}.

Read: ${O}/${cur}/instructions.md (the current instructions), ${O}/OPTIMIZATION_LOG.md (history), and the error analysis below.

=== ERROR ANALYSIS of ${cur} ===
${analysis}
=== END ===

${RULES}

Make the one to three edits with the best expected net gain in F1 that follow the rules. Write ONLY these two files with the Write tool (the folder ${O}/${next}/ may need to be created by writing into it):
- ${O}/${next}/instructions.md : the complete new instructions (copy ${cur}'s and apply your edits; change nothing else).
- ${O}/${next}/change.md : for each edit: the old text and the new text, the error pattern and its counts (the evidence), the reasoning, whether it also has a theory basis (cite a source and page, or say "pattern only"), the predicted effect on false positives and false negatives, and the measurement that would show it failed.
Then reply with a three-line summary.`

const REVIEW = `You are an adversarial reviewer in a prompt-optimization loop. Read-only: do not edit files; return a verdict as your final text.

Compare ${O}/${cur}/instructions.md with ${O}/${next}/instructions.md and read ${O}/${next}/change.md.
Check, and quote the exact sentence for every problem:
1. Leakage: does any new or changed sentence name, describe or single out a specific module, entity, element or structure of the evaluated processor, or encode a reference answer, even without using its identifier? Would the sentence make sense for an unrelated RTL design?
2. Repeated failures: is any edit a bare exclusion sentence, a redirect to report a named kind of element, a second output list, an in-call per-value question block, or a numeric quota?
3. Consistency: does an edit contradict another rule of the prompt or the worked examples' decisions described in the change note?
4. Scope: were only the edits described in change.md made (no other text changed)?
5. Basis: does each edit cite a "Prompt" row of ${R}/assetgen_meta/ASSET_DEFINITION.md section 3 or a paper with page, and contradict no "Prompt" row and no unchanged definition in the prompt?
Answer with "VERDICT: PASS" or "VERDICT: FAIL", then the problems and, for each, the minimal fix.`

phase('Analyse')
const analysis = await agent(ANALYSE, { label: `analyse ${cur}`, phase: 'Analyse' })
phase('Edit')
const edit = await agent(EDIT(analysis), { label: `edit ${next}`, phase: 'Edit' })
phase('Review')
let review = await agent(REVIEW, { label: `review ${next}`, phase: 'Review' })
let fixed = null
if (!/VERDICT:\s*PASS/.test(String(review))) {
  fixed = await agent(`You are the prompt editor. The reviewer rejected your edit of ${O}/${next}/instructions.md. Apply the minimal fixes below, keep the rest, update ${O}/${next}/change.md to match, and write only those two files.\n\n=== REVIEW ===\n${review}\n=== END ===\n\n${RULES}\n\nReply with a three-line summary.`,
    { label: `fix ${next}`, phase: 'Edit' })
  review = await agent(REVIEW, { label: `re-review ${next}`, phase: 'Review' })
}
return { analysis, edit, review, fixed }
