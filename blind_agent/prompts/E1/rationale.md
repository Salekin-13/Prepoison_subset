# Rationale for prompt E1 (angle: worked examples)

## Core idea

The prompt teaches the executor by worked examples taken from the sources' own case studies on other designs:
a watchdog timer (SA-EDI Annex B), an AES engine (IEEE P3164 white paper and LAsset), an SRAM controller and a
Gaussian noise generator (P3164), and a microcontroller core plus a shared bus (SAIF). Each example shows the
decision for every element an engineer would weigh, including the ones left out, with the reason.

This mirrors how LAsset itself generates assets: few-shot in-context learning with case studies (AES, GPIO,
Gaussian noise generator) "annotated with asset listings and corresponding justifications explaining why some design
elements are security assets and others are not" (LAsset, PDF p. 3-4).

To make the examples transfer to unseen RTL, every decision is labelled with one of a small set of roles: Home,
Door, Status (listed) and Handle, Hallway, Shared interface, Inert, Ordinary setting, Test port (not listed). The
same role words appear in the rules, the examples, the map-reading guide and the final checks, so the executor
applies one vocabulary everywhere. That is the main lever against inconsistent decisions between similar elements.

## Page convention

- LAsset (`2601.02624v2.pdf`): PDF page.
- IEEE P3164 white paper: printed page (equal to PDF page in this file).
- Accellera SA-EDI v1.0: printed page, with the PDF page in brackets (PDF page = printed page + 8).
- Nath & Tan (`2502.04648.pdf`): PDF page.
- SAIF: PDF page of the file.

## Decision rules and their sources

| Rule in the prompt | Source and page | What the source says |
|---|---|---|
| Primary asset = the element that is itself the attacker's target; secondary = elements that help expose it | LAsset p. 2 | "Primary Assets ... serve as the direct target of an attack"; secondary assets "interact with or facilitate the exposure of primary assets", e.g. "system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset". |
| Conceptual vs structural asset | LAsset p. 2; P3164 p. 8 | Conceptual = information tied to use-case flows needing C/I/A; structural = RTL material that physically stores or carries it (registers, buffers, latches). |
| Primary = structural mapping of conceptual assets; elements that influence a primary asset are secondary | LAsset p. 4 | Conceptual assets "mapped to their corresponding structural RTL references ... these are the primary assets"; "internal signals/registers that influence/violate its security objective ... are termed as the secondary assets". This is the basis of [Handle] and [Hallway]. |
| Step B questions (C, I, A, undermined behaviour); "no" to all means not an asset | P3164 p. 9-10 | The four conceptual-analysis questions; "If the answer is 'No' to all ... the element is not an asset". |
| An intended update is not an integrity threat | P3164 p. 22 | DCache replacing data on a store "is expected behavior and should not result in a 'yes'". |
| Override/bypass/test path: the asset is what it overrides, the path is not | P3164 p. 12-13 | GNG: "Addr_OvR" can force a wrong coefficient, "Therefore, Coeff ROM is a conceptual asset"; the override input is not in the asset list (p. 13). GPIO: Direction Select is "the attack point", the mux gates are the assets (p. 12). |
| Step E attack check with the attack classes | LAsset p. 4 | Attack Scenario Analysis over side-channel, fault injection, secure-to-nonsecure leakage, unauthorized access, privilege escalation, hardware Trojan, denial of service; "assets without such scenarios are excluded". |
| Warning against over-listing; default is "not listed" | LAsset p. 4; P3164 p. 16, 19 | "LLMs often lean toward listing a broad set of possible security and non-security assets"; CSA "may end up identifying all the internal blocks ... which could result in false positives". |
| Decide from behaviour, not names | LAsset p. 1; Nath & Tan p. 3 | LAsset criticises a method that "relies heavily on RTL signal and register naming conventions"; Nath & Tan: "simple name matching is insufficient". |
| [Home] key, seed, random-state registers | LAsset p. 2 (Key Register is the primary asset); SAIF p. 1-2 (primary examples: "cryptographic keys, random numbers and seeds"); P3164 p. 13 (LFSR/XOR seed, confidentiality); Nath & Tan p. 4 ("Seed" and "Key" are typical data signals linked to confidentiality) | |
| [Home] register/array holding the payload the module stores, receives or sends | P3164 p. 8 (a buffer that stores the data is a structural asset), p. 17 (SRAM Memory Array is an asset); SA-EDI printed p. 12 [PDF 20] (an asset can be a port, module, register or other object) | |
| [Home] counter that decides a security event | SA-EDI printed p. 24-25 [PDF 32-33] | `wd_timer` (the count) and `wd_assert_timeout` (the timeout register) are the two Asset Definitions; SA-EDI Table 2 printed p. 10 [PDF 18] lists Timers/Counters as "Critical". |
| [Home] register holding a security policy (privilege mode, permissions, authorization) | SAIF p. 1-2 ("configuration bits for operational and privilege modes" listed among primary assets); P3164 p. 9 (Q2: "state or configuration settings that need to be immutable"); SA-EDI Table 2 printed p. 10 [PDF 18] ("Control: FSM, control register") | |
| [Home] for a constant table: the register that first captures the read-out value | P3164 p. 13-14 | The structural asset of the coefficient ROM is its output register `d` (line 51), with its own Asset Definition object; LAsset p. 6 (SHA-3 round constants should be assets because tampering would corrupt the transformation). Constants are not elements (MAP_FORMAT.md). |
| [Door] ports of the outer entity that carry the protected value or event | LAsset p. 5 Table II | For AES-128 the primary structural assets are `key`, `state` and `out`, the ports of the AES top module, while the copies inside one-round, final-round and table-lookup sub-modules are secondary. Nath & Tan p. 1 (primary assets "interact with other IPs in an SoC and communicate with the external peripherals") and p. 5 (Refinement: candidates related to the I/O ports of the TOP module are potential primary assets; Case 1). |
| [Door] interrupt/timeout/reset request outputs, Availability | SA-EDI printed p. 17 [PDF 25] and p. 29 [PDF 37] | The watchdog reset assertion needs Availability: "no gating logic on the watchdog reset". P3164 p. 9 Q3: elements that "could gate an output port" matter for availability. |
| [Door] memory/buffer exception to [Shared interface] | P3164 p. 17 | The memory array is the asset; in a module whose whole content is the payload, the payload ports carry nothing but that content. Reasoning step (mine): this is why the exception exists. |
| [Status] status registers/outputs | LAsset p. 2 Fig. 2 | Status Regs are drawn as a primary asset of the AES engine. P3164 p. 15: "the Status Regs may leak confidential information"; Table 1 (p. 15): status registers report "error codes, state, completion". Nath & Tan p. 3: status signals carry Availability or Integrity. |
| [Handle] clock and reset | Nath & Tan p. 6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI printed p. 25 [PDF 33] (clock and reset appear only as Element ports, i.e. attack points, of the watchdog assets) | |
| [Handle] enables, strobes, addresses, pointers, selectors, overrides | LAsset p. 4 (influencers are secondary); SA-EDI printed p. 14 [PDF 22] §7.4 (Element objects list ports "that can affect and/or observe the behavior of the asset"; these are attack points, not assets); P3164 p. 12 (Direction Select is the attack point) | |
| [Handle] guarding bits (locking bit) | SA-EDI printed p. 26 [PDF 34] | The lock bit appears only as the Condition of the APSO object for `wd_timer`; it has no Asset Definition. Consistent with LAsset p. 4 (influencer = secondary). |
| [Handle] state that restricts access to an asset | SAIF p. 2 Example 2 | "the state of the execution (e.g., boot vs. normal) is the secondary asset which restricts an IP's access to the internal registers". SAIF p. 6: the debug enable is used as a precondition. |
| [Hallway] internal carriers, staging buffers, sub-unit copies | LAsset p. 2 Fig. 2 (Input Buffer, Output Buffer, Enc/Dec Engine are secondary); LAsset p. 5 Table II (per-round copies in sub-modules are secondary); Nath & Tan p. 1 (secondary assets "are mostly internal design components of an IP that help to propagate and handle the primary assets"); SAIF p. 5-6 (state and decode registers that carry program-counter information are the secondary assets) | |
| [Shared interface] generic bus/register-interface fields | LAsset p. 2 ("system buses, peripheral ports" are secondary); SAIF p. 2 Fig. 1 (the system bus and decoder are secondary); SA-EDI printed p. 25 [PDF 33] (`i_wen`, `i_ren`, `i_addr`, `i_data`, `o_data` are Element ports, not assets) | |
| [Inert] tied outputs, unused inputs, constants | LAsset p. 4 (no attack scenario, no mappable CWE: removed); P3164 p. 16 (the hardcoded Debug Values block is the one block that is not an asset); MAP_FORMAT.md (constants, generics, variables are not elements) | |
| [Ordinary setting] configuration that tunes the engine, IV | LAsset p. 2 Fig. 2 | Config Regs and IV Reg are drawn as secondary assets of the AES engine. |
| [Test port] observation outputs | SA-EDI printed p. 14 [PDF 22] (ports that observe the asset are attack points); P3164 p. 7 ("a confidentiality security objective may be violated by a port if it can be used to observe an asset"); P3164 p. 12-13 (the test output Split_Inp is not in the GNG asset list) | |
| Consistency: alternatives and parallel copies get the same decision | P3164 p. 18 | Both SRAM address signals `ZBT_addr` and `ZBT_addr2` get their own Asset Definition, "so it is explicit"; SA-EDI printed p. 13 [PDF 21] §7.2.1: an array is one asset unless a range is named, each range its own object. |
| Names exactly as declared; record field, not whole record | SA-EDI printed p. 12-13 [PDF 20-21] | "The attribute Name ... shall match its corresponding text in the source"; case-sensitive full name (Table 3). Field naming from MAP_FORMAT.md and the brief. |
| Objective choice: Confidentiality for secrets, Integrity for policies/results/counters, Availability for events | SA-EDI Table 2 printed p. 10 [PDF 18] (Secret, Sensitive, Critical); SA-EDI printed p. 16 [PDF 24] (one security objective per APSO object); LAsset p. 5 Table II (objective per primary asset) | |

## Where the examples depart from the source's own decision, and why

The examples are adapted, not copied. Where the source's own decision conflicts with LAsset's primary/secondary
split, I followed LAsset, because the reference list comes from the LAsset study.

- Watchdog: SA-EDI treats `o_wd_reset` as an attack point of the timeout asset (printed p. 29 [PDF 37]). The
  prompt lists it as a door, because LAsset lists boundary ports that carry the asset itself as primary (Table II,
  p. 5) and Nath & Tan root primary assets at the module's I/O ports (p. 1, p. 5).
- AES: P3164 calls almost every block a conceptual asset (p. 15-16). The prompt follows LAsset Fig. 2 (p. 2): key
  and status are primary; config, IV, buffers and engine are secondary. The key, plaintext and result ports are
  listed as doors following LAsset Table II.
- SRAM: P3164 lists the Data-In Register, Output Register and Address Register as conceptual assets (p. 17-18).
  The prompt marks the staging registers as hallways and the address registers as handles, following LAsset p. 4
  (influencers are secondary) and Fig. 2 (buffers are secondary). P3164 itself says the address is an asset only
  "pending on the use case" (p. 17). The payload port is added as a door (memory case).
- Gaussian noise generator: P3164 names the XOR, LFSR, ADDR and Coeff ROM blocks (p. 13). The prompt keeps the LFSR
  state and the coefficient register, treats the combined XOR wire as a hallway and the ADDR logic as a handle (LAsset
  p. 4), and adds the seed inputs and noise output as doors (LAsset Table II, Nath & Tan p. 5).
- Nath & Tan treat 1-bit control inputs and small configuration inputs as asset patterns (p. 3). The prompt treats
  them as handles, following LAsset p. 4 and SA-EDI §7.4. Nath & Tan is used for the status and data patterns and
  for rooting primaries at the I/O ports.

## Why the prompt is shaped this way

- Over-listing is the failure LAsset reports for LLMs (p. 4), so every Do-not-list rule names a concrete RTL shape
  (clock, strobe, pointer, next-value helper, tied output, unused input, shared bus field). The default is "not
  listed" unless a List rule names the role (Step D).
- Under-listing is handled by Step C: every register and every outer-entity port must get an explicit decision.
  The "rejected" array in the analysis makes the executor commit to a role for close calls, which also keeps similar
  elements consistent.
- The map-reading section translates each role into relation types (`GATES`/`SELECTS`/`SEQUENCES`/`RESETS`/
  `CONSTRAINS` = handle; `COPIES`/`DERIVES_FROM` then `CARRIES`/`SOURCES` with storage `none` = hallway; drive
  `tied` = inert). The watchdog example also shows how a home and its handles look in such a map. This uses the map
  as an index and the RTL as the authority, as MAP_FORMAT.md requires.
- `CONSTRAINS` / `CONSTRAINED_BY` are not described in MAP_FORMAT.md, but they occur in the FIFO example input
  (map lines for the comparison at RTL lines 92-94). The prompt explains them as comparison inside a deciding
  condition, so the executor does not stall on them.
- The objective field is not scored, so the guidance is short.

## Compliance with the brief

- No identifier from the processor: no entity, port, signal, field, constant or process name from either design
  file, and not the processor's name. I also avoided ordinary English words that are identifiers in the two design
  files (for example the response/request field names and the FIFO's flag names), and the pronoun that equals one of
  the FIFO's signal names. The only code-font names are from the SA-EDI watchdog (`wd_timer`, `wd_assert_timeout`,
  `o_wd_reset`) plus map keywords and relation types. Other example elements are described in words.
- No numeric quotas or proportions, and no digits anywhere in the prompt. The only count phrase is the
  "one or two sentences" placeholder inside the mandated output contract.
- No instruction to use HDL comments; the prompt says to judge by behaviour.
- Output contract copied verbatim from the brief; the one added key, `analysis`, sits before `assets`, as allowed.
- Self-contained: definitions, method, examples and map guide are all in the prompt.

## How the rules should act on the two example inputs (reasoning, not a measurement)

This is my expectation of the executor's behaviour, written to make the rules checkable; it is not derived from
any reference.

- FIFO input: homes = the memory array and the single-register variant (build-option alternatives, RTL lines 135
  and 150 / 171 and 184, same decision by the consistency rule); doors = the write-in and read-out payload ports
  (buffer case of [Door]); not listed = the read/write strobes and clear input (handles), the pointers and their
  next-value helpers (lines 76-83: handles and hallways), the occupancy flags and count output ([Shared interface]),
  clock and reset.
- Read-only memory input: home = the register that captures the word read out of the constant image (line 48, the
  constant-table rule); door = the response payload field (memory case); not listed = the request fields (handles or
  unused: several have no relationship records), the acknowledge path (line 65, [Shared interface]), the error field
  tied to a constant (line 66, [Inert]), the whole record ports (fields are listed instead), clock and reset.

## What could prove the design wrong, and what to measure after the run

- If the reference lists control inputs (enables, strobes), as Nath & Tan's patterns would, recall drops on
  [Handle]. Measure: the share of missed reference entries whose role is Handle.
- If the reference keeps only internal registers (SA-EDI style), precision drops on [Door]. Measure: precision on
  listed ports versus listed signals, separately.
- The line between [Status] and [Shared interface] (acknowledge, ready/valid, occupancy) is the least certain rule.
  Measure: misses and false listings on handshake-type outputs.
- Staging copies are excluded as hallways; P3164 would include them. Measure: misses on registered copies.
- Report precision and recall separately for each of these role groups, per prompt version, never pooled across
  versions.

## Files read

- E:/jobs/ff/test/Prepoison_subset/blind_agent/TASK_BRIEF.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/MAP_FORMAT.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/design/neorv32_boot_rom.txt
- E:/jobs/ff/test/Prepoison_subset/blind_agent/inputs/design/neorv32_fifo.txt
- E:/jobs/ff/2601.02624v2.pdf (all pages)
- E:/jobs/ff/IEEE_P3164_Asset_Identification.pdf (all pages)
- E:/jobs/ff/Accellera_SA-EDI_Standard_v10.pdf (PDF pages 1-40 and 41-44)
- E:/jobs/ff/2502.04648.pdf (all pages)
- E:/jobs/ff/SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf (all pages)
