The goal is to reproduce a human annotator's reasoning:

  - take every occurrence of each closed-set element in the RTL,
  - find the VHDL structures that enclose it,
  - determine the syntactic construct containing that occurrence,
  - determine the element's role within that construct,
  - assign the SITE tag or tags given by the rulebook,
  - record the result in a JSON occurrence table.

Do not infer anything from comments, identifiers, naming conventions, or general design intent.
The RTL syntax gives the answer.

==================================================
A. AUTHORITATIVE INPUTS
==================================================

SOURCE 1: ANNOTATION RULEBOOK (section N)
The rulebook is the complete and authoritative taxonomy. For every SITE it gives a trigger, the
required structures, the context and the exclusions. Its conflict rules say how look-alike SITEs
are told apart, and which SITEs are written together for one occurrence.

Use ONLY the SITE tags the rulebook defines.
Do not create new SITE tags.
Do not rename SITE tags.
Do not replace a SITE tag with a synonym.

If an intuitive interpretation conflicts with the rulebook, follow the rulebook.

Sections B to M of these instructions apply the rulebook. Where they and the rulebook differ,
follow the rulebook.

SOURCE 2: CLOSED SET
The closed set is the complete list of elements whose occurrence profiles must be generated.

Only a name that appears in the list of elements given to you gets a site. Every other name
gets none: literals, named constants, aggregates, generics, loop parameters, enumeration
values, and the names of functions and types.

Do not add elements merely because they appear in the RTL.

SOURCE 3: RTL
The RTL source is the only source from which occurrences, their structures, their sites and their
roles are determined.

==================================================
B. COMMENT HANDLING
==================================================

Comments beginning with "--" were removed from the source before it was given to you. Line
numbers are unchanged. Blank lines and lines that held only a comment are not shown.

If any comment text remains, ignore it. A commented-out occurrence is NOT an occurrence.

==================================================
C. UNIT OF ANNOTATION
==================================================

A program has already listed the occurrences in the OCCURRENCE INVENTORY. Each has an Occurrence
ID, its line, and the name as written there. The program follows these rules:

1. An occurrence is the element's name written as a whole name. VHDL reads upper and lower case
   letters in a name as the same.
2. These are not occurrences of the element:
   - a part of a longer identifier,
   - the same field name reached through a different base,
   - a similarly named identifier,
   - a name in the port clause of a component declaration, which declares a port of a
     different entity,
   - a name to the left of => in a port map or in a named association, which names the port or
     the field being associated, not the element. A name to the right of => is an occurrence
     where it is an element.
3. A field of a record occurs on the line that declares its base, and wherever <base>.<field> is
   written.
4. Each occurrence is its own entry, even where several share a line.

For every occurrence, identify:
   a. its enclosing structures (section D),
   b. the statement that contains it,
   c. the role of the element in that statement,
   d. the applicable SITE tag or tags.

==================================================
D. STRUCTURAL NAVIGATION
==================================================

The SITE rules say what role an occurrence has. This section says where it is: which VHDL
structures enclose its line, and the first and last line of each. Find the structures with this
section before you apply any SITE rule, and report them in the Structure field.

LINES

The source shows only lines that hold code; blank lines and comment-only lines are left out. A
span is given with the line numbers shown in the source: the first shown line of the structure
and the last shown line of the structure. A structure contains its own first and last line.

THE STRUCTURES TO REPORT

Report every structure of these kinds whose span contains the line of the occurrence, from the
outermost to the innermost. Use the kind names exactly as written here.

  port clause
    From the line with port ( in the entity declaration to the line with the ) that closes it.
    Count ( and ) to find that ): parentheses inside a type, as in
    std_ulogic_vector(<high> downto <low>), open and close inside the clause. A port clause inside
    a component declaration is not reported.

  declarative part
    From the first shown line after the architecture header,
    architecture <architecture_name> of <entity_name> is, to the last shown line before the
    architecture's begin.

  architecture body
    From the architecture's begin line to its end line.

  generate
    From the generate statement's first line to its matching end generate line. Its first line is
    its label line where the label stands alone on the line above the for ... generate or
    if ... generate line; otherwise it is the generate line itself.

  process
    From the process statement header to the first end process after it. A process block cannot
    hold another process.

  loop
    From the for ... loop or while ... loop line to its matching end loop line.

  if
    From the if line to its matching end if line.

  branch
    One branch of an if statement: from its if, elsif or else line to the last shown line before
    the next elsif, else or end if of the same if statement.
    "opened by": EDGE_CHECK where the condition holds rising_edge(...) or falling_edge(...);
    IF_COND for any other if or elsif condition; else for an else branch.

  case
    From the case ... is line to its matching end case line.

  alternative
    One alternative of a case statement: from its when <choice> => line to the last shown line
    before the next alternative of the same case statement, or before its end case.
    "opened by": the choice, as written.

  association list
    From the line with port map ( or generic map ( to the line with the ) that closes it,
    counting ( and ) as for a port clause.

NOT STRUCTURES

  - The else of a when ... else conditional assignment opens no branch, on whichever line it is
    written.
  - A when that is not written as when <choice> => at the start of a line, such as the when of a
    conditional assignment or of exit when, starts no alternative.
  - An if ... generate is a generate statement, not an if statement; it ends with end generate.
  - Component declarations, record type declarations and instantiation statements are not
    reported; only the association lists inside an instantiation are.

MATCHING NESTED STRUCTURES

Structures of the same kind can sit inside one another. To find the end of a structure, read down
from its first line and count:
  - each if adds one and each end if takes one away; elsif and else change nothing;
  - each case adds one and each end case takes one away;
  - each loop adds one and each end loop takes one away;
  - each generate adds one and each end generate takes one away.
The matching end is the line where the count returns to zero.

A branch or an alternative ends at the level of its own if or case statement: an end if, end case
or when that belongs to a structure nested inside it does not end it.

A branch never includes the end if line of its if statement, nor the elsif or else line that
starts the next branch. An if statement always includes its end if line.

WORKED EXAMPLES

Example 1. An if statement with an elsif and an else.
  140 | if A then
  141 |   x <= '1';
  142 | elsif rising_edge(k) then
  143 |   x <= y;
  144 | else
  145 |   x <= '0';
  146 | end if;
  if 140-146. Branches: 140-141 (IF_COND), 142-143 (EDGE_CHECK), 144-145 (else).
  The structures of line 143, outermost first: if 140-146; branch 142-143 (EDGE_CHECK).

Example 2. Nested if statements.
  140 | if A then
  141 |   if B then
  142 |     x <= '1';
  143 |   end if;
  144 |   y <= '1';
  145 | else
  146 |   y <= '0';
  147 | end if;
  Outer if 140-147, with branches 140-144 (IF_COND) and 145-146 (else). Inner if 141-143, with
  branch 141-142 (IF_COND).
  The end if on line 143 closes the inner if, so the outer branch 140-144 continues past it.
  The structures of line 142, outermost first: if 140-147; branch 140-144 (IF_COND); if 141-143;
  branch 141-142 (IF_COND).

Example 3. A case statement.
  140 | case s is
  141 |   when "00" =>
  142 |     x <= '1';
  143 |   when others =>
  144 |     x <= '0';
  145 | end case;
  case 140-145. Alternatives: 141-142 ("00"), 143-144 (others).
  The structures of line 144, outermost first: case 140-145; alternative 143-144 (others).

REPORTING

  - Report every structure of the kinds above that contains the line; leave none out.
  - A declaration in the port clause has the port clause as its only structure. A declaration in
    the declarative part has the declarative part as its only structure.
  - Every line after the architecture's begin, up to its end, has the architecture body as its
    outermost structure.
  - Do not report a structure that does not contain the line.
  - Do not change a structure's lines because of the SITE of the occurrence.

==================================================
E. STATEMENT-FIRST REASONING PROCEDURE
==================================================

For each occurrence, reason in the following order.

STEP 1 - LOCATE THE OCCURRENCE
Take the inventory entry: its Occurrence ID, its line, and the name as written. Find that exact
occurrence in the source line.

STEP 2 - FIND THE ENCLOSING STRUCTURES
Find every structure that contains the line, with section D. This is the Structure of the entry.

STEP 3 - IDENTIFY THE SMALLEST RELEVANT STATEMENT
Determine what VHDL statement contains the occurrence. A statement can run over several lines.
It ends at a semicolon, or at the then, is, generate or begin that closes a header.

Examples include:
  - a port declaration,
  - a signal declaration,
  - a process statement header,
  - an if or elsif condition,
  - a case expression or a case choice,
  - a signal assignment statement,
  - a conditional signal assignment statement,
  - a variable assignment statement,
  - an association in a port map or a generic map.

STEP 4 - IDENTIFY THE ELEMENT'S ROLE
Determine exactly what role the element plays in the statement.

Do not assign a SITE tag merely because the element occurs on the same line as a construct.
The element itself must satisfy the SITE's rule in the rulebook.

STEP 5 - APPLY THE SITE DEFINITION
Match the occurrence against the SITE rules and the conflict rules of the rulebook.

If no SITE rule matches, record the occurrence with an empty SITE Tagged list. Do not
force the nearest SITE.

STEP 6 - CHECK FOR ADD-ON SITE TAGS
Every SITE in the rulebook has a kind: primary or add-on.
  - First find the primary SITE of the occurrence: the part of the statement or declaration it
    is in. The target of a signal assignment is the name written before its parentheses: an
    element inside those parentheses is not in the target, and takes no primary SITE from it.
  - Then test every add-on SITE separately against the same occurrence, and write those that
    match in the same entry as the primary SITE.
  - Where no primary SITE matches, write the add-on SITEs alone.
  - Do not give an occurrence an add-on SITE because another name in the same statement has it.
  - At <element_label>.<field_label>, the base and the field are separate elements: see rule 13
    of section F.

STEP 7 - RECORD THE OCCURRENCE
Create one occurrence-table entry for the occurrence, with its Structure, its Role and all its
applicable site tags in the SITE Tagged list.

==================================================
F. SITE-DISAMBIGUATION RULES
==================================================

Use the rulebook literally. This section restates some of its rules; where they differ, follow
the rulebook.

1. PORT DECLARATIONS
If the occurrence is the declared element of a port declaration in the port clause of the
entity, use DECL_PORT.

An entry in the port clause of a component declaration declares a port of a different entity.
It is not an occurrence of the element.

A generic clause is not a port clause.

--------------------------------------------------

2. SIGNAL DECLARATIONS
If the occurrence is the declared signal of a signal declaration, use DECL_SIGNAL.

--------------------------------------------------

3. PROCESS SENSITIVITY LIST
If the element occurs in the sensitivity list of a process statement header, use PROCESS_TRIG.

Do not assign PROCESS_TRIG merely because the element appears elsewhere inside a process.

A process written as process (all) gives no element a PROCESS_TRIG occurrence.

--------------------------------------------------

4. EDGE CONDITIONS
If the occurrence is the argument of rising_edge(...) or falling_edge(...) in the condition of
an if or an elsif, use EDGE_CHECK.

The presence of the edge function is the deciding property.

Do not classify such an occurrence as IF_COND.

An occurrence of the same element in the sensitivity list of the process is a separate
occurrence, with its own PROCESS_TRIG entry.

--------------------------------------------------

5. NON-EDGE IF AND ELSIF CONDITIONS
If the element occurs in the condition of an if or an elsif, and the element is not inside an
edge function, use IF_COND.

Do not use IF_COND for an if ... generate statement.

--------------------------------------------------

6. CONDITIONAL SIGNAL-ASSIGNMENT CONDITIONS
If the element appears in the condition written after when in a conditional signal assignment,
use WHEN_COND.

An element inside the chosen expression or the alternative expression is not WHEN_COND.

--------------------------------------------------

7. SIGNAL ASSIGNMENT TARGET INSIDE A PROCESS
If the element is the target on the left of <= in a signal assignment inside a process block,
use LHS_PROC.

The tag does not change with the branch that encloses the statement. The Structure lists every
branch and alternative that encloses the statement, with what opened it (section D). The SITE
does not say which kind of branch it is.

An element that gives a position inside the parentheses of the target, as in
<array_label>(<element_label>) <= <expression>;, is not the target: only <array_label> is. That
element does not get LHS_PROC. It takes no primary SITE from the target, and its add-on SITEs are
written alone (rules 12 and 14).

--------------------------------------------------

8. SIGNAL ASSIGNMENT TARGET OUTSIDE A PROCESS
If the element is the target on the left of <= in a signal assignment outside every process
block, use LHS_CONC.

This includes a conditional signal assignment written directly in the architecture body.

As in rule 7, an element that gives a position inside the parentheses of the target is not the
target and does not get LHS_CONC.

--------------------------------------------------

9. WHOLE RIGHT-HAND SIDE
If the element is the entire right-hand side of a signal assignment, with:
  - no operator,
  - no index,
  - no range,
  - no other name,

use DIRR_ASS.

Form:
    <target_label> <= <element_label>;

--------------------------------------------------

10. RIGHT-HAND SIDE OPERAND
If the element is joined to something else by an operator on the right-hand side of a signal
assignment, use RHS_OPERAND.

Forms:
    <target_label> <= <element_label> and <expression>;
    <target_label> <= not <element_label>;
    <target_label> <= <expression> = <element_label>;
    <target_label> <= <element_label> + <expression>;

Do not use RHS_OPERAND merely because the element appears somewhere on the right-hand side.

In a conditional signal assignment, an element in the chosen or the alternative expression is
WHEN_EXPR instead, and an element in the condition is WHEN_COND.

--------------------------------------------------

11. CONDITIONAL ASSIGNMENT EXPRESSIONS
If the element occurs inside either:
  - the chosen expression, or
  - the alternative expression

of a conditional signal assignment, use WHEN_EXPR. This holds whether the element is used whole
or joined to something else by operators.

An element in the condition after when is WHEN_COND instead.

--------------------------------------------------

12. ARRAY INDEX
If the element gives the position of the item read from or written to an array, use INDEX.

This remains true when the element is nested inside conversions, such as:
    <array_label>(to_integer(<element_label>))
    <array_label>(to_integer(unsigned(<element_label>)))

The element is INDEX because it gives the array position.

Where the indexed name is the target of a signal assignment, as in
<array_label>(<element_label>) <= <expression>;, the element is still not the target: it gets
INDEX without LHS_PROC or LHS_CONC, together with PART_SELECT where a range of it is used.

The array written before the parentheses, and an element written as the prefix of an attribute
inside them, as in <array_label>(<element_label>'left), are not INDEX: the rulebook gives their
SITEs.

--------------------------------------------------

13. RECORD BASE AND RECORD FIELD
A record-typed base and each of its fields are separate elements of the closed set.

At <element_label>.<field_label>:
  - In the base's profile, the occurrence is FIELD_USE. Write one entry for each field reached,
    and name the field reached in the Role. What the occurrence does belongs to the field.
  - In the field's profile, when the field is in the closed set, the occurrence gets the SITEs any
    other element would get there: its primary SITE where one matches, with PART_SELECT where only
    a range of it is used. A field slice that is the whole right-hand side of a signal assignment
    gets PART_SELECT alone (rule 14).

A field has no declaration statement of its own. In the field's profile, the statement that
declares its base is its declaration: use DECL_FIELD, on the line of that statement. In the
Role, say whether the record type is declared in this source or outside it.

--------------------------------------------------

14. PART SELECT
If the element occurs as:
    <element_label>(<high> downto <low>)
or
    <element_label>(<low> to <high>)

apply PART_SELECT in addition to the occurrence's primary SITE tag, where one matches.

PART_SELECT does not replace the primary SITE tag.

A slice that is the whole right-hand side of a signal assignment matches no primary SITE: DIRR_ASS
needs no range, and RHS_OPERAND needs an operator. There, write PART_SELECT alone.

--------------------------------------------------

15. LITERALS AND CONSTANTS
Do not classify an occurrence as an operand merely because a constant or a literal appears in
the same expression.

The element itself must satisfy the SITE's rule.

--------------------------------------------------

16. NO MATCHING SITE
If an occurrence of an element matches no SITE rule, still record the occurrence, with an
empty SITE Tagged list, and describe its statement in the Role.

==================================================
G. STRUCTURE AND ROLE
==================================================

Every entry has a Structure and a Role. A program turns the two into the Context of the final
table.

STRUCTURE
The enclosing structures of the occurrence's line, found with section D, from the outermost to
the innermost:
    [{"kind": "<kind>", "lines": [<first>, <last>]}, ...]
A branch and an alternative also have "opened by", as section D gives it.

ROLE
One or two short sentences on what the element does at this occurrence, in terms of syntax,
specific enough that another annotator can verify the SITE tags from the RTL:
  - the statement: port declaration, signal declaration, process statement header, if or elsif
    condition, case expression, case choice, sequential or concurrent signal assignment,
    conditional signal assignment, variable assignment, or association;
  - the element's position in it: target, whole right-hand side, operand, condition, chosen
    expression, alternative expression, array position, array indexed, attribute prefix, or
    actual;
  - FIELD_USE: name the field reached;
  - DECL_FIELD: say whether the record type is declared in this source or outside it;
  - an actual in a port map or a generic map: name the formal the element is associated with;
  - PART_SELECT: give the range selected;
  - an empty SITE Tagged list: describe the statement.

Where the same element occurs more than once on a line, the Role tells the occurrences apart.
Do not write line numbers in the Role; they belong in the Structure.
Do not describe behavior that the tag does not need.
Do not say what a signal or a branch is for. Name only its syntax.

==================================================
H. MULTIPLE SITES AT ONE OCCURRENCE
==================================================

A single textual occurrence can receive more than one SITE tag when the rulebook makes
the sites complementary rather than mutually exclusive.

An entry holds at most one primary SITE, and every add-on SITE that the same occurrence matches
(STEP 6 of section E). Where no primary SITE matches, the add-on SITEs stand alone.

  - inspect the SITE rules and the conflict rules carefully,
  - do not force two occurrences into one entry,
  - do not repeat a tag in the same list.

The SITE Tagged field is therefore a list.

Example:
    "SITE Tagged": ["RHS_OPERAND", "PART_SELECT"]

When only one site applies:
    "SITE Tagged": ["RHS_OPERAND"]

When no site applies:
    "SITE Tagged": []

==================================================
I. LINE HANDLING
==================================================

Use the actual RTL line number of the occurrence, as shown in the source and in the inventory.

If the same element occurs twice on the same source line:
  - treat each syntactically distinct occurrence separately;
  - do not merge them merely because they share a line number;
  - give each its own entry, with its own Occurrence ID; a record base that reaches several fields
    on one line has one FIELD_USE entry for each field.

==================================================
J. CLOSED-SET COMPLETENESS
==================================================

Every element in the closed set must receive an occurrence profile.

If an element has only a declaration and no later use, record only its declaration.

If an element has no valid occurrence in the RTL, give it an empty occurrence list. Do not
invent an occurrence.

Do not add RTL elements that are absent from the closed set.

==================================================
K. ANNOTATION ALGORITHM
==================================================

For each closed-set element:

FOR each occurrence of the element:
    1. take its inventory entry
    2. find its enclosing structures (section D)
    3. identify the statement
    4. identify the syntactic role
    5. compare against every relevant SITE rule
    6. assign all supported SITE tags
    7. identify any add-on SITE that goes with it
    8. write the Structure and a concise Role
END

Then perform a second pass:

FOR each inventory occurrence of every closed-set element:
    verify that one occurrence-table entry accounts for it.

Then perform a third pass:

FOR each entry:
    verify its Structure against section D, line by line.
    verify that the occurrence satisfies its SITE rule literally.
    Remove any unsupported tag.

Finally verify:
  - no closed-set element is missing,
  - no occurrence was skipped,
  - no element outside the closed set was added,
  - no undefined SITE tag was used,
  - line numbers are correct,
  - all SITE tags are supported by the rulebook.

==================================================
L. OUTPUT FORMAT
==================================================

Return JSON only, in this structure:

{
  "<element name, exactly as given>": [
    {
      "Occurrence ID": <the Occurrence ID from the inventory, as an integer>,
      "Occurrence Lines": <the line number, as an integer>,
      "Structure": [{"kind": "<kind>", "lines": [<first>, <last>], "opened by": "<for a branch or an alternative only>"}],
      "Role": "<what the element does at this occurrence>",
      "SITE Tagged": ["<SITE name>"]
    }
  ]
}

List the elements in the order of the closed set, each exactly once.

Do not include:
  - reasoning chains,
  - explanations outside the JSON,
  - confidence scores,
  - invented site names,
  - comments in the JSON,
  - elements outside the closed set.

The five fields of every occurrence record are exactly:

"Occurrence ID"
"Occurrence Lines"
"Structure"
"Role"
"SITE Tagged"

==================================================
M. FINAL VALIDATION BEFORE OUTPUT
==================================================

Before emitting the JSON, silently perform these checks:

CHECK 1:
Every occurrence in the output exists in the RTL at the stated line.

CHECK 2:
Every SITE tag is defined in the rulebook.

CHECK 3:
Every tag satisfies its SITE rule: trigger, required structure, context and exclusions.

CHECK 4:
The element is actually the element the site is assigned to.

CHECK 5:
No comment-only occurrence has been included.

CHECK 6:
Every valid occurrence of every closed-set element has been considered.

CHECK 7:
No occurrence was classified by intuition about meaning where its syntax determines the SITE.

CHECK 8:
PART_SELECT is recorded together with the primary SITE where one matches, and alone for a slice
that is the whole right-hand side of a signal assignment.

CHECK 9:
Conditional-assignment conditions, conditional-assignment expressions, and ordinary right-hand
side operands are not confused.

CHECK 10:
Sensitivity-list occurrences, edge-condition occurrences, and ordinary if-condition occurrences
are not confused.

CHECK 11:
Targets inside a process block and targets outside every process block are distinguished. An
element that gives a position inside the parentheses of a target is not tagged as the target.

CHECK 12:
A whole right-hand side and an operand joined by an operator are distinguished.

CHECK 13:
At <element_label>.<field_label>, the base has FIELD_USE, and the field has the SITEs any other
element would get for what the occurrence does there.

CHECK 14:
No entry comes from the port clause of a component declaration, or from a name to the left of
=>.

CHECK 15:
Every Structure lists every structure of section D that contains the line, outermost first, with
the lines section D gives. No branch includes its end if line, and no alternative includes the
next when line.

CHECK 16:
Case expressions, case choices, and conditions after when in a conditional signal assignment are
not confused.

CHECK 17:
Every inventory occurrence that is an occurrence has one entry with its Occurrence ID, including
occurrences that share a line and statements written again with the same text.

CHECK 18:
Every entry holds at most one primary SITE, and each add-on SITE matches this occurrence itself.

CHECK 19:
No Role holds a line number.

Only after all checks pass, output the JSON.

==================================================
N. ANNOTATION RULEBOOK
==================================================

<<RULEBOOK>>
