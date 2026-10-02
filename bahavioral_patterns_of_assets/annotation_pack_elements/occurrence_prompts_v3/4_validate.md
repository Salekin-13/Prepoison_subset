YOU CHECK AND CORRECT RTL OCCURRENCE PROFILES

You are given:

  - the source of ONE entity: its entity declaration and its architecture. Every line starts with
    its line number in the original file.
  - the closed set: the list of elements of that entity profiled in this call. A port has a name, a
    direction and a type. An internal signal has a name and a type. A field of a record-typed port
    or signal is listed as <base>.<field>. This list is only part of the entity's elements: write no
    entry for any name that is not in this list.
  - an OCCURRENCE INVENTORY made by a program: for each element, every occurrence, with its
    Occurrence ID, its line, which occurrence it is on that line, the name as written there, and the text of
    that line, plus the program-computed Context and Path.
  - OCCURRENCE PROFILES from an earlier step, which wrote the roles and
    tagged the occurrences with SITEs.
  - a CODE CHECK: items a program found by comparing the profiles with the source and the
    inventory. It counts the occurrences of each element on each line, compares every entry's
    Occurrence ID with the inventory's ID for its line, counts the indexed and sliced names, finds
    FIELD_USE on an occurrence that is not written as <element_label>.<field_label>, and looks for
    Role words that say what a signal or a branch is for.

Your task is to check every profile independently against the RTL source and the rulebook, and
to return the corrected profiles in the same format.

Do not trust the profiles you are given. Re-derive each entry from the source, by the rules
below, and compare.
Context and Path are fixed facts; do not re-derive, change, repeat or output them.

  - Keep an entry that is correct, as it is.
  - Correct a wrong line number.
  - Correct a wrong tag, add a missing tag, and remove a tag the rulebook does not support.
  - Correct a Role that does not justify the tags, holds a line number, or says what something is
    for.
  - Add an occurrence that was missed.
  - Remove an entry that is not an occurrence of its element.
  - Check every CODE CHECK item against the source and the rules. Where the item is right, correct
    the profiles as it shows.
  - Give every entry the Occurrence ID the inventory gives its occurrence. Every inventory
    occurrence needs an entry. An occurrence the inventory does not list keeps an Occurrence ID
    above the inventory's highest ID for its element.

Return the whole corrected set of profiles, not only the changes.

<<ANNOTATE_RULES>>
