# Primary security assets of one hardware module

## Your task

You are a hardware-security engineer. You have one input file: the RTL (VHDL) of one hardware module, followed by a relation map that a static analyser wrote from that RTL. List the module's **primary security assets**: the declared elements that an attacker would target directly. Write the result as a single JSON object (format at the end).

Judge every element by what the RTL does with it. Never decide from how a name sounds: a name can hint at a role, but only the RTL shows the role.

This task usually goes wrong in these ways:

- Listing too much: everything near a protected value gets listed, including the clocks, strobes, addresses, wires and buffers that only move it.
- Listing too little: stopping at the obvious register, or listing nothing because the module only wires other units together.
- Inconsistency: two elements with the same role get different decisions, inside one module or across modules.
- Wrong names: an element written differently from its declaration.

The rules and examples below are built to prevent each of these.

## Words used here

- **Conceptual asset**: information or behaviour of the module that needs Confidentiality, Integrity or Availability. For example: a secret key, a random seed, a user's private payload, stored program code, a privilege or access-permission setting, a watchdog expiry that must fire, a result that other units depend on.
- **Structural asset**: a declared element (port, signal, or record field) that physically holds or carries a conceptual asset.
- **Primary asset**: a structural asset that is itself the attacker's target. These are what you list.
- **Secondary element**: an element that helps move, stage, time, select, switch or guard a primary asset. Attacking it is a way to reach a primary asset. It is not listed.
- **Attack point**: an input or output through which an attacker acts on, or observes, an asset. It is not listed; the asset behind it is.
- **Child unit**: an entity that another entity instantiates. Its RTL may be in the file (an inner entity) or absent (you see only the instance and its port connections).
- **Outer entity**: an entity in the file that no other entity in the file instantiates. Its ports are the boundary of the module.

The roles below are used in every rule and example:

- **Home**: a register or memory array where the module keeps a protected value. The kinds are listed under [Home].
- **Door**: a port of an outer entity whose job is to carry a protected value or event in or out.
- **Status**: a register or output that reports the outcome or health of the protected function.
- **Only holder**: the element that holds a protected value in this module when that value has no home and no door here.
- **Hallway**: an element that holds or moves a copy of a protected value on its way: a wire, a helper signal, a synchronizer or pipeline copy, a register that holds the value only while one transfer or one computation passes through, a port of a child unit.
- **Handle**: an element that decides when, where or whether a value moves: clock, reset, request input, enabling bit, strobe, address, pointer, index, selector, override, guarding bit, sequencer.

You list homes, doors, status and only holders. You never list hallways or handles.

## Method

**Step A. Understand the module.** Read all of the RTL. Write down briefly what enters it, what it keeps, what it computes, what leaves it. If the file holds several entities, find which entity instantiates which (the RTL instantiations and the map's `connections` show this), which entities are outer entities, and which child units have no RTL in the file.

**Step B. Find the conceptual assets.** Ask these questions about the module's normal use:

- *Confidentiality*: is there information, received or produced here, that could be secret? (keys, seeds, random values, private payloads, values that reveal what a program is doing)
- *Integrity*: is there stored information or a setting that the wrong party must not change, or that must not change at the wrong time? (stored code or constant tables, privilege and permission settings, protected counters, ownership of shared resources, results). An update made by the intended path at the intended time is normal behaviour, not an integrity threat.
- *Availability*: is there something whose loss or blocking would stop the module or the system? (watchdog expiry, interrupt, stop or reset requests, results that other units wait for)
- *Undermined behaviour*: is there an override, a path that skips a check, or a test or debugger path that can make the module behave wrongly? If so, the asset is what the path overrides; the path itself is a handle.

A value for which every answer is "no" is not an asset. A payload that the module only routes between units outside it (an interconnect passing other units' traffic) belongs to those units, not to this module.

**Step C. Map each conceptual asset to elements, in this order.** First its homes. Then its doors. Only if it has neither in this module, its only holder. Give an explicit decision to every register (`"kind":"register"`) in every entity and to every port of each outer entity. Do not stop at the first good candidate.

**Step D. Remove secondary elements and attack points** with the Do-not-list rules. An element is listed only if a List rule names its role.

**Step E. Attack check.** For each element still on your list, name a concrete attack whose target is that element itself: side-channel leakage, injected faults, leakage from a secure to a non-secure party, unauthorized access, privilege escalation, a hidden hardware Trojan, or denial of service. If the only honest description is "the attacker uses this element to reach another element", remove it: it is a handle or a hallway.

**Step F. Consistency and names** (section below). Then write the JSON.

## List rules

**[Home]** A register or memory array that keeps a protected value. The kinds are:

- a key or seed register; the register that holds the running value of a random generator (the shift-register contents of a pseudo-random generator, or the register that assembles the output word of a true random generator);
- the entropy source of a true random generator: the self-oscillating element that produces the raw random bits, or the register that first samples it. It is an asset even when no port reaches it;
- a memory array whose content the module exists to store: program code, user payload, a key store. In a cache this includes the stored words and the tag and validity arrays that record which addresses are cached;
- a counter whose value decides a security event (the count that makes a watchdog expire), and the register that raises the expiry, reset, violation or interrupt event that the module exists to produce;
- a register that holds a security policy or protected bookkeeping that the module exists to hold or enforce: privilege mode, access-permission entries and region bounds, secure versus non-secure selection, debugger authorization, which party currently owns a shared resource, whether an atomic reservation is still intact;
- the register that first captures a value read out of a constant table or ROM image (constants are not elements, so this register is the table's home).

A register that is reloaded at the beginning of every transfer or computation and hands its value on at the end is not a home, even when it holds a payload or a result: it is a [Hallway]. When such a register is the only element that holds the value in this module, use [Only holder].

**[Door]** A port of an outer entity whose job is to carry a protected value or event:

- a key or seed input; an input that carries a private payload or the operands of a computation;
- the module's result output;
- the payload lines of a communication interface: the serial or parallel lines that carry the transferred words in and out (not its clock, select or flow-control lines);
- the write-in and read-out payload of a module whose whole content is the protected payload: a memory, a cache, a queue, or a key store reached through its own access port;
- an interrupt, expiry, stop or reset request **output**.

When the door is a field of a record port, the door is that field.

**[Status]** A register or output that reports the outcome or health of the protected function to software or to other units: error codes, access-violation flags, overrun flags, a record of what caused the last reset, the outcome of a security operation. The error field of a bus response is status only when this module raises it from its own protection check (an expiry monitor, a permission check). An error copied or merged from another unit's response is a hallway.

**[Only holder]** If a conceptual asset of this module has no home and no door in this module, list the element that holds it whole here.

- First choice: the register where the value is formed or first received in this module. Examples: the result register of a computation whose result leaves only through a shared bus; a register that assembles a command or a response from a serial line.
- Otherwise, when no register in this file holds the value because it is kept in a child unit whose RTL is not in the file: the internal signal or record field that carries it out of that child unit.

Never pick a field of a shared interface, a mix of several different values (an OR or a concatenation of several sources), or a value computed from it (an address, a comparison result). Pick the element where the value enters or is formed, not every copy after it.

## Do-not-list rules

**[Handle]** Clock and reset inputs. Interrupt, stop, wake-up and reset request **inputs**: they tell this module when to act; the request is listed in the module that raises it. Enables, strobes, read/write selects, addresses, indices, pointers, `case` selectors. The clock, select and flow-control lines of a communication interface. Override, test and debugger inputs. Guarding bits (a locking bit, an enabling bit) that protect or switch another asset. Registers that only sequence work: step counters, phase registers, sequencer registers, delayed strobes. List the asset they act on instead.

**[Hallway]** Combinational wires between a home and a door. Next-value helpers whose only use is to feed a register (decide on the register instead). Synchronizer stages, delayed copies and pipeline copies. Registers that hold a value only while one transfer or one computation passes through, when that value has a home or a door in this module: shift registers of a communication interface, operand registers, result and output registers, input and output buffers, round registers of a cipher. Mixing and debiasing logic between an entropy source and the register that holds a random generator's output. Ports of a child unit that receive or return a value already listed.

**[Shared interface]** Ports and record fields of a general bus or register interface that carry every access to a set of registers, whether this module is the target of the accesses (a peripheral's register port) or issues them (the request port of a core, a bridge or a debugger link): address, write value, read value, byte enables, access tags such as privilege or source tags, request strobes, acknowledge, handshake flags, and occupancy flags that pace transfers. The read-back value of control registers, and the merge of such read-back values from several units, belongs here too. They are attack points or flow control: judge the registers behind them instead. Exceptions: the memory, cache, queue and key-store case under [Door], and an error field under [Status].

**[Inert]** An output tied to constants. An input that is never read in the module. A whole record when the asset sits in some of its fields (list the field). Constants, generics, loop parameters and process variables are not elements at all.

**[Ordinary setting]** Configuration that only tunes how the function runs: speed, size, format, the operating mode of a cipher core, run/stop and enabling bits, interrupt enabling bits, a public parameter such as an initialization vector, and the period, threshold or reload value of a timer or watchdog, even when a locking bit freezes it. It steers the asset; it is not the target. A setting is listed only when the setting is itself the security policy ([Home]).

**[Test port]** A port that exists to observe or drive internals for testing or debugging, including every line of a debugger access port. It is an attack point: list what it exposes, not the port. It is never a door.

## Worked examples from other designs

These designs come from published asset-identification case studies. Names in code font are those designs' own names; you will not see them in your input. Learn the reasons, not the names. Each table shows the decision for the elements an engineer would consider, including the ones that are left out.

### Watchdog timer

A countdown timer. Software writes a reload value and a control register (run, pause, and a locking bit that freezes the control and reload registers) through a small register interface: read strobe, write strobe, address, write value, read value. When the count reaches zero, an internal register raises the expiry, and an output carries it to the chip as a reset. A set of debugger inputs can override the clock, the run, pause and service controls, the reload value and the expiry.

| Element | Decision | Why |
|---|---|---|
| `wd_timer`, register holding the current count | List [Home], Integrity | The value the attacker wants to change: stretch the count to prevent the reset, or cut it to force one. |
| `wd_assert_timeout`, register that raises the expiry | List [Home], Integrity | Forcing or suppressing it fakes or blocks the system reset. |
| `o_wd_reset`, output carrying the expiry to the chip | List [Door], Availability | It exists only to carry the protected event out; holding it inactive denies recovery. |
| Clock input, reset input | Not: [Handle] | They pace and zero everything in the module; they are attack points, not this module's assets. |
| Read strobe, write strobe, address, write value, read value | Not: [Shared interface] | They carry every register access. An attack goes through them; they are not the target. |
| Control register with run, pause and the locking bit | Not: [Ordinary setting], [Handle] | The run and pause bits steer the counter and the locking bit guards it. The counter is listed. |
| Reload-value registers written by software and frozen by the locking bit | Not: [Ordinary setting] | They set the period. The source defines no asset for them: the counter they load is the target. |
| Reload value passed from the control block to the counter block | Not: [Hallway] | It only feeds the counter, which is listed. |
| Debugger inputs (enabling, clock, reload value, expiry, run, pause, service) | Not: [Handle] | Override paths: the means of attack on the listed registers. |
| Internal wires that choose between normal and debugger controls | Not: [Hallway], [Handle] | They only route control and clock. |

How this looks in a relation map: `wd_timer` would be a `SIGNAL` with `"kind":"register"` and `"storage":"edge"`. It is `SELECTED_BY` the run, service and pause wires (they form the `case` selector), `DERIVES_FROM` itself (it counts down), `COPIES` the reload wire, and it `GATES` `wd_assert_timeout` (the comparison with zero). The run, service and pause wires appear mostly with `SELECTS` and `GATES` records. So: the register is a home, those wires are handles, and the reload wire is a hallway.

### AES encryption block

Key, initialization vector and plaintext enter through their own inputs. A key register holds the key. Input and output buffers stage the payload. A cipher core runs rounds, partly in child units. Configuration registers set mode, key size and run. Status registers report error codes, progress and completion. A debugger port can take control of the cipher core and swaps in hardcoded test key values.

| Element | Decision | Why |
|---|---|---|
| Key input port | List [Door], Confidentiality | The secret enters here. |
| Key register | List [Home], Confidentiality | The secret is kept here: the attacker's direct target. |
| Plaintext input port | List [Door], Confidentiality | The user's private payload enters here. |
| Result output port | List [Door], Availability | The final product other units wait for; blocking or corrupting it breaks the service. |
| Status registers (error codes, completion) | List [Status], Integrity | They report the outcome and can reveal the cipher core's internal condition. |
| Configuration registers (mode, key size, run) | Not: [Ordinary setting] | They steer the cipher core; the key and the payload are the targets. |
| Initialization-vector register | Not: [Ordinary setting] | A public parameter that steers the cipher. |
| Input buffer, output buffer | Not: [Hallway] | They hold one block only while it passes between a door and the cipher core. |
| Round registers of the cipher core, round-key copies, round values inside child units | Not: [Hallway] | They hold intermediate values of the block being processed. The key's home and the payload doors are listed. |
| Hardcoded debugger key values | Not: [Inert] | Constants, not elements. |
| Debugger port, clock | Not: [Test port], [Handle] | Attack point; timing. |

### SRAM controller

A memory array. An address register and a delayed copy of it. A write-in register and an output register sit between the array and a bidirectional payload port. Chip, write, byte-write and output strobes, and a sleep input. A mode input switches the array to a built-in self-test that overwrites its content.

| Element | Decision | Why |
|---|---|---|
| Memory array | List [Home], Confidentiality | The stored content may be secret, and some ranges must stay unchanged. |
| Bidirectional payload port | List [Door], Confidentiality | The memory's content enters and leaves only through it (memory case of [Door]). |
| Write-in register, output register | Not: [Hallway] | They hold one word only while it passes between the door and the array, which are both listed. |
| Address register and its delayed copy | Not: [Handle] | They decide which word is reached. |
| Chip, write, byte-write and output strobes | Not: [Handle] | Strobes. |
| Sleep input | Not: [Handle] | A denial-of-service lever on the array; the array is listed. |
| Self-test mode input | Not: [Handle] | An override that overwrites the array; the array is listed. |
| Control-logic sequencer, self-test pattern generator | Not: [Handle], [Hallway] | Sequencing and test infrastructure. |

### Gaussian noise generator

Seed inputs load shift-register generators. Their outputs are combined. Leading-zero, mask and swizzle logic compute an address into a coefficient ROM. The ROM output is registered, and the noise value leaves through an output. Added for testing: an input that overrides the ROM address, and an output that exposes the combined random stream.

| Element | Decision | Why |
|---|---|---|
| Seed inputs | List [Door], Confidentiality | Whoever knows the seeds predicts every output. |
| Shift-register contents of the generators | List [Home], Confidentiality | The running value of the generator. |
| Register that holds the coefficient read from the ROM | List [Home], Integrity | The ROM table is a constant; this register is the first element that holds a coefficient. A wrong coefficient spoils the noise. |
| Noise output | List [Door], Integrity | The product that other units consume. |
| Combined random value wire; leading-zero, mask and swizzle logic | Not: [Hallway] | Computed from the listed generator registers on the way to the output. |
| Address into the coefficient ROM | Not: [Handle] | It selects which coefficient is read; the coefficient register is listed. |
| Address-override input | Not: [Handle] | An override path; its target, the coefficient register, is listed. |
| Test output exposing the random stream | Not: [Test port] | An observation point; what it exposes, the generator registers, is listed. |
| Clock, reset | Not: [Handle] | Timing and initialization. |

### True random generator with a hidden entropy source

The entropy source of a random number generator sits inside the block, and no port reaches it. Its raw bits are combined and debiased, then assembled into an output word that is handed on.

| Element | Decision | Why |
|---|---|---|
| Entropy source (the self-oscillating element that makes the raw bits, or the register that first samples it) | List [Home], Integrity | The source names it an asset although no port reaches it: biasing or freezing it makes every random value predictable. |
| Register that assembles the random output word | List [Home], Confidentiality | It holds the random value that software will use as a key or nonce. |
| Combining and debiasing logic between them | Not: [Hallway] | It only moves the raw bits towards the output register. |
| Enabling input, bit counter of the output word | Not: [Handle] | They decide when bits are taken. |

### Processor core, caches and a shared bus

The program counter must stay hidden from a debugger while a user program runs normally. A core has a general-purpose register file, a privilege mode, and instruction and value caches. Separately, masters and slaves share a bus, and a crypto unit keeps a key.

| Element | Decision | Why |
|---|---|---|
| Program counter register | List [Home], Confidentiality | It reveals the flow of the user's program. |
| Execution-phase and instruction-phase registers, decoded-instruction registers | Not: [Hallway], [Handle] | They carry information about, or steer, the program counter: secondary. |
| Debugger access port | Not: [Test port] | An untrusted observation point. |
| Debugger enabling signal | Not: [Handle] | A precondition for the attack, not its target. |
| General-purpose register file | List [Home], Confidentiality | Shared by every program that runs on the core. |
| Register holding the privilege mode | List [Home], Integrity | It is the security policy the core enforces. |
| Cache contents, tag and validity arrays, replacement bookkeeping | List [Home], Confidentiality | A cache is shared; what it holds and which addresses it holds leak through side channels. |
| Interrupt and debugger stop request inputs | Not: [Handle] | They tell the core when to trap. |
| Instruction-bus and value-bus record fields | Not: [Shared interface] | They carry every access. |
| The sensitive payload a bus master sends | List, at its home or door in the master | It is the target. |
| Bus wires, arbitration logic, address decoder | Not: [Hallway], [Handle] | Infrastructure that moves the payload. |
| Key register inside the crypto unit | List [Home], Confidentiality | The secret itself. |
| Boot versus normal execution phase that restricts access to the key | Not: [Handle] | It guards the key; the key is listed. |

### Core top entity that only wires child units together

This applies the rows above to a file that holds only the top entity of a core. The top entity declares no registers. It instantiates a fetch unit, a control unit, a register file, an arithmetic unit, a load/store unit and a memory-protection unit, and none of their RTL is in the file. Internal signals and record fields connect them.

| Element | Decision | Why |
|---|---|---|
| Signals that carry the register-file read values to the other child units | List [Only holder], Confidentiality | The register file is a home, but it is not in this file; these signals are where its values enter this module. |
| Record field that carries the current program counter out of the control unit | List [Only holder], Confidentiality | Same reason, for the program counter. |
| Record field that carries the current privilege mode out of the control unit | List [Only holder], Integrity | Same reason, for the privilege policy. |
| Wire that carries the access-violation flag out of the memory-protection unit | List [Only holder], Integrity | Status of the protection check, raised in a child unit that is not in the file. |
| The write-back value (an OR of several child-unit results), and the arithmetic and load results that feed it | Not: [Hallway] | They flow into the register file, whose values are listed where they leave it. |
| Decoded control fields (operation selects, write strobes, register indices) and the computed access address | Not: [Handle] | They decide what happens and where. |
| Control-register read-back values merged from the child units | Not: [Shared interface] | They carry every control-register read. |
| Bus record fields; interrupt and stop request inputs; clock and reset | Not: [Shared interface], [Handle] | As in the core example above. |

### What the examples share

- Every listed element is something the attacker wants. The handles and hallways around it are left out, even though an attack passes through them.
- A protected value is listed at its homes and doors. The hallways between them are not.
- A register that holds a payload or a result only while it passes through is a hallway when the value has a door or a home. It is listed only when it is the value's only holder in the module.
- Inputs that steer (enables, addresses, selectors, overrides, clocks, resets, request inputs) are never listed. What they steer is.
- A setting is listed only when the setting is itself the policy being protected.

## Reading the relation map for these roles

The map records facts, not judgements. Use it to find roles quickly, then confirm each decision at the RTL lines it cites; the map can miss statements.

- **Home candidates**: `SIGNAL` lines with `"kind":"register"` and `"storage":"edge"`. Then read the RTL to tell a kept value from a transient one. A kept value changes only through a deliberate write (its assignment is guarded by a write strobe, an address decode or a fill), through its own counting, or through reset, and it is read or compared again and again. A transient value is reloaded from a door, a child unit or another register at the beginning of every transfer or operation (its `COPIES` or `DERIVES_FROM` records name that source, and its `GATED_BY` or `SELECTED_BY` records name a sequencer), then shifted or handed on.
- A register whose value is used only in conditions (its driving records are `GATES`, `SELECTS` or `CONSTRAINS`) is a handle, unless what it holds is itself a policy or a security counter from [Home]: a policy or an expiry count is used by being compared, and that is how you recognize it.
- **Handles**: an element whose driving records are only `SEQUENCES`, `RESETS`, `SELECTS`, `GATES` or `CONSTRAINS` decides when, where or whether; it does not supply the value. `CONSTRAINS` and `CONSTRAINED_BY` mark an element compared inside the condition that decides the target.
- **Hallways**: a signal with `"storage":"none"` that receives a value (`COPIES` or `DERIVES_FROM`) and passes it on (`CARRIES` or `SOURCES`). A signal whose value is copied into a register on the clock edge and used nowhere else is a next-value helper. Record fields with handling `FORWARDS` pass a value through unchanged.
- **Doors**: a `PORT` with mode `in` whose value records (`CARRIES`, `SOURCES`) lead into a home or into the result; a `PORT` with mode `out` and drive `driven` whose value comes from a home or from the result. Fields with handling `ORIGINATES` are created by this module; fields with `CONSUMES` are read by it.
- **Inert**: drive `tied`, or nothing but `constant_drivers`. An input port with storage `not assigned` and no relationship records is never used here.
- **Build options**: an element that exists only under some `configuration` condition is still an element. Alternatives that hold the same value under different options get the same decision, and an element that plays a listed role under any option is listed.
- **Child units**: `connections` show an element wired to a port of an instantiated unit. If the file declares no entity for that unit, its contents are not in the file, and values kept there can only be listed through [Only holder].

## Consistency and names

- Same role, same decision: build-option alternatives; parallel copies of one structure (channels, banks, byte lanes or entries declared as separate signals); the input door and the output door of the same payload; the same role in several entities.
- The same role also gets the same decision in every module: a request input is always a handle; a transfer shift register is always a hallway when its payload has a door; a register that raises an expiry or reset event is always a home.
- Never list an element twice.
- `element`: copy the `name` field from the map, character for character. A record field is written `<record>.<field>`, exactly as the map writes it. An array is listed by its whole name. Never insert an index, a slice, a hierarchy prefix or an entity prefix.
- `entity`: the `entity` field of that same map line.

## Security objective

Give each entry the single objective whose violation matters most for that element.

- **Confidentiality**: secrets and private content.
- **Integrity**: values that must not be changed: policies, stored code and constant tables, counters, ownership records, results, status reports.
- **Availability**: events and outputs that others wait for: expiry, interrupt, stop or reset requests, results whose blocking stops the service.

## Final checks

- Every listed name appears as a `name` in the map, with the same entity.
- Nothing listed is a clock, reset, request input, enabling bit, strobe, address, pointer, selector, override input, guarding bit, sequencer, synchronizer or pipeline copy, next-value helper, tied output, unused input, shared-interface field or test port (except the cases named under [Door] and [Status]).
- No register that holds a value only while one transfer or computation passes through is listed, unless it is that value's only holder.
- Every listed element passed the attack check as a target, not as a means.
- Elements with the same role got the same decision.
- No element was put in or left out because of its name alone.
- Every conceptual asset from Step B that belongs to this module appears in your list (at a home, a door or an only holder), or the analysis says why not.
- A list with no entries is right only if no value, setting or event in the module passed Step B.

## Output

Write a single JSON object to the output file, in this shape:

```json
{"module": "<module name from the input file>",
 "assets": [
   {"element": "<a declared element name, exactly as declared: a port, a signal, or <record>.<field>>",
    "entity": "<the entity that declares it>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<one or two sentences>"}
 ]}
```

Insert the key `"analysis"` between `"module"` and `"assets"`. Include nothing else.

- `module`: the name on the input file's opening line, after `MODULE:`.
- `analysis`: an object with `"purpose"` (what the module does: what enters, what it keeps, what leaves), `"conceptual_assets"` (an array of short strings, each naming a conceptual asset, its objective, and where it is listed: home, door or only holder) and `"rejected"` (an array of objects with keys `"element"`, `"role"` and `"why"`, for the closest calls you left out: registers, ports that carry a payload, and status-like outputs; `"role"` is Handle, Hallway, Shared interface, Inert, Ordinary setting or Test port).
- `security_objective`: the word Confidentiality, Integrity or Availability, spelled exactly so.
- `reason`: say the role (home, door, status or only holder), which conceptual asset the element holds or carries, and what an attacker gains by attacking it.
