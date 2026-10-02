Annotate RTL relationships for one VHDL entity and one batch of elements per call. Follow the occurrence profiles and the rules below. Return only the JSON object specified in section 6.

==================================================
1. INPUTS
==================================================

Read these inputs in this order:

  a. THE SOURCE. Read the entity declaration and architecture of one entity, with comments removed. Treat the number
     at the start of every line as its line number in the original file. Use the source to determine statement
     extent, operators, signal widths, and assignments to process variables. Take no element or occurrence position
     from the source unless the profile lists it.
  b. THE CLOSED SET. Use this list as the complete set of elements of the entity. Read each port's name, direction
     and type, and each internal signal's name and type. Recognize a field of a record-typed port or signal by its
     listed name <base>.<field>. Treat only names in this list as elements. Exclude literals, named constants,
     generics, loop parameters, process variables, enumeration values, and function and type names from elements.
  c. THE OCCURRENCE PROFILE OF EVERY ELEMENT OF THE ENTITY. Read the profile produced by a program and an earlier
     annotator. For each element, use every listed occurrence and its fields:
       Occurrence ID   a whole number, unique within the element
       Occurrence Lines, Name As Written, Line Text
       Context         the constructs enclosing the occurrence, innermost first, each with its first and last line:
                       <kind> <first>-<last> in <kind> <first>-<last> in ... in architecture <first>-<last>
       Path            the conditions that must all hold at the occurrence, outermost first. An elsif or else arm
                       carries not (...) of every earlier arm. A case alternative carries <selector> = <choice>,
                       <selector> in {<a>, <b>}, or not (<selector> in {...}) for others. When ... else and
                       with ... select arms carry theirs the same way. Prefixes: [generic] and [static] (fixed when the
                       design is built), [for-generate] and [loop] (index ranges).
       SITE Tagged     the positional category of the occurrence
       Role            one sentence on the element's syntactic position there
     Treat Context and Path as correct, fixed facts computed from a VHDL grammar. Never re-derive or correct them.
  d. THE BATCH. Annotate only the elements in this call's batch. Use every other element's profile to find partners.

==================================================
2. YOUR WORK AND THE PROGRAM'S WORK
==================================================

Go through the batch element by element and each element occurrence by occurrence. Write the relationships that
hold at each occurrence, seen from that element.

Treat every relationship as a pair. For a statement that gives <target> a value from <source>, write the driving
record at <source>'s occurrence and the matching receiving record at <target>'s assignment occurrence. Write each
side when processing that element's occurrence. Use profiles outside the batch to find partners, but do not emit
an element outside the batch. Expect the program afterwards to check every record for its partner at the place
section 4 gives and to return records without partners for checking. Establish each record from the evidence,
not from an expected partner.

For every batch element, write functionality in one or two plain sentences about what the element does in this
entity, in terms of the logic the source shows. Follow the length limit in section 6.

Leave every field in the following list to the program. Write none of them:
  kind              for an internal signal: register (assigned on a clock edge) or signal
  handling          for a record field (a dotted name): any combination of ORIGINATES, CONSUMES, FORWARDS
  guard             inside each GATES, SELECTS or CONSTRAINS record and its partner: the Path entry, selector
                    entry or right-hand side the relationship comes from
  boundary          for a port: its mode, and whether an outward port is driven, tied or undriven
  storage           whether the element's assignments are on a clock edge
  constant_drivers  the literals or constants that are the element's whole value, where they are
  configuration     the conditions over generics and constants under which the element is declared or driven
  connections       the element's wiring to the ports of instantiated sub-blocks, both directions

Treat the following as the program's merged final-file shape, not your response format. Return only the shape in
section 6:
{"ports": [
  {"name": "<exactly as given>",
   "functionality": "<1-2 sentences, <=45 words>",
   "handling": ["ORIGINATES" | "CONSUMES" | "FORWARDS", "..."],
   "boundary": {"mode": "<in | out | inout | buffer>", "drive": "<driven | tied | undriven | n/a>"},
   "storage": "<edge | none | mixed | not assigned>",
   "constant_drivers": [{"at": <Occurrence ID>, "value": "<literal or named constant>"}],
   "configuration": ["<Path entry over generics or constants>"],
   "connections": [{"at": <Occurrence ID>, "instance": "<label>", "formal": "<port>", "mode": "<mode>"}],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "guard": "<required for GATES/SELECTS/CONSTRAINS>",
                     "bits": "<optional>"}]}
 ],
 "signals": [
  {"name": "<exactly as given>",
   "kind": "register" | "signal",
   "functionality": "<1-2 sentences, <=45 words>",
   "handling": [...], "storage": ..., "constant_drivers": [...], "configuration": [...], "connections": [...],
   "relationship": [same shape as for ports]}
 ]}

==================================================
3. THE RELATIONSHIP PAIRS (carry this section into the prompt WORD FOR WORD; worked examples after it are welcome,
   written only with placeholders)
==================================================

Read "X's assignment" as an occurrence of X tagged LHS_PROC or LHS_CONC, or X as the target of a when ... else or
with ... select assignment, and "its Path" as that occurrence's Path. "On a clock edge" means an edge function
(rising_edge(<clk>), falling_edge(<clk>), or <clk>'event and <clk> = <literal>) appears in that Path without
not (...) around it.

  driving (at Y)   receiving (at X)   the pair holds when
  CARRIES          COPIES             X's right-hand side is exactly Y: no operator, slice, index or conversion.
  SOURCES          DERIVES_FROM       Y's value is read on X's right-hand side in any other way: an operand, a function
                                      argument, an array element read, a slice, an indexed name, or the value arm of a
                                      when ... else or with ... select assignment.
  SEQUENCES        CLOCKED_BY         Y is the argument of the edge function that puts X's assignment on a clock edge.
  RESETS           RESET_BY           Y is tested in an arm of the same if statement as that edge function, the arm
                                      comes before the edge arm, and in that arm X is assigned a literal or a named
                                      constant.
  SELECTS          SELECTED_BY        Y is the selector of the case statement or the with ... select assignment whose
                                      alternative holds X's assignment; or an index computed while the design runs
                                      that picks which part of an array is read into X, or written when X is the
                                      array.
  CONSTRAINS       CONSTRAINED_BY     Y is compared (=, /=, <, <=, >, >=) with an expression that contains another
                                      element, and that comparison is a condition in X's Path. Every element on either
                                      side of the comparison carries it.
  GATES            GATED_BY           Y decides whether X takes a value, or forces it to a fixed level. Its form is
                                      condition: Y appears in an if, elsif or when ... else condition in X's Path, or
                                      in an earlier arm's condition that the Path negates, used bare or compared with a
                                      literal or a named constant; or operand: Y is a single-bit operand, bare or as
                                      not Y, of a top-level and, or, nand or nor on the right-hand side of a single-bit
                                      X.

ONE TYPE PER PAIR OF OCCURRENCES
  1. For one occurrence of Y and one assignment of X, keep the first that applies: SEQUENCES, RESETS, SELECTS,
     CONSTRAINS, GATES, CARRIES, SOURCES. Its partner is the matching receiving type.
  2. The clock is only SEQUENCES: an edge function in X's Path is never GATES.
  3. The reset is only RESETS: a reset arm that X's Path negates is not GATES. An arm inside the edge arm that
     assigns constants is not a reset arm: its condition is GATES.
  4. An entry <selector> = <choice>, <selector> in {...} or not (<selector> in {...}) in the Path is only SELECTS.
  5. Y compared with another element is CONSTRAINS; compared with a literal or a named constant it is GATES.
  6. A condition over generics or named constants alone gives no relationship.
  7. An index built from an element is SELECTS; an index built only from literals, named constants, generics or loop
     parameters goes in bits. The array that is read is SOURCES.
  8. An attribute prefix such as <elem>'length reads the shape, not the value: no relationship.
  9. An element that feeds or decides itself writes both records of the pair on itself.
 10. A choice of a case or with ... select (a literal, a named constant, a range or others) is never Y.

PROCESS VARIABLES are not elements. Where X's assignment reads a variable, the pairs go from the elements the variable
was computed from, in the same process, to X: an element read in the variable's assignment SOURCES X (or GATES it,
operand form); an element in a condition governing that variable assignment GATES X; inside a loop, every element read
in the loop body SOURCES X. The driving record sits at the element's occurrence in the variable's assignment.

==================================================
4. FROM SITE TO RELATIONSHIP (carry this section into the prompt WORD FOR WORD)
==================================================

Where the partner is: facts about the profile, established by a program.
  L1  A condition element sits inside the branch it opens: the innermost frame of an occurrence tagged IF_COND or
      EDGE_CHECK is the then or elsif branch that condition opens. A case selector's innermost frame is its case.
  L2  The assignments a condition governs are the occurrences, tagged LHS_PROC or LHS_CONC, whose Context contains THE
      SAME frame: same kind, same first and last line. Through its negation, a condition also governs the assignments
      in the later arms of the same if frame (rule 3 of section 3 still applies to a reset arm).
  L3  The assignments a case selector governs are those whose Context contains the same case frame.
  L4  A right-hand-side occurrence feeds the target of the SAME statement: the occurrence tagged LHS_PROC or LHS_CONC
      in that statement. Where a statement runs over several lines, or a line holds several statements, take the
      statement's extent from the source.
  L5  A when ... else condition governs the target of its own statement.

What each SITE of the current occurrence leads to:
  SITE of this occurrence       this element is   records to write here, and where the partner is
  EDGE_CHECK                    Y                 SEQUENCES, to every X assigned in the same branch (L1, L2)
  IF_COND                       Y                 RESETS, to every X assigned a literal or named constant in an arm
                                                  that comes before the edge arm; otherwise CONSTRAINS or GATES
                                                  (condition), to every X assigned in the same branch and, through its
                                                  negation, in the later arms (L2); a variable assigned there passes it
                                                  on to every X that reads the variable (section 3)
  WHEN_COND                     Y                 CONSTRAINS or GATES (condition), to the target of its statement (L5)
  CASE_EXPR                     Y                 SELECTS, to every X assigned in the same case (L3)
  (the selector of a with ... select, written between with and select; the rulebook gives it no SITE of its own)
                                Y                 SELECTS, to the target of that assignment (L4)
  INDEX                         Y                 SELECTS, when the index is computed while the design runs, to the
                                                  target of the statement or the array written (L4)
  DIRR_ASS                      Y                 CARRIES, to the target of the statement (L4)
  RHS_OPERAND                   Y                 GATES (operand) under a top-level and, or, nand or nor of a single-
                                                  bit X; otherwise SOURCES; to the target of the statement (L4)
  WHEN_EXPR                     Y                 SOURCES, to the target of its statement (L4)
  VAR_RHS_OPERAND, or an empty  Y                 SOURCES (or GATES, operand form), to each X whose assignment reads
  SITE list on the right-hand                     that variable (section 3)
  side of a variable assignment
  INDEXED_NAME or PART_SELECT   Y                 SOURCES, to the target of the statement (L4), with the index or the
  standing alone on a right-                      slice in bits: an indexed or sliced whole right-hand side carries no
  hand side                                       other SITE
  INDEXED_NAME or PART_SELECT   (add-on)          no record of its own: it goes with the occurrence's other SITE, and
  with another SITE                               a fixed index or the slice goes in bits
  LHS_PROC, LHS_CONC            X                 the receiving record of every pair that ends at this assignment:
                                                  COPIES or DERIVES_FROM for each element read in the statement, or,
                                                  where the statement reads a process variable, each element the
                                                  variable was computed from (L4); CLOCKED_BY, RESET_BY, SELECTED_BY,
                                                  CONSTRAINED_BY or GATED_BY for each element in a condition or a
                                                  selector of this occurrence's Path, or of the Path of the variable
                                                  assignment it reads, and for each element read as a run-time index
                                                  or a forcing operand. For a record field reached through its base,
                                                  the partner is the field, never the base.
  DECL_PORT, DECL_SIGNAL,
  DECL_FIELD, PROCESS_TRIG,
  CASE_COND, ATTR_PREFIX,
  FIELD_USE, ASSOC_ACTUAL       -                 none. FIELD_USE: the field's own occurrence carries the record.
                                                  ASSOC_ACTUAL: the program writes the connection.

==================================================
5. GUARDS AGAINST INVENTED RELATIONSHIPS (carry this section into the prompt WORD FOR WORD)
==================================================

  G1  Every number in at is an Occurrence ID of the current element listed in the profile, and every name in targets
      is an element of the closed set.
  G2  Write a record only where the profile lists an occurrence of the partner at the place section 4 gives: the same
      statement, the same branch, the same case, or the condition of an earlier arm of the same if. Where it lists
      none, there is no relationship.
  G3  The type is one that section 4 allows for the SITE of every occurrence listed in at.
  G4  Copy no text from the profile or the source into the output: no condition, no Path entry, no line. The program
      writes every guard itself, from the Path and the statement.
  G5  Positions come from the profile and operators from the source, never from a name. What an element is called
      decides nothing: two elements with telling names and no statement between them have no relationship.
  G6  Where the profile and the source do not show a relationship, write none. No record is written to complete a
      pattern, to match a record elsewhere, or because a partner record is expected.
  G7  A record lists several occurrences in at, or several names in targets, only where the relationship holds
      between EVERY listed occurrence and EVERY listed target.

==================================================
6. THE OUTPUT CONTRACT (carry this into the prompt exactly)
==================================================

Return one JSON object and nothing else:

{"ports": [
  {"name": "<exactly as given>",
   "functionality": "<1-2 sentences, <=45 words>",
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "bits": "<optional>"}]}
 ],
 "signals": [
  {"name": "<exactly as given>",
   "functionality": "<1-2 sentences, <=45 words>",
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "bits": "<optional>"}]}
 ]}

<EDGE> is one of the fourteen types of section 3, written bare. The relationship list holds the relationship records
of section 3: each record is one type, the elements it relates this element to, and the occurrences where it holds.
A batch element listed as a port, a port's field included, goes in "ports"; an internal signal, a signal's field
included, goes in "signals". Every batch element appears exactly once, in its array, in closed-set order; an array
with no batch element is empty. An element with no relationship gets an empty relationship list. Group records: one
record per type and bits, listing every occurrence and every target it holds for (G7). List no occurrence that has
no relationship. Omit bits where it does not apply. The two forms of GATES share the one type; the program tells
them apart by the SITE of the occurrence in at. Write no field of the program's list in section 2: not kind,
handling, guard, boundary, storage, constant_drivers, configuration or connections.

==================================================
7. OUTPUT LANGUAGE
==================================================

Forbid the following words in every output field:
asset, secret, confidential, integrity, availability, sensitive, critical, important, protect, trusted, untrusted,
privileged, vulnerable, vulnerability, exploit, threat, attacker, adversary, malicious, secure, insecure, security,
cwe, risk, leak, may, could, might, possibly, potentially, likely.

Keep the output free of verdicts. State what the logic does in functionality, never why it matters.

==================================================
8. ANNOTATION PROCEDURE
==================================================

1. Take each batch element in closed-set order. Use its closed-set classification to choose its output array.
2. Visit each occurrence of that element. Read its Occurrence ID, complete SITE list, Context and Path. Keep the
   supplied Context and Path unchanged.
3. Find the applicable SITE entry in section 4. Locate the partner occurrence in the full profiles by L1 to L5.
   Match frames by kind and both endpoint lines. Use the source for statement extent, including statements split
   over lines and separate statements on the same line. Follow the process-variable rule where applicable.
4. Apply section 3 to the candidate pair of occurrences. Read the source for operators, widths and variable
   assignments. Apply the type precedence and exclusions. At an assignment occurrence, identify the receiving
   type from the same evidence that establishes its driving type.
5. Check G1 to G7 for the candidate record. Discard a candidate without the required evidence or partner occurrence.
6. Add the current element's Occurrence ID to at and the partner's exact closed-set name to targets in the matching
   type-and-bits record. Preserve G7 when grouping. Keep groups separate wherever merging would assert an
   unsupported occurrence-target combination. Omit bits where it does not apply.
7. After visiting the element's occurrences, write its functionality from the shown logic. Retain an empty
   relationship list if no relationship holds. Continue with the next batch element.

==================================================
9. WORKED EXAMPLES
==================================================

VALUE PAIR
Read the placeholder statement:
  <target> <= <source>;
Assume the profile lists <source> at <source_occurrence_id> with SITE DIRR_ASS and <target> at
<target_occurrence_id> with SITE LHS_CONC in this same statement. Apply L4 and the exact-value rule. Write CARRIES
on <source>, with targets containing <target> and at containing <source_occurrence_id>. Write COPIES on <target>,
with targets containing <source> and at containing <target_occurrence_id>. Omit bits. Emit each side only when its
element belongs to the batch.

CONTROL PAIR
Read the placeholder statement:
  if <condition> then <target> <= <literal>; end if;
Assume <condition> is a bare condition element, the profile lists its IF_COND occurrence at
<condition_occurrence_id>, and the profile lists <target>'s LHS_PROC occurrence at <target_occurrence_id> with the
same branch frame in Context and the condition in Path. Assume no edge function in this if statement. Apply L1
and L2. Write GATES on <condition>, targeting <target>, at <condition_occurrence_id>. Write GATED_BY on <target>,
targeting <condition>, at <target_occurrence_id>. Write no relationship for <literal>. Leave guard to the program.

INDEXED WHOLE RIGHT-HAND SIDE
Read the placeholder statement:
  <target> <= <array>(<fixed_index>);
Assume <fixed_index> is a named constant. Assume the profile lists <array> at <array_occurrence_id> with
INDEXED_NAME standing alone as its SITE and lists <target> at <target_occurrence_id> with SITE LHS_CONC in the same
statement. Apply L4. Write SOURCES on <array>, targeting <target>, at <array_occurrence_id>. Write DERIVES_FROM on
<target>, targeting <array>, at <target_occurrence_id>. Put the fixed index in bits. Do not treat this whole
right-hand side as an exact copy. Write no relationship for <fixed_index>.

NO PARTNER AT THE REQUIRED PLACE
Consider an IF_COND occurrence of <condition>. Assume the profile lists <target>'s assignment only in an unrelated
process, with no assignment occurrence of <target> in the opened branch or any later arm governed through the
condition's negation. Apply G2. Write no relationship between these occurrences, even when both names are in the
closed set. Do not replace the missing partner with an occurrence from the unrelated process.

==================================================
10. FINAL SELF-CHECK
==================================================

Before answering:
- Verify that every batch element appears exactly once, in the correct array and in closed-set order, with no
  element outside the batch.
- Verify that every number in at is an Occurrence ID belonging to that record's element, not a source line number
  or an Occurrence ID belonging to another element.
- Verify that every target is an exact name in the closed set.
- Verify that every type is allowed for the SITE of every occurrence in its at, and that every grouped record
  satisfies G7.
- Verify that every supported pair whose elements are both in the batch is written from both sides at the proper
  occurrences. Recheck the evidence for an omission; do not invent a relationship to complete a pair.
- Verify that no text is copied from the input, as required by G4.
- Verify that no field from the program's list in section 2 appears in the response.
- Verify that no forbidden word appears in any output field.
- Verify that functionality describes only the shown logic and meets the length limit.
- Verify that the response is valid JSON in the section 6 shape, with no surrounding prose.