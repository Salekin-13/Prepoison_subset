# Primary security assets of one hardware module

You get one input file: a VHDL module whose lines are numbered, followed by a relation map that a static analyser
wrote from that RTL. List the module's **primary security assets** by their declared names. List nothing else.

## What to list

- An **asset** is a value whose confidentiality, integrity or availability must be protected.
- A **conceptual asset** is that value as an idea: a secret, stored data, a setting, the progress of an operation,
  a security decision.
- A **primary asset** is a declared element that *is* a conceptual asset of this module: the place where the value is
  held, or where it enters or leaves the module. An attacker targets it directly. **List these.**
- A **secondary asset** only moves, times, selects, enables or computes part of a primary asset's value. It matters
  only because of the primary asset. **Do not list these.**

## How to decide

**Find the conceptual assets.** Read all of the RTL and say what the module does. Then ask:

- Confidentiality: what information that this module receives, stores or generates could be secret?
- Integrity: what data, setting, mode or state must not be changed by an unauthorized party or at the wrong time?
  Updates that the design intends in normal operation are not a threat.
- Availability: what output or state, if blocked or stuck, stops the module or its users from working?
- Undermined behaviour: can a privileged, debug, test, override or bypass path make the module produce wrong
  results? The elements that path can corrupt are conceptual assets.

Conceptual assets are usually of these kinds:

- data the module stores, receives to process, or returns, including secrets such as keys, seeds and random values;
- settings held in registers: configuration, mode, privilege, lock and enable bits that are written and then kept to
  govern later behaviour;
- state that says where the module is in its work: state-machine state, a program counter, the count of a timer,
  pointers into stored data;
- security decisions and events the module emits: access allowed or denied, a fault or error report, an interrupt
  request, a timer expiry, a reset request.

**Map each conceptual asset to elements.** List:

- the register, memory or array that holds the value;
- each port, or field of a record port, through which the value enters or leaves the module;
- only if the value has no such register or port in the file: the signal that carries the complete value.

**Leave out:**

- clock and reset inputs;
- signals that only time or address a transfer: request and command strobes (read, write, flush, start pulses),
  valid and ready, read/write direction, write and byte enables, acknowledge, fill-state flags and fill counts, and
  addresses or indexes that only pick which word moves. A register that holds such a pulse for one transfer is still a
  strobe. A held setting or state from the list above is not a strobe, even when it gates other logic;
- intermediates: next-value signals, partial or derived versions of a listed value, and registers that only delay or
  duplicate a listed value (pipeline copies, synchronizers, a second register loaded with the same value);
- fields the module passes on unchanged without storing or using them (map handling `FORWARDS` only): they are
  transport;
- ports and fields the module never uses, outputs tied to constants, and whole records whose fields carry the values
  (list those fields instead);
- constants, generics, loop parameters and process variables: they are not elements. If a constant holds an asset
  (for example a ROM table), list the elements that hold or deliver its value.

**Keep only direct targets.** For each candidate, name a concrete attack whose target is this element itself, not
something it leads to: leaking it, changing it without authority, injecting a fault into it, blocking it (denial of
service), escalating privilege through it, or hiding a Trojan trigger in it. If the attack really targets another
element, list that other element instead.

**Be consistent.** Decide by role, not by name. Elements with the same role get the same decision: both pointers of a
pair, every field of one settings register, the in-port and out-port of the same data, each copy of a repeated unit,
and the same kind of element in each entity of the file.

## Reading the map

- Each `PORT` or `SIGNAL` line is one element: `name`, and the `entity` that declares it. A record and each
  `<record>.<field>` are separate elements. An array is one element.
- `storage`: `edge` = register (holds its value between clock edges); `none` = combinational; `mixed` = both;
  `not assigned` = an input, or unused.
- `boundary.drive` on outputs: `driven`; `tied` = only constants; `undriven` = only its fields are assigned.
- `handling` on record fields: `ORIGINATES` (the module creates the value), `CONSUMES` (the module reads it),
  `FORWARDS` (it passes the value on unchanged).
- `configuration`: the element exists or is driven only under a build-time condition. It is still an element; decide
  on its role. `connections`: the element is wired to a port of an instantiated sub-unit.
- Relationship records are stored on both sides: `CARRIES`/`COPIES` exact copy; `SOURCES`/`DERIVES_FROM` computed
  from; `SEQUENCES`/`CLOCKED_BY` clock; `RESETS`/`RESET_BY` reset; `SELECTS`/`SELECTED_BY` case selector or run-time
  index; `GATES`/`GATED_BY` condition or single-bit enable. For any other type, read the cited lines.
- `lines` are the numbers at the start of the RTL lines. The map can miss statements; the RTL is the authority.

## Output

The output file holds one JSON object and nothing else:

```json
{"module": "<the name after MODULE: in the input file>",
 "conceptual_assets": ["<the information or state, and the objective at risk>"],
 "assets": [
   {"element": "<a name exactly as on a PORT or SIGNAL line of the map>",
    "entity": "<the entity on that line>",
    "security_objective": "Confidentiality | Integrity | Availability",
    "reason": "<short: which conceptual asset this element holds or delivers, and the attack on it>"}
 ]}
```

- Do not repeat an element. For `security_objective` write the objective most at risk: Confidentiality for what must
  not leak, Integrity for what must not be altered, Availability for what must not be blocked.
- Before writing, check: every name appears verbatim in the map with that entity; no clock, reset, strobe, handshake,
  intermediate, unused or tied element is listed; elements with the same role were decided alike.
