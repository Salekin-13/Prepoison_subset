Annotate RTL relationships for one VHDL entity and one batch per call. Use the supplied inputs to identify relationships, and return only the JSON object specified in section 6.

==================================================
1. READ THE INPUTS
==================================================

Read these inputs in this order:

  a. THE SOURCE
     Read the entity declaration and architecture of one entity, with comments removed. Treat the number at the start
     of every line as its line number in the original file. Read the source for statement extents, operators, signal
     widths and assignments to process variables. Never take an element or an occurrence position from the source
     that the profile does not list.

  b. THE CLOSED SET
     Use the supplied list of every element of the entity. Read each port's name, direction and type, and each internal
     signal's name and type. Treat a listed field of a record-typed port or signal, written <base>.<field>, as an
     element. Treat only names in this list as elements. Exclude literals, named constants, generics, loop parameters,
     process variables, enumeration values, and function and type names from the set of elements.

  c. THE OCCURRENCE PROFILE OF EVERY ELEMENT OF THE ENTITY
     Read the profile supplied by the program and an earlier annotator. For every element, read every occurrence and
     these fields:
       Occurrence ID   Read a whole number unique within that element; do not confuse it with a source line number.
       Occurrence Lines, Name As Written, Line Text
                       Use these fields to locate the supplied occurrence in the source.
       Context         Read the enclosing constructs, innermost first, each with its first and last line:
                       <kind> <first>-<last> in <kind> <first>-<last> in ... in <entity or architecture> <first>-<last>
       Path            Read the conditions that must all hold at the occurrence, outermost first. Read an elsif or
                       else arm as carrying not (...) of every earlier arm. Read a case alternative as carrying
                       <selector> = <choice>, <selector> in {<a>, <b>}, or not (<selector> in {...}) for others.
                       Read when ... else and with ... select arms in the same way. Interpret [generic] and [static]
                       as fixed when the design is built, and [for-generate] and [loop] as index ranges.
       SITE Tagged     Read the positional category of the occurrence.
       Role            Read the sentence describing the element's syntactic position there.
     Accept Context and Path as correct, fixed facts computed from a VHDL grammar. Never re-derive or correct them.

  d. THE BATCH
     Annotate only the elements in this call's batch. Use every other element's profile to find partner occurrences,
     not to add elements to the output.

==================================================
2. SEPARATE YOUR WORK FROM THE PROGRAM'S WORK
==================================================

Go through the batch element by element, and through each element occurrence by occurrence. Write the relationships
that hold at each occurrence, seen from that element.

Treat every relationship as a pair. For a statement that gives X a value from Y, X = F(Y), write the DRIVING record
at Y's occurrence and the RECEIVING record at X's assignment occurrence. Write each side when you reach its element
and occurrence in the batch. Use profiles outside the batch to find partners without writing output entries for those
elements. Expect the program afterwards to check that every record has its partner. Find each partner yourself at the place
section 4 gives, and never add a record solely to make a pair.

For each batch element, write functionality as 1-2 sentences, <=45 words. Describe what the element does in this entity
in terms of the logic the source shows. State what the logic does, never why it matters.

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
  occurrences       every Occurrence ID of the element with its source line number and line text
  entity            the entity the element belongs to, since one file can hold several
  partner_at        inside each relationship record: for each target, the Occurrence IDs of the partner record

==================================================
3. THE RELATIONSHIP PAIRS
==================================================

Read "X's assignment" as an occurrence of X tagged LHS_PROC or LHS_CONC, or X as the target of a when ... else or
with ... select assignment, and "its Path" as that occurrence's Path. Wherever this section speaks of a condition in X's Path, a
condition of the when ... else statement that assigns X counts as well (L5); the supplied Path stays unchanged. "On a clock edge" means an edge function
(rising_edge(<clk>), falling_edge(<clk>), or <clk>'event and <clk> = <literal>) appears in that Path without
not (...) around it.

  driving (at Y)   receiving (at X)   the pair holds when
  CARRIES          COPIES             X's right-hand side is exactly Y: no operator, slice, index or conversion.
  SOURCES          DERIVES_FROM       Y's value is read on X's right-hand side in any other way: an operand, a function
                                      argument, an array element read, a slice, an indexed name, or the value arm of a
                                      when ... else or with ... select assignment.
  SEQUENCES        CLOCKED_BY         Y is the argument of the edge function that puts X's assignment on a clock edge.
  RESETS           RESET_BY           Y is tested in an arm of the same if statement as that edge function, the arm
                                      comes before the edge arm, and X's assignment is in that arm and gives X a literal
                                      or a named constant.
  SELECTS          SELECTED_BY        Y is the selector of the case statement or the with ... select assignment whose
                                      alternative holds X's assignment; or an index computed while the design runs
                                      that picks which part of an array is read into X, or written when X is the
                                      array.
  CONSTRAINS       CONSTRAINED_BY     Y is compared (=, /=, <, <=, >, >=) with an expression that contains another
                                      element, and that comparison is a condition in X's Path. Every element on either
                                      side of the comparison carries it.
  GATES            GATED_BY           Y decides whether X takes a value, or forces it to a fixed level. Its form is
                                      condition: Y appears in an if, elsif or when ... else condition in X's Path, or
                                      in an earlier arm's condition that the Path negates (never a reset arm, rule 3), used bare or compared with a
                                      literal or a named constant; or operand: Y is a single-bit operand, bare or as
                                      not Y, of a top-level and, or, nand or nor on the right-hand side of a single-bit
                                      X.

ONE TYPE PER PAIR OF OCCURRENCES
  1. For one occurrence of Y and one assignment of X, keep the first that applies: SEQUENCES, RESETS, SELECTS,
     CONSTRAINS, GATES, CARRIES, SOURCES. Its partner is the matching receiving type.
  2. The clock is only SEQUENCES: an edge function in X's Path is never GATES.
  3. The reset is only RESETS: a reset arm that X's Path negates is not GATES. An arm inside the edge arm that
     assigns constants is not a reset arm: the other rules type its condition, never as RESETS.
  4. An entry <selector> = <choice>, <selector> in {...} or not (<selector> in {...}) in the Path is only SELECTS.
  5. In a condition of X's Path, Y compared with another element is CONSTRAINS; compared with a literal or a named
     constant it is GATES.
  6. A condition over generics or named constants alone gives no relationship.
  7. An index built from an element is SELECTS; an index built only from literals, named constants, generics or loop
     parameters goes in bits. A run-time index is SELECTS, and a fixed slice written on it still goes in bits: in
     <dst> <= <array>(to_integer(<idx>(7 downto 2))), <idx> SELECTS <dst> with bits 7 downto 2. The array that is
     read is SOURCES.
  8. An attribute prefix such as <elem>'length reads the shape, not the value: no relationship.
  9. An element that feeds or decides itself writes both records of the pair on itself.
 10. A choice of a case or with ... select (a literal, a named constant, a range or others) is never Y.

PROCESS VARIABLES are not elements. Where X's assignment reads a variable, the pairs go from the elements the variable
was computed from, in the same process, to X: an element read in the variable's assignment takes the type rules 1 to 10 give it as though it
were read in X's statement: SOURCES X, GATES it (operand form), or SELECTS it as a run-time index; an element in a condition or a selector governing that variable assignment takes the type that rules 1
to 10 give it, as though that condition or selector were in X's Path. Inside a loop this holds for every assignment to
the variable in the loop body. The driving record sits at the element's occurrence in the variable's assignment, or in
the condition or selector.

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
                                                  that comes before the edge arm, and no record to X's assignments in
                                                  the later arms of that if (rule 3); otherwise CONSTRAINS or GATES
                                                  (condition), to every X assigned in the same branch and, through its
                                                  negation, in the later arms (L2); a variable assigned there passes it
                                                  on to every X that reads the variable (section 3)
  WHEN_COND                     Y                 CONSTRAINS or GATES (condition), to the target of its statement (L5)
  CASE_EXPR                     Y                 SELECTS, to every X assigned in the same case (L3)
  (the selector of a with ... select, written between with and select; it has no SITE of its own)
                                Y                 SELECTS, to the target of that assignment (L4)
  INDEX                         Y                 SELECTS, when the index is computed while the design runs, to the
                                                  target of the statement or the array written (L4); in a
                                                  variable's assignment, to each X that reads the variable
                                                  (section 3)
  DIRR_ASS                      Y                 CARRIES, to the target of the statement (L4)
  RHS_OPERAND                   Y                 GATES (operand), when Y is single-bit and bare or
                                                  not Y under a top-level and, or, nand or nor of a single-bit X;
                                                  otherwise SOURCES; to the target of the statement (L4)
  WHEN_EXPR                     Y                 SOURCES, to the target of its statement (L4)
  VAR_RHS_OPERAND, or an empty  Y                 SOURCES (or GATES, operand form), to each X whose assignment reads
  SITE list on the right-hand                     that variable (section 3)
  side of a variable assignment
  INDEXED_NAME or PART_SELECT   Y                 SOURCES, to the target of the statement (L4), with a fixed index or the
  standing alone on a right-                      slice in bits: an indexed or sliced whole right-hand side carries no
  hand side                                       other SITE
  INDEXED_NAME or PART_SELECT   (add-on)          no record of its own: it goes with the occurrence's other SITE, and
  with another SITE                               a fixed index or the slice goes in bits
  LHS_PROC, LHS_CONC            X                 the receiving record of every pair that ends at this assignment:
                                                  COPIES or DERIVES_FROM for each element whose value
                                                  the statement reads (one type per pair, section 3), or,
                                                  where the statement reads a process variable, each element the
                                                  variable was computed from (L4); CLOCKED_BY, RESET_BY, SELECTED_BY,
                                                  CONSTRAINED_BY or GATED_BY for each element in a condition or a
                                                  selector of its Path (section 3; none for a negated reset
                                                  arm, rule 3), or of the Path of the variable
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
      statement, the same branch, the same case, the condition of an earlier arm of the same if, or, through a process
      variable, the variable's assignment in the same process and the assignment of X that reads it (section 3).
      Where it lists none, there is no relationship.
  G3  The type is one that section 4 allows for the SITE of every occurrence listed in at.
  G4  Copy no condition, no Path entry and no line from the profile or the source into the output;
      input text appears in the output only as exact names and as bits. The program
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

<EDGE> is one of the fourteen types of section 3, written as a JSON string holding the bare name. The object above
is a schematic: each angle-bracketed placeholder and each "..." stands for real values, and each Occurrence ID is
a JSON number. The relationship list holds the relationship records
of section 3: each record is one type, the elements it relates this element to, and the occurrences where it holds.
A batch element listed as a port, a port's field included, goes in "ports"; an internal signal, a signal's field
included, goes in "signals". Every batch element appears exactly once, in its array, in closed-set order; an array
with no batch element is empty. An element with no relationship gets an empty relationship list. Group records by type
and bits only as far as G7 allows: where the occurrences of one type and bits do not all relate to the same targets,
write several records of that type and bits. List no occurrence that has
no relationship. bits holds the fixed index or slice written at this element's own occurrence, as the source writes it;
omit bits where that occurrence has none. The two forms of GATES share the one type. Write no field of the program's list in section 2: not kind,
handling, guard, boundary, storage, constant_drivers, configuration, connections, occurrences, partner_at or entity.

==================================================
7. RESOLVE THE PAIRS FIRST, THEN WRITE THE BATCH
==================================================

Treat each relationship as one pair between two occurrences: the occurrence of Y and the assignment occurrence of X.
A record in the output is one side of such a pair. Decide the pair, then write its sides; never decide one side on
its own.

PASS A: resolve the pairs that touch a batch element
  1. For each batch element, go through its occurrences. For each occurrence that section 4 gives a record, find the
     partner occurrence by L1 to L5 in the complete profiles, including the profiles of elements outside the batch.
     Match branch and case frames by kind and both line endpoints; take statement extent, operators and widths from
     the source; follow a process variable to its assignments in the same process (section 3). The batch limits what
     you write, never where you look.
  2. Where the profile lists no partner occurrence at the place section 4 gives, there is no pair and no record (G2).
  3. With both occurrences found, choose the type of the pair once, by section 3: the first of SEQUENCES, RESETS,
     SELECTS, CONSTRAINS, GATES, CARRIES, SOURCES that applies, with its exclusions.
  4. Read both sides from the same row of the table in section 3: the driving type at Y's occurrence, the receiving
     type at X's assignment. Never choose the receiving type separately.
  5. Keep each resolved pair in mind as: Y's occurrence, X's assignment occurrence, the row. A pair whose other side
     belongs to an element outside the batch is resolved all the same; that side is written in the call whose batch
     holds its element.

PASS B: write the batch
  6. For every resolved pair, write the driving record where Y is a batch element and the receiving record where X is
     a batch element. At an assignment occurrence write only a receiving type; at any other occurrence write only a
     driving type.
  7. Add the current Occurrence ID and the partner's exact closed-set name to the matching type-and-bits record only
     when every listed occurrence relates to every listed target (G7); otherwise create a separate record. Add bits
     only where the rules call for them, and never add a guard.
  8. After all pairs are written, write each batch element's functionality from the logic its occurrences show, and
     keep an empty relationship list for an element with no pair.

==================================================
8. APPLY THE RULES TO THESE WORKED EXAMPLES
==================================================

Treat all angle-bracketed names below as placeholders. Treat the displayed integers in at as example Occurrence IDs,
not source line numbers. Assume the elements in each paired-record example belong to the batch. Use the examples to
apply the rules, not to infer facts about the supplied entity.

A. Follow a whole-value pair.

Read this example statement:
  <dst> <= <src>;

Use the listed occurrence 7 of <src>, tagged DIRR_ASS, and the listed occurrence 12 of <dst>, tagged LHS_CONC, in that
same statement. Apply L4. Choose CARRIES and COPIES because the whole right-hand side is exactly <src>.

Write this record at <src>:
  {"type": "CARRIES", "targets": ["<dst>"], "at": [7]}
Write this record at <dst>:
  {"type": "COPIES", "targets": ["<src>"], "at": [12]}

B. Follow a condition pair.

Read this example statement inside a process:
  if <enable> = '1' then
    <dst> <= '0';
  end if;

Use the listed occurrence 4 of <enable>, tagged IF_COND, and the listed occurrence 9 of <dst>, tagged LHS_PROC. Use the
same branch frame supplied in their Contexts and the supplied condition in <dst>'s Path. Assume no edge function in
this if statement. Apply L1 and L2. Choose GATES and GATED_BY because <enable> is compared with a literal in the
condition governing the assignment, without satisfying the reset rule.

Write this record at <enable>:
  {"type": "GATES", "targets": ["<dst>"], "at": [4]}
Write this record at <dst>:
  {"type": "GATED_BY", "targets": ["<enable>"], "at": [9]}
Leave guard and constant_drivers to the program.

C. Follow a sliced whole right-hand side.

Read this example statement:
  <dst> <= <array>(7 downto 4);

Use the listed occurrence 23 of <array>, tagged PART_SELECT with no other SITE, and the listed occurrence 24 of <dst>,
tagged LHS_CONC, in the same statement. Apply L4 and the standalone PART_SELECT entry in section 4. Choose SOURCES,
not CARRIES, because the whole right-hand side is a slice. Put the fixed slice range in bits.

Write this record at <array>:
  {"type": "SOURCES", "targets": ["<dst>"], "at": [23], "bits": "7 downto 4"}
Write the matching receiving record at occurrence 24 of <dst> with type DERIVES_FROM and target <array>. Do not treat
the literal slice bounds as elements or add SELECTS for them.

D. Reject a proposed pair under G2.

Read these separate example statements:
  <dst> <= '0';
  <other> <= <src>;

Use the listed occurrence 6 of <dst>, tagged LHS_CONC, in the first statement. Use the listed occurrence 15 of <src>,
tagged DIRR_ASS, and occurrence 16 of <other>, tagged LHS_CONC, in the second statement. Assume no condition, selector
or process-variable flow connects <src> to <dst>.

Test a proposed pair from <src> to <dst>. Apply L4 and G2: find no listed assignment occurrence of <dst> in <src>'s
statement, and write no record for that pair. Keep the evidenced value pair between <src> and <other> separate. Under
only the shown logic, give <dst> an empty relationship list; leave its literal driver to the program.

E. Tell a value arm from a copy.

Read this example statement:
  <dst> <= <src> when <cond> = '1' else <other>;

<src> is the chosen expression of a when ... else, not the whole right-hand side, so the pair from <src> to <dst> is
SOURCES and DERIVES_FROM, never CARRIES and COPIES. <other>, in the alternative expression, is SOURCES and
DERIVES_FROM too. <cond>, compared with a literal in the when condition, is GATES and GATED_BY. At <dst>'s assignment
write DERIVES_FROM with targets <src> and <other>, and GATED_BY with target <cond>; at <src> write SOURCES with target
<dst>.

F. Keep each side at its own occurrence.

Read these example statements inside a process:
  case <state> is
    when <state_a> => <ack> <= '1';

The pair from <state> to <ack> is SELECTS and SELECTED_BY. Write SELECTS at <state>'s occurrence in the case
expression, and SELECTED_BY with target <state> at <ack>'s assignment. Never write SELECTS or GATES at <ack>'s
assignment: an assignment occurrence takes only receiving types. The literal gets no record.

G. Resolve the clock and the reset of a register whose partner lies outside the batch.

Read these example statements inside a process:
  if <rst> = '0' then
    <q> <= '0';
  elsif rising_edge(<clk>) then
    <q> <= <d>;
  end if;

The pairs are: <rst> to the first assignment of <q>, RESETS and RESET_BY; <clk> to the second assignment of <q>,
SEQUENCES and CLOCKED_BY; <d> to the second assignment of <q>, CARRIES and COPIES. <rst> gives no GATES pair on the
second assignment (rule 3). Where only <clk> belongs to the batch, find <q>'s second assignment before writing
SEQUENCES at <clk>; <q>'s CLOCKED_BY is written in the call whose batch holds <q>, from the same row.

==================================================
9. EXCLUDE VERDICTS
==================================================

Use none of these words in functionality, the one field you write in your own words.
asset, secret, confidential, integrity, availability, sensitive, critical, important, protect, trusted, untrusted,
privileged, vulnerable, vulnerability, exploit, threat, attacker, adversary, malicious, secure, insecure, security,
cwe, risk, leak, may, could, might, possibly, potentially, likely.

==================================================
10. CHECK BEFORE ANSWERING
==================================================

  1. Check that every batch element appears exactly once, in the correct array and in closed-set order. Check that no
     element outside the batch has an output entry and that an array without batch elements is empty.
  2. Check that every number in at is a listed Occurrence ID of the element containing that record.
  3. Check that every target is an exact name from the closed set and has a partner occurrence at the place required
     by section 4.
  4. Check that every type is allowed for the SITE of every occurrence in its at and follows section 3's priority.
  5. Check that every evidenced pair inside the batch is written from both sides, including a pair on one element
     itself. Recheck evidence rather than inventing a record to complete a pair.
  6. Check G7 for every grouped record, and check that bits is omitted where it does not apply.
  7. Check compliance with G4: include no condition, Path entry or source line; input text appears only as
     exact names and bits.
  8. Check that functionality describes the shown logic in 1-2 sentences, <=45 words, without explaining why it matters.
  9. Check that no field from the program's list in section 2 appears in the output.
 10. Check that no word listed in section 9 appears in functionality.
 11. Return valid JSON in the exact shape of section 6, without surrounding prose or formatting fences.