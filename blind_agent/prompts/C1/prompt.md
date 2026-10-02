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
  selects it, addresses it, times it, resets it, passes it along, or keeps a short-lived copy of it.
  Secondary assets are NOT listed.
- **Security objectives**: Confidentiality (the wrong party must not read the value), Integrity (the wrong
  party must not change it), Availability (nobody must be able to block it).

Being wired next to an asset does not make an element primary. Acting on an asset makes an element
secondary, never primary.

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
- `handling` (record fields): `ORIGINATES` (this module creates the value), `CONSUMES` (this module reads
  it), `FORWARDS` (this module passes it on unchanged).
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
  a state register).
- Other relationship types may appear (for example one meaning "compared inside a condition"). Read the
  cited lines and use what the RTL does there.
- The map can miss a statement. Whenever a decision depends on a map fact, read the cited RTL lines.

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
  machine, pointers and addresses, counters and timers whose count is the module's job, and results the rest
  of the system relies on.
- **Availability**: is there anything whose loss or blocking would stop the module or the system? Think of
  the main data path, the result output, timeout and reset requests, interrupt and error signals.
- **Undermined behaviour**: are there privileged, debug or test modes, overrides or bypasses that change what
  the module does?

Write each conceptual asset in `conceptual_assets`. Name only what this RTL really implements. Do not judge
by names alone: a name is a hint, the statements decide.

### Step C. Give every element a role

Go through every `PORT` and `SIGNAL` line of the map. Give each element a role from the lists below. The
map facts point to a role; read the cited RTL lines to confirm it. Write the result in `triage`.

When an element seems to fit two roles, choose by what its value means. A value that only tells timing or
permission to proceed (acknowledge, ready, busy, done, has-room, fill count) is a handshake or flow status,
even when the module creates it and sends it out. A value that makes another part of the system act on an
event (interrupt request, error, fault, timeout) is an event output, even when it is copied from an internal
flag.

**Roles that are never assets**

- **clock**: only SEQUENCES records. Clock-enable and tick inputs coming from a clock divider count as clock.
- **reset**: only RESETS records, sometimes also used in a condition.
- **tied**: an output with `drive` `tied`, or an element that only ever gets constants.
- **unused**: no relationship records, no constant drivers, storage `not assigned`. First look for its name
  in the RTL statements. If it is used there, the map missed it: judge it from the RTL.
- **whole record**: a record port or signal whose fields have their own lines with records. Judge the
  fields, not the record. Judge the record itself only if none of its fields has records.

**Roles that hold or carry a value (candidates for primary)**

- **data store**: a register or array (storage `edge` or `mixed`) loaded from a data input (COPIES or
  DERIVES_FROM), often GATED_BY a write enable and SELECTED_BY an index. It later feeds an output.
- **secret or generated value**: a register that holds a key, a seed, a random value, or the word read from
  a constant table.
- **setting**: a register loaded from the host's write data, GATED_BY a write strobe or an address
  comparison, which then GATES, SELECTS or SOURCES what the module does; it is often read back. Examples:
  enable, mode, privilege, permission, lock, bounds, rate, threshold.
- **operating state**: a register whose new value uses its own old value, either directly (a record on it
  names itself) or through a next-value signal (it COPIES a signal that DERIVES_FROM it). State machines
  (they SELECT), pointers, address registers, program counters, and counters or timers whose count is the
  module's job.
- **sticky status**: a register that keeps an error, overflow, violation or tamper indication until it is
  cleared, for software to read or to raise an event.
- **data input**: an input whose value is carried (CARRIES, SOURCES) into a stored or computed value: write
  data, data to process, key or seed inputs, configuration value inputs, external receive pins. Usually
  several bits wide.
- **created output**: an output (`drive` `driven`, or a field with handling ORIGINATES) whose value is made
  in this module: read from a store, computed, sent out on an external pin, or a read-back selection of
  registers.
- **event output**: an output that tells the rest of the system that something happened and makes it act:
  interrupt request, error, fault, violation, exception, timeout, reset request, alarm.
- **mode attribute input**: an input carrying a privilege, security-mode, debug-mode or test-mode indication
  that the module uses to allow, deny or change what it does.
- **sub-unit link**: an internal signal with a `connections` entry to an output port of an instantiated
  sub-unit, delivering a value or an event of the kinds above.

**Roles that act on a value (secondary)**

- **control input**: an input whose records are only GATES, SELECTS or comparisons, or that reaches only
  such uses through internal renames. Enable, strobe, start, clear, read, write, byte select. Usually a
  single bit. To decide, follow CARRIES and SOURCES through internal combinational signals until you reach a
  register, an output, or a GATES / SELECTS use.
- **address or index input**: an input used to choose which entry or which register is read or written.
- **handshake or flow status**: a signal, register or port that only says "now" or "may I": acknowledge,
  valid, ready, busy, done, strobe, read/write flag, has-room, has-items, fill count, and protocol timing
  outputs such as a link clock or a select line.
- **pacing counter**: a counter that only paces an internal transfer: bit counter, tick divider, wait
  counter. A counter whose count is the module's job is operating state instead.
- **timing copy**: a register that only re-registers another element: a synchronizer stage, a delay stage,
  an edge-detect stage, or a duplicate that takes the same next value as another register.
- **pipeline stage**: a register that only moves a value from one stage to the next.
- **pass-through**: an element that COPIES one element and CARRIES it on unchanged, or a field with handling
  FORWARDS.
- **next-value**: a combinational signal (storage `none`) that CARRIES into a register and DERIVES_FROM that
  same register.
- **intermediate**: any other combinational signal computed and used inside the module: decoded controls,
  comparison results, partial results, renames.

### Step D. Decide

Apply these rules in order. The first rule that fits decides.

- **D-a. Never list**: clock, reset, tied, unused, whole record whose fields you judged, and anything that
  is not an element.
- **D-b. Ports** (whatever their storage). List: data input, created output, event output, mode attribute
  input. Do not list: control input, address or index input, handshake or flow status, pass-through,
  clock-enable or tick input.
- **D-c. Sub-unit links**: list them.
- **D-d. Internal registers and arrays** (storage `edge` or `mixed`). List: data store, secret or generated
  value, setting, operating state, sticky status. Do not list: handshake or flow status, pacing counter,
  timing copy, pipeline stage.
- **D-e. Internal combinational signals** (storage `none`) that are not sub-unit links: do not list them.
- **D-f. Values that live in constants**. A constant cannot be listed. If a conceptual asset lives in a
  constant (a read-only table, a fixed identifier, a hard-coded key), list the first element that receives
  its value instead, for example the register that holds the word read from the table.

### Step E. Check the list

- **Direct-target test.** For each element you plan to list, finish this sentence: "This element holds or
  carries <conceptual asset>; an attacker who could read / change / block it would <harm>." The harm should
  fit a known attack: side-channel leakage, fault injection, leakage to a less trusted party, unauthorized
  access, privilege escalation, hardware Trojan, or denial of service. If the element holds no conceptual
  asset itself, and only decides when, whether or where something happens to one, it is secondary: drop it.
- **Coverage.** Every conceptual asset from Step B has its home elements in the list, or a triage note that
  says why no element holds it. Do not stop at the obvious secret: settings, state, pointers, read-back
  outputs and event outputs are assets too when the module has them.
- **Same role, same decision.** Elements that play the same role on parallel structures get the same
  decision: the write side and the read side, transmit and receive, each channel or lane, each register of a
  bank, and alternatives that hold the same value under different build options. List all of them or none,
  unless the RTL shows a real difference in role.
- **Granularity.** List a record field, not its record, when the fields have their own lines. Never list
  both a record and its fields. List an array by its name, with no index or slice: the whole array is the
  asset.
- **Names.** Copy `element` and `entity` from the same map line, with the same spelling and case. No
  hierarchical paths, no indexes, no slices, no invented names.
- **No duplicates.** Each element appears in the list as a single entry.

### Step F. Choose the objective and write the reason

For each listed element, pick the objective an attacker most likely goes after:

- **Confidentiality**: secrets, keys, seeds, random values, stored or passing data, memory contents, and
  read-back that exposes them.
- **Integrity**: settings, permissions, state, pointers, addresses, counters, and results the system relies
  on.
- **Availability**: event outputs, and anything whose blocking stops the service.

The `reason` names the conceptual asset the element holds or carries, and the attack.

## A worked example (an invented module)

Entity `qx_seal` is a small encryption block. The host writes a key and a mode bit through a request
record. Plaintext arrives on a port. A state machine runs the operation. The result is stored and sent out.
The host can read back the mode and the state. An event output tells the processor that a result is ready.

| element | map facts (shortened) | role | decision |
|---|---|---|---|
| `qx_ck` | SEQUENCES only | clock | not an asset |
| `qx_rn` | RESETS only | reset | not an asset |
| `qx_host` | record input, no records of its own | whole record | judge its fields |
| `qx_host.qx_wv` | CONSUMES; CARRIES `qx_keyq`; SOURCES `qx_cfgq.qx_enc` | data input | primary, Confidentiality |
| `qx_host.qx_wstb` | CONSUMES; GATES `qx_keyq`, `qx_cfgq.qx_enc` | control input | secondary |
| `qx_host.qx_adr` | CONSUMES; compared in the write condition | address input | secondary |
| `qx_host.qx_spare` | no records; name not used in the RTL | unused | not an asset |
| `qx_plain` | in; SOURCES `qx_mixw` | data input | primary, Confidentiality |
| `qx_keyq` | register, edge; COPIES `qx_host.qx_wv`; GATED_BY `qx_host.qx_wstb` | secret | primary, Confidentiality |
| `qx_cfgq` | record signal; its fields have their own records | whole record | judge its fields |
| `qx_cfgq.qx_enc` | edge; DERIVES_FROM `qx_host.qx_wv`; GATES `qx_mixw` | setting | primary, Integrity |
| `qx_stq` | edge; a record on it names itself; SELECTS `qx_resq` | operating state | primary, Integrity |
| `qx_mixw` | none; DERIVES_FROM `qx_keyq`, `qx_plain` | intermediate | secondary |
| `qx_resq` | edge; DERIVES_FROM `qx_mixw`; SELECTED_BY `qx_stq` | data store | primary, Confidentiality |
| `qx_ciph` | out, driven; COPIES `qx_resq` | created output | primary, Confidentiality |
| `qx_doneq` | edge; GATED_BY `qx_stq`; CARRIES `qx_rsp.qx_okay`, `qx_evt` | handshake | secondary |
| `qx_rsp.qx_back` | out, ORIGINATES; DERIVES_FROM `qx_cfgq.qx_enc`, `qx_stq` | created output (read-back) | primary, Integrity |
| `qx_rsp.qx_okay` | out; COPIES `qx_doneq` | handshake | secondary |
| `qx_rsp.qx_bad` | out, drive tied | tied | not an asset |
| `qx_evt` | out, driven; COPIES `qx_doneq` | event output | primary, Availability |

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
- Every element of the map has a role in `triage`.
- Every listed element is a data input, created output, event output, mode attribute input, sub-unit link,
  data store, secret or generated value, setting, operating state, or sticky status, and it passed the
  direct-target test.
- No clock, reset, tied, unused, control, address, handshake, pass-through, pacing, timing-copy, pipeline,
  next-value or intermediate element is listed.
- Elements with the same role on parallel structures have the same decision.
- Every conceptual asset has its home in the list, or a note saying why not.
- Every `element` and `entity` is copied exactly from one map line; no record is listed together with its
  fields; there are no duplicate entries.
