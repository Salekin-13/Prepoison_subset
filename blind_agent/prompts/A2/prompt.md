# Instructions: list the primary security assets of one hardware module

## The task

The input file holds the RTL of one hardware module (VHDL; comments were removed; every line starts with its line
number in the original source) followed by its relation map. Your job is to list the module's **primary security
assets**: the declared elements (ports, internal signals, and fields of records) that are themselves the target of an
attack.

List every primary asset and nothing else. A primary asset that you leave out and an element that you list but should
not have listed are both errors, and they weigh the same. Decide each element with the definitions and rules below,
and apply them the same way to every element. Do not aim for any list size, and do not add an element "to be safe".

You do not know the system this module will be used in. Assume it is used in a system that needs confidentiality,
integrity and availability protection, and judge only what this module itself holds, produces and controls. The RTL is
the authority; the map is a mechanical index into it.

## Definitions (every decision rests on these)

- **Security asset**: a hardware component or value whose protection is needed to keep confidentiality, integrity or
  availability.
- **Conceptual asset**, the *what*: a piece of information or state that matters for how the module is used, together
  with the objective at risk. Examples: a secret key; a random seed; a message being sent or received; a protection or
  configuration setting; the address of the next instruction; a countdown that ends in a system reset; the module's
  computed result. A conceptual asset is the information itself, wherever it sits: the same outgoing message in a
  queue, in a shift register and on a serial port is a single conceptual asset. Information that moves the other way
  (received instead of sent) is a separate conceptual asset.
- **Structural asset**, the *where*: the RTL element that physically stores, produces or carries a conceptual asset
  (a register, a memory, a buffer, a wire, a port).
- **Primary asset**: the structural element that *is* the conceptual asset inside this module, the place where it is
  held, so that an attacker who reads, changes or blocks this element gets the harm directly. Example: in an encryption
  engine the key is the conceptual asset, and the register that stores the key is the primary asset.
- **Secondary asset** (never listed): an element that only interacts with a primary asset or helps expose it. That
  covers the buses and interface fields that move it, the ports and wires that carry a copy or a part of it, the
  enables, selects and addresses that decide when it is written or which part is read, and the machinery that steps an
  operation along. In the encryption engine, the processing logic and the output buffer are secondary.
- **Content value**: information that the module stores, transforms, computes with, or transfers as payload.
  Examples: keys, seeds, random numbers, messages, operands, results, memory contents, instruction words.
- **Steering value**: information that decides whether, when, where or how something happens. Examples: write enables,
  strobes, selects, addresses and indexes, operation codes, handshakes, request attributes (privilege, debugger or
  origin tags), configuration and protection settings, modes, bus grants, locking bits, reservations, and reset, halt
  or interrupt requests.
- **Sub-unit**: an entity instantiated inside this module (the map names it as an `instance` under `connections`). A
  sub-unit is part of this module, even when its RTL is not in the file. **Another unit** means anything outside this
  module.

In short: **primary = where the valued thing is held; secondary = how it gets in, gets out, gets used, or is steered.**
Being connected to an asset, or influencing it, is what makes an element secondary. It never makes it primary.

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
- `connections`: the element is wired to a port of a sub-unit; `instance` names the sub-unit, `formal` is the
  sub-unit's port, and `mode` its direction (`out` means the sub-unit drives this element). The `mode` can be empty.
  Then read the port map in the RTL: if this module assigns the element nowhere else and reads it, or wires it to an
  output port, the sub-unit drives it. When a whole record is wired to a sub-unit, its fields are wired through it
  too, even though their own lines show no `connections` and say `not assigned`.

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
what enters and leaves through each interface; which sub-units it instantiates and what each one holds, as far as the
port map shows; what it stores; what software or another unit can set through a register interface (elements loaded
from the interface's write payload under a write condition); what software can read back (elements that feed the
read-back response); what it computes; and which reactions it can trigger in the rest of the system. Element names are
useful hints about meaning, but confirm every hint by what the RTL does with the element.

### Step B: find the conceptual assets

Ask these questions about the module. Each "yes" names a conceptual asset and its objective.

- **Confidentiality.** Is there information here, received or generated, that someone could want kept secret? Typical
  answers: keys, seeds, random numbers, identifiers; a message or payload being transferred, buffered or stored; the
  contents of a memory; the operands and results of a computation; values that reveal what another process is doing.
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

Then decide which of these belong to this module:

- A **content value** that this module or one of its sub-units receives, stores, computes or produces is a
  conceptual asset when a question above answers "yes" for it.
- A **steering value** is a conceptual asset of this module only when this module or one of its sub-units keeps it as
  its own state: a setting written by software and kept, a mode, a grant, a locking state or a reservation, a count
  that triggers a reaction, a stored status record; or when it is a reaction request (reset, timeout, alarm, fault,
  halt, interrupt) that this module or a sub-unit generates.
- A steering value that arrives from another unit and is only used here (a requester's privilege or debugger tag, an
  address, an enable, a reset, halt or interrupt request raised elsewhere) is held in that other unit. Record it with
  holder case `held in another unit` (Step C). Its port or field is an interface carrier here.
- A steering value kept only for the length of one transfer or operation (an operation code, a request attribute, a
  direction flag) is a transient control, not this module's own state.

If every answer is "no" for a piece of information or state, it is not an asset. Normal functional use is not an
attack: a write enable that writes as designed, or a pointer that advances as designed, does not by itself make
anything an asset.

### Step C: map each conceptual asset to its holder

For each conceptual asset, apply these tests in the order listed and stop at the first that fits. Write the name of
the test in `holder_case`.

- **`forwarded`.** The value only passes through: it arrives through a port of this module and leaves through another
  port in the same form, and this module (with its sub-units) neither keeps it for its own operation nor computes with
  it. Map cues: a port that `COPIES` a port; a port field marked `FORWARDS` that is wired straight to another port; a
  register stage that copies a whole request or response on every transfer. `FORWARDS` on its own does not decide this
  test: an internal record field marked `FORWARDS` that carries a value from one sub-unit of this module to another is
  not forwarded; use the `sub-unit` test for it. When this test fits, no element of this module is the holder.
- **`stored here`.** An element of this file stores it: a register, register array or memory assigned on a clock
  edge (`storage` `edge` or `mixed`) that keeps the value between deliberate updates. This includes a register that
  captures a value from a port or from a sub-unit under a load condition (a write, the launch of an operation, an
  accepted transfer) and keeps it, and a register that builds a value step by step (a shift register assembling a
  received word, a counter, an accumulator). A memory or register array is a single element: list the array name. If
  the value is kept in alternative stores that exist under different build settings, each store is a holder. If
  parallel stores each keep a different part of it (for example separate byte lanes of the same memory), each store
  is a holder.
- **`read from a constant`.** The value comes from a constant (for example a read-only memory image declared as a
  constant). The constant is not an element; the holder is the register that receives the value read from it.
- **`sub-unit`.** The value rests inside a sub-unit whose RTL is not in this file. The holder is the element of this
  module connected to the sub-unit output that delivers the value (its read-out, its current value, its decision or
  its request), even when that output delivers only the selected entry of a larger store. When the output is a record
  wired as a whole, the holder is the field that carries the value (see the record check). Fields of bus request and
  response records are never holders under this test; they stay interface carriers (Step D). If no output of the
  sub-unit delivers the value (the sub-unit only consumes it), the holder is the element that carries the value into
  the sub-unit from outside this module, usually an input port. The `stored here` test comes first: when the same
  value is also stored in this file, the sub-unit's connections are secondary.
- **`produced here`.** The module computes the value and does not store it. The holder is the signal or output port
  that the computation assigns.
- **`content input`.** A content value enters through an input port, this module computes with it, and no element of
  this module stores it in any build (as it is, or in a converted form such as sign-extended or negated). The holder
  is that input port.
- **`held in another unit`.** A steering value that arrives from another unit and is only used here. No holder; its
  port or field is an interface carrier.
- **`constant only`.** The value is a constant that is compared or used but never read into an element. No holder.

`held_by` may be empty only under `forwarded`, `held in another unit` or `constant only`. In every other case, name the
holder. If no test fits and you cannot name a holder, the item is not a conceptual asset (it is a transient control,
bookkeeping or a carrier): remove it from `conceptual_assets`.

**The holder of a chain.** A conceptual asset usually appears at several places along a chain (input port, register,
delayed copy, sub-unit connection, output port). It is listed at its holder only; every other element of the chain is
secondary. When several stores of this file hold the same value one after another, choose the holder in this order of
preference:

- first, the store that another party (software, an external debugger, another unit) writes or reads directly;
- otherwise, the store where the complete value comes to rest and is kept until the next deliberate update.

The other stores of the chain (staging registers, pipeline stages, delayed copies, shift-out stages loaded from the
holder) are secondary.

**Store or copy.** A register is a *store* when it loads a value under a condition and keeps it otherwise, or when it
builds a value step by step. A register is a *delayed copy* when its next value is another element of this file,
copied on every clock with no load condition (`COPIES`, or a slice of it). A *synchroniser* is a chain of registers
that copies an input port on every clock. Delayed copies and synchronisers are secondary. A register that captures a
content value from a port under a load condition is a store, not a copy.

An element that holds a conceptual asset is primary even when it also gates, selects or feeds other logic
(configuration registers always do).

### Step D: everything else is secondary

These are not primary assets. Do not list them, whatever their names suggest.

- **Clock and reset**: elements with `SEQUENCES` or `RESETS` records.
- **Holds nothing**: a signal never assigned in this module (`storage` `not assigned`) unless a sub-unit drives it
  through `connections`, its own or those of its whole record; an input with no relationship records and no
  `connections`; an output whose `drive` is `tied` or that only ever receives constants; a whole record port or signal
  that is `undriven` or `not assigned` as a whole (judge its fields one by one).
- **Interface carriers**: fields of bus request and response records, and other ports, that move a value whose holder
  is another element of this module or belongs to another unit. This covers the address, the write payload, byte
  enables, strobes, read/write flags, requester attributes such as privilege, debugger or origin tags, the read-back
  payload, acknowledge or error responses that copy an internal element, and steering inputs raised by another unit
  (enables, reset, halt and interrupt requests). Fields of bus request and response records stay interface carriers
  even when a sub-unit drives them. They are the attack points through which assets are reached, not assets. An
  internal signal or record field that connects sub-units is judged with the `sub-unit` test of Step C, not here.
- **Copies and parts**: an element whose value is a plain copy (`COPIES`); a slice; an indexed read of an array stored
  in this file (`SELECTED_BY` with a read from the array); a multiplexed or gated version of a holder (`GATED_BY`
  together with `DERIVES_FROM` of the holder); a merge of several holders (an `or` or a concatenation of them); a
  delayed copy or a synchroniser; a serial-line port or a sub-unit connection that carries a value stored in this
  file.
- **Next-value helpers**: combinational signals computed only to be loaded into a register at the next clock edge
  (they `CARRIES` into a register that `COPIES` them).
- **Transient controls**: enables, strobes, selects, read and write pulses, handshake and flow-control flags (request
  accepted, transfer pending, unit occupied, room available, entries available), decoded conditions, comparison
  results that only gate other assignments, and operation codes or request attributes kept only for the length of one
  transfer or operation.
- **Bookkeeping state**: pointers and indexes into a buffer, bit and beat counters, prescaler ticks, and state machines
  that only step through the phases of an operation. Software cannot set or read these as such, and they do not encode
  a privilege, protection or security mode. A state register is bookkeeping when its value only says which step is
  running. It holds a conceptual asset when its value says who owns or may use something (a bus grant, a locking
  state, a reservation) or which privilege, protection or security mode is in force.
- **Derived status**: values computed combinationally from other state (for example a fill count computed from
  pointers), unless they are stored as a status record that software acts on, or are a reaction request from Step B.

### Step E: check before you write

- **Attack check.** For each element you keep, name the attack on its own value: observing it (side channel, leakage
  to a less trusted party), changing it (fault injection, unauthorized write, privilege escalation, hidden malicious
  logic), or blocking or forcing it (denial of service). If the attack would really be aimed at another element that
  this one only carries or controls, this element is secondary.
- **Chain check.** If two listed elements are linked by `COPIES`/`CARRIES`, or one is a slice, indexed read, gated
  version, merge or delayed copy of the other, or one is a store and the other a sub-unit connection carrying the same
  value, keep only the holder.
- **Sibling check.** Elements with the same role get the same decision: every channel, both directions (transmit and
  receive), every region or entry register of the same kind, every field of the same kind, every operand store of the
  same operation, every read-out of the same store, and every fault, error or alarm request that the module or its
  sub-units generate. If you list one, list all of them; if you drop one, drop all of them, unless the RTL shows a real
  difference in role.
- **Record check.** Never list a record together with any of its own fields. List the whole record when it is a single
  software-visible register whose fields are loaded together by the same write (it is a single asset). List individual
  fields when the record groups values with different roles (an interface record, a record holding several separate
  registers, a record mixing state and payload), and then list only the fields that are primary.
- **Holder check.** Every conceptual asset has a `holder_case`. `held_by` is empty only for `forwarded`,
  `held in another unit` and `constant only`.
- **Coverage check.** Each conceptual asset from Step B has a holder in your list, or one of the holder cases that
  allow an empty `held_by`. Every entity in the file has been examined.

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
- **Execution units and co-processors** (arithmetic units, cipher or hash helpers attached to a processor). The
  operands, at the registers that keep them for the operation (or at the input ports when nothing stores them); the
  result; for a cipher, the key, the block being enciphered or deciphered, and the running cipher state. Usually
  secondary: operation codes, launch and completion flags, step counters, combinational intermediate terms, the result
  port when it only selects from the result registers.
- **Units that only connect sub-units** (a processor top, a subsystem wrapper). The elements connected to the
  sub-unit outputs that deliver held values: read-outs of register files and of control and status registers, the
  current and next instruction address, the current privilege and debugger state, fetched instruction words,
  protection decisions, and the fault or error requests that sub-units raise; a content input that rests in a sub-unit
  and is never delivered back. Usually secondary: bus request and response fields, merged read-back words, write
  payloads on their way into a store, handshakes, and interrupt or halt requests raised by other units.
- **Bus and memory units.** Memory arrays (each as a whole array); the stored lines of caches with their address tags
  and valid bits; in a unit that only routes or arbitrates, the elements that hold its own decisions (current grant,
  selected target, timeout and error decisions, reservations). Usually secondary: forwarded request and response
  fields, register stages that pass requests and responses through, address decoders, handshakes, operation codes
  latched for one transfer.
- **Debugger units.** The registers through which an external debugger reads or writes the system (command, argument
  and result registers, program buffer contents, payload being shifted in or out); the halt, resume and reset requests
  the unit generates; its enable or authentication state. Usually secondary: transport handshakes, shift and bit
  counters, synchronisers, sequencing state, staging copies of the shifted payload.
- **Timers and watchdogs.** The count value, the compare and reload values, the control register, and the timeout,
  reset or interrupt request the unit generates. Usually secondary: prescaler ticks, edge detectors, output ports that
  only combine the stored requests.
- **Communication peripherals.** The control register; the transmit and receive payload registers, buffers and shift
  registers of this file (the connections of a queue sub-unit are secondary when the same message is stored in this
  file); stored error and status flags; interrupt requests. Usually secondary: bit and baud counters, input
  synchronisers, serial-line ports that only carry bits of a held register, buffer handshakes.
- **Security peripherals** (random number generation, cryptography, protection). Keys, seeds, the internal state of the
  noise source or entropy pool, random or cryptographic output registers, health-test and alarm flags, the control
  register.

## Worked examples (invented designs, not your input)

### First example: a register-mapped peripheral

Entity `demo_signer` is a small signing peripheral. Software writes through the record port `host_in` (fields
`host_in.word`, `host_in.place`, `host_in.put`) and reads back through the record port `host_out` (field
`host_out.word`). One write loads the configuration record `setup_q` (fields `setup_q.go` and `setup_q.wprot`, both
loaded by that same write). Another write loads the secret register `secret_q`. For each operation the module computes
`sig_next` and loads it into the result register `sig_q`. `sig_dly_q` copies `sig_q` one cycle later and feeds the
read-back. `step_q` counts the steps of an operation, `occupied_s` says an operation is running, and the output port
`alarm_out` is set on a clock edge when an internal check fails.

| element | decision | why |
|---|---|---|
| `secret_q` | primary, Confidentiality | `stored here`: holds the secret |
| `setup_q` | primary, Integrity | `stored here`: a single software-visible configuration register whose fields are loaded by the same write, so the record is listed and its fields are not |
| `sig_q` | primary, Integrity | `stored here`: holds the module's computed result |
| `alarm_out` | primary, Availability | `stored here`: the reaction request is produced and held on this port itself |
| `host_in.word` | secondary | interface carrier into `secret_q` and `setup_q` |
| `host_in.place`, `host_in.put` | secondary | select and strobe |
| `host_out.word` | secondary | read-back carrier |
| `sig_next` | secondary | next-value helper of `sig_q` |
| `sig_dly_q` | secondary | delayed copy of `sig_q` |
| `step_q` | secondary | bookkeeping counter |
| `occupied_s` | secondary | handshake flag |
| `setup_q.go`, `setup_q.wprot` | not listed | their record is listed |
| the clock and reset inputs | secondary | clock and reset |

### Second example: a serial link with a queue sub-unit

Entity `demo_link` sends and receives words on a serial line. Software writes outgoing words through the record port
`host_in` (fields `host_in.word`, `host_in.put`, and `host_in.rank`, the privilege tag of the requester). A write is
accepted only when the comparison `rank_ok_s` finds `host_in.rank` high enough. Accepted words go into a queue
sub-unit `outq_inst` whose RTL is not in the file: `outq_feed_s` is wired to its write port and `outq_head_s` to its
read port. When the line is idle, the module loads the oldest queued word from `outq_head_s` into the shift register
`shift_q` and shifts it out bit by bit on `line_out`. Incoming bits on `line_in` pass through the synchroniser
registers `line_ma_q` and `line_mb_q` and are shifted into `catch_q`, which software reads through `host_out.word` once
a word is complete. `bitpos_q` counts the bits. Software sets the bit rate in `mode_q`, which keeps it until the next
write.

| element | decision | why |
|---|---|---|
| `shift_q` | primary, Confidentiality | `stored here`: the outgoing message is stored in this file here. The queue holds the same message, but a store in this file comes first |
| `catch_q` | primary, Confidentiality | `stored here`: the incoming message is assembled and kept here until software reads it (a separate conceptual asset: the other direction) |
| `mode_q` | primary, Integrity | `stored here`: the module's own setting, written by software and kept |
| `outq_feed_s`, `outq_head_s` | secondary | sub-unit connections that carry a value stored in this file (`shift_q`) |
| `line_out` | secondary | carries bits of `shift_q` |
| `line_in` | secondary | carries bits that come to rest in `catch_q` |
| `line_ma_q`, `line_mb_q` | secondary | synchroniser copies of `line_in` |
| `host_in.rank` | secondary | steering input: the requester's privilege is held in the requesting unit and only decides here whether a write is accepted (conceptual asset with holder case `held in another unit`, empty `held_by`) |
| `rank_ok_s` | secondary | comparison result that gates a write |
| `host_in.word`, `host_in.put` | secondary | write payload and strobe |
| `host_out.word` | secondary | read-back carrier |
| `bitpos_q` | secondary | bookkeeping counter |

### Third example: a module that only connects sub-units

Entity `demo_top` contains no register of its own. The sub-unit `vault_inst` (RTL not in the file) holds secret words
and delivers the selected one on its output port, wired to the signal `vault_secret_s`, which feeds the cipher sub-unit
`mix_inst` (RTL not in the file). The input port `plain_in` carries the words to be enciphered straight into
`mix_inst`; no element of `demo_top` stores them and no sub-unit output delivers them back. `mix_inst` drives the
output port `mix_out` with its result. The read-outs of the status registers of the sub-units arrive on `vault_stat_s`
and `mix_stat_s`; `stat_all_s` is their `or` and drives the record field `host_out.word`. The input port `stop_in` is a
halt request raised by another unit and wired to each sub-unit.

| element | decision | why |
|---|---|---|
| `vault_secret_s` | primary, Confidentiality | `sub-unit`: the secret rests in `vault_inst`; this is the element connected to the output that delivers it |
| `plain_in` | primary, Confidentiality | `sub-unit`: the words rest in `mix_inst` and no output delivers them back, so the element that carries them in is the holder |
| `mix_out` | primary, Integrity | `sub-unit`: the computed result, delivered by the cipher sub-unit's output |
| `vault_stat_s`, `mix_stat_s` | primary, Integrity | `sub-unit`: each delivers the status registers that rest in its sub-unit (siblings) |
| `stat_all_s` | secondary | merge of holders |
| `host_out.word` | secondary | read-back carrier |
| `stop_in` | secondary | steering input raised by another unit (`held in another unit`) |

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
     "holder_case": "stored here | read from a constant | sub-unit | produced here | content input | forwarded | held in another unit | constant only",
     "held_by": ["<element>"],
     "chain_not_listed": ["<carriers, copies and controls of it>"]}
  ],
  "element_roles": {
    "primary": ["<element>"],
    "field_of_listed_record": ["<element>"],
    "clock_or_reset": ["<element>"],
    "holds_nothing": ["<element>"],
    "interface_carrier": ["<element>"],
    "copy_or_part": ["<element>"],
    "control_or_bookkeeping": ["<element>"],
    "derived_status": ["<element>"]
  }
}
```

Every element line of the map goes into a single list of `element_roles`, by name (a name declared in several
entities is written once per entity that declares it). The `primary` list and the `assets` array name the same
elements. The fields of a record listed whole go into `field_of_listed_record`. If, after all steps, no element
qualifies, `assets` is an array with no entries.
