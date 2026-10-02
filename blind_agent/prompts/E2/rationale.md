# Rationale for prompt E2 (angle: worked examples)

## What this revision is, in short

E2 keeps E1's design: one role vocabulary (Home, Door, Status listed; Handle, Hallway, Shared interface, Inert,
Ordinary setting, Test port not listed) taught through worked examples from the sources' own case studies. It changes
four things that made the executor decide the same kind of element in different ways, adds one role (Only holder) for
values that have no home and no door in the module, and adds three source-backed examples (a hidden RNG entropy
source, caches, a core top entity that only wires child units).

## Input to this revision, and one missing input

- The critic report `blind_agent/critic/E1/report.md` did not exist at the path given in the task. The blindness rule
  forbids listing or searching for it, so I did not look elsewhere. Every change below is therefore backed by my own
  reading of the fifteen E1 executor outputs (run `r0`) against the E1 prompt and the RTL of the inputs I opened
  (cpu, debug_dtm, trng, wdt, cpu_cp_cfu, cpu_cp_muldiv; grep views of bus, cache, uart). No critic point is cited
  because there were none to cite.
- I did not use, and did not try to derive, any reference list or score. LAsset Table I (PDF p. 5) prints per-IP
  counts of a "golden" list; I did not use those counts to set or check any rule here.

## Page convention

- LAsset (`2601.02624v2.pdf`): PDF page.
- IEEE P3164 white paper: printed page (equal to the PDF page in this file).
- Accellera SA-EDI v1.0: printed page, with the PDF page in brackets (PDF page = printed page + 8).
- Nath & Tan (`2502.04648.pdf`): PDF page.
- SAIF: PDF page of the file.

## Decision rules and their sources

Every rule in the prompt that decides whether an element is listed, with its basis. Rules new or changed in E2 are
marked (E2).

| Rule in the prompt | Source and page | What the source says |
|---|---|---|
| Primary asset = the element that is itself the attacker's target; secondary = elements that help expose it | LAsset p. 2 | Primary assets "serve as the direct target of an attack"; secondary assets "interact with or facilitate the exposure of primary assets", e.g. "system buses, peripheral ports, and internal signals/registers that carry the data of the primary asset". |
| Conceptual vs structural asset | LAsset p. 2; P3164 p. 8 | Conceptual = information tied to use-case flows needing C/I/A; structural = RTL material that physically stores or carries it. |
| Primary = structural mapping of each conceptual asset, made per module from that module's own elements; influencers are secondary | LAsset p. 4 (text and Algorithm 1, line 5) | Conceptual assets are "mapped to their corresponding structural RTL references, derived from the parsed design elements - these are the primary assets at the module level"; elements that "influence/violate" a primary asset's objective are secondary. Algorithm 1 runs the generation once per module on that module's parsed elements. |
| Step B questions; "no" to all = not an asset | P3164 p. 9-10 | The four conceptual-analysis questions; "If the answer is 'No' to all ... the element is not an asset". |
| An intended update is not an integrity threat | P3164 p. 22 | DCache replacing a value on a store "is expected behavior and should not result in a 'yes'". |
| Override/test/debugger path: the asset is what it overrides | P3164 p. 12-13; P3164 p. 11-12 | GNG: the address-override input can force a wrong coefficient, "Therefore, Coeff ROM is a conceptual asset"; GPIO: Direction Select is "the attack point". |
| (E2) A payload that an interconnect only routes for other units is not this module's asset | SAIF p. 2 Example 1 | The master's sensitive payload is the primary asset; "the bus and the decoder are the secondary supports". |
| Step E attack check with the attack classes | LAsset p. 4 | Attack Scenario Analysis over seven attack classes; "assets without such scenarios are excluded". |
| Default is "not listed"; warning against over-listing | LAsset p. 4; P3164 p. 19 | "LLMs often lean toward listing a broad set of possible security and non-security assets"; CSA "may end up identifying all the internal blocks ... which could result in false positives". |
| Decide from behaviour, not names | LAsset p. 1; Nath & Tan p. 3 | LAsset criticises a method that "relies heavily on RTL signal and register naming conventions"; Nath & Tan: "simple name matching is insufficient". |
| [Home] key, seed, running value of a random generator | LAsset p. 2 (Key Reg is primary); SAIF p. 1-2 (primary examples include "cryptographic keys, random numbers and seeds"); P3164 p. 13 (LFSR and XOR output act as a seed, confidentiality); Nath & Tan p. 4 ("Seed" and "Key" are typical data signals linked to confidentiality) | |
| (E2) [Home] entropy source of a true RNG, even without a port | SA-EDI printed p. 15 [PDF 23] | "An example could be the entropy source of a random number generator (RNG) ... might not be exposed to the integration layer via a port ... However, the asset may still require a security objective (e.g., Integrity)". |
| [Home] memory array whose content the module exists to store | P3164 p. 17 (Memory Array is the asset); SA-EDI printed p. 12 [PDF 20] (an asset can be "a port, module, register, or another object"); SA-EDI Table 2, printed p. 10 [PDF 18] ("Code/Data: Storage") | |
| (E2) [Home] cache contents include tag and validity arrays | P3164 p. 22-23 | For DCache and ICache, the structural assets are "replacement policy, DCache contents, and DCache internal state" (Table 3), objectives confidentiality and availability; "Caches ... can be used as covert/side channels to exfiltrate data". |
| [Home] counter that decides a security event, and the register that raises the event | SA-EDI printed p. 24-25 [PDF 32-33] | `wd_timer` (the count) and `wd_assert_timeout` (the register that raises the timeout) are the two Asset Definitions; SA-EDI Table 2 printed p. 10 [PDF 18] lists "Timers/Counters" as Critical. |
| [Home] security policy and protected bookkeeping (privilege mode, permissions, region bounds, debugger authorization, owner of a shared resource, intact reservation) | SAIF p. 1-2 ("configuration bits for operational and privilege modes" are primary); P3164 p. 9 (Q2: "state or configuration settings that need to be immutable during certain operations or modes"); SA-EDI Table 2 printed p. 10 [PDF 18] ("Control: ... Material used to alter and/or control the state of the IP") | Ownership and reservation records are my application of Q2 (reasoning): they are settings that must not change except through the intended protocol. |
| [Home] first register that captures a constant-table read-out | P3164 p. 13-14 | The structural asset of the coefficient ROM is its output register `d` (line 51), with its own Asset Definition object. Constants are not elements (MAP_FORMAT.md). LAsset p. 6: SHA-3 round constants should be assets. |
| (E2) A register reloaded for every transfer or computation is a hallway, not a home, when its value has a home or a door | LAsset p. 2 (text: "internal signals/registers that carry the data of the primary asset" are secondary; "Encryption/Decryption Engine and the Output Buffer qualify as secondary assets"); LAsset p. 2 Fig. 2 (only Key Reg and Status Regs are marked primary; Input Buffer is not); LAsset p. 5 Table II (for AES-128 the ports `key`, `state`, `out` are primary; the internal round values, including `state (AES-128)`, are secondary) | |
| [Door] key, seed, private payload or operand inputs; the result output | LAsset p. 5 Table II (the AES-128 top-module ports are the primary structural assets); Nath & Tan p. 1 (primary assets "interact with other IPs ... and communicate with the external peripherals") and p. 5 (Refinement, Case 1: a candidate that is an I/O port of the TOP module is a potential primary asset) | |
| (E2) [Door] payload lines of a communication interface, not its clock, select or flow-control lines | Nath & Tan p. 3-4 (Data signals are multi-bit inputs or outputs that carry information and are linked to confidentiality; control signals are a separate pattern); LAsset p. 5 Table II (payload ports primary) | Writes down what the E1 executor already did, so it stays stable now that shift registers are hallways. |
| [Door] memory, cache, queue and key-store case (exception to [Shared interface]) | P3164 p. 17 (the memory array is the asset); LAsset p. 5 Table II (ports that carry the asset itself are primary) | Reasoning: in a module whose whole content is the payload, those ports carry nothing but that content. |
| [Door] interrupt, expiry, stop and reset request outputs | SA-EDI printed p. 17 [PDF 25] and p. 29 [PDF 37] | The watchdog reset needs Availability: "no gating logic on the watchdog reset". P3164 p. 9 Q3: elements that "could gate an output port" matter for availability. |
| [Status] status registers and outputs | LAsset p. 2 Fig. 2 (Status Regs marked primary); P3164 p. 15 ("the Status Regs may leak confidential information"; Table 1: status registers report "error codes, state, completion"); Nath & Tan p. 3 (status signals such as done, ready, error carry Availability or Integrity) | |
| (E2) A bus-response error field is status only when this module raises it from its own check; a copied or merged error is a hallway | Same sources as [Status], plus LAsset p. 2 (elements that only carry another element's value are secondary) | |
| (E2) [Only holder]: a conceptual asset with no home and no door in the module is listed once, at the register where it is formed or first received, else at the signal that carries it out of a child unit whose RTL is absent | LAsset p. 4 (primary assets are taken from each module's own parsed elements; a module with conceptual assets therefore has primary assets); P3164 p. 10 ("The structural assets would be the RTL code that produces 'Data' and stores and transports its value (e.g., reg and wire)"); SA-EDI printed p. 15 [PDF 23] (an asset need not reach a port) | The ordering (home, then door, then only holder) and the exclusions (no shared-interface field, no mix, no derived value) are my reconciliation of LAsset p. 2 (carriers are secondary when a primary exists) with P3164 p. 10 (carriers are structural assets): a carrier is listed only when nothing better exists in the module. This is reasoning, not a quotation. |
| [Handle] clock and reset | Nath & Tan p. 6 ("we did not consider 'Clock' and 'Reset' signals"); SA-EDI printed p. 25-26 [PDF 33-34] (clock and reset appear only as Element ports, i.e. attack points, of the watchdog assets) | |
| (E2) [Handle] interrupt, stop, wake-up and reset request inputs | LAsset p. 4 (elements that influence a primary asset are secondary); SA-EDI printed p. 25-26 [PDF 33-34] (the debugger expiry input and the reset input are Element ports of the watchdog assets, not assets; the asset is the register that raises the event inside the module) | |
| [Handle] enables, strobes, addresses, pointers, selectors, overrides, sequencers | LAsset p. 4 (influencers are secondary); SA-EDI printed p. 14 [PDF 22] §7.4 (Element objects list ports "that can affect and/or observe the behavior of the asset" as access points); P3164 p. 12 (Direction Select is the attack point); SAIF p. 6 and Table II (execution-phase and instruction-phase registers are secondary assets) | |
| [Handle] guarding bits (locking bit) | SA-EDI printed p. 26 [PDF 34] and Table 6 printed p. 16 [PDF 24] | The lock bit appears only as the Condition of the APSO object for `wd_timer` ("a lock bit, which protects the integrity of a register"); it has no Asset Definition. |
| [Handle] phase that restricts access to an asset | SAIF p. 2 Example 2; SAIF p. 6 | "the state of the execution (e.g., boot vs. normal) is the secondary asset which restricts an IP's access"; the debug enable is used as a precondition. |
| [Hallway] wires, helpers, synchronizer and pipeline copies, buffers, round registers, child-unit ports | LAsset p. 2 (text and Fig. 2); LAsset p. 5 Table II (copies in sub-modules are secondary); Nath & Tan p. 1 (secondary assets "help to propagate and handle the primary assets"); SAIF p. 5-6 (registers that carry program-counter information are secondary) | |
| (E2) [Hallway] combining and debiasing logic after an entropy source | P3164 p. 13 and LAsset p. 2 as applied in E1's GNG example (the combined random-value wire is a hallway) | P3164 itself names the XOR block a conceptual asset (p. 13). E1 and E2 follow LAsset's "carriers are secondary" here. |
| [Shared interface] general bus or register interface fields | LAsset p. 2 ("system buses, peripheral ports" are secondary); SAIF p. 2 Fig. 1 (system bus and decoder are secondary); SA-EDI printed p. 25 [PDF 33] (`i_wen`, `i_ren`, `i_addr`, `i_data`, `o_data` are Element ports, not assets) | |
| (E2) [Shared interface] also when this module issues the accesses, and for control-register read-back | Same sources: LAsset p. 2 names "system buses" without regard to direction; P3164 p. 20 shows a core's instruction and value ports as the interface where conceptual assets enter, while its structural assets are inside (p. 22-23) | |
| [Inert] tied outputs, unused inputs, whole records, constants | LAsset p. 4 (no attack scenario: removed); P3164 p. 16 (the hardcoded Debug Values block is the one AES block that is not an asset); MAP_FORMAT.md (constants, generics, variables are not elements) | |
| [Ordinary setting] configuration that tunes the function, IV | LAsset p. 2 Fig. 2 (Config Regs and IV Reg are not marked primary) | |
| (E2) [Ordinary setting] period, threshold or reload value of a timer or watchdog, even when locked | SA-EDI printed p. 23-25 [PDF 31-33] | REG_COUNT_LOW and REG_COUNT_HIGH hold "the initial value of the timer" and are frozen by the lock bit; Step #2 defines only `wd_timer` and `wd_assert_timeout` as assets. |
| [Test port] observation and debugger ports, never a door | SA-EDI printed p. 14 [PDF 22] (ports that observe the asset are access points); P3164 p. 7 (a port that can observe an asset violates confidentiality as an attack surface); P3164 p. 12-13 (the test output Split_Inp is not in the GNG asset list); SAIF p. 5 (the debug access port is an untrusted observable point) | |
| Consistency: alternatives and parallel copies get the same decision | P3164 p. 18 | Both SRAM address signals get their own Asset Definition, "so it is explicit"; SA-EDI printed p. 13 [PDF 21] §7.2.1: an array is one asset unless a range is named. |
| (E2) An element that plays a listed role under any build option is listed | Same as above, plus P3164 p. 13-14 (the constant-capture register is an asset) | Reasoning: the reference is one list per module, not per build option. |
| Names exactly as declared; record field, not whole record | SA-EDI printed p. 12-13 [PDF 20-21] | "The attribute Name ... shall match its corresponding text in the source"; case-sensitive (Table 3). Field naming from MAP_FORMAT.md and the brief. |
| Objective choice | SA-EDI Table 2 printed p. 10 [PDF 18]; SA-EDI Table 6 printed p. 16 [PDF 24] (one objective per APSO object); LAsset p. 5 Table II | |

## Worked examples: where each comes from and where E2 departs from the source

- Watchdog: SA-EDI Annex B, printed p. 22-30 [PDF 30-38]. E2 adds the row for the reload-value registers, which the
  source describes (printed p. 24 [PDF 32]) and gives no Asset Definition. `o_wd_reset` stays a door, following LAsset
  Table II and Nath & Tan p. 5, although SA-EDI treats it as an attack point of the timeout asset (printed p. 29
  [PDF 37]).
- AES: P3164 p. 14-16 and LAsset p. 2 Fig. 2, p. 5 Table II. P3164 calls almost every block a conceptual asset
  (p. 16). E2 follows LAsset: key register and status are primary, buffers and round values are secondary, and the
  key, plaintext and result ports are primary (Table II). E2 adds an explicit row for the cipher core's round
  registers.
- SRAM: P3164 p. 16-18. P3164 lists the Data-In, Output and Address registers as conceptual assets. E2, like E1,
  marks the staging registers as hallways and the address registers as handles (LAsset p. 2, p. 4), and P3164 itself
  says the address is an asset only "pending on the use case" (p. 17).
- Gaussian noise generator: P3164 p. 12-14. Same departure as E1 (XOR wire and ADDR logic not listed).
- True random generator (E2): SA-EDI printed p. 15 [PDF 23] supplies the entropy-source decision. The rows for the
  output register (SAIF p. 1-2: random numbers are primary), the combining logic (hallway, as in the GNG example) and
  the enabling input (handle) are my application of the other rules, not quotations.
- Processor core, caches and shared bus: SAIF p. 2 and p. 5-6 (program counter, debug port, debug enable, boot
  phase, shared bus), P3164 p. 22-23 (register file, caches). The cache row is new in E2.
- Core top entity that only wires child units (E2): a reasoning example. It applies the core rows above (register
  file, program counter, privilege mode from SAIF and P3164) and the [Only holder] rule to a top entity whose child
  units are not in the file. No source analyses such a wrapper; the basis is the per-module mapping of LAsset p. 4 and
  P3164 p. 10.

## Change log

Each change, the evidence behind it, and what it breaks.

1. **Transient registers are hallways, not homes (E1 [Home] bullet "payload the module exists to store, receive or
   send" narrowed to "store").**
   Evidence: E1 contradicted itself. Its [Home] bullet made a register that holds a received or sent payload a home,
   while its AES example made the input and output buffers hallways. The executor followed one side in some modules
   and the other side in others: `neorv32_cpu_cp_cfu` rejected its result register as an output buffer by analogy to
   the AES example, while `neorv32_cpu_cp_muldiv` listed its product, quotient and remainder registers as homes and
   `neorv32_uart`, `neorv32_spi`, `neorv32_twi` listed their transfer shift registers as homes. I resolved it towards
   LAsset (Fig. 2 and Table II), because the reference comes from the LAsset study.
   Breaks: comparability with E1 on muldiv, uart, spi and twi (those registers should now drop out).

2. **New role [Only holder].**
   Evidence: `neorv32_cpu` (a top entity with no registers whose child units are not in the file) listed only its
   interrupt request inputs; its own analysis names the register file, privilege mode and program counter as
   conceptual assets "not in this entity". E1 gave no way to map a conceptual asset whose home is absent, so the
   executor listed the only inputs a List rule seemed to allow. The rule also keeps change 1 from losing values that
   have no other representation in the module: the debugger command assembled in `neorv32_debug_dtm`, the
   atomic-operation result in `neorv32_bus`, and the random output word in `neorv32_trng`.
   Breaks: the cpu list changes completely.

3. **Request inputs are handles everywhere.**
   Evidence: `neorv32_cpu` listed its interrupt request inputs as doors (E1's [Door] rule names only outputs) and in
   the same output rejected its debugger stop request input as a handle; `neorv32_sys` rejected its reset request
   inputs as handles. Same role, three decisions.

4. **Timer and watchdog period, threshold and reload values are ordinary settings, even when a locking bit freezes
   them; the watchdog example now says so.**
   Evidence: `neorv32_wdt` listed its threshold field as a home "protected by the lock bit" while rejecting the
   enabling bit that the same locking bit freezes. SA-EDI's own watchdog defines no asset for its lock-frozen
   initial-count registers (printed p. 24-25 [PDF 32-33]).

5. **[Shared interface] covers request ports this module issues and control-register read-back; [Test port] covers
   every line of a debugger access port and is never a door.**
   Evidence: `neorv32_debug_dtm` (request record to the debug side), `neorv32_cpu` (bus records) and
   `neorv32_cpu_pmp` (control-register read-back) were all decided as shared interface, but E1's text described only
   the target side. Writing it down keeps those decisions stable. The [Test port] sentence prevents the new
   payload-lines bullet of [Door] from capturing a debugger's serial lines.

6. **Error field of a bus response: status only when this module raises it from its own check.**
   Evidence: `neorv32_bus` listed the gateway's response error field (driven by its own expiry register) while
   rejecting error fields that are passed through from other units, and `neorv32_cache` rejected its accumulated
   downstream error. The decisions were consistent, but E1 had no text for them.

7. **Cache tag and validity arrays are homes.**
   Evidence: `neorv32_cache` rejected its tag array as an address store and its validity bits as guarding bits.
   P3164 Table 3 (p. 22-23) lists cache contents and internal state as structural assets.

8. **Entropy source of a true RNG is a home; new example.**
   Evidence: `neorv32_trng` listed only the output assembly register and rejected every element of the entropy cells
   as a handle or a hallway. SA-EDI names the RNG entropy source as an asset without a port (printed p. 15
   [PDF 23]).

9. **[Door] bullets for operand inputs, payload lines of a communication interface, and a key store reached through
   its own access port.**
   Evidence: the executor already decided these as doors (`neorv32_cpu_cp_muldiv`, `neorv32_uart`, `neorv32_spi`,
   `neorv32_twi`, `neorv32_cpu_cp_cfu`). Written down so the decisions hold after change 1.

10. **Build options: an element with a listed role under any option is listed.**
    Evidence: `neorv32_imem` listed its read register because it captures the ROM image in one build option; E1's
    text covered only alternatives that are different elements.

11. **Method order and final checks.** Step C now maps each conceptual asset in the order home, door, only holder.
    A final check asks that every conceptual asset of the module appears in the list or that the analysis explains
    why not, and the `conceptual_assets` strings now name where each asset is listed. This makes a missing mapping
    visible in the output, which change 2 needs.

12. **Wording.** I replaced ordinary words that are also identifiers in the tuning inputs or the design files (for
    example the cipher block's "engine", "sub-unit", "start", "enable" as a noun, "level", "bypass", "timeout" in
    prose) with synonyms. E1 used several of these and was accepted, so this is caution, not a fix of a known failure.

Kept from E1, because the outputs show them working: the role vocabulary, the attack check, the name rules (no
naming error found in the fifteen outputs), the sub-unit-port hallway rule, the constant-table rule, the
shared-interface exclusion, the inert rule, the parallel-copy rule (byte-lane arrays were decided together in cache
and imem), and the output contract.

## How E2 should act on the tuning modules (reasoning, not a measurement)

This is my expectation, written so the next run can be checked against it. It is not derived from any reference.

- muldiv: operand inputs and the result output listed; product, quotient and remainder registers become hallways.
- uart, spi, twi: payload lines, interrupt outputs and the overrun flag stay; transfer shift registers drop.
- cpu_cp_cfu: unchanged (key array, its access-port payload, operand inputs, result output).
- wdt: the threshold field drops; counter, the two reset-raising registers, the reset output and the reset-cause
  register stay.
- cache: tag and validity arrays are added.
- trng: one or more entropy-cell elements may be added next to the output assembly register.
- cpu: interrupt inputs drop; register-file read signals, the program-counter field, the privilege field and the
  access-violation wire should appear as only holders.
- debug_dtm, bus, pmp, imem, hwspinlock, sys: little or no change.

## What could prove E2 wrong, and what to read after the next run

- Change 1 is the largest bet. If the reference lists transfer shift registers and computation working registers,
  recall drops on uart, spi, twi and muldiv. Read: per module, which E1-listed elements E2 dropped, and whether they
  were reference entries. Report precision and recall separately for the dropped group and the kept group.
- Change 2 could over-list in a wrapper. Read: precision on elements decided as [Only holder], separately from homes
  and doors.
- Change 3: if the reference lists request inputs (Nath & Tan's control-signal pattern, p. 3), recall drops on cpu.
  Read: misses whose role in E2's analysis is Handle and whose port mode is `in`.
- Change 4: if the reference lists lock-frozen thresholds (P3164 Q2 reading), recall drops on wdt. Read the wdt miss
  list.
- Changes 7 and 8 add elements in two modules. Read precision on cache and trng separately.
- Never pool E1 and E2 results in one metric; they come from different prompt versions and write to different run
  directories.

## Compliance with the brief

- No identifier from the processor: no entity, port, signal, field, constant or process name from the design files
  or tuning inputs, and not the processor's name. I checked the prompt for the field names of the design files'
  request and response records, the queue's signal names, and plain-word identifiers seen in the tuning inputs. The
  only code-font names are SA-EDI's `wd_timer`, `wd_assert_timeout`, `o_wd_reset`, plus map keywords and relation
  types.
- No numeric quotas or proportions, and no digits in the prompt. The only count phrase is "one or two sentences"
  inside the mandated output contract.
- No instruction to use HDL comments; the prompt says to judge by behaviour.
- Output contract copied verbatim from the brief; the one added key, `analysis`, sits before `assets`.
- Self-contained: definitions, method, examples and map guide are all in the prompt.

## Files read for this revision

- E:/jobs/ff/test/Prepoison_subset/blind_agent/TASK_BRIEF.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/MAP_FORMAT.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/prompts/E1/prompt.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/prompts/E1/rationale.md
- E:/jobs/ff/test/Prepoison_subset/blind_agent/critic/E1/report.md (not present)
- The fifteen E1 outputs under E:/jobs/ff/test/Prepoison_subset/blind_agent/runs/tuning/E1/r0/
- Inputs: design/neorv32_boot_rom.txt, design/neorv32_fifo.txt (RTL part), tuning/neorv32_debug_dtm.txt,
  tuning/neorv32_cpu.txt, tuning/neorv32_trng.txt (RTL and start of map), and the RTL lines of tuning/neorv32_wdt.txt,
  tuning/neorv32_cpu_cp_cfu.txt, tuning/neorv32_cpu_cp_muldiv.txt; selected RTL lines of tuning/neorv32_bus.txt,
  tuning/neorv32_cache.txt, tuning/neorv32_uart.txt
- E:/jobs/ff/2601.02624v2.pdf (all pages)
- E:/jobs/ff/IEEE_P3164_Asset_Identification.pdf (all pages)
- E:/jobs/ff/Accellera_SA-EDI_Standard_v10.pdf (PDF pages 16-44)
- E:/jobs/ff/2502.04648.pdf (all pages)
- E:/jobs/ff/SAIF_Automated_Asset_Identification_for_Security_Verification_at_the_Register_Transfer_Level.pdf (all pages)
