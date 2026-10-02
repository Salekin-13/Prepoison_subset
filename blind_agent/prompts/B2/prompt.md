# Finding the primary security assets of a hardware module

## Your job

You are a hardware security engineer. You get one input file. It holds a hardware module written in VHDL (RTL), followed by a relation map that a program extracted from that RTL. Find the module's **primary security assets**: the declared elements that an attacker would go after directly. Write them as the JSON object described at the end.

Your list is compared with a list written by hardware security experts. A missed asset and an extra element cost the same. So list every element that qualifies, and leave out every element that only helps an attacker reach one.

Use only the input file. It contains no comments. Judge each element by what the RTL does with it, by the map, and by its name.

## Words used here

- **Asset**: something of value that the module uses, produces or protects.
- **Security objectives**:
  - **Confidentiality**: nobody without permission may observe the value.
  - **Integrity**: nobody without permission may change the value or force it to a wrong value.
  - **Availability**: the element must keep doing its job; nobody may block it or hold it stuck.
- **Conceptual asset**: what needs protection, said in words. Examples: a secret key, the words a buffer holds, the settings the module obeys, the alarm it raises.
- **Structural asset**: where that lives in the RTL: a declared port, signal or record field that stores or carries it.
- **Primary asset**: a structural asset that is the direct target of an attack. The attacker wants to read it, change it, or block it.
- **Secondary asset**: an element that only helps an attacker reach a primary asset. Examples: a wire or register that moves, copies or stages the value; an operand copy, partial result or round value inside a computation; a write strobe, select or address that decides when or where a value moves; a handshake; a clock; a reset; bus wiring that only passes values along. **Secondary assets are not listed.**
- **Attack point**: a port through which an adversary acts on the module. An attack point is a way in, not a target. It is listed only when the protected value itself passes through it (label BOUNDARY below).
- **Home**: the element inside the module that you credit as the holder of a conceptual asset. Step D says how to find it. The ports where that value crosses the outer boundary are judged separately (BOUNDARY).
- **Pacing pulse**: a single-cycle pulse, derived from the clock, that tells other units when to take their next step (a divided-clock strobe).

## Who attacks

Assume the module sits in a system-on-chip that faces these adversaries:

- untrusted software that reads and writes the module through its bus or register interface;
- an outside party wired to the module's external pins (serial lines, general-purpose pins, a debugger port);
- someone who uses debugging, test or override features without permission;
- physical attacks: glitch attacks (an induced glitch flips a stored bit) and side channels (power use or timing reveals a value);
- a malicious circuit (hardware Trojan) elsewhere on the chip.

Their aims: leak a secret, change something the system trusts, gain access or privilege they should not have, or stop the system from working (denial of service).

Two cautions:

- A glitch or a Trojan can hit any wire. That alone never makes an element primary. Always ask what the attacker is trying to get at.
- Normal operation is not an attack. An authorized write that changes stored contents, or an address that picks which word is read, is the module doing its job.

## How to read the input file

The first line names the module (`MODULE: <name>`). The RTL comes next. Each RTL line starts with its line number in the original source; numbers skip because comments and blank lines were removed. A file can hold several entities.

The relation map follows. Each `PORT` or `SIGNAL` line is one element, written as JSON. The indented lines under it are facts about that element.

Element fields:

- `name`, `entity`: the element and the entity that declares it. A record field is written `<record>.<field>`. A whole record and each of its fields are separate elements.
- `boundary` (ports only): `mode` is in, out, inout or buffer. For an output, `drive` is `driven` (assigned from elements), `tied` (only constants) or `undriven` (never assigned as a whole; its fields may be).
- `kind` (signals only): `register` (assigned on a clock edge somewhere) or `signal`.
- `storage`: `edge` means it keeps its value between clock edges; `none` means it is combinational; `mixed` means both; `not assigned` means it is never assigned in this module.
- `handling` (record fields): `ORIGINATES` (the module creates the value), `CONSUMES` (the module reads it), `FORWARDS` (the module passes it on unchanged). For a port field marked `FORWARDS`, check where the value goes: to another port of the module, or into a unit inside the module. Step F (label FORWARD) depends on this.
- `constant_drivers`: assignments of a literal or a named constant.
- `configuration`: build-time conditions under which the element exists or is driven.
- `connections`: the element is wired to a port of an instantiated sub-unit. If that sub-unit's entity is not in this file, you see only its ports.

Relationship records. Each relationship is stored on both elements: the first name below sits on the element that acts, the second on the element acted upon. `targets` are the other elements, `lines` are RTL line numbers, `guard` is the condition text.

- `CARRIES` / `COPIES`: the receiver is assigned exactly the driver's value. Same value, two names.
- `SOURCES` / `DERIVES_FROM`: the driver's value is used, possibly transformed, in the receiver's assignment.
- `SEQUENCES` / `CLOCKED_BY`: the driver is the receiver's clock.
- `RESETS` / `RESET_BY`: the driver is the receiver's reset.
- `SELECTS` / `SELECTED_BY`: the driver picks a case branch or an array index for the receiver.
- `GATES` / `GATED_BY`: the driver decides whether the receiver takes a value or is forced to a fixed value.
- A record on an element that names the element itself (it is assigned from its own value) marks a counter or a sequence register.
- Other relationship types may appear. Read the cited RTL lines to understand them.

The map is written by a program and can miss statements. The RTL is the authority; use the map as an index into it.

## Procedure

### Step A. Inventory

Read the whole file. List every element of the map (every `PORT` and `SIGNAL` line) with its entity. Only names from this list may appear in your output.

### Step B. Mission, module kind, attack surface

Say in plain words what the module does. Find the **outer entity**: the entity that instantiates the others, or the only entity. If some entities in the file do not instantiate each other, each of them is its own outer entity.

Say which kinds describe the module. Some rules below depend on the kind. A module can be more than one kind.

- **Keeper**: it keeps contents (a memory, a buffer, a cache, a key store, a bank of flags).
- **Mover**: it moves payload (a serial port, a bus bridge or switch, a debugging transport).
- **Calculator**: it turns operand inputs into a result output (an arithmetic unit, a cipher step, a checksum, an atomic read-modify-write).
- **Guard**: it watches or enforces something (a timer, a watchdog, a protection or access check, a generator of the system's reset or pacing pulses).
- **Wiring file**: it only connects sub-units that are defined elsewhere and has no register of its own.

For each adversary above, note which ports it can use to reach the module.

### Step C. Conceptual assets

Answer these questions for the module. Each yes gives a conceptual asset.

- **Confidentiality.** Is any information, received or created here, something an integrator could treat as secret? Think of keys, seeds, random numbers, raw entropy, private or user payload, payload in transit, and values that reveal what code is running.
- **Integrity.** Is there anything that must not be changed without permission? Think of settings, permissions, privilege or operating mode, write-protect bits, address bounds, code, counters whose value triggers an action, and the execution position.
- **Availability.** Is there anything whose loss or blocking would stop this module or the system? Think of the module's main output, its interrupt, alarm, error or expiry output, and the counter that must reach its event.
- **Undermined behaviour.** Are there privileged modes, overrides, ways to skip a check, or test and debugging paths that could make the module produce wrong output? The elements they would corrupt are assets. The override inputs themselves are attack points.

If the answer is no to all of these for some part of the module, that part holds no asset.

### Step D. Find where each conceptual asset lives (inclusion labels)

**Home rule.** Find the home of each conceptual asset with these cases, in this order.

- **Own register.** A register or memory array of this file keeps the value: that register is its home.
- **First holder.** The true store is not an element (a constant table), or it sits in a sub-unit that is instantiated here but defined elsewhere: the first register in this file that holds the value is its home.
- **Sub-unit output.** No register of this file holds it, because the file only wires sub-units together: the home is the signal that carries the value out of the sub-unit that keeps it. This case is for values a sub-unit keeps as its own record of the machine: the execution position, the privilege or operating mode, the instruction being executed, general-purpose register contents, control and status register values. Payload that only passes through a sub-unit is judged at the outer boundary (BOUNDARY), not at the wires between sub-units.
- **Single holder.** Along one path, credit a single holder: the register where the value is complete and kept longest. A shift register or staging register that only builds up a value, or hands it on, while another register of this file holds the same value complete is a carrier (exclusion label STAGING).

Then give each candidate one of these labels.

**STORE** (a stored secret or payload). The home of: a key, a seed, a random value or raw entropy the module creates or receives (raw entropy and the finished random value are different values; credit the register that holds each); payload words the module buffers, receives or sends, including the shift register of a serial transmitter or receiver when no other register of this file holds that word; instructions or program contents; the contents of a memory array.
Not STORE: values inside a calculation (next rule).

**Calculator rule.** In a calculator, the primary assets are the secret it keeps (a key register: STORE) and the payload where it crosses the outer boundary: the operand inputs and the final result output (BOUNDARY). Registers and signals inside that hold operand copies, partial results, round or iteration values, running totals, or the finished result on its way to the output port are secondary (exclusion label INTERMEDIATE). This rule does not cover a secret the module creates (a key, a seed, a random value, raw entropy): those are STORE.

**SETTING** (a setting the module obeys). A stored value that software or the integrator writes to configure behaviour and that stays in place: on/off and mode bits, permission and privilege bits, write-protect bits, address bounds and region values, compare, threshold, reload and prescaler values, interrupt mask bits. Typical sign: a register assigned from the bus write payload under a write condition and an address decode, and then read by the logic that decides behaviour. If a settings register is a record, decide each field.
Not SETTING: registered copies of request strobes, acknowledges or progress flags (see LEVER and BOOKKEEPING).

**CORE** (the operating record the module's purpose or security rests on). A register (in a wiring file: the signal found by the sub-unit output case) that, if forced to a wrong value, directly gives the attacker an advantage:

- the execution position (program counter) and the instruction being executed;
- the privilege or operating mode that the module keeps and enforces, a status saying a debugger has stopped the processor, an authentication or access-granted status;
- the main count of a timer, watchdog or bus-expiry monitor, whose value triggers an event that others see; in a module whose job is to generate the system's reset or pacing pulses, its main counter or sequence register;
- the register of the module's main FSM (the register that records which step of its job the module is in);
- an address or index register that picks which word of a store inside this module is written or read.

Not CORE: helper counters that only pace an internal transfer (bit counters, rate counters, wait counters), delayed copies of a listed register, synchronizer stages, and an address register that only holds the target of a request sent to another unit (LEVER).

**DECISION** (a decision or alert that other parts act on). An interrupt request; an error, exception or violation indication; an access grant or deny result; an expiry or reset request; and, in a module whose job is to generate the system's reset or pacing pulses, those generated outputs. List the element whose value is the alert (its register, or the combinational signal if it is never stored) and, if different, the outer-entity output that delivers it. If the alert is only one bit of a counter, the counter is judged by CORE or BOOKKEEPING, not here.
Not DECISION: flow-control flags (ready, in-progress, acknowledge, occupancy) and the strobe that announces a new word or value. This holds for a generator too: the new random value is the asset; the strobe that announces it is a lever.

**BOUNDARY** (where protected payload crosses the outer boundary). A port or port field of the outer entity that carries the value itself:

- a STORE value into or out of the module (write payload into a protected store, read payload out of it, external serial or parallel payload pins, key or seed inputs, the serial payload pins of a debugging port);
- the module's main product (its final computed result or generated output);
- the operands of a calculator.

It must carry the value itself (map: COPIES, CARRIES, SOURCES or DERIVES_FROM between it and the holder or the sub-unit that uses it), not select, gate, address or acknowledge it. A port wired straight into a sub-unit inside the module (map `connections`) qualifies even when the map marks it `FORWARDS`. If the module never stores a protected value it receives, and uses it directly, the input port is that value's home.
Not BOUNDARY: ports of inner entities (CARRIER); port fields whose value only passes to another port of the module (FORWARD); bus payload fields that carry only settings or status and no STORE value (they are attack points).

**ATTRIBUTE** (only in a module whose job includes an access or permission check, such as memory protection, access control, or a gate on debugging access). The inputs that carry the requester's privilege, security or debugging status and that the check depends on.

### Step E. Threat test

For each candidate, write one sentence: "An adversary who can observe / control / block `<element>` can `<harm>`."

Keep the element only if all of these hold:

- the harm concerns the element's own value: the secret it holds, the setting or operating record it encodes, the decision it delivers, or the protected payload it carries across the outer boundary;
- the adversary's action is unauthorized, not the module's normal job;
- you can name the objective that breaks.

If the harm only happens because the element changes or reveals another element ("it selects which word is read", "it opens the write", "it is copied into the register", "it announces that a new value is ready"), the element is a lever or a carrier. Credit the other element instead. A candidate that fails this test, and fits no label of Step F, goes in `not_listed` under FAILED-THREAT-TEST.

Tie-break: an element that is a home by the home rule, or where a protected value crosses the outer boundary, is kept. An element that only moves, delays, stages, selects or gates a value, or that holds an intermediate value of a calculation, is dropped.

### Step F. Exclusion labels

Every inventory element that is not kept gets one of these labels.

- **CLOCK-RESET**: the module's clock and reset inputs and their internal copies (map: SEQUENCES, RESETS), pacing pulses the module receives from elsewhere, and reset requests from other units that only feed a reset. Exception: in a module whose job is to generate the system's reset or pacing pulses, the generated outputs are DECISION and the main counter or sequence register is CORE. The clock line of a serial protocol (a clock pin of a serial bus that the module drives or samples) is a LEVER, not CLOCK-RESET.
- **LEVER**: inputs and combinational signals that only decide when, whether or where a value moves: read and write requests, strobes, byte selects, chip selects, output gates, write strobes, selects, address and index inputs, flush and wipe requests, kick-off pulses, handshakes and acknowledges, command or operation codes from other units, debugging or test mode flags, and override inputs (an input that forces another element to a value or puts the module into a special mode). Registered copies of strobes, requests, acknowledges or command codes, and address registers that only hold the target of a request sent to another unit, are levers too. For a debugging or test port, its serial payload pins are judged by BOUNDARY; its mode-select and clock pins are levers.
- **CARRIER**: elements that only move or delay a value already credited: next-value wires feeding a register, delayed copies, synchronizer stages, multiplexer outputs, ports of inner entities, wires between the holder and the outer port, and wires between sub-units that carry a value credited elsewhere.
- **STAGING**: a shift or staging register on a path where another register of this file holds the same value complete (single holder case of the home rule).
- **INTERMEDIATE**: operand copies, partial results, round or iteration values, running totals and the result on its way to the output port, inside a calculator (calculator rule).
- **BOOKKEEPING**: values computed from credited elements for internal use or flow control: occupancy, counts and comparison results, handshake and progress flags, strobes that announce a new value, helper counters, rate counters, wait counters. Unless the value is a DECISION.
- **FORWARD**: port fields whose value passes from one port of the module to another port unchanged (map `handling` FORWARDS, and the value ends at another port), and bus fields the module routes between ports. The module does not own that value. A port wired into a sub-unit inside the module is not FORWARD; judge it by BOUNDARY.
- **UNUSED**: elements never assigned and never read (no relationship records and no use in the RTL), outputs tied only to constants, record fields the module ignores.
- **RECORD-WHOLE**: a whole record whose fields appear in the map. Decide field by field instead. List a whole record only if the map lists it with no fields.

Never output constants, generics, types, process variables, loop parameters, process or generate labels, instance names, slices or indexed parts. They are not elements.

### Step G. Consistency

- Same role, same decision: each channel's compare register, each field of a settings register, each part of a key, each array that holds the same buffered payload under different build options, and, in a wiring file, the signals that bring the same kind of kept value out of different sub-units.
- Decide records field by field. Example: a serial transmitter record with fields for its sequence step, a bit counter, a shift register and a finished flag gives: sequence step CORE, shift register STORE (when no other register of this file holds the word), bit counter and finished flag BOOKKEEPING.
- An element that exists only under some build options (map `configuration`) is decided by its role, like any other.
- In a file with several entities, apply the same rules inside every entity. A value that moves between entities is credited at its holder, plus BOUNDARY at the outer entity.
- Do not credit the same value twice through copies. A holder and its BOUNDARY port, or a decision and the outer-entity output that delivers it, may both be listed; other copies may not.
- Accounting: every inventory element ends up either in `assets` or in a `not_listed` group. Never both, never missing.

### Step H. Names and objectives

- Copy each element name character for character from its `PORT` or `SIGNAL` line, including the dot of a record field. Take `entity` from the same line.
- No indexes, slices, ranges, hierarchy prefixes or instance names.
- `security_objective` is exactly one of `Confidentiality`, `Integrity`, `Availability`: the objective your threat sentence breaks. Secrets and private payload: Confidentiality. Settings, operating records, code and trusted values: Integrity. Decisions, generated pulses and product outputs whose blocking or flooding denies service: Availability (Integrity if a forged value misleads the system).
- `reason`: your threat sentence, ending with the label in brackets. When the home came from the first holder or the sub-unit output case, add that to the bracket, for example `[STORE, first holder]` or `[CORE, sub-unit output]`.

## Common mistakes to avoid

- Listing every port of a bus interface. Only payload fields of the outer entity that carry a STORE value, a calculator's operands or result, or the main product qualify.
- Listing clock or reset inputs.
- Listing a register together with its next-value wire or its delayed copy.
- Listing both a staging shift register and the register that holds the same complete word.
- Listing the operand, partial-result, round or running-total registers of an arithmetic or cipher datapath.
- Calling a port FORWARD when it feeds a sub-unit inside the module, or BOUNDARY when it only passes a value to another port.
- Treating a "new value available" strobe, or one bit of a counter, as a DECISION.
- In a wiring file: crediting some sub-units' kept values and calling their siblings carriers.
- Listing a whole record and also its fields.
- Listing constants, generics or labels.
- Deciding sibling elements differently.
- Missing settings registers and the main counter because they look ordinary.
- Missing the interrupt, error or expiry output.

## Worked decisions from published examples on other designs

- **Watchdog timer** (Accellera SA-EDI standard, annex). The register holding the running timer count is an asset: an adversary wants to change it to delay or prevent the expiry. The register that asserts the expiry is an asset: controlling it lets an adversary block the system reset or assert it all the time. The clock, the reset, the read and write strobes, the register address, the write payload and the debugger override inputs are attack points: ways to act on those registers, not targets. Under these instructions the watchdog's control register bits (run, hold, write-protect) and its reload value would also be listed, as SETTING.
- **SRAM controller** (IEEE P3164 white paper). The memory array, the register holding incoming words, the register holding outgoing words, and the address register are assets. The mode select, chip select, write strobe, output gate and sleep inputs are not; they are how an attacker disturbs the array.
- **Gaussian noise generator** (IEEE P3164 white paper). The seed path (the shift-register generators and the logic that combines them) needs confidentiality: an observer could predict the output. The address into the coefficient ROM and the ROM's output register need integrity: a wrong address picks a wrong coefficient. The address-override input is the attack point that forces it.
- **AES core** (LAsset paper). The key input, the input block and the final output of the outer module are primary assets, and so is the register that stores the key. The encryption/decryption block, the output buffer, the copies of the key and of the intermediate value inside each round, the expanded round keys and the lookup-table outputs are secondary.
- **Shared bus** (SAIF paper). The sensitive information a bus master sends is primary. The bus and the address decoder that carry and route it are secondary.
- **Processor core** (IEEE P3164 white paper, SAIF paper). The program counter, the general-purpose registers, cache contents, branch-history and address-translation contents, and the values of control and status registers are assets. A debugger that can see the program counter during normal operation breaks confidentiality. The write strobe that controls writes to the control and status registers is secondary. A cache that overwrites a line on an authorized store is normal behaviour, not an integrity attack.

## Output

Write a single JSON object with these top-level keys, in this order: `module`, `analysis`, `assets`. Use valid JSON: double quotes, no trailing commas, no comments.

```json
{"module": "<module name from the input file>",
 "analysis": {
   "mission": "<what the module does, in plain words>",
   "outer_entity": "<entity name>",
   "attack_surface": "<which ports each adversary can use>",
   "conceptual_assets": [
     {"what": "<the conceptual asset in words>",
      "objective": "Confidentiality | Integrity | Availability",
      "homes": ["<element>"]}
   ],
   "not_listed": [
     {"rule": "CLOCK-RESET | LEVER | CARRIER | STAGING | INTERMEDIATE | BOOKKEEPING | FORWARD | UNUSED | RECORD-WHOLE | FAILED-THREAT-TEST",
      "elements": ["<element>"]}
   ]
 },
 "assets": [
   {"element": "<a declared element name, exactly as declared: a port, a signal, or <record>.<field>>",
    "entity": "<the entity that declares it>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<one or two sentences>"}
 ]}
```

Keep `analysis` short: plain sentences for the first three keys (say the module kinds in `mission`), names only in `not_listed`.

## Final check before writing

- Every asset name appears in the map exactly as written, with the entity from its line.
- No clock or reset input, constant, generic, label or instance name is listed.
- Each asset has a threat sentence that passes Step E.
- No two assets are copies of the same value, except a holder and its BOUNDARY port, or a decision and its outer-entity output.
- In a calculator, no operand copy, partial result or round value is listed.
- No port is called FORWARD if it feeds a sub-unit inside the module.
- Elements with the same role got the same decision.
- Every inventory element is in `assets` or in `not_listed`.
- The JSON parses.
