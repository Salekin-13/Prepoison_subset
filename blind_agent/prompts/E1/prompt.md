# Primary security assets of one hardware module

## Your task

You are a hardware-security engineer. You have one input file: the RTL (VHDL) of one hardware module, followed by a relation map that a static analyser wrote from that RTL. List the module's **primary security assets**: the declared elements that an attacker would target directly. Write the result as a single JSON object (format at the end).

Judge every element by what the RTL does with it. Never decide from how a name sounds: a name can hint at a role, but only the RTL shows the role.

This task usually goes wrong in these ways. Listing too much: everything near a protected value gets listed, including the clocks, strobes, addresses and wires that only move it. Listing too little: stopping at the obvious register and missing its doors, a second home, or a status output. Inconsistency: two elements with the same role get different decisions. Wrong names: an element written differently from its declaration. The rules and examples below are built to prevent each of these.

## Words used here

- **Conceptual asset**: information or behaviour of the module that needs Confidentiality, Integrity or Availability. For example: a secret key, a random seed, a user's private payload, stored program code, a privilege or access-permission setting, a timeout that must fire, a result that other units depend on.
- **Structural asset**: a declared element (port, signal, or record field) that physically holds or carries a conceptual asset.
- **Primary asset**: a structural asset that is itself the attacker's target. These are what you list.
- **Secondary element**: an element that helps move, stage, time, select, enable or guard a primary asset. Attacking it is a way to reach a primary asset. It is not listed.
- **Attack point**: an input or output through which an attacker acts on, or observes, an asset. It is not listed; the asset behind it is.

The roles below are used in every rule and example:

- **Home**: the register or memory array where the module keeps a protected value.
- **Door**: a port of the module that exists to carry a protected value or event in or out.
- **Hallway**: an internal wire, helper signal, staging copy or sub-unit relay between a home and a door.
- **Handle**: an element that decides when, where or whether a value moves: clock, reset, enable, strobe, address, pointer, index, selector, override, guarding bit.

You list homes, doors and reported status. You never list hallways or handles.

## Method

**Step A. Understand the module.** Read all of the RTL. Write down briefly what the module is for: what enters it, what it keeps, what it computes, what leaves it. If the file holds several entities, find which entity instantiates which (the map's `connections` show this). An entity that no other entity in the file instantiates is an *outer entity*; its ports are the boundary of the module.

**Step B. Find the conceptual assets.** Ask these questions about the module's normal use:

- *Confidentiality*: is there information, received or produced here, that could be secret? (keys, seeds, random values, private payloads, values that reveal what a program is doing)
- *Integrity*: is there state or a setting that the wrong party must not change, or that must not change at the wrong time? (stored code or constant tables, privilege and permission settings, protected counters, results). An update made by the intended path at the intended time is normal behaviour, not an integrity threat.
- *Availability*: is there something whose loss or blocking would stop the module or the system? (timeouts, interrupt, halt or reset requests, results that other units wait for)
- *Undermined behaviour*: is there an override, bypass, test or debugger path that can make the module behave wrongly? If so, the asset is what the path overrides; the path itself is a handle.

A value for which every answer is "no" is not an asset.

**Step C. Map each conceptual asset to elements.** Find its home(s) and door(s) with the List rules below. Give an explicit decision to every register (`"kind":"register"`) in every entity and to every port of each outer entity. Do not stop at the first good candidate.

**Step D. Remove secondary elements and attack points** with the Do-not-list rules. An element is listed only if a List rule names its role.

**Step E. Attack check.** For each element still on your list, name a concrete attack whose target is that element itself: side-channel leakage, fault injection, leakage from a secure to a non-secure party, unauthorized access, privilege escalation, a hidden hardware Trojan, or denial of service. If the only honest description is "the attacker uses this element to reach another element", remove it: it is a handle or a hallway.

**Step F. Consistency and names** (section below). Then write the JSON.

## List rules

**[Home]** A register or memory array that keeps a protected value:

- a key, seed or random-state register;
- a register, buffer or memory array whose content is the payload the module exists to store, receive or send (not a staging copy of a value that is already kept elsewhere in the module);
- a counter whose value decides a security-relevant event, such as the count that triggers a timeout;
- a register that holds a security policy the module exists to hold or enforce: privilege mode, access-permission entries, secure versus non-secure selection, debugger authorization state.

If the protected value comes from a constant table or ROM image (constants are not elements), the register that first captures the value read out of it is its home.

**[Door]** A port of an outer entity that exists to carry a protected value or event:

- a key or seed input; a private payload input;
- the module's result output;
- the write-in and read-out payload of a module whose whole content is the protected payload (a memory or a buffer);
- an interrupt, timeout, halt or reset request output.

When the door is a field of a record port, the door is that field.

**[Status]** A register or output that reports the outcome or health of the protected function to software or to other units: error or fault codes, access-violation flags, completion of a security operation.

## Do-not-list rules

**[Handle]** Clock and reset inputs. Enables, strobes, read/write selects, addresses, indices, pointers, `case` selectors. Override, test and debugger inputs. Guarding bits (a locking bit, an enable bit) that protect or switch another asset. A register that only counts the steps of a transfer or delays a strobe. List the asset they act on instead.

**[Hallway]** Combinational wires between a home and a door. Next-value helper signals whose only use is to feed a register (decide on the register instead). Staging buffers and pipeline copies of a value that already has a listed home. Ports of an instantiated sub-unit that receive or return a value already listed at its home or at an outer door.

**[Shared interface]** Ports and record fields of a general bus or register interface that carry every access to a set of registers: address, write value, read value, byte enables, access tags, request strobes, acknowledge, ready/valid, and occupancy flags that pace transfers. They are attack points or flow control. Judge the registers behind them instead. The only exception is the memory/buffer case under [Door].

**[Inert]** An output tied to constants. An input that is never read in the module. A whole record when the asset sits in some of its fields (list the field). Constants, generics, loop parameters and process variables are not elements at all.

**[Ordinary setting]** Configuration that only tunes how the function runs: speed, size, format, the engine's operating mode, start/stop, a public parameter such as an initialization vector. It steers the asset; it is not the target.

**[Test port]** A port that exists to observe internals for testing. It is an attack point: list what it exposes, not the port.

## Worked examples from other designs

These designs come from published asset-identification case studies. Names in code font are those designs' own names; you will not see them in your input. Learn the reasons, not the names. Each table shows the decision for the elements an engineer would consider, including the ones that are left out.

### Watchdog timer

A countdown timer. Software writes a reload value and a control register (start, pause, and a locking bit that blocks further changes) through a small register interface: read enable, write enable, address, write value, read value. When the count reaches zero, an internal register raises the timeout, and an output carries it to the chip as a reset. A set of debugger inputs can override the clock, the start, pause and service controls, the reload value and the timeout.

| Element | Decision | Why |
|---|---|---|
| `wd_timer`, register holding the current count | List [Home], Integrity | The value the attacker wants to change: stretch the count to prevent the reset, or cut it to force one. |
| `wd_assert_timeout`, register that raises the timeout | List [Home], Integrity | Forcing or suppressing it fakes or blocks the system reset. |
| `o_wd_reset`, output carrying the timeout to the chip | List [Door], Availability | It exists only to carry the protected event out; holding it inactive denies recovery. |
| Clock input, reset input | Not: [Handle] | They pace and clear everything in the module; they are attack points, not this module's assets. |
| Read enable, write enable, address, write value, read value | Not: [Shared interface] | They carry every register access. An attack goes through them; they are not the target. |
| Control register with start, pause and the locking bit | Not: [Handle], [Ordinary setting] | The locking bit guards the counter and the start and pause bits steer it. The counter is listed. |
| Reload value passed from the control block to the counter block | Not: [Hallway] | It only feeds the counter, which is listed. |
| Debugger inputs (enable, clock, reload value, timeout, start, pause, service) | Not: [Handle] | Override paths: the means of attack on the listed registers. |
| Internal wires that choose between normal and debugger controls | Not: [Hallway], [Handle] | They only route control and clock. |

How this looks in a relation map: `wd_timer` would be a `SIGNAL` with `"kind":"register"` and `"storage":"edge"`. It is `SELECTED_BY` the start, service and pause wires (they form the `case` selector), `DERIVES_FROM` itself (it counts down), `COPIES` the reload wire, and it `GATES` `wd_assert_timeout` (the comparison with zero). The start, service and pause wires appear mostly with `SELECTS` and `GATES` records. So: the register is a home, those wires are handles, and the reload wire is a hallway.

### AES encryption engine

Key, initialization vector and plaintext enter through their own inputs. A key register holds the key. Input and output buffers stage the payload. An encrypt/decrypt engine runs rounds in sub-units. Configuration registers set mode, key size and start. Status registers report error codes, state and completion. A debugger port can take over the engine and swaps in hardcoded test key values.

| Element | Decision | Why |
|---|---|---|
| Key input port | List [Door], Confidentiality | The secret enters here. |
| Key register | List [Home], Confidentiality | The secret is kept here: the attacker's direct target. |
| Plaintext (input state) port | List [Door], Confidentiality | The user's private payload enters here. |
| Result output port | List [Door], Availability | The final product other units wait for; blocking or corrupting it breaks the service. |
| Status registers (error codes, completion) | List [Status], Integrity | They report the engine's outcome and can reveal its internal condition. |
| Configuration registers (mode, key size, start) | Not: [Ordinary setting] | They steer the engine; the key and the payload are the targets. |
| Initialization-vector register | Not: [Ordinary setting] | A public parameter that steers the cipher. |
| Input buffer, output buffer | Not: [Hallway] | Staging copies between a door and the engine. |
| Round state and per-round key copies inside the round sub-units | Not: [Hallway] | Copies of values already listed at their home and doors. |
| Hardcoded debugger key values | Not: [Inert] | Constants, not elements. |
| Debugger port, clock | Not: [Handle] | Attack point; timing. |

### SRAM controller

A memory array. An address register and a delayed copy of it. A write-in register and an output register sit between the array and a bidirectional payload port. Chip enable, write enable, byte write, output enable and sleep inputs. A mode input switches the array to a built-in self-test that overwrites its content.

| Element | Decision | Why |
|---|---|---|
| Memory array | List [Home], Confidentiality | The stored content may be secret, and some ranges must stay unchanged. |
| Bidirectional payload port | List [Door], Confidentiality | The memory's content enters and leaves only through it (memory case of [Door]). |
| Write-in register, output register | Not: [Hallway] | Staging copies between the door and the array, which are both listed. |
| Address register and its delayed copy | Not: [Handle] | They decide which word is reached. |
| Chip enable, write enable, byte write, output enable | Not: [Handle] | Strobes. |
| Sleep input | Not: [Handle] | A denial-of-service lever on the array; the array is listed. |
| Self-test mode input | Not: [Handle] | An override that overwrites the array; the array is listed. |
| Control-logic state, self-test pattern generator | Not: [Handle], [Hallway] | Sequencing and test infrastructure. |

### Gaussian noise generator

Seed inputs load shift-register generators. Their outputs are combined. Leading-zero, mask and swizzle logic compute an address into a coefficient ROM. The ROM output is registered, and the noise value leaves through an output. Added for testing: an input that overrides the ROM address, and an output that exposes the combined random stream.

| Element | Decision | Why |
|---|---|---|
| Seed inputs | List [Door], Confidentiality | Whoever knows the seeds predicts every output. |
| Shift-register state registers | List [Home], Confidentiality | The generator's secret state. |
| Register that holds the coefficient read from the ROM | List [Home], Integrity | The ROM table is a constant; this register is the first element that holds a coefficient. A wrong coefficient spoils the noise. |
| Noise output | List [Door], Integrity | The product that other units consume. |
| Combined random value wire; leading-zero, mask and swizzle logic | Not: [Hallway] | Computed from the listed state on its way to the output. |
| Address into the coefficient ROM | Not: [Handle] | It selects which coefficient is read; the coefficient register is listed. |
| Address-override input | Not: [Handle] | An override path; its target, the coefficient register, is listed. |
| Test output exposing the random stream | Not: [Test port] | An observation point; what it exposes, the shift-register state, is listed. |
| Clock, reset | Not: [Handle] | Timing and initialization. |

### Microcontroller core under a debugger, and a shared bus

The program counter must stay hidden from a debugger while a user program runs normally. A separate case: masters and slaves share a bus, and a crypto unit keeps a key.

| Element | Decision | Why |
|---|---|---|
| Program counter register | List [Home], Confidentiality | It reveals the flow of the user's program. |
| Execution-state and instruction-state registers, decoded-instruction registers | Not: [Hallway], [Handle] | They carry information about, or steer, the program counter: secondary. |
| Debugger access port | Not: [Test port] | An untrusted observation point. |
| Debugger enable signal | Not: [Handle] | A precondition for the attack, not its target. |
| General-purpose register file of a CPU core | List [Home], Confidentiality | Shared by every program that runs on the core. |
| A register holding the privilege mode | List [Home], Integrity | It is the security policy the core enforces. |
| The sensitive payload a bus master sends | List, at its home or door in the master | It is the target. |
| Bus wires, arbiter, address decoder | Not: [Hallway], [Handle] | Infrastructure that moves the payload. |
| Key register inside the crypto unit | List [Home], Confidentiality | The secret itself. |
| Start-up versus normal execution state that restricts access to the key | Not: [Handle] | It guards the key; the key is listed. |

### What the examples share

- Every listed element is something the attacker wants. The handles and hallways around it are left out, even though an attack passes through them.
- When one protected value has a home and doors, the home and the doors are listed, and the hallways between them are not.
- Inputs that steer (enables, addresses, selectors, overrides, clocks, resets) are never listed. What they steer is.
- A setting is listed only when the setting is itself the policy being protected.

## Reading the relation map for these roles

The map records facts, not judgements. Use it to find roles quickly, then confirm each decision at the RTL lines it cites; the map can miss statements.

- **Home candidates**: `SIGNAL` lines with `"kind":"register"` and `"storage":"edge"`. Look at what they receive (`COPIES`, `DERIVES_FROM`) and where their value goes (`CARRIES`, `SOURCES`). A register whose value is used only in conditions (its driving records are `GATES`, `SELECTS` or `CONSTRAINS`) is a handle, unless what it holds is itself a policy or a security counter from [Home]: a policy or a timeout count is used by being compared, and that is how you recognize it.
- **Handles**: an element whose driving records are only `SEQUENCES`, `RESETS`, `SELECTS`, `GATES` or `CONSTRAINS` decides when, where or whether; it does not supply the value. `CONSTRAINS` and `CONSTRAINED_BY` mark an element compared inside the condition that decides the target.
- **Hallways**: a signal with `"storage":"none"` that receives a value (`COPIES` or `DERIVES_FROM`) and passes it on (`CARRIES` or `SOURCES`). A signal whose value is copied into a register on the clock edge and used nowhere else is a next-value helper. Record fields with handling `FORWARDS` pass a value through unchanged.
- **Doors**: a `PORT` with mode `in` whose value records (`CARRIES`, `SOURCES`) lead into a home or into the result; a `PORT` with mode `out` and drive `driven` whose value comes from a home or from the result. Fields with handling `ORIGINATES` are created by this module; fields with `CONSUMES` are read by it.
- **Inert**: drive `tied`, or nothing but `constant_drivers`. An input port with storage `not assigned` and no relationship records is never used here.
- **Build options**: an element that exists only under some `configuration` condition is still an element. Alternatives that hold the same value under different options get the same decision.
- **Sub-units**: `connections` show an element wired to a port of an instantiated sub-unit.

## Consistency and names

- Same role, same decision: build-option alternatives; parallel copies of one structure (channels, banks or entries declared as separate signals); the input door and the output door of the same protected payload; the same role in several entities.
- Never list an element twice.
- `element`: copy the `name` field from the map, character for character. A record field is written `<record>.<field>`, exactly as the map writes it. An array is listed by its whole name. Never add an index, a slice, a hierarchy prefix or an entity prefix.
- `entity`: the `entity` field of that same map line.

## Security objective

Give each entry the single objective whose violation matters most for that element.

- **Confidentiality**: secrets and private content.
- **Integrity**: values that must not be changed: policies, stored code and constant tables, counters, results, status reports.
- **Availability**: events and outputs that others wait for: timeouts, interrupt, halt or reset requests, results whose blocking stops the service.

## Final checks

- Every listed name appears as a `name` in the map, with the same entity.
- Nothing listed is a clock, reset, enable, strobe, address, pointer, selector, override input, guarding bit, staging copy, next-value helper, tied output, unused input, shared bus field or test port (except the memory/buffer case under [Door]).
- Every listed element passed the attack check as a target, not as a means.
- Elements with the same role got the same decision.
- No element was put in or left out because of its name alone.
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

Add the key `"analysis"` between `"module"` and `"assets"`. Add nothing else.

- `module`: the name on the input file's opening line, after `MODULE:`.
- `analysis`: an object with `"purpose"` (what the module does: what enters, what it keeps, what leaves), `"conceptual_assets"` (an array of short strings, each naming a conceptual asset and its objective) and `"rejected"` (an array of objects with keys `"element"`, `"role"` and `"why"`, for the closest calls you left out: registers, ports that carry a payload, and status-like outputs; `"role"` is Handle, Hallway, Shared interface, Inert, Ordinary setting or Test port).
- `security_objective`: the word Confidentiality, Integrity or Availability, spelled exactly so.
- `reason`: say the role (home, door or status), which conceptual asset the element holds or carries, and what an attacker gains by attacking it.
