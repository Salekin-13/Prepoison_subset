# Primary security assets of one hardware module

You get one input file: a VHDL module whose lines are numbered, followed by a relation map that a static analyser
wrote from that RTL. List the module's **primary security assets** by their declared names. List nothing else.

## What to list

- An **asset** is a value whose confidentiality, integrity or availability must be protected.
- A **conceptual asset** is that value as an idea: a secret, stored data, a setting, the progress of an operation,
  a security decision.
- A **primary asset** is a declared element of this file that *is* a conceptual asset: the place where the value is
  held, or where it enters or leaves the module. An attacker targets it directly. **List these.**
- A **secondary asset** only moves, routes, times, selects, enables or computes part of a primary asset's value. It
  matters only because of the primary asset. **Do not list these.**

## How to decide

### First: find the conceptual assets

Read all of the RTL and say what the module does. Then ask:

- Confidentiality: what information that this module receives, stores or generates could be secret?
- Integrity: what data, setting, mode or state must not be changed by an unauthorized party or at the wrong time?
  Updates that the design intends in normal operation are not a threat.
- Availability: what output or state, if blocked or stuck, stops the module or its users from working?
- Undermined behaviour: can a privileged, debug, test, override or bypass path make the module produce wrong
  results? The elements that path can corrupt are conceptual assets.

Conceptual assets are of these kinds:

- **Data**: what the module stores, receives to process, or returns, including program code and secrets such as
  keys, seeds and random values.
- **Settings**: configuration, mode, privilege, lock and enable values that are written and then kept to govern later
  behaviour.
- **State**: the state of a state machine, a program counter, the read and write pointers of a buffer or memory, and a
  count when counting is the module's own job (the count of a timer, a watchdog, a time limit on transfers, or a clock
  generator).
- **Security decisions and events**: access allowed or denied, a fault or error report, an interrupt request, a timer
  expiry, a reset request, a request to stop the processor for debug. They count where the module produces them, and
  where it receives them and acts on them.

### Second: find the module's boundary

A file can hold several entities. The module's **boundary** is the ports of every entity that no other entity of this
file instantiates. An entity that another entity of this file instantiates is a sub-unit: its ports are internal
wires, never list them; its registers and memories still count as holders. An instance whose entity is not declared in
this file is a sub-unit whose code is elsewhere (the map's `connections` name the instance and its port).

### Third: map each conceptual asset to elements

List:

- **the holder**: the register, memory or array in this file that holds the value. The register that holds the word
  just read from a memory or from a constant table is a holder, not a copy. A sub-unit whose code is elsewhere is not
  a holder in this file;
- **the boundary ports**: each port, or field of a record port, of the boundary through which the value enters or
  leaves the module;
- **the carrier**, only when the value has neither a holder nor a boundary port in this file (it is held in a sub-unit
  whose code is elsewhere): the one signal or field of this file that carries its complete value to or from that
  sub-unit.

If an element's role differs between build options (map `configuration`), decide its role under each option and list
it if it is a primary asset under any of them.

### Fourth: leave out

- **the module's own clock and reset**: inputs whose only map records are `SEQUENCES` (clock) or `RESETS` (reset). A
  reset or debug request that the module acts on in another way is an event (see the kinds above);
- **transport**: a value the module only routes from one of its ports to another (through wires, multiplexers or a
  register slice) without holding it or deciding on it. List nothing for it. The map's `FORWARDS` label marks exact
  copies; it alone does not make an element transport, and its absence does not make an element an asset;
- **transfer control**: request and command strobes (read, write, flush, start pulses), valid and ready, read/write
  direction, write and byte enables, acknowledge, flags that a request raises and its acknowledge or completion
  lowers (outstanding-transfer flags), fill-state flags and fill counts, and addresses or indexes that only pick
  which word moves. A register that holds a command written to this module until the command is carried out is still
  a strobe, even when the command is a reset. A held setting or state of the kinds above is not a strobe, even when it
  gates other logic;
- **pacing counts**: a count inside a transfer or compute engine that only paces its steps (bit position, bit-rate
  divider, iteration count). It times the primary asset; it is not one;
- **intermediates**: next-value signals, partial or derived versions of a listed value, merges of listed values, and
  registers that only delay or duplicate a listed value (pipeline copies, synchronizers, a second register loaded with
  the same value);
- **unused and tied**: ports and fields the module never uses, outputs tied to constants, and whole records whose
  fields carry the values (list those fields instead);
- **non-elements**: constants, generics, loop parameters and process variables. If a constant holds an asset (for
  example a ROM table), list the elements that hold or deliver its value.

### Fifth: keep only direct targets

For each candidate, name a concrete attack whose target is this element itself, not something it leads to: leaking
it, changing it without authority, injecting a fault into it, blocking it (denial of service), escalating privilege
through it, or hiding a Trojan trigger in it. If the attack really targets another element, list that other element
instead.

### Sixth: be consistent

Decide by role, not by name. Elements with the same role get the same decision: both pointers of a pair, every field
of one settings register, the in-port and out-port of the same data, every count of the same kind, every flag of the
same kind, each copy of a repeated unit, and the same kind of element in each entity of the file.

## Reading the map

- Each `PORT` or `SIGNAL` line is one element: `name`, and the `entity` that declares it. A record and each
  `<record>.<field>` are separate elements. An array is one element.
- `storage`: `edge` = register (holds its value between clock edges); `none` = combinational; `mixed` = both;
  `not assigned` = an input, an element driven only by a sub-unit, or unused.
- `boundary.drive` on outputs: `driven`; `tied` = only constants; `undriven` = only its fields are assigned.
- `handling` on record fields: `ORIGINATES` (the module creates the value), `CONSUMES` (the module reads it),
  `FORWARDS` (it passes the value on as an exact copy).
- `configuration`: the element exists or is driven only under a build-time condition. It is still an element.
  `connections`: the element is wired to a port of an instance of a sub-unit.
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
- Before writing, check: every name appears verbatim in the map with that entity; no port of a sub-unit entity is
  listed; no element whose only map records are `SEQUENCES` or `RESETS` is listed; no transport, strobe, handshake,
  held command, pacing count, intermediate, unused or tied element is listed; a carrier is listed only for a value
  with no holder and no boundary port in this file; elements with the same role were decided alike.
