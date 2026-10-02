Annotate RTL relationships for one VHDL entity and one batch per call. Use only the supplied inputs. Return only the object specified in section 6.

1. INPUTS

Read these inputs in this order:

  a. THE SOURCE. Read the entity declaration and its architecture, with comments removed. Treat the number at the start of every line as its line number in the original file. Use the source to determine statement extents, operators, signal widths and assignments to process variables. Never take an element or a position from the source that the profile does not list.

  b. THE CLOSED SET. Treat this list as the complete set of elements of the entity. Read a port's name, direction and type, and an internal signal's name and type. Read each field of a record-typed port or signal as the listed element <base>.<field>. Treat only names in this list as elements. Exclude literals, named constants, generics, loop parameters, process variables, enumeration values and the names of functions and types from the elements.

  c. THE OCCURRENCE PROFILE OF EVERY ELEMENT OF THE ENTITY. Read the profile made by a program and an earlier annotator. For each element, read every occurrence and its fields:
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
     Accept Context and Path as correct fixed facts computed from a VHDL grammar. Never re-derive or correct them.

  d. THE BATCH. Annotate only the elements listed for this call. Use the profiles of all other elements to find partners. Do not emit element entries for elements outside the batch.

2. RESPONSIBILITIES

Go through the batch element by element, and through each element occurrence by occurrence. Write the relationships that hold at each occurrence, seen from that element.

Treat every relationship as a pair. For a statement that assigns a value to <X> from <Y>, write the driving record at <Y>'s occurrence and the matching receiving record at <X>'s assignment occurrence. Write each side when you reach its element and occurrence. Use section 4 to locate the partner. Expect the program to check every record for its partner record and return a record without a partner for checking. Never create a relationship merely to satisfy that check.

Write functionality for every batch element as one or two plain sentences about what the element does in this entity, in terms of the logic shown by the source. Describe what the logic does, never why it matters.

Leave every field below to the program. Write none of them:
  kind              for an internal signal: register (assigned on a clock edge) or signal
  handling          for a record field (a dotted name): any of ORIGINATES, CONSUMES, FORWARDS
  guard             for each control relationship: the condition it comes from, read from the Path
  boundary          for a port: its mode, and whether an outward port is driven, tied or undriven
  storage           whether the element's assignments are on a clock edge
  constant_drivers  the literals or constants that are the element's whole value, where they are
  configuration     the conditions over generics and constants under which the element is declared or driven
  connections       the element's wiring to the ports of instantiated sub-blocks, both directions

Read this as the final file's layout after the program merges its fields, not as your output contract:
  {"ports":   [{"name", "functionality", "handling", "boundary", "storage", "constant_drivers", "configuration",
                "connections", "relationship": [{"type", "targets", "at", "form", "bits", "guard"}]}],
   "signals": [{"name", "kind", "functionality", "handling", "storage", "constant_drivers", "configuration",
                "connections", "relationship": [{"type", "targets", "at", "form", "bits", "guard"}]}]}

3. THE RELATIONSHIP PAIRS

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

4. FROM SITE TO RELATIONSHIP

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

5. GUARDS AGAINST INVENTED RELATIONSHIPS

  G1  Every number in at is an Occurrence ID of the current element listed in the profile, and every name in targets
      is an element of the closed set.
  G2  Write a record only where the profile lists an occurrence of the partner at the place section 4 gives: the same
      statement, the same branch, the same case, or the condition of an earlier arm of the same if. Where it lists
      none, there is no relationship.
  G3  The type is one that section 4 allows for the SITE of every occurrence listed in at.
  G4  Copy no text from the profile or the source into the output: no condition, no Path entry, no line. The program
      reads the condition of every control relationship from the Path.
  G5  Positions come from the profile and operators from the source, never from a name. What an element is called
      decides nothing: two elements with telling names and no statement between them have no relationship.
  G6  Where the profile and the source do not show a relationship, write none. No record is written to complete a
      pattern, to match a record elsewhere, or because a partner record is expected.
  G7  A record lists several occurrences in at, or several names in targets, only where the relationship holds
      between EVERY listed occurrence and EVERY listed target.

6. THE OUTPUT CONTRACT

Return one JSON object and nothing else:

{"ports": [
  {"name": "<exactly as given>",
   "functionality": "<1-2 sentences, <=45 words>",
   "relationship": [{"type": "<one of the fourteen types of section 3>",
                     "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "form": "<condition | operand -- GATES and GATED_BY only, omit otherwise>",
                     "bits": "<optional>"}]}
 ],
 "signals": [
  {"name": "<exactly as given>",
   "functionality": "<1-2 sentences, <=45 words>",
   "relationship": [{"type": "<one of the fourteen types of section 3>",
                     "targets": ["<name>", "..."],
                     "at": [<Occurrence ID of this element>],
                     "form": "<condition | operand -- GATES and GATED_BY only, omit otherwise>",
                     "bits": "<optional>"}]}
 ]}

A batch element listed as a port, a port's field included, goes in "ports"; an internal signal, a signal's field
included, goes in "signals". Every batch element appears exactly once, in its array, in closed-set order; an array
with no batch element is empty. An element with no relationship gets an empty relationship list. Group records: one
record per type, form and bits, listing every occurrence and every target it holds for (G7). List no occurrence that
has no relationship. Omit form except for GATES and GATED_BY, and omit bits where it does not apply. Write no field of
the program's list in section 2: not kind, handling, guard, boundary, storage, constant_drivers, configuration or
connections.

7. OUTPUT LANGUAGE

Do not use any of the following words in any output field, regardless of letter case:
asset, secret, confidential, integrity, availability, sensitive, critical, important, protect, trusted, untrusted, privileged, vulnerable, vulnerability, exploit, threat, attacker, adversary, malicious, secure, insecure, security, cwe, risk, leak, may, could, might, possibly, potentially, likely.

Write factual descriptions of the implemented logic. State what the logic does, never why it matters. Omit verdicts and speculation.

8. PROCEDURE

  1. Visit each batch element in closed-set order. Put its entry in the array required by section 6. Start with an empty relationship list.
  2. Visit each listed occurrence of the current element. Read its SITE, Context and Path. Keep its Occurrence ID distinct from source line numbers. Read the source only for the statement extent, operators, widths and process-variable computations needed for that occurrence.
  3. Find the occurrence's SITE in section 4. Determine whether to write driving records, receiving records or none. Treat an add-on SITE as an add-on rather than a separate relationship.
  4. Find each partner occurrence in the profiles by L1 to L5. Match frame kind and both frame endpoints where a frame match is required. Match the complete statement where a statement match is required. Follow process-variable computations as specified in section 3. Use the field's own occurrence for a record field, never its base occurrence.
  5. Apply section 3 to each pair of occurrences. Apply its precedence order before selecting the type. Use the matching receiving type at an assignment occurrence. Distinguish condition and operand forms for GATES and GATED_BY. Put applicable fixed indices or slices in bits, not in targets.
  6. Check G1 to G7 for each proposed record. Discard any proposed relationship without the required evidence. Do not use the existence of another record as evidence for a pair.
  7. Add the current element's Occurrence ID and the partner element's exact name to the matching type, form and bits record. Merge only groups that satisfy G7; keep other groups separate. Order each at list by Occurrence ID and each targets list by closed-set order.
  8. Repeat for every occurrence of the element. Write its functionality from the implemented logic. Repeat for every batch element, including elements with empty relationship lists.

9. WORKED EXAMPLES

Treat every name in these examples as a placeholder. Replace each Occurrence ID placeholder with the whole-number ID supplied by the profile when producing actual output. Use the examples to apply the rules, not to infer missing occurrences.

VALUE PAIR

Use the statement pattern:
  <X> <= <Y>;

Take <X> and <Y> as closed-set elements. Use <Y>'s listed DIRR_ASS occurrence <Y-read-ID> and <X>'s listed LHS_CONC occurrence <X-write-ID> in that same statement. Apply L4 and the exact-right-hand-side rule. Write this record when visiting <Y>:
  {"type": "CARRIES", "targets": ["<X>"], "at": [<Y-read-ID>]}
Write its receiving record when visiting <X>:
  {"type": "COPIES", "targets": ["<Y>"], "at": [<X-write-ID>]}
Use each current element's own Occurrence ID in at, not the partner's ID.

CONTROL PAIR

Use the statement pattern:
  if <C> = <literal> then
    <X> <= <literal>;
  end if;

Take <C> and <X> as closed-set elements and <literal> as a literal, not an element. Use <C>'s listed IF_COND occurrence <C-condition-ID> and <X>'s listed LHS_PROC occurrence <X-write-ID>. Take the condition occurrence's innermost frame and the assignment's containing branch frame as identical. Take the assignment's Path to contain the condition and take the if statement to contain no edge function. Apply L1 and L2, and classify the literal comparison as condition-form gating. Write this record when visiting <C>:
  {"type": "GATES", "targets": ["<X>"], "at": [<C-condition-ID>], "form": "condition"}
Write its receiving record when visiting <X>:
  {"type": "GATED_BY", "targets": ["<C>"], "at": [<X-write-ID>], "form": "condition"}
Write no target for <literal> and no condition text in either record.

SLICED WHOLE RIGHT-HAND SIDE

Use the statement pattern:
  <X> <= <Y>(<high> downto <low>);

Take <X> and <Y> as closed-set elements and <high> and <low> as fixed named constants outside the closed set. Use <Y>'s listed PART_SELECT occurrence <Y-slice-ID>, with no other SITE, and <X>'s listed LHS_CONC occurrence <X-write-ID> in the same statement. Apply L4 and the standalone PART_SELECT rule. Write this driving record when visiting <Y>:
  {"type": "SOURCES", "targets": ["<X>"], "at": [<Y-slice-ID>], "bits": "<high> downto <low>"}
Use DERIVES_FROM for the receiving partner at <X-write-ID>, targeting <Y>. Do not classify the slice as CARRIES or create SELECTS records for its fixed bounds.

NO PARTNER UNDER G2

Use a listed IF_COND occurrence <C-condition-ID> of <C> in a branch containing only null, with no later arm and no variable assignment. Take <X>'s only assignment occurrence to be in a different process. Take the profile to list no assignment in the frame opened by <C>. Apply L1 and L2, then G2. Write no relationship for <C-condition-ID>; do not link it to <X> merely because <X> has an assignment elsewhere. Keep <C>'s relationship list empty if no other occurrence of <C> supports a pair.

10. FINAL SELF-CHECK

Before answering, check all of the following:

  - Check that every batch element appears exactly once, in the correct array and in closed-set order, and that no element outside the batch has an entry.
  - Check that every number in at is a listed Occurrence ID of the current element, not a source line number or a partner's ID.
  - Check that every target is an exact closed-set element name and has a partner occurrence at the place required by section 4.
  - Check that every type is allowed for the SITE of every occurrence in its at list and that section 3's precedence rules hold.
  - Check that every grouped record satisfies G7 for every listed occurrence and every listed target.
  - Check that every pair whose elements are both in the batch is written from both sides at the corresponding occurrences. Recheck the evidence for any missing side; never add an unsupported pair to complete it.
  - Check that no input condition, Path entry, line or profile prose is copied into the output. Retain only the exact names, Occurrence IDs and applicable bits required by the output format.
  - Check that functionality describes the implemented logic within the format in section 6.
  - Check that no field from the program's list in section 2 is present, that form and bits obey section 6, and that no word forbidden in section 7 appears in any output field.
  - Check that the response is valid JSON and contains only the object required by section 6.

Return the JSON object and nothing else.