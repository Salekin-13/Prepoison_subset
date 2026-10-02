# The relation map in each input file

Each input file holds one RTL module (VHDL) and its **relation map**. A static analyser (a program, not a model)
writes the map from the RTL alone. It records facts about how values move and are controlled in the module, and
nothing else: no judgement about security, importance or assets.

## Layout in the input file

```
PORT   {element fields as JSON}
    {"constant_drivers": [...]}        list fields, possibly split over several lines
    {"type": "...", "targets": [...], "guard": "...", "lines": [...]}   one relationship record per line
SIGNAL {element fields as JSON}
    ...
```

Every **line number** (`lines`) refers to the numbered RTL above the map in the same file: the number at the start of
each RTL line is that line's number in the original source file. Comments were removed and blank lines left out, so
numbers skip.

## Elements

An element is a declared name of the module: a **port**, an internal **signal**, or a **field of a record**, written
`<name>.<field>` (for example `req_i.addr` for field `addr` of record port `req_i`, or `state.busy` for field `busy` of an
internal record signal `state`). A whole record and each of its fields are separate elements. Constants, generics,
loop parameters and process variables are not elements. A module file can hold several entities; `entity` says which
one declares the element.

| field | meaning |
|---|---|
| `name`, `entity` | the element and the entity that declares it |
| `boundary` | ports only: `mode` (`in`, `out`, `inout`, `buffer`) and, for an output, `drive`: `driven` (assigned from elements), `tied` (only constants), `undriven` (never assigned as a whole; its fields may be) |
| `kind` | signals only: `register` (assigned on a clock edge somewhere) or `signal` |
| `storage` | `edge`: every assignment is on a clock edge (the element holds its value between edges); `none`: assigned only outside clocked code (combinational); `mixed`: both; `not assigned`: never assigned in this module (inputs, unused names) |
| `handling` | record fields: `ORIGINATES` (the module creates the value), `CONSUMES` (the module reads it), `FORWARDS` (it passes the value on unchanged) |
| `constant_drivers` | assignments that give the element a literal or a named constant: `value` and `lines` |
| `configuration` | build-time conditions (generics, constants) under which the element exists or is driven: `condition`, `lines` |
| `connections` | the element is wired to a port of an instantiated sub-unit: `instance`, `formal` (the sub-unit's port), `mode` of that port; `at` is an internal occurrence number, not a line |

## Relationship records

Each record on element **E** names a relationship type, the other elements (`targets`), the RTL `lines` where it
holds, and, for control types, the `guard`: the condition text as written (a very long condition is cut and marked;
read it at the cited lines). Every relationship is stored from both sides: a **driving** record on the element that
acts, and the matching **receiving** record on the element acted upon.

| driving (on Y) | receiving (on X) | meaning, for a statement that assigns X |
|---|---|---|
| `CARRIES` | `COPIES` | X's right-hand side is exactly Y: no operator, slice, index or conversion |
| `SOURCES` | `DERIVES_FROM` | Y's value is read on X's right-hand side in any other way: as an operand, a function argument, an array element, a slice, the value arm of a conditional or selected assignment, or through a process variable |
| `SEQUENCES` | `CLOCKED_BY` | Y is the clock whose edge X's assignment waits for |
| `RESETS` | `RESET_BY` | Y is tested in the arm before the clock-edge arm of the same `if`, and that arm gives X a constant (a reset) |
| `SELECTS` | `SELECTED_BY` | Y is the selector of the `case` / `with ... select` that holds X's assignment, or a run-time index that picks which part of an array is read into X (or written, when X is the array) |
| `GATES` | `GATED_BY` | Y decides whether X takes a value or forces it to a fixed level: Y appears in an `if` / `elsif` / `when ... else` condition governing X's assignment (bare, compared with a constant, or compared with another element), or Y is a single-bit operand of a top-level `and` / `or` / `nand` / `nor` on X's right-hand side |

Rules the analyser applies: one type per occurrence, in the order SEQUENCES, RESETS, SELECTS, GATES, CARRIES, SOURCES;
the clock is only SEQUENCES and the reset only RESETS; a condition over generics or constants alone is a
`configuration` fact, not a relationship; `X = F(X)` (a counter, a state register) gives records on X naming X.

## What the map is not

- It is mechanical and can be incomplete: a statement the analyser could not place produces no record. The RTL is the
  authority; the map is an index into it.
- It says nothing about meaning or security. Any judgement is the reader's.
