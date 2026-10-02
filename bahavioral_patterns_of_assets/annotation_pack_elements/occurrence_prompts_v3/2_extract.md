YOU FIND THE OCCURRENCES OF VHDL ELEMENTS

You are given:

  - the source of ONE entity: its entity declaration and its architecture. Comments have been
    removed. Every line starts with its line number in the original file.
  - the closed set: the list of elements of that entity. A port has a name, a direction and a
    type. An internal signal has a name and a type. A field of a record-typed port or signal is
    listed as <base>.<field>.

Your task is to find every occurrence of every element in the closed set, and to record the
statement each occurrence sits in.

Do not decide what the occurrence does. Do not tag it. A later step classifies each occurrence.
Your job is that no occurrence is missed and none is invented.

==================================================
A. THE CLOSED SET
==================================================

Only a name that appears in the list of elements given to you gets a site. Every other name
gets none: literals, named constants, aggregates, generics, loop parameters, enumeration
values, and the names of functions and types.

In this step, that means: only those names get an occurrence entry. Do not add elements merely
because they appear in the source.

==================================================
B. WHAT COUNTS AS AN OCCURRENCE
==================================================

1. The element's name, written as a whole name. VHDL reads upper and lower case letters in a
   name as the same.

2. The declaration of the element counts: its port declaration, or its signal declaration.

3. For a record-typed base, <base>.<field> is an occurrence of the base, one for each field
   reached.

4. For a field, <base>.<field> is an occurrence of the field. A field has no declaration
   statement of its own: the statement that declares its base is its declaration. So the line
   that declares the base is also an occurrence of each of its fields.

5. Each occurrence is its own entry, even where two occurrences share a line, and even where the
   same statement text is written again on another line. A record base that reaches several
   fields on one line has one occurrence for each field reached.

These are NOT occurrences of the element:

  - the name as part of a longer name;
  - the same field name reached through a different base, as in <other_base>.<field>;
  - a name in the port clause of a component declaration: it declares a port of a different
    entity;
  - a name to the left of => in a port map or in a named association: it names the port or the
    field being associated, not the element. A name to the right of => is an occurrence where
    it is an element;
  - text inside a comment, if any remains.

==================================================
C. PROCEDURE
==================================================

Work through the elements in the order they are listed. For each element:

1. Start at the first line of the source.

2. Move down the source, line by line, until the element's name appears.

3. Check it against section B. If it is not an occurrence, go on to the next line.

4. Read the whole statement the occurrence is in. A statement can run over several lines. It
   ends at a semicolon, or at the then, is, generate or begin that closes a header.

5. Write one entry: its Occurrence ID, the line of the occurrence, the name as written, the first
   and last line of the statement, and the statement's text. Number the occurrences of each
   element 1, 2, 3, ... in source order. The name as written is the element's name as it appears
   at this occurrence, together with the field after it for a record base, as in <base>.<field>,
   and the attribute after it, as in <element>'<attribute>. It tells apart occurrences that share
   a line.

6. Continue from the next line, and repeat from step 2, until the last line of the source.

7. Move on to the next element in the list.

Then make a second pass. For each element, go through the source again from the first line:

  - every occurrence of the element has an entry;
  - where the element occurs several times on one line, there is one entry for each occurrence;
  - every entry is on a line where the element occurs, by section B.

Correct the entries before you return them.

==================================================
D. OUTPUT
==================================================

Return one JSON object, and nothing else:

{"<element name, exactly as given>": [
   {"Occurrence ID": <1, 2, 3, ... for this element, in source order, as an integer>,
    "Occurrence Lines": <the line number of the occurrence, as an integer>,
    "Name As Written": "<the name as written at this occurrence>",
    "Statement Lines": "<first>-<last>",
    "Statement": "<the text of the statement, copied from the source without line numbers>"}
 ]}

Where the statement runs over more than one line, copy only the line the occurrence is on.

Include every element of the closed set, in the listed order, each exactly once. If an element
has no occurrence in the source, give it an empty list.

Use only line numbers shown in the source.
