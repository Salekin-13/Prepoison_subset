# Finding the primary security assets of a hardware module

## Your task

You get one input file. It holds a hardware module written in VHDL (the "RTL"). After the RTL comes a
"relation map" of the same module. Your job is to list the module's **primary security assets** and write
them as one JSON object to the output file.

Your list is compared, name by name, with a list made by hardware-security experts. A missed asset counts
against you. An extra entry counts against you just as much. So aim for the exact set: every primary asset,
and nothing that is not one.

Work in the order given below. The map helps you find candidates and see each element's role quickly. The
RTL is always the final authority: when the map and the RTL seem to disagree, the RTL wins.

## Words used here

- **Element**: a declared name that has its own `PORT` or `SIGNAL` line in the map. It is a port, an
  internal signal, or a field of a record, written `record.field`. Only elements may be listed. Constants,
  generics, types, process variables, loop indexes, instance names, process labels and generate labels are
  never listed.
- **Conceptual asset**: a piece of information worth protecting, said in words. Examples: "the secret key",
  "the words held in the buffer", "the mode chosen by software", "the step the transfer is in", "the result
  sent out".
- **Structural asset**: an RTL element that holds or carries a conceptual asset: a register, a memory array,
  a wire, a port.
- **Primary asset**: an element that holds or carries the protected value itself. It is what an attacker
  targets directly.
- **Secondary asset**: an element that matters only because it acts on a primary asset. It enables it,
  selects it, addresses it, times it, resets it, passes it along, or keeps a copy of a value that another
  element already holds. Secondary assets are NOT listed.
- **Security objectives**: Confidentiality (the wrong party must not read the value), Integrity (the wrong
  party must not change it), Availability (nobody must be able to block it).

The rule behind every step below: **inside the module, list the element where a protected value is created
or kept; at the module's boundary, list the ports that a protected value crosses. Do not list the elements
in between that only re-hold, pass on, time, enable, select or address that value.** Being wired next to an
asset does not make an element primary.

## How to read the relation map

A program wrote the map from the RTL. It records facts about how values move and are controlled. It says
nothing about security or importance. Line numbers in the map refer to the numbers at the start of the RTL
lines in the same file.

Each element line (`PORT {...}` or `SIGNAL {...}`) gives these fields:

- `name`, `entity`: the element and the entity that declares it.
- `boundary` (ports only): `mode` (in, out, inout, buffer) and, for outputs, `drive`: `driven` (assigned
  from elements), `tied` (only ever given constants), `undriven` (never assigned as a whole; its fields may
  be).
- `kind` (signals only): `register` (assigned on a clock edge somewhere) or `signal`.
- `storage`: `edge` (every assignment is on a clock edge, so it holds its value), `none` (combinational),
  `mixed` (both), `not assigned` (never assigned in this module).
- `handling` (record fields): `ORIGINATES`, `CONSUMES` (this module reads it), `FORWARDS` (this module
  passes it on unchanged). See the note on `ORIGINATES` below.
- `constant_drivers`: places where the element gets a literal or a named constant.
- `configuration`: build options (generics, constants) under which the element exists or is driven.
- `connections`: the element is wired to a port of an instantiated sub-unit (`formal` is that port, `mode`
  its direction; `at` is an internal number, not a line).

The indented lines under an element are relationship records. Each names a type, the other elements
(`targets`), the RTL `lines`, and, for control types, the `guard` (the condition text; a long one is cut, so
read it at the cited lines). Every relationship is stored on both sides:

| on the element that acts | on the element acted upon | meaning, for a statement that assigns the acted-upon element |
|---|---|---|
| CARRIES | COPIES | the assigned value is exactly the other element, unchanged |
| SOURCES | DERIVES_FROM | the other element is read in the value in any other way: operand, function argument, array element, slice, the value arm of a conditional, or through a process variable |
| SEQUENCES | CLOCKED_BY | the other element is the clock |
| RESETS | RESET_BY | the other element is the reset that forces a constant |
| SELECTS | SELECTED_BY | the other element is the selector of a case or selected assignment, or a run-time index that picks which part of an array is read or written |
| GATES | GATED_BY | the other element decides whether the value is taken or forced: it is in an if / elsif / when-else condition, or it is a single-bit operand of a top-level and / or |

Notes:

- A record on an element that names the element itself means its new value uses its old value (a counter,
  a state register, a shift register).
- Other relationship types may appear (for example one meaning "compared inside a condition"). Read the
  cited lines and use what the RTL does there.
- The map can miss a statement. Whenever a decision depends on a map fact, read the cited RTL lines.
- **A record assigned as a whole.** When the RTL assigns a whole record signal inside the clock-edge branch
  of a process (for example `qx_r <= qx_r_nxt;`), every field of that record is a register, even when the
  map gives the field storage `none`. Judge those fields as registers.
- **`ORIGINATES`** only says that the field is assigned in this module, perhaps from an input through a
  condition or a selection. Whether the value is really made here is decided from the RTL (see created
  output and pass-through below).
- **Constant drivers do not make an element tied.** A state register is given state names, and a flag is
  given a low or a high constant, under different conditions. Those are constants, but the value changes at
  run time.
- **Build options.** A `drive` `tied`, or a constant driver, that holds only under one `configuration`
  condition does not make an element tied when another build option drives it from logic or from a sub-unit.
  Judge the element by the option that drives it.
- **Connections whose `mode` is null.** When the sub-unit's code is not in this file, the map cannot give
  the direction of its ports. Find it in the RTL: a signal that no statement of this file assigns is driven
  by an instance it is connected to; the port map and the way the signal is used elsewhere show which one. A
  port name that reads like an output is a hint, nothing more.

## Procedure

If the file is long, read it in parts until you have read all of it. Keep your notes as you go. Do not skip
the map lines of any entity.

### Step A. Understand the module

Read all the RTL first. In the `purpose` field, write in plain words: what the module does; who it talks to
(the host or bus side, external pins, sub-units it instantiates); what it stores; what it produces; what it
controls. If the file holds several entities, cover each one.

### Step B. Name the conceptual assets

Answer these four questions for this module, from its RTL:

- **Confidentiality**: is there information, received or made inside, that could be secret and that could
  leak? Think of keys, seeds, random values, private or stored data, memory contents, and values that reveal
  what the module is doing.
- **Integrity**: is there information that must change only through its intended path? Think of
  configuration and mode settings, protection and permission settings, lock settings, the state of a state
  machine, pointers and program counters, counters and timers whose count is the module's job, and results
  the rest of the system relies on.
- **Availability**: is there anything whose loss or blocking would stop the module or the system? Think of
  the main data path, the result output, and the timeout, reset, interrupt and error signals that this
  module raises.
- **Undermined behaviour**: are there privileged, debug or test modes, overrides or bypasses that change what
  the module does?

Write each conceptual asset in `conceptual_assets`. Name only what this RTL really implements. Do not judge
by names alone: a name is a hint, the statements decide.

### Step C. Give every element exactly one role

Go through every `PORT` and `SIGNAL` line of the map. Give each element exactly one role from the lists
below, spelled as written there. Do not join two roles with a slash and do not invent a role; you may add a
short note in brackets after the role name. The map facts point to a role; read the cited RTL lines to
confirm it. Write the result in `triage`.

How to choose when an element seems to fit two roles:

- Choose by what its value means. A value that only tells timing or permission to proceed (acknowledge,
  ready, busy, done, has-room, fill count) is a handshake or flow status, even when the module creates it
  and sends it out. A value that makes another part of the system act on an event (interrupt request,
  error, fault, timeout, reset request) is an event output, even when it is copied from an internal
  register.
- Width does not decide. A vector of request lines is still control; a one-bit serial data pin is still
  data.
- For a register, take the first role that fits, in this order: secret or table value, setting, operating
  state, sticky status, event register, data store, copy register, handshake or flow status, pacing counter.

**Roles that are never assets**

- **clock**: only SEQUENCES records. Clock-enable and tick inputs coming from a clock divider count as clock.
- **reset**: only RESETS records, sometimes also used in a condition.
- **tied**: an element that always gets one and the same constant, in every build option, so its value
  never changes at run time.
- **unused**: no relationship records, no constant drivers, no connections, storage `not assigned`. First
  look for its name in the RTL statements. If it is used there, the map missed it: judge it from the RTL.
- **whole record**: a record port or signal that has lines for its fields. Judge the fields, not the record.
  Exception: when no field of the record has a relationship record (this happens when the record is wired
  as a whole to a sub-unit), judge the record itself as one element, with the roles below, and give each of
  its fields the role "covered by the record".
- **covered by the record**: a field of a record that you judged as one element.

**Port roles that are primary**

- **data input**: an input whose value this module stores, computes with, or loads into a store: write
  data, data to process, operands, key or seed inputs, external receive pins, read data coming back from
  memory or from another unit. An input that is both forwarded and stored or computed with is a data input.
  An input that only goes into a sub-unit is judged by the kind of value it brings.
- **created output**: an output whose value this module makes: read from a store, computed, assembled, a
  read-back of registers, data driven on an external pin from an internal register, or a value driven
  straight from an output port of a sub-unit. If the value only comes unchanged from inputs of this module
  (copied, selected among inputs, merged with other inputs of the same kind, or re-registered), the output
  is a pass-through instead.
- **event output**: an output, raised by this module's own registers or logic, that tells the rest of the
  system that something happened and makes it act: interrupt request, error, fault, violation, exception,
  timeout, reset request, alarm. An error that is only routed from an input is a pass-through.
- **mode attribute input**: an input that holds the privilege or the mode of the current access or operation
  (privilege, debug mode, security or test mode) and that this module uses to allow, deny or change what it
  does. A request to enter a mode, sent as a pulse, is a control input. If the module only forwards the
  attribute, it is a pass-through.

**Internal roles that are primary**

- **sub-unit link**: an internal signal, or a field of one, driven by an output port of an instantiated
  sub-unit, that delivers a value of a primary kind: data, a computed result, a read-back, a setting or a
  privilege, a program counter value, an event. A link that delivers only an address, a handshake or a
  control takes that secondary role instead. A signal that only feeds an input of a sub-unit is not a link:
  judge it like any other combinational signal.
- **secret or table value**: a register or array that holds a key, a seed, a random or entropy value, or a
  word read from a constant table.
- **setting**: a register that holds a choice steering the module (enable, mode, select, permission, lock,
  bounds, rate, threshold, interrupt enable). It is loaded by a write of the host or by a command, it keeps
  its value across operations until it is replaced, and it GATES, SELECTS or SOURCES what the module does.
  It is often read back. A register captured at the start of each operation for that operation only is a
  copy register, even when it selects what the operation does.
- **operating state**: a register that steps by itself through values that are the module's progress: a
  state machine (its next state depends on its current state), a pointer or a program counter that
  advances, or a timer. A timer is a counter whose expiry raises an event, whose value software reads, or
  whose ticks are what this module delivers. A counter that only counts the bits, words, ticks or
  iterations of one transfer or computation is a pacing counter, not operating state. Shift registers are
  not operating state: see data store and copy register.
- **sticky status**: a register that records an error, overflow, violation or cause and keeps it until it is
  cleared, for software to read or to raise an event.
- **event register**: a register that this module sets from a condition it detects (a timeout, a mismatch,
  a violation, a failure, a reset request) and that drives an event output or a sticky status. A done or
  ready pulse is a handshake, not an event register.
- **data store**: an array that keeps data (a memory or a buffer written at an index); a register loaded by
  a write (a host write or a write enable) and kept until the next write; or a register whose value the
  module builds: a shift register that holds the word being sent or received, an accumulator, a working
  register that changes at each step of a computation, or a result register that holds what the module
  delivers.

**Roles that act on a value or copy it (secondary)**

- **control input**: an input that only decides whether, when or how something happens: enable, strobe,
  start, clear, read/write flag, byte select, operation select, instruction or command fields, an input used
  only in comparisons. To decide, follow CARRIES and SOURCES through internal combinational signals until
  you reach a register, an output, or a GATES / SELECTS use. An incoming request, interrupt, error or
  reset-request signal from another unit is a control input here: its home is the unit that raises it. A
  one-bit request attribute stays a control input even when it, or its inverse, is the value that a one-bit
  register takes.
- **address or index input**: an input used to choose which entry or which register is read or written, or
  the address that is checked.
- **handshake or flow status**: a signal, register or port that only says "now" or "may I": acknowledge,
  valid, ready, busy, done, pending, command pulses that clear themselves, has-room, has-items, fill count,
  and protocol timing outputs such as a link clock or a select line.
- **pacing counter**: a counter that only steps an internal transfer or computation: bit counter, word
  counter, baud or tick divider, wait counter, iteration counter. A timer (see operating state) is not a
  pacing counter.
- **copy register**: a register that only re-holds a value that another element already holds. It is one
  of these:
  - a capture of one element (COPIES, or a slice, sign or width change, or negation of it) taken at a step
    of an operation (a start, a response, a state of a state machine, every clock) and then held unchanged:
    an operand register, an address register, a request register, captured read data;
  - a synchronizer, delay, edge-detect or stretch chain: each stage holds an earlier value of the same
    signal, or a constant that is shifted in;
  - a register that re-registers another register: an output register, a duplicate with the same next
    value;
  - a register recomputed from other registers only to feed internal conditions: a registered decoded
    value or flag.

  Not copy registers: a register loaded by a write and kept (data store or setting), the first register
  that receives a word from a constant table (secret or table value), and an element that replaces a store
  under another build option (it is a store too).
- **pass-through**: an element whose value comes unchanged from inputs of this module and leaves on an
  output (copied, selected, merged with values of the same kind, or re-registered), with nothing stored or
  computed from it; a field with handling FORWARDS whose value goes through this way.
- **next-value**: a combinational signal (storage `none`) that CARRIES into a register and DERIVES_FROM that
  same register.
- **intermediate**: any other combinational signal computed and used inside the module: decoded controls,
  comparison results, partial results, renames, values that only feed an input of a sub-unit.

### Step D. Decide

- **List** (primary): data input, created output, event output, mode attribute input, sub-unit link, secret
  or table value, setting, operating state, sticky status, event register, data store.
- **Do not list** (secondary): control input, address or index input, handshake or flow status, pacing
  counter, copy register, pass-through, next-value, intermediate.
- **Never list**: clock, reset, tied, unused, a whole record whose fields you judged, covered by the record,
  and anything that is not an element.
- An internal combinational signal (storage `none`, and not a field of a record assigned as a whole on a
  clock edge) is listed only when it is a sub-unit link.
- A value that lives in a constant (a read-only table, a fixed identifier, a hard-coded key) cannot be
  listed itself. List the first register that receives it, as a secret or table value.

### Step E. Check the list

- **Direct-target test.** For each element you plan to list, finish this sentence: "This element holds or
  carries <conceptual asset>; an attacker who could read / change / block it would <harm>." The harm should
  fit a known attack: side-channel leakage, fault injection, leakage to a less trusted party, unauthorized
  access, privilege escalation, hardware Trojan, or denial of service. If the element holds no conceptual
  asset itself, and only decides when, whether or where something happens to one, it is secondary: drop it.
- **No copies inside the module.** For each internal register you plan to list, confirm that it is not a
  copy register by the definition in Step C. A shift register that sends or receives a word, a register that
  changes at each step of a computation, and a register loaded by a write and kept are not copy registers.
- **Coverage.** Every conceptual asset from Step B has its home elements in the list, or a triage note that
  says why no element holds it. Do not stop at the obvious secret: settings, state, pointers, read-back
  outputs, event registers and event outputs are assets too when the module has them.
- **Same role, same decision.** Elements that have the same role on parallel structures get the same
  decision: transmit and receive engines, each channel or lane, each register of a bank, each array of a
  split memory, and alternatives that hold the same value under different build options. List all of them
  or none, unless the RTL shows a real difference in role. This compares elements of the same role only:
  the wire that feeds an input of a sub-unit (intermediate) and the link that comes out of it (sub-unit
  link) are different roles.
- **Granularity.** List a record field, not its record, when the fields have their own records. Never list
  both a record and one of its fields. List an array by its name, with no index or slice: the whole array is
  the asset.
- **Names.** Copy `element` and `entity` from the same map line, with the same spelling and case. No
  hierarchical paths, no indexes, no slices, no invented names.
- **No duplicates.** Each element appears in the list as a single entry.

### Step F. Choose the objective and write the reason

For each listed element, pick the objective an attacker most likely goes after:

- **Confidentiality**: secrets, keys, seeds, random values, stored or passing data, memory contents, and
  read-back that exposes them.
- **Integrity**: settings, permissions, state, pointers, counters, sticky status, and results the system
  relies on.
- **Availability**: event registers, event outputs, and anything whose blocking stops the service.

The `reason` names the conceptual asset the element holds or carries, and the attack.

## A worked example (an invented module)

Entity `qx_seal` is a small encryption block. The host writes a key and a mode bit through a request
record. A start input loads the plaintext into an operand register. A state machine, kept in a control
record that the RTL updates as a whole on the clock edge, runs the operation. The result is kept and sent
out. A tamper pin passes through a synchronizer; when the tamper is seen, a fault register raises an alarm
output and sets a sticky flag that software reads back.

| element | map facts (shortened) | role | decision |
|---|---|---|---|
| `qx_ck` | SEQUENCES only | clock | not an asset |
| `qx_rn` | RESETS only | reset | not an asset |
| `qx_host` | record input; its fields have records | whole record | judge its fields |
| `qx_host.qx_wv` | CONSUMES; CARRIES `qx_keyq`; SOURCES `qx_cfgq.qx_enc` | data input | primary, Confidentiality |
| `qx_host.qx_wstb` | CONSUMES; GATES `qx_keyq`, `qx_cfgq.qx_enc` | control input | secondary |
| `qx_host.qx_adr` | CONSUMES; compared in the write condition | address or index input | secondary |
| `qx_host.qx_spare` | no records; name not used in the RTL | unused | not an asset |
| `qx_go` | in; GATES `qx_opq` and the next state | control input | secondary |
| `qx_plain` | in; CARRIES `qx_opq` | data input | primary, Confidentiality |
| `qx_tamp` | in; SOURCES `qx_tsyn` only | control input (an incoming event) | secondary |
| `qx_keyq` | register, edge; COPIES `qx_host.qx_wv`; GATED_BY `qx_host.qx_wstb` | secret or table value | primary, Confidentiality |
| `qx_cfgq` | record signal; its fields have records | whole record | judge its fields |
| `qx_cfgq.qx_enc` | edge; DERIVES_FROM `qx_host.qx_wv`; GATED_BY `qx_host.qx_wstb`; GATES `qx_mixw` | setting | primary, Integrity |
| `qx_opq` | edge; COPIES `qx_plain`; GATED_BY `qx_go`; no record names itself; read only by `qx_mixw` | copy register (operand register; `qx_plain` already holds the value) | secondary |
| `qx_ctl` | record signal; the RTL assigns `qx_ctl <= qx_ctl_nxt;` in the clock-edge branch | whole record | judge its fields |
| `qx_ctl.qx_st` | map storage `none`, but the whole record is clocked, so it is a register; its constant drivers are state names; COPIES `qx_ctl_nxt.qx_st`, which DERIVES_FROM it; SELECTS `qx_resq` | operating state | primary, Integrity |
| `qx_ctl_nxt.qx_st` | none; CARRIES `qx_ctl.qx_st`; DERIVES_FROM `qx_ctl.qx_st` | next-value | secondary |
| `qx_mixw` | none; DERIVES_FROM `qx_keyq`, `qx_opq` | intermediate | secondary |
| `qx_resq` | edge; DERIVES_FROM `qx_mixw`; SELECTED_BY `qx_ctl.qx_st`; CARRIES `qx_ciph` | data store (result register) | primary, Confidentiality |
| `qx_ciph` | out, driven; COPIES `qx_resq` | created output | primary, Confidentiality |
| `qx_tsyn` | edge; a record names itself; each stage holds an earlier value of `qx_tamp` | copy register (synchronizer) | secondary |
| `qx_faultq` | edge; set when `qx_tsyn` shows the tamper; CARRIES `qx_alarm`; GATES `qx_seenq` | event register | primary, Availability |
| `qx_alarm` | out, driven; COPIES `qx_faultq` | event output | primary, Availability |
| `qx_seenq` | edge; set by `qx_faultq`, cleared only by a host write; read back | sticky status | primary, Integrity |
| `qx_doneq` | edge; GATED_BY `qx_ctl.qx_st`; CARRIES `qx_rsp.qx_okay` | handshake or flow status | secondary |
| `qx_rsp` | record output; its fields have records | whole record | judge its fields |
| `qx_rsp.qx_okay` | out; COPIES `qx_doneq` | handshake or flow status | secondary |
| `qx_rsp.qx_back` | out, ORIGINATES; DERIVES_FROM `qx_cfgq.qx_enc`, `qx_seenq` | created output (read-back) | primary, Integrity |
| `qx_rsp.qx_bad` | out, drive tied | tied | not an asset |

One entry of the resulting list:

```json
{"element": "qx_keyq", "entity": "qx_seal", "security_objective": "Confidentiality",
 "reason": "Holds the secret key written by the host; reading it through a leak or side channel exposes every message."}
```

## Output

Write the JSON object below to the output file. Put `module` first and `assets` last. The keys in
between are your analysis; only `assets` is compared with the expert list.

```json
{"module": "<module name from the MODULE line of the input file>",
 "purpose": "<Step A, plain words>",
 "conceptual_assets": [
   {"asset": "<conceptual asset in words>", "objective": "Confidentiality | Integrity | Availability",
    "home": "<the element names that hold or carry it, or why none is an element>"}
 ],
 "triage": [
   "<entity> | <element> | <role> | primary / secondary / not an asset"
 ],
 "assets": [
   {"element": "<a declared element name, exactly as declared: a port, a signal, or <record>.<field>>",
    "entity": "<the entity that declares it>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<one or two sentences>"}
 ]}
```

- In `triage`, cover every element of the map. You may group elements that share entity, role and decision
  in one line, for example the unused fields of one record.
- In `assets`, `security_objective` is the word `Confidentiality`, `Integrity` or `Availability`, nothing
  else.
- If no element passes the procedure, write `"assets": []`.

## Final checklist

- I read all of the RTL and all of the map.
- Every element of the map has exactly one role in `triage`, spelled as in the lists.
- Every listed element is a data input, created output, event output, mode attribute input, sub-unit link,
  secret or table value, setting, operating state, sticky status, event register, or data store, and it
  passed the direct-target test.
- No clock, reset, tied, unused, control, address, handshake, pacing, copy, pass-through, next-value or
  intermediate element is listed.
- No listed internal register only re-holds a value that another element already holds.
- Elements with the same role on parallel structures have the same decision.
- Every conceptual asset has its home in the list, or a note saying why not.
- Every `element` and `entity` is copied exactly from one map line; no record is listed together with its
  fields; there are no duplicate entries.
