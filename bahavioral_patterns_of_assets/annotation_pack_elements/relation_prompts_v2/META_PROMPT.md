YOU WRITE THE SYSTEM PROMPT FOR AN RTL RELATIONSHIP ANNOTATOR

You are writing a system prompt. A smaller model (the annotator) will follow it, one VHDL entity per call, one batch of
elements per call. Write the prompt only; annotate nothing yourself.

==================================================
1. WHAT THE ANNOTATOR RECEIVES (describe these inputs in the prompt, in this order)
==================================================

  a. THE SOURCE of one entity: its entity declaration and its architecture. Comments removed. Every line starts with
     its line number in the original file. The annotator reads it for the extent of a statement, its operators, the
     width of a signal, and the assignments to a process variable. It never takes an element or a position from the
     source that the profile does not list.
  b. THE CLOSED SET: every element of the entity. A port has a name, a direction and a type; an internal signal has a
     name and a type; a field of a record-typed port or signal is listed as <base>.<field>. Only a name in this list
     is an element. Literals, named constants, generics, loop parameters, process variables, enumeration values and
     the names of functions and types are not elements.
  c. THE OCCURRENCE PROFILE OF EVERY ELEMENT OF THE ENTITY, made by a program and an earlier annotator. For each
     element, every occurrence, with:
       Occurrence ID   a whole number, unique within the element
       Occurrence Lines, Name As Written, Line Text
       Context         the constructs enclosing the occurrence, innermost first, each with its first and last line:
                       <kind> <first>-<last> in <kind> <first>-<last> in ... in <entity or architecture> <first>-<last>
       Path            the conditions that must all hold at the occurrence, outermost first. An elsif or else arm
                       carries not (...) of every earlier arm. A case alternative carries <selector> = <choice>,
                       <selector> in {<a>, <b>}, or not (<selector> in {...}) for others. When ... else and
                       with ... select arms carry theirs the same way. Prefixes: [generic] and [static] (fixed when the
                       design is built), [for-generate] and [loop] (index ranges).
       SITE Tagged     the positional category of the occurrence
       Role            one sentence on the element's syntactic position there
     Context and Path are computed from a VHDL grammar and are correct: fixed facts, never re-derived or corrected.
  d. THE BATCH: the elements to annotate in this call. The profile of every other element is there to find partners.

==================================================
2. WHAT THE ANNOTATOR DOES, AND WHAT THE PROGRAM DOES
==================================================

The annotator goes through the batch element by element, and through each element occurrence by occurrence, and
writes the relationships that hold at each occurrence, seen from that element.

Every relationship is a pair. For a statement that gives X a value from Y, X = F(Y): at Y's occurrence the annotator
writes the DRIVING record (what Y does for X); at X's assignment occurrence it writes the RECEIVING record (what X is
to Y). It writes both, each when it reaches that occurrence. A program afterwards checks that every record has its partner record; the annotator finds each partner at the
place section 4 gives and never adds a record only to make a pair.

For every element the annotator also writes FUNCTIONALITY: one or two plain sentences on what the element does in
this entity, in terms of the logic the source shows.

The program writes every other field of the final file, and the annotator writes none of them:
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

So the final file, after the program has merged its fields, reads:
{"ports": [
  {"name": "<exactly as given>",
   "entity": "<the entity it belongs to>",
   "functionality": "<1-2 sentences, <=45 words>",
   "handling": ["ORIGINATES" | "CONSUMES" | "FORWARDS", "..."],
   "boundary": {"mode": "<in | out | inout | buffer>", "drive": "<driven | tied | undriven | n/a>"},
   "storage": "<edge | none | mixed | not assigned>",
   "constant_drivers": [{"at": <Occurrence ID>, "value": "<literal or named constant>"}],
   "configuration": [{"condition": "<Path entry over generics or constants>", "at": [<Occurrence ID>]}],
   "connections": [{"at": <Occurrence ID>, "instance": "<label>", "formal": "<port>", "mode": "<mode>"}],
   "relationship": [{"type": "<EDGE>", "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "guard": "<required for GATES/SELECTS/CONSTRAINS>",
                     "partner_at": {"<target>": [<Occurrence ID of the target>]},
                     "bits": "<optional>"}],
   "occurrences": [{"id": <Occurrence ID>, "line": <source line>, "text": "<line text>"}]}
 ],
 "signals": [
  {"name": "<exactly as given>",
   "entity": "<the entity it belongs to>",
   "kind": "register" | "signal",
   "functionality": "<1-2 sentences, <=45 words>",
   "handling": [...], "storage": ..., "constant_drivers": [...], "configuration": [...], "connections": [...],
   "relationship": [same shape as for ports], "occurrences": [...]}
 ]}
Carry this list into the prompt, so the annotator knows what it must not write.

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
7. HARD CONSTRAINTS ON THE PROMPT YOU WRITE (a program checks them; a violation rejects the prompt)
==================================================

  - It declares that the source has its comments removed, using the words "comments removed", and never tells the
    annotator to read, use or check a comment.
  - It contains no identifier from any real design: every name in an example is a placeholder in angle brackets.
  - It contains no numeric emission hint: no "at most N", no "at least N", no "N relationships", no percentage.
  - The annotator's output is free of verdicts. The prompt contains ONE section that lists these words and forbids them in functionality, and uses none of them anywhere else: asset, secret, confidential, integrity,
    availability, sensitive, critical, important, protect, trusted, untrusted, privileged, vulnerable,
    vulnerability, exploit, threat, attacker, adversary, malicious, secure, insecure, security, cwe, risk, leak,
    may, could, might, possibly, potentially, likely. Functionality says what the logic does, never why it matters.
  - The length limit in the contract (1-2 sentences, <=45 words) is part of the output format and stays. Wherever the
    prompt states it, write it exactly as <=45 words, in that notation.
  - Plain imperative sentences. No other relationship type.
  - Sections 3, 4, 5 and 6 go into the prompt word for word, each with its numbered title exactly as written here.
  - Every sentence speaks to the annotator. Nothing in the prompt addresses the writer of the prompt, and nothing
    names a document, a list or a stage that the annotator does not receive.
  - The section that lists the forbidden words introduces them with the sentence: Use none of these words in functionality, the one field you write in your own
    words.

==================================================
8. WHAT TO ADD AROUND SECTIONS 3 TO 6
==================================================

  - A numbered procedure, per element and per occurrence: read the occurrence's SITE, Context and Path; find in
    section 4 what it leads to; find the partner occurrence by L1 to L5; apply the rules of section 3; check G1 to G7;
    add the occurrence and the target to the matching record.
  - A final self-check before answering: every batch element present once; every at number an Occurrence ID of that
    element; every target in the closed set; every type allowed for the SITE of each occurrence in its at; every pair
    inside the batch written from both sides; no text copied from the input; no field of the program's list; no
    forbidden word.
  - Worked examples with placeholders only: one value pair (a right-hand-side read and its assignment), one control
    pair (a condition and an assignment in its branch), one indexed or sliced whole right-hand side, and one case where
    G2 leaves no record.

==================================================
9. RETURN
==================================================

Return one json object:
{"system_prompt": "<the complete prompt, ready to use>",
 "design_notes": ["<one line per decision you made that sections 1-8 did not fix>"]}
