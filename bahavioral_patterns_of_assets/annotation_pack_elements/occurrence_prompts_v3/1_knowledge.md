YOU TURN SITE DEFINITIONS INTO AN ANNOTATION RULEBOOK

You are given the SITE definitions of a taxonomy. The taxonomy tags each occurrence of an element
in VHDL source with the kind of statement, and the position in it, where the element occurs.

A later step tags every occurrence of every element in a VHDL source. It uses your rulebook
together with the SITE definitions. You are given no VHDL source here, and you tag nothing.

Your task: turn each SITE definition into an explicit decision rule, and state how SITEs that
look alike are told apart, and which SITEs are written together for one occurrence.

==================================================
RULES FOR THE RULEBOOK
==================================================

1. Restate; do not extend. Every rule must follow from the SITE definitions.
   Do not add a SITE. Do not rename, merge or split one.

2. For every rule, copy into "basis" the sentence or sentences of the SITE definitions it comes
   from, word for word.

3. Write every name in a syntax pattern as a placeholder in angle brackets, as the definitions
   do, for example <element_label>. Keywords, operators and function names, such as process,
   when, else, rising_edge or to_integer, stay as written.

4. Describe syntax and position only. Do not say what a signal, a statement or a branch is for.

5. Where a definition leaves a case open, do not decide it. Leave the case out.

==================================================
WHAT TO PRODUCE
==================================================

For each SITE:

  trigger             One sentence: what must be true of an occurrence for this SITE to apply.
  required_structure  The syntax forms of the SITE, as patterns.
  context             Where the statement sits.
  exclusion           Each case that looks like this SITE but is another SITE or no SITE, and
                      which one it is.
  basis               The sentences of the definitions the rule comes from.

Then CONFLICT_RULES. Each one names a group of SITEs and gives the rule that decides between
them, or that combines them for one occurrence. Cover these groups:

  - EDGE_CHECK and IF_COND
  - PROCESS_TRIG and EDGE_CHECK, for the same element in the same process block
  - WHEN_COND and WHEN_EXPR
  - DIRR_ASS, RHS_OPERAND and WHEN_EXPR
  - LHS_PROC and LHS_CONC
  - INDEX and the SITEs of the value the element takes part in
  - PART_SELECT and the SITE of the same occurrence
  - DECL_FIELD, FIELD_USE, and the SITE of the field at the same occurrence
  - DECL_PORT, and an entry in the port clause of a component declaration

Add any other group the definitions tell apart.

==================================================
OUTPUT
==================================================

Return one JSON object, and nothing else:

{"SITE_RULES": {
   "<SITE name>": {
     "trigger": "<one sentence>",
     "required_structure": ["<pattern>"],
     "context": "<where the statement sits>",
     "exclusion": ["<the look-alike case, and which SITE it is instead, or that it is no SITE>"],
     "basis": ["<a sentence copied word for word from the SITE definitions>"]
   }
 },
 "CONFLICT_RULES": [
   {"sites": ["<SITE name>"],
    "rule": "<the rule>",
    "basis": ["<a sentence copied word for word from the SITE definitions>"]}
 ]}

Include every SITE of the definitions in SITE_RULES, each exactly once, under its exact name.

==================================================
SITE DEFINITIONS
==================================================

<<SITES_DEFINITIONS>>
