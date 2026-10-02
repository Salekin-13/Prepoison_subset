# Instructions: list the primary security assets of one hardware module

## The task

The input file holds the RTL of one hardware module (VHDL; comments were removed; every line starts with its line
number in the original source) followed by its relation map. Your job is to list the module's **primary security
assets**: the declared elements (ports, internal signals, and fields of records) that are themselves the target of an
attack.

List every primary asset and nothing else. A primary asset that you leave out and an element that you list but should
not have listed are both errors, and they weigh the same. Decide each element with the definitions and rules below. Do
not aim for any list size, and do not add an element "to be safe".

You do not know the system this module will be used in. Assume it is used in a system that needs confidentiality,
integrity and availability protection, and judge only what this module itself holds, produces and controls. The RTL is
the authority; the map is a mechanical index into it.

## Definitions (every decision rests on these)

- **Security asset**: a hardware component or value whose protection is needed to keep confidentiality, integrity or
  availability.
- **Conceptual asset**, the *what*: a piece of information or state that matters for how the module is used, together
  with the objective at risk. Examples: a secret key; a random seed; a message being sent or received; a protection or
  configuration setting; the address of the next instruction; a countdown that ends in a system reset; the module's
  computed result.
- **Structural asset**, the *where*: the RTL element that physically stores, produces or carries a conceptual asset
  (a register, a memory, a buffer, a wire, a port).
- **Primary asset**: the structural element that *is* the conceptual asset inside this module, the place where it is
  held, so that an attacker who reads, changes or blocks this element gets the harm directly. Example: in an encryption
  engine the key is the conceptual asset, and the register that stores the key is the primary asset.
- **Secondary asset** (never listed): an element that only interacts with a primary asset or helps expose it. That
  covers the buses and interface fields that move it, the ports and wires that carry a copy or a part of it, the
  enables, selects and addresses that decide when it is written or which part is read, and the machinery that steps an
  operation along. In the encryption engine, the processing logic and the output buffer are secondary.

In short: **primary = where the valued thing is held; secondary = how it gets in, gets out, or gets used.** Being
connected to an asset, or influencing it, is what makes an element secondary. It never makes it primary.

## Reading the relation map

**Element lines.** Each `PORT` or `SIGNAL` line is one element, written as JSON:

- `name`, `entity`: the element and the entity that declares it. A record field is written `<record>.<field>`. The
  whole record and each of its fields are separate elements. Constants, generics, types, loop parameters and process
  variables are not elements. A file can hold several entities.
- `boundary` (ports only): `mode` is `in`, `out`, `inout` or `buffer`. For an output, `drive` is `driven` (assigned
  from elements), `tied` (only constants) or `undriven` (never assigned as a whole; its fields may be).
- `kind` (signals only): `register` (assigned on a clock edge somewhere) or `signal`.
- `storage`: `edge` (every assignment is on a clock edge, so the element keeps its value between edges), `none`
  (combinational only), `mixed` (both, usually under different build settings), `not assigned` (never assigned in this
  module).
- `handling` (record fields): `ORIGINATES` (this module creates the value), `CONSUMES` (this module reads it),
  `FORWARDS` (this module passes it on unchanged).
- `constant_drivers`: assignments that give the element a literal or a named constant (reset values, defaults,
  tie-offs).
- `configuration`: build-time conditions under which the element exists or is driven. An element that exists only
  under some build settings is still a candidate.
- `connections`: the element is wired to a port of an instantiated sub-unit; `formal` is that port and `mode` its
  direction (`out` means the sub-unit drives this element).

**Relationship records** (the indented lines). Each record on an element names a type, the other elements
(`targets`), the RTL `lines` where it holds, and, for control types, the `guard` (the condition text; a very long one
is cut, so read it at the cited lines). Every relationship is stored on both sides: a driving record on the element
that acts and a receiving record on the element acted on. For a statement that assigns X using Y:

| on Y (drives) | on X (receives) | meaning |
|---|---|---|
| `CARRIES` | `COPIES` | X is exactly Y: no operator, slice, index or conversion |
| `SOURCES` | `DERIVES_FROM` | Y is read on X's right-hand side in any other way: operand, function argument, array element, slice, value arm of a conditional or selected assignment, or through a process variable |
| `SEQUENCES` | `CLOCKED_BY` | Y is the clock whose edge X's assignment waits for |
| `RESETS` | `RESET_BY` | Y is the reset that gives X a constant |
| `SELECTS` | `SELECTED_BY` | Y is the selector of the `case` or `select` holding X's assignment, or a run-time index that picks which part of an array is read into X (or written, when X is the array) |
| `GATES` | `GATED_BY` | Y appears in a condition that decides whether X takes a value or is forced to a fixed value, or Y is a single-bit operand of a top `and`/`or`/`nand`/`nor` on X's right-hand side |

Other types can appear (for example `CONSTRAINS` / `CONSTRAINED_BY`, for an element compared inside the condition that
defines another one); read the cited lines to see what they mean. A record on X that names X itself means X is
computed from its own value (a counter, an accumulator, a state register). The map can miss a statement; when in doubt,
read the RTL lines.

## Procedure

### Step A: understand the module

Read the whole file, in several reads if it is long, down to the last map line. Then work out: what the module is for;
what enters and leaves through each interface; what it stores; what software or another unit can set through a
register interface (elements loaded from the interface's write payload under a write condition); what software can
read back (elements that feed the read-back response); what it computes; and which reactions it can trigger in the
rest of the system. Element names are useful hints about meaning, but confirm every hint by what the RTL does with the
element.

### Step B: find the conceptual assets

Ask these questions about the module. Each "yes" names a conceptual asset and its objective.

- **Confidentiality.** Is there information here, received or generated, that someone could want kept secret? Typical
  answers: keys, seeds, random numbers, identifiers; a message or payload being transferred, buffered or stored; the
  contents of a memory; values that reveal what another process is doing.
- **Integrity.** Is there state or configuration that must not be changed by an unauthorized party or at the wrong
  time? Typical answers: configuration and control settings; permissions and protected address ranges; write-protection
  or locking bits; the current privilege mode; a debugger-halted or debugging state; code or instructions to be executed;
  control-flow state such as the program counter, trap vector and return address; counters and timers whose value is
  the module's function or triggers a reaction; stored status and error records that software acts on; the module's
  computed result.
- **Availability.** Is there an element that, if blocked or forced, stops the module or the system from operating or
  reacting? Typical answers: the reset, timeout, alarm, fault, halt and interrupt requests this module generates; an
  element whose stuck value cuts off the module's service.
- **Undermined behavior.** Are there privileged modes, overrides, bypasses, or test or debugger injection paths that
  can make the module produce wrong output? Typical answer: the stored setting or mode that turns them on.

If every answer is "no" for a piece of information or state, it is not an asset. Normal functional use is not an
attack: a write enable that writes as designed, or a pointer that advances as designed, does not by itself make
anything an asset.

### Step C: map each conceptual asset to its holder

For each conceptual asset, find where it is held in this module. Use the first case that applies:

- **Stored here.** A register, register array or memory of this module whose value is the conceptual asset (assigned
  on a clock edge and kept between writes: `storage` `edge` or `mixed`) is its holder. A memory or register array is
  a single element: list the array name. If the module keeps the same asset in alternative stores that exist under
  different build settings, each store is a holder.
- **Read from a constant.** If the value comes from a constant (for example a read-only memory image declared as a
  constant), the constant is not an element; the holder is the register that receives the value read from it.
- **Produced by a sub-unit whose RTL is not in this file.** The holder in this module is the element connected to that
  sub-unit's output port (`connections` with mode `out`) that carries the conceptual asset.
- **Not stored at all.** The holder is the element where the module produces the value (the signal or output port
  assigned by the computation). For a value that the module receives and uses in its computation without storing it,
  the holder is the input port through which it enters.
- **Only forwarded.** A value that the module passes on unchanged from one interface to another (`handling`
  `FORWARDS`, or a port that `COPIES` a port) belongs to another unit; nothing here is its holder.

A conceptual asset usually appears at several places along a chain (input port, register, delayed copy, output port).
It is listed at its holder only; every other element of the chain is secondary. When the same value sits in several
registers in a row, the holder is the one that keeps it as the asset: the register software sees, or the register that
keeps the value until the next deliberate update. Staging, pipeline and delayed copies are secondary.

An element that holds a conceptual asset is primary even when it also gates, selects or feeds other logic
(configuration registers always do).

### Step D: everything else is secondary

These are not primary assets. Do not list them, whatever their names suggest.

- **Clock and reset**: elements with `SEQUENCES` or `RESETS` records.
- **Holds nothing**: a signal never assigned in this module (`storage` `not assigned`) unless a sub-unit drives it
  through `connections`; an input with no relationship records; an output whose `drive` is `tied` or that only ever
  receives constants; a whole record port marked `undriven` (judge its fields one by one).
- **Interface carriers**: fields of request and response records, and other ports, that move a value whose holder is
  elsewhere in this module. This covers the address, the write payload, byte enables, strobes, read/write flags,
  requester attributes such as privilege or origin tags, the read-back payload, and acknowledge or error responses that
  copy an internal element. They are the attack points through which assets are reached, not assets.
- **Copies and parts**: an element whose value is a plain copy (`COPIES`), a slice or an indexed read of an array
  (`SELECTED_BY` with a read from the array), a multiplexed or gated version of a holder (`GATED_BY` together with
  `DERIVES_FROM` of the holder), or a delayed copy (a register that copies another element or another register's next
  value).
- **Next-value helpers**: combinational signals computed only to be loaded into a register at the next clock edge
  (they `CARRIES` into a register that `COPIES` them).
- **Transient controls**: enables, strobes, selects, read and write pulses, handshake and flow-control flags (request
  accepted, transfer pending, unit occupied, room available, entries available), decoded conditions, and comparison
  results that only gate other assignments.
- **Bookkeeping state**: pointers and indexes into a buffer, bit and beat counters, prescaler ticks, and sequencing
  state machines. These are values the module uses internally to step through an operation; software cannot set or read
  them as such, and they do not encode a privilege, protection or security mode.
- **Derived status**: values computed combinationally from other state (for example a fill count computed from
  pointers), unless they are stored as a status record that software acts on, or are a reaction request from Step B.

### Step E: check before you write

- **Attack check.** For each element you keep, name the attack on its own value: observing it (side channel, leakage
  to a less trusted party), changing it (fault injection, unauthorized write, privilege escalation, hidden malicious
  logic), or blocking or forcing it (denial of service). If the attack would really be aimed at another element that
  this one only carries or controls, this element is secondary.
- **Chain check.** If two listed elements are linked by `COPIES`/`CARRIES`, or one is a slice, indexed read, gated
  version or delayed copy of the other, keep only the holder.
- **Sibling check.** Elements with the same role get the same decision: every channel, both directions (transmit and
  receive), every region or entry register of the same kind, every field of the same kind. If you list one, list all of
  them; if you drop one, drop all of them, unless the RTL shows a real difference in role.
- **Record check.** Never list a record together with any of its own fields. List the whole record when it is a single
  software-visible register whose fields are loaded together by the same write (it is a single asset). List individual
  fields when the record groups values with different roles (an interface record, a record holding several separate
  registers, a record mixing state and payload), and then list only the fields that are primary.
- **Coverage check.** Each conceptual asset from Step B has a holder in your list, or a note in the analysis saying
  why no element of this module holds it. Every entity in the file has been examined.

### Step F: names

- `element`: copy the `name` of a `PORT` or `SIGNAL` line of the map, character for character (same case;
  `<record>.<field>` for a field). Never write a slice, bit range, index, constant, generic, type, process variable,
  process or generate label, or instance name. Never write a sub-unit's port name, unless that sub-unit's entity is in
  this file and the map lists the element under that entity.
- `entity`: that element's `entity` value in the map.
- `security_objective`: the objective most at risk for this element. `Confidentiality` when the harm is that someone
  learns the value; `Integrity` when the harm is that someone changes it; `Availability` when the harm is that it is
  blocked or forced so that the system cannot operate or react. Give a single value.
- `reason`: name the conceptual asset, say why this element is where it is held, and name the attack on it.
- Each element appears in `assets` only once.
- `module`: the name after `MODULE:` on the first line of the input.

## What the conceptual assets usually are, by kind of unit

Use this as a reminder of what to look for, not as a list to copy. Every entry still has to pass Steps C to E in the
module you are reading.

- **Processor core parts.** The program counter and the address of the next instruction; fetched instruction words
  waiting to execute; register file contents; control and status registers (trap vector, exception return address,
  trap cause and value, interrupt enable and pending bits, status and mode bits, scratch and counter registers); the
  current privilege mode and the debugger-halted state; memory-protection configuration and address registers.
  Usually secondary: pipeline handshakes, decoded instruction fields, operand selects, forwarding paths, sequencing
  state.
- **Bus and memory units.** Memory arrays (each as a whole array); the stored lines of caches with their address tags
  and valid bits; in a unit that only routes or arbitrates, the elements that hold its own decisions (current grant,
  selected target, timeout and error decisions, reservations). Usually secondary: forwarded request and response
  fields, address decoders, handshakes.
- **Debugger units.** The registers through which an external debugger reads or writes the system (command, argument
  and result registers, program buffer contents, payload being shifted in or out); the halt, resume and reset requests
  the unit generates; its enable or authentication state. Usually secondary: transport handshakes, shift and bit
  counters, synchronisers, sequencing state.
- **Timers and watchdogs.** The count value, the compare and reload values, the control register, and the timeout,
  reset or interrupt request the unit generates. Usually secondary: prescaler ticks, edge detectors.
- **Communication peripherals.** The control register; transmit and receive payload registers, buffers and shift
  registers; stored error and status flags; interrupt requests. Usually secondary: bit and baud counters, input
  synchronisers, serial-line ports that only carry bits of a held register, buffer handshakes.
- **Security peripherals** (random number generation, cryptography, protection). Keys, seeds, the internal state of the
  noise source or entropy pool, random or cryptographic output registers, health-test and alarm flags, the control
  register.

## Worked example (an invented design, not your input)

Entity `demo_signer` is a small signing peripheral. Software writes through the record port `host_in` (fields
`host_in.word`, `host_in.place`, `host_in.put`) and reads back through the record port `host_out` (field
`host_out.word`). One write loads the configuration record `setup_q` (fields `setup_q.go` and `setup_q.wprot`, both
loaded by that same write). Another write loads the secret register `secret_q`. For each operation the module computes
`sig_next` and loads it into the result register `sig_q`. `sig_dly_q` copies `sig_q` one cycle later and feeds the
read-back. `step_q` counts the steps of an operation, `occupied_s` says an operation is running, and the output port
`alarm_out` is set on a clock edge when an internal check fails.

| element | decision | why |
|---|---|---|
| `secret_q` | primary, Confidentiality | holds the secret |
| `setup_q` | primary, Integrity | a single software-visible configuration register whose fields are loaded by the same write, so the record is listed and its fields are not |
| `sig_q` | primary, Integrity | holds the module's computed result |
| `alarm_out` | primary, Availability | the reaction request is produced and held on this port itself |
| `host_in.word` | secondary | interface carrier into `secret_q` and `setup_q` |
| `host_in.place`, `host_in.put` | secondary | select and strobe |
| `host_out.word` | secondary | read-back carrier |
| `sig_next` | secondary | next-value helper of `sig_q` |
| `sig_dly_q` | secondary | delayed copy of `sig_q` |
| `step_q` | secondary | bookkeeping counter |
| `occupied_s` | secondary | handshake flag |
| `setup_q.go`, `setup_q.wprot` | not listed | their record is listed |
| the clock and reset inputs | secondary | clock and reset |

## Output

Write a single JSON object and nothing else. Its required shape is:

```json
{"module": "<module name from the input file>",
 "assets": [
   {"element": "<a declared element name, exactly as declared: a port, a signal, or <record>.<field>>",
    "entity": "<the entity that declares it>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<one or two sentences>"}
 ]}
```

Between `module` and `assets`, add the key `analysis`, filled in before you write `assets`:

```json
"analysis": {
  "purpose": "<what the module does, in plain words>",
  "conceptual_assets": [
    {"what": "<the valued information or state>",
     "objective": "Confidentiality | Integrity | Availability",
     "held_by": ["<element>"],
     "chain_not_listed": ["<carriers, copies and controls of it>"]}
  ],
  "element_roles": {
    "primary": ["<element>"],
    "clock_or_reset": ["<element>"],
    "holds_nothing": ["<element>"],
    "interface_carrier": ["<element>"],
    "copy_or_part": ["<element>"],
    "control_or_bookkeeping": ["<element>"],
    "derived_status": ["<element>"]
  }
}
```

Every element line of the map goes into a single list of `element_roles`, by name. The `primary` list and the
`assets` array name the same elements. If, after all steps, no element qualifies, `assets` is an array with no entries.
