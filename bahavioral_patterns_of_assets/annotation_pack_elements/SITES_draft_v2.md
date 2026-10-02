## SITE definitions

- DECL_PORT:  The statement declares one element of the entity's external interface. The structure/basic syntax of a port declaration statement:

  `<element_label> : <dir> <type>`

  The `<dir>` indicates the direction of the interface; it can be in, out, inout or buffer. `<type>` specifies the data type. A `;` separates one entry from the next, so every entry except the last one is followed by a semicolon. Several identifiers can share one entry, and each of them is then an element of its own:

  `<element_label1>, <element_label2> : <dir> <type>`

  Context: The statements appear inside a port clause, which holds the interface list. A port clause appears in an entity declaration. It also appears in a component declaration, which describes the interface of a different entity, so those entries are not elements of the entity being read. A generic clause has a similar shape but declares constants and carries no `<dir>`, which is what tells the two apart. The structure:

  port (
  
  `<element_label1> : <dir> <type>;`

  `<element_label2> : <dir> <type>;`

  ...

  `<element_labelN> : <dir> <type>`

  );

- DECL_SIGNAL:  The statement declares an internal signal that can be used to carry values between parts of a design. The structure/basic syntax of a signal declaration statement:

  `signal <element_label> : <type>;`

  The signal has no direction. A signal can be given a starting value, written after the type:

  `signal <element_label> : <type> := <value>;`

  Context: The statement appears in a declarative part, which is the region of a construct where things are declared, before any of its statements. Normally that is the architecture's declarative part, between the architecture header and the `begin` of its body:

  `architecture <architecture_name> of <entity_name> is`

  `signal <element_label> : <type>;`

  `begin`

  `...`

  `end <architecture_name>;`

  A signal declared there belongs to that architecture and cannot be seen from outside it. The declarative part of a block statement and of a generate statement can hold signal declarations too, and both of those sit inside the architecture body. A package can declare signals as well, which makes them visible to every design unit that uses the package. A process block and a subprogram cannot: those declare `variable`s, which are not signals. Multiple signals can share one declaration statement:

  `signal <element_label1>, <element_label2>, ... : <type>;`

- PROCESS_TRIG: The element appears in the sensitivity list of a process statement header. The structure/basic syntax:

    `<process_label> : process (<element_label1>, <element_label2>, ...)`

    the `element_label`s inside the `( )` are called the sensitivity list. It is a list of signals whose events trigger process execution.

    A process statement can be written without a `<process_label>`, and a sensitivity list can be written as `process (all)`. Neither form names an element, so neither gives an element this site.

    Context: Always appears in the process statement header, at the start of a process block. The process block is a block of sequential statements: it starts with the process statement header and ends with:

    `end process <process_label>;`

    The `<process_label>` is repeated at the end only where the header carries one.

- EDGE_CHECK: The element is the argument of an edge function in the condition of an `if` or an `elsif`. The syntax:

  `if rising_edge(<element_label>) then`

  `...`

  `end if;`

  or

  `if falling_edge(<element_label>) then`

  `...`

  `end if;`

  or, as the `elsif` of an `if` block:

  `if ... then`

  `...`

  `elsif rising_edge/falling_edge(<element_label>) then`

  `...`

  `end if;`

  The edge function, `rising_edge(...)` or `falling_edge(...)`, is what identifies this site. The `element_label` inside it is the **edge condition** of that branch. Whether the element is also named in the sensitivity list is recorded by its own site and is no part of this one.

  Context: Always appears inside a process block. The branch the edge condition opens is entered only at that edge. A process that holds an edge condition is a clocked process.

- DECL_FIELD: The element is one field of a record-typed port or signal. A record groups several named fields under one name, so the field has no declaration statement of its own. Its declaration is the statement that declares the base, and its type comes from the record type:

  `type <record_type> is record`

  `<field_label> : <type>;`

  `...`

  `end record;`

  A field is written with the base and the field name joined by a dot: `<element_label>.<field_label>`. This site is recorded on the field. Where the same text is read as an occurrence of the base, that is FIELD_USE instead.

  Context: The record type is declared either in this source, or outside it, in a package. Record which of the two it is. The base itself is declared by a port declaration statement or a signal declaration statement.

- IF_COND: The element is in the condition of an `if` or an `elsif` statement, and not inside an edge function. The structure/basic syntax:

  `if <element_label> = <literal> then`

  `...`

  `end if;`

  or, as the `elsif` of an `if` block:

  `if ... then`

  `...`

  `elsif <element_label> = <literal> then`

  `...`

  `end if;`

  The condition can test the `<element_label>` against a fixed value, against another element, or on its own. What identifies this site is that the condition holds no edge function: a condition with `rising_edge(...)` or `falling_edge(...)` is EDGE_CHECK.

  Context: Always appears inside a process block (or a function or procedure), because an `if` statement is a sequential statement. The same process block can also hold an EDGE_CHECK, before or after this condition. An `if ... generate` is a different statement and is not this site.

- WHEN_COND: The element is the condition of a conditional signal assignment statement. The structure/basic syntax:

  `<target_label> <= <chosen_expression> when <element_label> = <literal> else <alternative_expression>;`

  The condition is written to the right of `<=`, beside the values, inside the `when`'s condition , but it is not a value the `<target_label>` can take. It decides which of the values the `<target_label>` takes.

  Context: Normally a concurrent statement in the architecture body, outside every process block. 
  
- LHS_PROC: The element is the target of a signal assignment statement written inside a process block. The structure/basic syntax:

  `<element_label> <= <expression>;`

  The `<element_label>` is on the left of `<=`. The statement is a sequential statement, so it is written inside a process block, where it can sit inside the branch of an `if` statement:

  `<process_label> : process (<element_label1>, ...)`

  `begin`

  `if ... then`

  `<element_label> <= <expression>;`

  `end if;`

  `end process <process_label>;`

  Context: Always appears inside a process block. Record the lines of every branch that encloses the statement: a branch opened by an EDGE_CHECK, a branch opened by an IF_COND, or none. This site does not say which kind of branch it is; that is read from those lines at a later stage.

- LHS_CONC: The element is the target of a signal assignment statement written outside every process block. The structure/basic syntax:

  `<element_label> <= <expression>;`

  The `<element_label>` is on the left of `<=`. The statement is a concurrent statement, written directly in the architecture body:

  `architecture <architecture_name> of <entity_name> is`

  `...`

  `begin`

  `<element_label> <= <expression>;`

  `end <architecture_name>;`

  A conditional signal assignment written there is this site too, with the `<element_label>` as its target:

  `<element_label> <= <chosen_expression> when <condition> else <alternative_expression>;`

  Context: Always appears in the architecture body, outside every process block. No `if` statement encloses it, because an `if` statement is only written inside a process block; an `if ... generate` is a different statement.

- DIRR_ASS: The element is the whole right hand side of a signal assignment statement. The structure/basic syntax:

  `<target_label> <= <element_label>;`

  No operator, no index, no range and no other name appears to the right of `<=`.

  Context: Appears as a concurrent statement in the architecture body, or as a sequential statement inside a process block. Both sides have the same type and the same width.

- WHEN_EXPR: The element appears in the chosen expression or the alternative expression of a conditional signal assignment statement. The structure/basic syntax:

  `<target_label> <= <chosen_expression> when <condition> else <alternative_expression>;`

  The chosen expression is the value the `<target_label>` takes when the `<condition>` holds. The alternative expression is the value it takes otherwise. An element anywhere inside either one is this site:

  `<target_label> <= <element_label> when <condition> else <alternative_expression>;`

  `<target_label> <= <chosen_expression> when <condition> else <element_label>;`

  This holds whether the `<element_label>` is used whole or joined to something else by operators. An element in the `<condition>` is WHEN_COND, not this site.

  Context: The `<condition>` and both expressions sit to the right of `<=` in one statement. A chain of conditions, `... when <condition1> else ... when <condition2> else ...`, has one chosen expression for each condition and one alternative expression at the end.

- RHS_OPERAND: The element is joined to something else by operators on the right hand side of a signal assignment statement. The structure/basic syntax:

  `<target_label> <= <element_label> <operator> <expression>;`

  An `<operator>` is a symbol or word such as `and`, `or`, `not`, `xor`, `+`, `-`, `=`, `/=` or `&`. An expression built from operators is combinational logic: its result depends only on the current values of its inputs.

  Context: Appears as a concurrent statement in the architecture body, or as a sequential statement inside a process block. In a conditional signal assignment, the element is WHEN_EXPR instead.

- INDEX: The element gives the position of the item read from or written to an array. The structure/basic syntax:

  `<target_label> <= <array_label>(<element_label>);`

  or

  `<array_label>(<element_label>) <= <expression>;`

  The `<element_label>` is not part of the value; it says which item of the array the value comes from or goes to. The position can be written in several forms, and in each of them the `<element_label>` is this site:

  `<array_label>(<element_label>)`

  `<array_label>(<conversion>(<element_label>))`

  `<array_label>(<expression containing <element_label>>)`

  A `<conversion>` is a function such as `to_integer`, `unsigned` or `signed`. Conversions change how the same bits are read, not where they come from, and one conversion can wrap another. An array of arrays takes one position per level, `<array_label>(<index1>)(<index2>)`, and each element used as a position is this site.

  Context: Where the position is a literal or a named constant, no element gives it, so no element gets this site. Where the `<array_label>` is a named constant, the array is a table of fixed values, a read-only memory, and the constant is not an element.

- PART_SELECT: Only a range of the element's bits is used. The structure/basic syntax:

  `<element_label>(<high> downto <low>)`

  or

  `<element_label>(<low> to <high>)`

  Only those bits take part; the rest of the element does not.

  Context: Recorded together with the site of the occurrence it appears in, not instead of it. It says which bits are used, not what the occurrence does.

- FIELD_USE: The element is a record-typed base, and this occurrence reaches one of its fields. The structure/basic syntax:

  `<element_label>.<field_label>`

  Name the `<field_label>` that was reached.

  Context: The field is its own entry in the list of elements given to you. What the occurrence does there belongs to the field; this site records on the base that one of its fields was reached, and which one.
