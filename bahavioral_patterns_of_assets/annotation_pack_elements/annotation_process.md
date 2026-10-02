# annotating the neorv32_boot_rom

## Some basics I followed when annotating the behaviors

- When a port is declared is the declaration statement. The structure:

    > `port ( <port_element> : <dir> <type>);`

- A signal is declared in the architecture, between its `is` and its `begin`. The structure:

    > `signal <element> : <type>;`

    A signal has no direction: it is internal to the architecture and cannot be seen from outside the entity. Several signals can share one declaration: `signal <element>, <element> : <type>;`

- The *process* keyword after a : in a statement indicates the process declaration or the **process statement header**

    > `<process_label> : process (<sensitivity_list>)`

    the sensitivity_list are the signals that trigger the block to operate. Only when the signals in the list (signals listed in the parenthese) changes phase, does the block wake up.

- After the header/declaration, the next line will be `'begin'` followed by operations inside the process block, ending with
    > `end process <process_label>;`

    to indicate the conclusion of that process block. The entire structure from the label all the way down to the end is the **Process Block**

- Inside the process block, `if-else` statemenys are called **Sequential Conditional Statements**. As they appear inside the process block, they are sequential.

    > `if <element> then
    ...
    end if;`

    or, as the `elsif` of an `if` block:
    > `if ... then
    ...
    elsif <element> then
    ...
    end if;`

    the element WITHOUT any edge trigger is the **condition** of the `if` or `elsif` statements

    Seen from the other side, a `<target>` assigned inside a branch is assigned only when the condition selects that branch.

- If the element in the sensitivity list of the process is the condition of the `if-else` block WITH an edge trigger / Edge Functions ,

    > `if rising_edge(<element>) then
    ...
    end if;`

    or
    > `if falling_edge(<element>) then
    ...
    end if;`

    or, as the `elsif` of an `if` block:
    > `if ... then
    ...
    elsif rising_edge/falling_edge(<element>) then
    ...
    end if;`

    Then the process is a **Sequential process**. And the `<element>` in the `if <edge_trigger>(<element>) then ... end if;` or in the `elsif <edge_trigger>(<element>) then` of an `if` block acts as a **guard condition**.

    Seen from the other side, a `<target>` assigned inside that branch changes only at the clock edge and keeps its value between edges: it is stored, like a register.

- An `if` block whose first branch tests a level (no edge trigger) and whose `elsif` tests a clock edge:

    > `if <reset_condition> then
    <target> <= <literal>;
    elsif rising_edge(<clock_element>) then
    <target> <= <expression>;
    end if;`

    is an **asynchronous reset**. While the `<reset_condition>` holds, the `<target>` is forced to the `<literal>` straight away, without waiting for the clock. Otherwise the `<target>` takes the `<expression>` at each clock edge. When the reset test is written inside the clock-edge branch instead, the reset also waits for the clock edge: a **synchronous reset**.

- The general vhdl form for a port being a record object:
    > `<record_object>.<record_element>`

    A record uses a *named element*. The `<record_element>` will be a *named selection*. This is a **record-element selection**.

    However, the record type may be declared outside the vhdl file being inspected.

- The statements in the following structure:

    > `<target>  <=  [expression containing <element>]`

    are **signal assignment** statements. The *`<element>`* appearing on the *right hand side* of the operation is an **input operand** to an expression used by a **signal assignment statement**.

    Seen from the other side, the `<target>` on the *left hand side* receives the value of the whole expression.

- An expression that combines elements with operators such as `and`, `or`, `not` or `+` is **combinational logic**: its result depends only on the current values of its inputs, and it has no memory. The assignment decides when the `<target>` takes that result: at once, or only at the clock edge when the assignment sits under an edge trigger.

- An **array** holds several items of the same type, each at a numbered position. One item is selected by giving its position:

    > `<array>(<index>)`

    This is an **indexed name**. When the `<index>` is an expression, the item chosen depends on its value at that moment. Seen from the other side, the `<index>` decides which item is read or written; it is not itself part of the value.

- A range of bits selected from an element:

    > `<element>(<high> downto <low>)` or `<element>(<low> to <high>)`

    is a **slice**. Only those bits are used; the rest of the element is not.

- Functions such as `unsigned(<expression>)` and `to_integer(<expression>)` are **conversions**: they change how the same bits are read, for example as a number that can serve as an `<index>`. They do not change which elements the value comes from.

- The statements in the following structure:

    `<TARGET> <= <EXPRESSION> when <CONDITION> else <ALTERNATIVE>;`

    are **conditional signal assignment statements**.

    Seen from an element in the `<EXPRESSION>` or the `<ALTERNATIVE>`, its value reaches the `<TARGET>` only when its branch is chosen. When it is used whole, with no operator, the value passes unchanged.

- Every statement written directly in the architecture body, after its `begin`, is a **concurrent statement**:

    > `architecture <architecture_name> of <entity_name> is
    ...
    begin
    <concurrent_statement>
    <concurrent_statement>
    end <architecture_name>;`

    Concurrent statements operate in parallel with each other. A process block is one concurrent statement: the block runs in parallel with the others, while the statements inside it are sequential. A signal assignment written outside every process block is a concurrent statement on its own.

- An `if ... else` and a `when ... else` can describe the same choice:

    > `if <CONDITION> then
    <TARGET> <= <EXPRESSION>;
    else
    <TARGET> <= <ALTERNATIVE>;
    end if;`

    > `<TARGET> <= <EXPRESSION> when <CONDITION> else <ALTERNATIVE>;`

    The `if ... else` is a *sequential conditional statement*: it is written only inside a process block (or a function or procedure), and each branch can hold any number of statements for any targets. The `when ... else` is a *conditional signal assignment*: it is written outside a process block as a concurrent statement (VHDL-2008 also allows it inside one), and it has exactly one `<TARGET>`. In the `when ... else`, the `<CONDITION>` sits on the right hand side of `<=` beside the values, but it is never a value the `<TARGET>` takes; it only decides which value it takes.

- The statements in the following structure, with no `when` condition:

    > `<target> <= <expression>;`

    are **simple signal assignment** statements. Written outside a process block, such a statement behaves like a process block whose sensitivity list holds every signal on its right hand side: the `<target>` is updated whenever one of them changes.

    When the `<expression>` is a single `<element>` used whole, with no operator, index or slice:

    > `<target> <= <element>;`

    the `<target>` always holds exactly the value of the `<element>`, like a wire connecting the two. Seen from the `<element>`, it passes its value unchanged to the `<target>`.

- A **literal** is a fixed value written directly in the code, such as `'0'`, `'1'`, `"0101"` or a number. A **named constant** is a fixed value given a name:

    > `constant <constant_name> : <type> := <value>;`

    An **aggregate** builds a value from its parts: `(others => '0')` sets every bit of the `<target>` to `'0'`, whatever its width. Literals, named constants and aggregates are fixed values. They are not ports or signals, so they are never elements to annotate.

- A *named constant* that is an array is a table of fixed values: a **read-only memory**. Indexing it:

    > `<target> <= <constant_array>(<index>);`

    reads the item stored at that position. Nothing in the design can write to it; only the `<index>` changes which item is read.

- A simple signal assignment whose right hand side is only a fixed value:

    > `<target> <= <literal>;`

    written outside a process block, ties the `<target>` to that value. No element feeds it, so nothing in the design can change it. This is called a **tie-off**. Written inside a branch of a process block, the same statement gives the `<target>` that value only when the branch is taken; other branches can give it other values, so it is not a tie-off.

## Steps followed  to create *Occurrence Profiles*

1. Used the `neorv32_boot_rom.json` as the closed set with the list of elements whose behaviors to annotate.
2. The RTL file is where to look for the behaviors.
3. Ignored all the comments in the RTL, recognized by the `--` sign `--`
4. Started creating the occurrence profile for the first element `clk_i`
5. first appearance @ **line 21**

    > *`clk_i     : in  std_ulogic;`*

6. The first appearance matches the structure of a declaration statement. The occurrence site is tagged as *DECL*

7. Next occurrence @ **line 45**

    > *`mem_access : process(clk_i)`*

    This matches the structure of a *process statement header*. Looking at the following statements, the process block concludes @ **line 50** by matching the *`end process mem_access;`* statement's structure.

8. The `clk_i` is in the sensitivity list of the process. Site tagged as *PROC_SEN*

9. Next occurrence @ **line 47**

    > *`if rising_edge(clk_i) then`*

    is followed by the end of the `if-else` block @ **line 49**

    and matches the structure of *guard condition*

10. The `clk_i` is the *guard condition* of the *Sequential Conditional Statements*. Site tagged as *EDGE_GUARD*

11. Next appearance is @ **line 55**

    > *`bus_feedback: process(rstn_i, clk_i)`*

    which is the start of another process block.
    Site tagged as *PROC_SEN*

12. Next occurrence @ **line 59**

    > *`elsif rising_edge(clk_i) then`*

    matches the structure of *guard condition*.
    Site tagged as *EDGE_GUARD*

13. The occurrence profile of port 'clk_i':

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 21 | port declarations from lines 20-25 | DECL |
    | line 45 | process block from lines 45-50 | PROC_SEN |
    | line 47 | sequential conditional statements / if statements from line 47-49 | EDGE_GUARD |
    | line 55 | process block from lines 55-62 | PROC_SEN |
    | line 59 | sequential conditional statements / if statements from line 57-61 | EDGE_GUARD |

14. Moved to next element in the closed set list, `rstn_i`

15. first appearance @ **line 22**

    > *`rstn_i    : in  std_ulogic;`*

16. The first appearance matches the structure of a declaration statement. The occurrence site is tagged as *DECL*

17. Next occurrence @ **line 55**

    > *`bus_feedback: process(rstn_i, clk_i)`*

    This matches the structure of a *process statement header*. Looking at the following statements, the process block concludes @ **line 62** by matching the *`end process bus_feedback;`* statement's structure.

18. The `rstn_i` is in the sensitivity list of the process. Site tagged as *PROC_SEN*

19. Next occurrence @ **line 57**

    > *`if (rstn_i = '0') then`*

    is followed by the end of the `if-else` block @ **line 61**

    and matches the structure of *condition*

20. The `rstn_i` is the *condition* of the *Sequential Conditional Statements*. Site tagged as *COND*

21. The occurrence profile of port 'rstn_i':

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 22 | port declarations from lines 20-25 | DECL |
    | line 55 | process block from lines 55-62 | PROC_SEN |
    | line 57 | sequential conditional statements / if statements from line 57-61 | COND |

22. Moved to next element in the closed set list, `bus_req_i`

23. first appearance @ **line 23**

    > *`bus_req_i : in  bus_req_t;`*

    The occurrence site is tagged as *DECL*

24. Next occurrence @ **line 48**

    > *`rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))));`*

    This matches the structure of a *signal assignment* statement. `bus_req_i` appearing on the RIGHT HAND SIDE is an *input operrand* to the assignment statement. Site tagged as *INPUT_OP*

25. The line accesses a named object `addr` from the `bus_req_i`, this matches the structure of a *record object type* and `.addr` is a *record-element selection*. Site tagged as *REC_OBJ*

26. Next occurrence @ **line 60**

    > *`rden <= bus_req_i.stb and (not bus_req_i.rw);`*

    This matches the structure of a *signal assignment* statement. `bus_req_i` appearing on the RIGHT HAND SIDE is an *input operrand* to the assignment statement.

    The line accesses a named objects `stb` and `rw` from the `bus_req_i`, this matches the structure of a *record object type* and `.stb` and `.rw` are *record-element selections*.

27. 'bus_req_i' is acting as a source object from which two individual record elements are used as input operrands of the logical operation. Site tagged as *INPUT_OP* and *REC_OBJ*

28. Ignored the .data, .ben, .src, .priv, .debug, .amo, .amoop, .lock, .fence as the do not appear anywhere in the code.

29. The occurrence profile of port 'bus_req_i':

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 23 | port declarations from lines 20-25 | DECL |
    | line 48 | sequential conditional statements / if statements from line 47-49; used as a location in a signal assignment operation from array lookup from ROM content | INPUT_OP |
    | | a source object from which individual record element is used as input operrand | REC_OBJ |
    | line 60 | sequential conditional statements / if statements from line 57-61; used as inputs to a signal assignment operation from a logic expression | INPUT_OP |
    | | a source object from which two individual record elements are used as input operrands | REC_OBJ |

30. Moved to next element in the closed set list, `bus_rsp_o`

31. first appearance @ **line 24**

    > *`bus_rsp_o : out bus_rsp_t`*

    The structure matches port declarations. The occurrence site is tagged as *DECL*

32. Next occurrence @ **line 64**

    > *`bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');`*

    The line accesses a named object `data` from the `bus_rsp_o`, this matches the structure of a *record object type* and `.data` is a *record-element selection*. Site tagged as *REC_OBJ*

33. The same line @ **line 64** also matches the structure of a *conditional signal assignment* statement:

    > `<TARGET> <= <EXPRESSION> when <CONDITION> else <ALTERNATIVE>;`

    - `<TARGET>` = `bus_rsp_o.data`
    - `<EXPRESSION>` = `rdata`
    - `<CONDITION>` = `(rden = '1')`
    - `<ALTERNATIVE>` = `(others => '0')`, an *aggregate* that sets all 32 bits to `'0'`

    `bus_rsp_o` appears on the LEFT HAND SIDE: its field `.data` is the `<TARGET>`. The statement is outside every process block (the last one ends @ **line 62**), so it is a *concurrent statement*. When `rden` is `'1'`, `.data` takes the value of `rdata`; otherwise all its bits are `'0'`.

34. Next occurrence @ **line 65**

    > *`bus_rsp_o.ack  <= rden;`*

    This matches the structure of a *simple signal assignment* statement: there is no `when` condition. `bus_rsp_o` appears on the LEFT HAND SIDE: its field `.ack` is the `<target>`. The right hand side is the single element `rden`, used whole, with no operator; both are `std_ulogic`. So `.ack` always holds exactly the value of `rden`. The statement is outside every process block, so it is a *concurrent statement*.

    The line accesses a named object `ack` from the `bus_rsp_o`: `.ack` is a *record-element selection*. Site tagged as *REC_OBJ*

35. Next occurrence @ **line 66**

    > *`bus_rsp_o.err  <= '0';`*

    This matches the structure of a *simple signal assignment* whose right hand side is only a *literal*, `'0'`. `bus_rsp_o` appears on the LEFT HAND SIDE: its field `.err` is the `<target>`, and it is tied to `'0'`, a *tie-off*. No element appears on the right hand side. The statement is outside every process block, so it is a *concurrent statement*.

    The line accesses a named object `err` from the `bus_rsp_o`: `.err` is a *record-element selection*. Site tagged as *REC_OBJ*

36. The occurrence profile of port 'bus_rsp_o' (new tags left for later):

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 24 | port declarations from lines 20-25 | DECL |
    | line 64 | concurrent statement, outside any process block; its field `.data` is the target of a conditional signal assignment: takes `rdata` when `(rden = '1')`, else `(others => '0')` | (to tag) |
    | | a record object whose field `.data` is selected | REC_OBJ |
    | line 65 | concurrent statement, outside any process block; its field `.ack` is the target of a simple signal assignment from the single element `rden` | (to tag) |
    | | a record object whose field `.ack` is selected | REC_OBJ |
    | line 66 | concurrent statement, outside any process block; its field `.err` is the target of a simple signal assignment of the literal `'0'` (a tie-off) | (to tag) |
    | | a record object whose field `.err` is selected | REC_OBJ |

37. Moved to the signals in the closed set list. First signal: `rden`

38. first appearance @ **line 38**

    > *`signal rden  : std_ulogic;`*

    The structure matches signal declarations. The occurrence site is tagged as *DECL*

39. Next occurrence @ **line 58**

    > *`rden <= '0';`*

    This is inside the process block from lines 55-62, in the first branch of the *sequential conditional statement* from line 57-61. That `if` block matches the structure of an *asynchronous reset*: its first branch tests `(rstn_i = '0')`, and its `elsif` @ **line 59** tests the clock edge.

    `rden` is the `<target>` of a *simple signal assignment* whose right hand side is only the *literal* `'0'`. Because it is written inside a branch of a process block, this is not a tie-off: `rden` is forced to `'0'` only while `rstn_i` is `'0'`, without waiting for the clock.

    This is the other side of steps 19-20, where `rstn_i` was the *condition* of this branch.

40. Next occurrence @ **line 60**

    > *`rden <= bus_req_i.stb and (not bus_req_i.rw);`*

    This is in the `elsif` branch of the same *sequential conditional statement*, whose condition is the edge trigger `rising_edge(clk_i)`. `rden` is the `<target>` of a *signal assignment*: it receives the value of the expression `bus_req_i.stb and (not bus_req_i.rw)`.

    The expression is *combinational logic*, but the assignment sits under the edge trigger. So `rden` takes the result only at the rising edge of `clk_i` and keeps it until the next edge: `rden` is stored, like a register.

    This is the other side of steps 26-27, where `bus_req_i` gave the *input operands* of this expression, and of step 12, where `clk_i` was the *guard condition* of this branch.

41. Next occurrence @ **line 64**

    > *`bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');`*

    This matches the structure of a *conditional signal assignment*. `rden` is in the `<CONDITION>`, `(rden = '1')`. It is not a value `bus_rsp_o.data` can take: it decides whether `.data` takes `rdata` or `(others => '0')`. The statement is outside every process block, so it is a *concurrent statement*.

    This is the other side of step 33, where `bus_rsp_o.data` was the `<TARGET>` of this assignment.

42. Next occurrence @ **line 65**

    > *`bus_rsp_o.ack  <= rden;`*

    This matches the structure of a *simple signal assignment* whose right hand side is a single element used whole. `rden` is that element, an *input operand*: it passes its value unchanged to `bus_rsp_o.ack`. The statement is outside every process block, so it is a *concurrent statement*. Site tagged as *INPUT_OP*

    This is the other side of step 34, where `bus_rsp_o.ack` was the `<target>` of this assignment.

43. The occurrence profile of signal 'rden':

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 38 | signal declarations from lines 38-39 | DECL |
    | line 58 | sequential conditional statements / if statements from line 57-61, asynchronous reset branch `if (rstn_i = '0')`; target of a simple signal assignment of the literal `'0'` | (to tag) |
    | line 60 | sequential conditional statements / if statements from line 57-61, clock-edge branch `elsif rising_edge(clk_i)`; target of a signal assignment from the combinational logic `bus_req_i.stb and (not bus_req_i.rw)`, stored at the clock edge | (to tag) |
    | line 64 | concurrent statement, outside any process block; in the `<CONDITION>` `(rden = '1')` of the conditional signal assignment to `bus_rsp_o.data`, deciding whether it takes `rdata` or `(others => '0')` | (to tag) |
    | line 65 | concurrent statement, outside any process block; the single element on the right hand side of a simple signal assignment, passing its value unchanged to `bus_rsp_o.ack` | INPUT_OP |

44. Moved to the next signal in the closed set list: `rdata`

45. first appearance @ **line 39**

    > *`signal rdata : std_ulogic_vector(31 downto 0);`*

    The structure matches signal declarations. The occurrence site is tagged as *DECL*

46. Next occurrence @ **line 48**

    > *`rdata <= mem_rom_c(to_integer(unsigned(bus_req_i.addr(boot_rom_size_index_c+1 downto 2))));`*

    This is inside the process block from lines 45-50, in the *sequential conditional statement* from line 47-49, whose only branch is the edge trigger `rising_edge(clk_i)`. This `if` block has no reset branch. `rdata` is the `<target>` of a *signal assignment*, so it takes its value only at the rising edge of `clk_i` and keeps it until the next edge: `rdata` is stored, like a register.

    The value it receives is an *indexed name*: an item of `mem_rom_c`, a *named constant* that is an array, so a *read-only memory*. The `<index>` is a *slice* of `bus_req_i.addr`, bits `boot_rom_size_index_c+1 downto 2`, turned into a number by the *conversions* `unsigned(...)` and `to_integer(...)`. So at each clock edge, `rdata` receives the memory word stored at the position the address selects.

    This is the other side of steps 24-25, where `bus_req_i` supplied the address used as the location, and of steps 9-10, where `clk_i` was the *guard condition* of this branch.

47. Next occurrence @ **line 64**

    > *`bus_rsp_o.data <= rdata when (rden = '1') else (others => '0');`*

    This matches the structure of a *conditional signal assignment*. `rdata` is the `<EXPRESSION>`, one of the two values `bus_rsp_o.data` can take; the other is the `<ALTERNATIVE>`, `(others => '0')`. When the `<CONDITION>` `(rden = '1')` holds, `rdata` is used whole, with no operator, so its value passes unchanged to `bus_rsp_o.data`; both are 32 bits wide. `rdata` is an *input operand*. The statement is outside every process block, so it is a *concurrent statement*. Site tagged as *INPUT_OP*

    This is the other side of step 33, where `bus_rsp_o.data` was the `<TARGET>`, and of step 41, where `rden` was the `<CONDITION>` of the same line.

48. The occurrence profile of signal 'rdata':

    | Occurrence Lines | Context | SITE Tagged |
    | --- | --- | --- |
    | line 39 | signal declarations from lines 38-39 | DECL |
    | line 48 | sequential conditional statements / if statements from line 47-49, clock-edge branch `if rising_edge(clk_i)`, no reset branch; target of a signal assignment that reads the read-only memory `mem_rom_c` at the index given by a slice of `bus_req_i.addr`, stored at the clock edge | (to tag) |
    | line 64 | concurrent statement, outside any process block; the `<EXPRESSION>` of the conditional signal assignment to `bus_rsp_o.data`, passing its value unchanged when `(rden = '1')` | INPUT_OP |
