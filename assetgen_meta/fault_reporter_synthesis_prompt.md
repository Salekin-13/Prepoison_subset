You write the synthesis of an error analysis of a language model (the generator) that lists the security assets of
RTL modules. A program grouped the generator's listed elements into clusters by the relationship types the relationship
map records for them, and measured how much hits (elements in the reference list) and false positives (elements not in
it) overlap. For each cluster, an analyst explained the generator's fault, citing occurrences, and the program tested
every candidate rule.

You receive: the program's FACTS (overlap measures, separability scores, rule tests; every number you may use is in
them) and the analyst's per-cluster findings (already checked against the evidence by the program).

Write:
1. A fault taxonomy: group the clusters into a few classes of generator fault. Name each class plainly and list its
   cluster ids.
2. What rules stated on relationship types achieve and what they do not: how many false positives they remove, at what
   cost in hits, on the elements they were found on and on other modules when the FACTS give it, and why, tied to the
   overlap of relationship types between hits and false positives.
3. What information would be needed to separate them, if the relationship map does not hold it.
4. The limits of this analysis.

Rules:
- Refer to clusters by their ids. Use only the FACTS and the findings given.
- Any number you write must appear in the FACTS exactly as written there. Do not compute new numbers.
- Label hypotheses as hypotheses. Write plainly, in short sentences.

Return one JSON object:
{
 "fault_classes": [{"name": "<short name>", "clusters": ["<id>", ...], "description": "<what the generator does wrong>"}],
 "what_rules_achieve": "<answer>",
 "missing_information": "<answer>",
 "limits": "<answer>"
}
