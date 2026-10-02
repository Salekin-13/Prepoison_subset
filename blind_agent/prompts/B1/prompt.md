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
- **Secondary asset**: an element that only helps an attacker reach a primary asset. Examples: an internal wire or copy that moves the value; an enable, select or address that decides when or where it moves; a handshake; a clock; a reset; bus wiring that only passes values along. **Secondary assets are not listed.**
- **Attack point**: a port through which an adversary acts on the module. An attack point is a way in, not a target. It is listed only when the protected value itself passes through it (rule BOUNDARY below).

## Who attacks

Assume the module sits in a system-on-chip that faces these adversaries:

- untrusted software that reads and writes the module through its bus or register interface;
- an outside party wired to the module's external pins (serial lines, general-purpose pins, a debugger port);
- someone who uses debugging, test or override features without permission;
- physical attacks: fault injection (a glitch flips a stored bit) and side channels (power use or timing reveals a value);
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
- `handling` (record fields): `ORIGINATES` (the module creates the value), `CONSUMES` (the module reads it), `FORWARDS` (the module passes it on unchanged).
- `constant_drivers`: assignments of a literal or a named constant.
- `configuration`: build-time conditions under which the element exists or is driven.
- `connections`: the element is wired to a port of an instantiated sub-unit.

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

### Step B. Mission and attack surface

Say in plain words what the module does. Find the **outer entity**: the entity that instantiates the others, or the only entity. If some entities in the file do not instantiate each other, each of them is its own outer entity. For each adversary above, note which ports it can use to reach the module.

### Step C. Conceptual assets

Answer these questions for the module. Each yes gives a conceptual asset.

- **Confidentiality.** Is any information, received or created here, something an integrator could treat as secret? Think of keys, seeds, random numbers, private or user payload, payload in transit, and values that reveal what code is running.
- **Integrity.** Is there anything that must not be changed without permission? Think of settings, permissions, privilege or operating mode, write-protect bits, address bounds, code, counters whose value triggers an action, and the execution position.
- **Availability.** Is there anything whose loss or blocking would stop this module or the system? Think of the module's main output, its interrupt, alarm, error or timeout output, and the counter that must reach its event.
- **Undermined behaviour.** Are there privileged modes, overrides, bypasses, or test and debugging paths that could make the module produce wrong output? The elements they would corrupt are assets. The override inputs themselves are attack points.

If the answer is no to all of these for some part of the module, that part holds no asset.

### Step D. Find where each conceptual asset lives (inclusion rules)

Give each candidate one of these tags.

**STORE** (a stored secret or payload). A register or memory (map: `kind` register with `storage` edge or mixed, or a signal of an array type in the RTL) that holds a key, a seed, a random value or entropy sample; payload words the module buffers, receives, sends, computes or returns, including a shift register that holds payload in transit; instructions or program contents; or the contents of a memory array. If the real store is not an element (a constant table, or a unit outside this file), the first register in this file that holds the value is its home.

**SETTING** (a setting the module obeys). A stored value that software or the integrator writes to configure behaviour and that stays in place: enable and mode bits, permission and privilege bits, write-protect bits, address bounds and region values, compare, threshold, reload and prescaler values, interrupt enable bits. Typical sign: a register assigned from the bus write payload under a write condition and an address decode, and then read by the logic that decides behaviour. If a settings register is a record, decide each field.
Not SETTING: registered copies of request strobes, acknowledges or progress flags (see LEVER and BOOKKEEPING).

**CORE** (the operating status the module's purpose or security rests on). A register that, if forced to a wrong value, directly gives the attacker an advantage:

- the execution position (program counter) and the instruction being executed;
- the privilege or operating mode that the module keeps and enforces, a debugger-halted status, an authentication or unlock status;
- the main count of a timer or watchdog, whose value triggers an event that others see;
- the register of the module's main state machine (the one that decides what the module is doing);
- stored pointers or address registers that decide where protected contents are written or read.

Not CORE: helper counters that only pace an internal transfer (bit counters, rate ticks, wait counters), delayed copies of a listed register, synchronizer stages.

**DECISION** (a decision or alert that other parts act on). An interrupt request; an error, fault, exception or violation indication; an access grant or deny result; a timeout or reset request; the indication that a fresh secret or random value is ready. List the element where the decision is formed (its register, or the combinational signal if it is never stored) and, if different, the outer-entity output that delivers it.
Not DECISION: generic flow-control flags (ready, busy, acknowledge, occupancy or count indications); see BOOKKEEPING.

**BOUNDARY** (where protected payload crosses the outer boundary). A port or port field of the outer entity that carries a STORE value itself into or out of the module (write payload into a protected store, read payload out of it, external serial or parallel payload pins, key or seed inputs), or that delivers the module's main product to the outside (its final computed result or generated output). It must carry the value itself (map: COPIES, CARRIES, SOURCES or DERIVES_FROM between it and the holder), not select, enable, address or acknowledge it. If the module never stores a protected value it receives, and uses it directly, the input port is that value's home.
Not BOUNDARY: ports of inner entities that move a value between units (CARRIER); bus write or read payload fields that carry only settings or status and no STORE value (they are attack points).

**ATTRIBUTE** (only in a module whose job includes an access or permission check, such as memory protection, access control, or a gate on debugging access). The inputs that carry the requester's privilege, security or debugging status and that the check depends on.

### Step E. Threat test

For each candidate, write one sentence: "An adversary who can observe / control / block `<element>` can `<harm>`."

Keep the element only if all of these hold:

- the harm concerns the element's own value: the secret it holds, the setting or operating status it encodes, the decision it delivers, or the protected payload it carries across the outer boundary;
- the adversary's action is unauthorized, not the module's normal job;
- you can name the objective that breaks.

If the harm only happens because the element changes or reveals another element ("it selects which word is read", "it enables the write", "it is copied into the register"), the element is a lever or a carrier. Credit the other element instead. A candidate that fails this test, and fits no tag of Step F, goes in `not_listed` under FAILED-THREAT-TEST.

Tie-break: an element that holds a protected value across clock cycles, or where that value crosses the outer boundary, is kept. An element that only moves, delays, selects or enables it is dropped.

### Step F. Exclusion rules

Every inventory element that is not kept gets one of these tags.

- **CLOCK-RESET**: clock and reset inputs and their internal copies (map: SEQUENCES, RESETS), and clock-enable ticks. Exception: if the module's job is to generate a reset or timeout for the system, that generated output is a DECISION.
- **LEVER**: inputs and combinational signals that only decide when, whether or where a value moves: read and write requests, strobes, byte enables, chip and output enables, write enables, selects, address and index inputs, clear and flush requests, start pulses, handshakes and acknowledges, command or operation codes from other units, debugging and test override inputs. They mainly GATE or SELECT other elements and hold nothing of their own. Registered copies of strobes, requests or acknowledges are levers too.
- **CARRIER**: elements that only move or delay a value already credited: next-value wires feeding a register, delayed copies, synchronizer stages, multiplexer outputs, ports of inner entities, wires between the holder and the outer port.
- **BOOKKEEPING**: values computed from credited elements for internal use or flow control: occupancy, counts and comparison results, handshake and progress flags, helper counters, rate ticks, wait counters. Unless the value is a DECISION.
- **FORWARD**: record fields the module only passes on (map `handling` FORWARDS), and bus fields it passes between ports unchanged. The module does not own that value.
- **UNUSED**: elements never assigned and never read (no relationship records and no use in the RTL), outputs tied only to constants, record fields the module ignores.
- **RECORD-WHOLE**: a whole record whose fields appear in the map. Decide field by field instead. List a whole record only if the map lists it with no fields.

Never output constants, generics, types, process variables, loop parameters, process or generate labels, instance names, slices or indexed parts. They are not elements.

### Step G. Consistency

- Same role, same decision: each channel's compare register, each field of a settings register, each part of a key, each array that holds the same buffered payload under different build options.
- Decide records field by field. Example: a transmit engine record with fields for its sequence step, a bit counter, a shift register and a finished flag gives: sequence step CORE, shift register STORE, bit counter and finished flag BOOKKEEPING.
- An element that exists only under some build options (map `configuration`) is decided by its role, like any other.
- In a file with several entities, apply the same rules inside every entity. A value that moves between entities is credited at its holder, plus BOUNDARY at the outer entity.
- Do not credit the same value twice through copies. A holder and its BOUNDARY port, or a decision and the outer-entity output that delivers it, may both be listed; other copies may not.
- Accounting: every inventory element ends up either in `assets` or in a `not_listed` group. Never both, never missing.

### Step H. Names and objectives

- Copy each element name character for character from its `PORT` or `SIGNAL` line, including the dot of a record field. Take `entity` from the same line.
- No indexes, slices, ranges, hierarchy prefixes or instance names.
- `security_objective` is exactly one of `Confidentiality`, `Integrity`, `Availability`: the objective your threat sentence breaks. Secrets and private payload: Confidentiality. Settings, operating status, code and trusted values: Integrity. Decisions and product outputs whose blocking or flooding denies service: Availability (Integrity if a forged value misleads the system).
- `reason`: your threat sentence, ending with the rule tag in brackets.

## Common mistakes to avoid

- Listing every port of a bus interface. Only payload fields of the outer entity that carry a STORE value or the main product qualify.
- Listing clock or reset inputs.
- Listing a register together with its next-value wire or its delayed copy.
- Listing a whole record and also its fields.
- Listing constants, generics or labels.
- Deciding sibling elements differently.
- Missing settings registers and the main counter because they look ordinary.
- Missing the interrupt, error or timeout output.

## Worked decisions from published examples on other designs

- **Watchdog timer** (Accellera SA-EDI standard, annex). The register holding the running timer count is an asset: an adversary wants to change it to delay or stop the timeout. The register that asserts the timeout is an asset: controlling it lets an adversary block the system reset or assert it all the time. The clock, the reset, the read and write enables, the register address, the write payload and the debugger override inputs are attack points: ways to act on those registers, not targets. Under these instructions the watchdog's control register bits (start, pause, write-protect) and its reload value would also be listed, as SETTING.
- **SRAM controller** (IEEE P3164 white paper). The memory array, the register holding incoming words, the register holding outgoing words, and the address register are assets. The mode select, chip enable, write enable, output enable and sleep inputs are not; they are how an attacker disturbs the array.
- **AES core** (LAsset paper). The key input, the input block and the final output of the outer module are primary assets. The copies of the key and of the intermediate value inside each round, the expanded round keys and the lookup-table outputs are secondary.
- **Shared bus** (SAIF paper). The sensitive information a bus master sends is primary. The bus and the address decoder that carry and route it are secondary.
- **Processor core** (IEEE P3164 white paper, SAIF and LAsset papers). The program counter, the general-purpose registers, cache contents, branch-history and address-translation contents, and the values of control and status registers are assets. A debugger that can see the program counter during normal operation breaks confidentiality. The write enable that controls writes to the control and status registers is secondary. A cache that overwrites a line on an authorized store is normal behaviour, not an integrity attack.

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
     {"rule": "CLOCK-RESET | LEVER | CARRIER | BOOKKEEPING | FORWARD | UNUSED | RECORD-WHOLE | FAILED-THREAT-TEST",
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

Keep `analysis` short: plain sentences for the first three keys, names only in `not_listed`.

## Final check before writing

- Every asset name appears in the map exactly as written, with the entity from its line.
- No clock or reset input, constant, generic, label or instance name is listed.
- Each asset has a threat sentence that passes Step E.
- No two assets are copies of the same value, except a holder and its BOUNDARY port, or a decision and its outer-entity output.
- Elements with the same role got the same decision.
- Every inventory element is in `assets` or in `not_listed`.
- The JSON parses.
