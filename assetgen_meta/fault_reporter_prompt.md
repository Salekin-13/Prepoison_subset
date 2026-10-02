You analyse the errors of a language model (the generator) that lists the security assets of RTL modules. A program
has checked the generator's list against a reference list written by people. You receive ONE cluster of elements the
generator listed. The program grouped them because the relationship map records similar relationship types for them.
Some members are in the reference list (label "hit"), some are not (label "false positive").

For every member you get:
- the module and the element name, and the role the generator gave it (stores, sets, computes, exit port);
- its tokens: the relationship profile the program computed from the map (the same tokens a rule may use);
- the occurrence the generator cited: its ID, its line number and the RTL text of that line;
- the edge the generator cited (a relationship record type and its partner element);
- the element's relationship records from the map: record type, the elements on the other end with what they are
  (itself, internal, input port, output port), and their lines; "(+N more)" marks a list the program shortened;
- its connections to sub-units (the sub-unit port and its direction) and its constant drivers, when it has them;
- its storage (stored on a clock edge, combinational, or not assigned here) and whether it is a record field.

Relationship record types, in the direction the map writes them:
- CARRIES, SOURCES: the element's value goes into another element, unchanged or as part of an expression.
- COPIES, DERIVES_FROM: the element takes its value from another element, unchanged or through an expression.
- GATES, SELECTS, CONSTRAINS: the element controls whether, which or how another element is assigned.
- GATED_BY, SELECTED_BY, CONSTRAINED_BY: the element's assignment is controlled by another element.
- CLOCKED_BY, RESET_BY: the element is stored on a clock edge, or is reset, by that element.
- SEQUENCES, RESETS: a clock or reset input that clocks or resets other elements.
A connection "in" means the element's value goes into the sub-unit; "out" means the sub-unit drives the element.

Your task, for this cluster:
1. State what the map evidence of the members has in common.
2. Say why the generator listed the false positives: what in the cited occurrence and edge made them look like assets.
3. Compare hits and false positives: is there anything in the cited RTL lines, the cited edges or the records that
   differs between them? Quote occurrences to show it. If nothing differs, say so.
4. Decide whether the tokens separate the false positives from the hits in this cluster:
   "yes" if a rule on the tokens drops every false positive shown and no hit; "partly" if a rule drops some false
   positives and no hit; "no" if every rule that drops a false positive also drops a hit.
5. If "yes" or "partly", give that rule using only tokens from the TOKEN VOCABULARY in the input: drop an element when
   it has all tokens in "drop_if_all" and none in "unless_any". "drop_if_all" must not be empty. The program applies the
   rule to every listed element of every module, not only to this cluster, so include the tokens that define the
   cluster when the rule needs them. If "no", give null.
6. If the evidence does not separate them, state the convention of the reference that would explain listing the hits
   and not the false positives. This is a hypothesis: label it as one.

Rules for your answer:
- Use only the evidence in the input. Cite evidence as module, element, the cited occurrence ID and its line number,
  exactly as given.
- Cite several hits and several false positives when the cluster shows them.
- Do not count or compute rates: the program reports all numbers. Do not write any number except occurrence IDs and
  line numbers copied from the input.
- Write plainly, in short sentences.

Return one JSON object:
{
 "cluster": "<the cluster id from the input>",
 "shared_evidence": "<what the members' map evidence has in common>",
 "generator_fault": "<why the generator listed the false positives>",
 "difference": "<what differs between hits and false positives in the cited evidence, or 'none found'>",
 "separable_by_relationship_types": "yes" | "partly" | "no",
 "candidate_rule": {"drop_if_all": ["<token>", ...], "unless_any": ["<token>", ...]} or null,
 "reference_convention_hypothesis": "<hypothesis, or empty>",
 "evidence": [{"module": "<module>", "element": "<element>", "occurrence": <id>, "line": <line>,
               "label": "hit" | "false positive", "point": "<what this occurrence shows>"}]
}
