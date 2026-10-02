Annotate RTL relationships for one VHDL entity and one batch of elements per call. Use only the supplied elements and occurrence positions. Return only the JSON object specified in section 6.

==================================================
1. READ THE INPUTS IN THIS ORDER
==================================================

  a. THE SOURCE: Read the entity declaration and architecture of one entity, with comments removed. Read the number
     at the start of each line as its line number in the original file. Use the source to determine statement extents,
     operators, signal widths, and assignments to process variables. Never take an element or an occurrence position
     from the source that the supplied profile does not list.
  b. THE CLOSED SET: Read the list of every element of the entity. Read each port's name, direction and type, and each
     internal signal's name and type. Read a field of a record-typed port or signal as <base>.<field>. Treat only names
     in this list as elements. Exclude literals, named constants, generics, loop parameters, process variables,
     enumeration values, and function and type names from the elements.
  c. THE OCCURRENCE PROFILE OF EVERY ELEMENT OF THE ENTITY: Read every supplied occurrence and these fields:
       Occurrence ID   Read a whole number unique within that element, not an original-file line number.
       Occurrence Lines, Name As Written, Line Text
                       Use these to locate the supplied occurrence in the source.
       Context         Read the enclosing constructs, innermost first, with each construct's first and last line:
                       <kind> <first>-<last> in <kind> <first>-<last> in ... in architecture <first>-<last>
       Path            Read the conditions that must all hold at the occurrence, outermost first. Interpret an elsif
                       or else arm's not (...) entries as the negation of every earlier arm. Interpret a case
                       alternative's entry as <selector> = <choice>, <selector> in {<a>, <b>}, or
                       not (<selector> in {...}) for others. Read when ... else and with ... select arm entries in
                       the same way. Treat [generic] and [static] entries as fixed when the design is built, and
                       [for-generate] and [loop] entries as index ranges.
       SITE Tagged     Read the positional category of the occurrence.
       Role            Read the sentence describing the element's syntactic position there.
     Treat Context and Path as correct, grammar-computed facts. Never re-derive or correct them.
  d. THE BATCH: Annotate only the listed batch elements. Use every other element's profile to find partners, not to
     add elements to the batch output.

==================================================
2. WRITE YOUR FIELDS AND LEAVE THE PROGRAM'S FIELDS ALONE
==================================================

Go through the batch element by element and each element occurrence by occurrence. Write the relationships that hold
at each occurrence, seen from the current element.

Treat every relationship as a pair. For an assignment that gives <target> a value from <source>, write the DRIVING
record at <source>'s occurrence and the matching RECEIVING record at <target>'s assignment occurrence. Write each side
when processing its occurrence in the batch. Find partners outside the batch without adding their element objects to
the output. Leave the subsequent partner check to the program: let it check each record against its partner at the
place section 4 gives and return an unpaired record for checking. Never use an expected partner record as evidence.

Write FUNCTIONALITY for every batch element as one or two plain sentences, <=45 words, describing what the
element does in this entity according to the source logic. State what the logic does, never why it matters.

Leave every field below to the program. Write none of them:
  kind              for an internal signal: register (assigned on a clock edge) or signal
  handling          for a record field (a dotted name): any combination of ORIGINATES, CONSUMES, FORWARDS
  guard             inside each GATES, SELECTS or CONSTRAINS record and its partner: the Path entry, selector
                    entry or right-hand side the relationship comes from
  boundary          for a port: its mode, and whether an outward port is driven, tied or undriven
  storage           whether the element's assignments are on a clock edge
  constant_drivers  the literals or constants that are the element's whole value, where they are
  configuration     the conditions over generics and constants under which the element is declared or driven
  connections       the element's wiring to the ports of instantiated sub-blocks, both directions

Use the following merged-file layout only to distinguish your fields from the program's fields. Return the smaller
object in section 6, not this merged layout:
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
3. THE RELATIONSHIP PAIRS
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
4. FROM SITE TO RELATIONSHIP
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
  (the selector of a with ... select, written between with and select; it has no SITE of its own)
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
5. GUARDS AGAINST INVENTED RELATIONSHIPS
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
6. THE OUTPUT CONTRACT
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
7. FOLLOW THIS PER-ELEMENT, PER-OCCURRENCE PROCEDURE
==================================================

1. Take each batch element in closed-set order. Place it in the array specified in section 6 and initialize its
   relationship list. Visit every occurrence in that element's supplied profile.
2. Read the current occurrence's SITE, Context and Path. Use its Occurrence Lines and the numbered source to locate
   its statement. Read the source for statement extent, operators, widths and process-variable assignments; retain
   the supplied Context, Path and occurrence positions unchanged.
3. Find the current SITE in section 4. Determine whether to seek driving records, receiving records, or none. Treat
   a standalone indexed or sliced right-hand side differently from an index or slice that accompanies another SITE.
4. Find each partner occurrence using L1 to L5 and the complete entity profiles. Match frames by kind and both line
   endpoints, and match value reads to their own statement rather than merely their line. For a process variable,
   trace the source assignments within the same process under section 3, then locate the contributing elements'
   supplied occurrences and the assignments that read the variable. Reject any candidate without the required
   profiled partner position.
5. Apply section 3 to each candidate occurrence pair. Apply its precedence order and all exclusions. At an assignment,
   write the receiving type matching the selected driving type, not an additional lower-precedence value type. Use
   the field's own occurrence for a record field. Use bits only where the rules prescribe an index or slice.
6. Check G1 to G7 for every candidate record. Add the current element's Occurrence ID and the partner's exact
   closed-set name to the matching type-and-bits record only when the resulting group satisfies G7. Keep records
   separate when merging would assert an unsupported occurrence-target combination. Never put the partner's
   Occurrence ID in the current element's at array.
7. After processing the element's occurrences, write its functionality from the source logic. Keep an empty
   relationship list when no candidate passes the rules. Continue through the batch without adding non-batch objects.

==================================================
8. APPLY THESE WORKED EXAMPLES
==================================================

Use the following placeholder examples to distinguish original-file line numbers from element-local Occurrence IDs.
Treat the displayed relationship objects as fragments for the named current elements, not as an alternative output
format. Write each fragment only when processing that element in the batch.

VALUE PAIR
Read this concurrent assignment:
10 <value_target> <= <value_source>;

Use these supplied occurrences:
  <value_source>: Occurrence ID 3; line 10; SITE DIRR_ASS; Context architecture 1-30; Path empty.
  <value_target>: Occurrence ID 5; line 10; SITE LHS_CONC; Context architecture 1-30; Path empty.

Match the occurrences by L4. Apply CARRIES because the entire right-hand side is exactly <value_source>, with no
operator, slice, index or conversion. Write under <value_source>:
{"type": "CARRIES", "targets": ["<value_target>"], "at": [3]}
Write the matching receiving record under <value_target>:
{"type": "COPIES", "targets": ["<value_source>"], "at": [5]}

CONTROL PAIR
Read this statement inside a process with no edge function:
41 if <control> = '1' then
42   <controlled_target> <= '0';
43 end if;

Use occurrence ID 4 of <control>, tagged IF_COND on line 41, with innermost Context frame then 41-42 inside if 41-43.
Use occurrence ID 6 of <controlled_target>, tagged LHS_PROC on line 42, with that same then 41-42 frame in its Context
and <control> = '1' in its Path. Treat both occurrences as enclosed by process 40-44 in architecture 1-60.

Match the condition to the assignment by L1 and L2. Apply GATES because the condition compares an element with a
literal. Do not classify the constant assignment as a reset without the required earlier arm of an edge-bearing if.
Write under <control>:
{"type": "GATES", "targets": ["<controlled_target>"], "at": [4]}
Write under <controlled_target>:
{"type": "GATED_BY", "targets": ["<control>"], "at": [6]}
Leave the guard and the literal driver to the program.

SLICED WHOLE RIGHT-HAND SIDE
Read this concurrent assignment:
70 <slice_target> <= <slice_source>(7 downto 4);

Use these supplied occurrences:
  <slice_source>: Occurrence ID 8; line 70; SITE PART_SELECT alone; Context architecture 1-90; Path empty.
  <slice_target>: Occurrence ID 2; line 70; SITE LHS_CONC; Context architecture 1-90; Path empty.

Match the occurrences by L4. Apply SOURCES rather than CARRIES to the sliced whole right-hand side. Put the fixed
slice in bits and write under <slice_source>:
{"type": "SOURCES", "targets": ["<slice_target>"], "at": [8], "bits": "7 downto 4"}
Write under <slice_target>:
{"type": "DERIVES_FROM", "targets": ["<slice_source>"], "at": [2], "bits": "7 downto 4"}
Do not create an element or a SELECTS record for the literal slice bounds.

NO PROFILED PARTNER: G2
Read this source statement:
91 <missing_target> <= <observed_source>;

Treat both names as members of the supplied closed set. Use occurrence ID 9 of <observed_source>, tagged DIRR_ASS on
line 91. For this example, use a supplied profile for <missing_target> containing only its DECL_SIGNAL occurrence and
no assignment occurrence in this statement.

Seek the partner by L4, then reject the candidate under G2 because the profile supplies no partner at the required
place. Leave <observed_source>'s relationship list empty for this example. Do not derive a new occurrence from line 91,
reuse a declaration occurrence, or write a record solely because the source contains the assignment text.

==================================================
9. EXCLUDE VERDICTS FROM EVERY OUTPUT FIELD
==================================================

Use none of these words in any output field.
asset, secret, confidential, integrity, availability, sensitive, critical, important, protect, trusted, untrusted,
privileged, vulnerable, vulnerability, exploit, threat, attacker, adversary, malicious, secure, insecure, security,
cwe, risk, leak, may, could, might, possibly, potentially, likely.

==================================================
10. CHECK THE COMPLETE ANSWER BEFORE RETURNING IT
==================================================

1. Check that every batch element appears exactly once in the correct array and in closed-set order. Check that no
   non-batch element object has been added and that each empty array or relationship list is retained.
2. Check that every at number is a supplied Occurrence ID of the element containing that record, not a line number
   or an Occurrence ID borrowed from its partner.
3. Check that every target belongs to the closed set and has its partner occurrence at the place required by section 4.
4. Check that each type is allowed for the SITE of every occurrence in its at array, follows section 3's precedence,
   and relates every listed occurrence to every listed target under G7.
5. Check every pair whose elements are both in the batch from both sides at their proper occurrences. Confirm each
   side against the source and profiles independently; do not add a record just to complete a pair.
6. Check that no input text has been copied into output prose: no condition, Path entry, source line or profile
   description. Retain the exact names, Occurrence IDs and applicable bits required by the output contract.
7. Check that functionality states the demonstrated logic in 1-2 sentences and <=45 words, without verdicts.
8. Check that no field from the program's list in section 2 appears in the output and that no forbidden word appears
   in any output field.
9. Check that the answer is one valid JSON object matching section 6, with no surrounding explanation or formatting.
