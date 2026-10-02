# Critique of the external review, and a strategy for meta v4

**Setup.** Scoring used 15 modules and 111 ground-truth (GT) entries; that denominator is exact. Matching is strict. Precision (P) is TP divided by the number of elements reported. Recall (R) is TP divided by 111.
- The baseline v2x3r8 is 3 repeats of one prompt.
- v1, v2 and v3 each have 3 meta samples, with **one executor run per sample**. So every meta comparison is 3 runs against 3 runs. The smallest exact permutation p that design can produce is 0.10.

**Reproduction.** Every number below was re-derived in this task. The scripts are in `critique/report/`. The three evidence analyses were re-run from copies (`rerun_v3/`, `rerun_ce/`, `rerun_ta/`), and all their self-tests passed. My own script `verify.py` passed three self-tests:
- meta_tools.selftest;
- 12 hand-read RTL lines;
- the record fields of bus_req_t (package:121) and bus_rsp_t (package:154).

**Labels.** MEASURED means computed from code or read from a file. REASONING means argument.

---

## A. Overall assessment of the SoC security engineer's evaluation

**Short answer.** The review is sound on method and weak on the text. Its methodological points hold: benchmark agreement is not validity (E2), a rule's origin can leak labels into the prompt (E19), output-validity checks should be mechanical (E13), and the held-out set needs protecting (E24). Its concrete rewrites (E8, E12, E10, E18) either cost ground-truth entries on this corpus or recover none.

- **Tally (MEASURED against the evidence, REASONING for the judgement).** 7 claims are Supported, 4 Mostly supported, 12 Partially supported, 3 Uncertain, 0 Unsupported, and 3 Contradicted by the evidence.
- **Wrong target (MEASURED, text).** 7 of 29 claims aim at text that is not in meta v2 or v3, or misread it:
  - E4 and E29 misread v3.
  - E9 asks for something v3 already has.
  - E11's F4 to F6 are in no meta prompt, and the review calls F6 the "reset network", which it is not.
  - E12's F7 is in no meta prompt.
  - E14 and E15 quote the roadmap page (`scratchpad/roadmap/apply_1b.py:34`) and older prompts.
- **The main misreading (MEASURED).** The review says v3 "calls every security attribute a conceptual asset". The v3 text says the opposite: `meta_prompt_v3.txt:16` "When this block decides on such an attribute, … that access-control decision is a conceptual asset." The phrase "is a conceptual asset" occurs once in the file, in that sentence.
- **What the review missed: v3's actual failure (MEASURED; the mechanism is REASONING).**
  - v3 brought back whole transaction ports. False positives (FP) of this kind: v2 0/0/1 rows per run, v3 8/2/6.
  - Of the 19 (concept, port) pairs behind them, 15 are input ports labelled "sets". 14 of those 15 name, in the same concept, an internal element that already holds the decision.
  - So most of them are not uses of the "port, named whole" fallback. They follow the input-port rule, now that v3 no longer excludes transaction ports inside that rule.
  - None of the 19 concepts mentions a privilege, debug or source attribute.
- **v2 against v3 overall (MEASURED).** They cannot be told apart on P or R. Exact permutation p is 0.6 for P (0.7 when computed on 3-decimal values) and 0.3 for R. The ranges overlap.
- **The ground truth encodes conventions (MEASURED).** 0 of 112 transaction-typed ports are GT. 0 of 36 clock or reset inputs are GT. All 9 interrupt request lines are GT, and 0 of 9 mask bits. So some cheap benchmark gains are label conventions. This supports E2 and E19.
- **Strategy (REASONING).** Meta v4a is v3 with two changes: the transaction-port exclusion goes back into the input-port rule, and the whole-port fallback is removed. Everything else is conditional on its own screen.

---

## B. Claim-by-claim validity assessment

Q1 means "does the rule improve agreement with this benchmark's GT". Q2 means "is the rule semantically valid for arbitrary RTL". Line references are to `meta_prompt_v3.txt` unless another file is named.

| id | claim (short) | evidence (MEASURED unless marked) | classification | reasoning | implication for prompt engineering |
|---|---|---|---|---|---|
| E1 | CWE is a weakness catalogue, not an asset ontology | v3 cites CWE only as "the concern of CWE-1302…" (:16) and "security concerns: CWE-1206" (:13). GT rows carry CWE lists; for example pmp ctrl_i has "1191, 1220" | Supported | Meta v3 already uses CWE as a concern, not as a definition | No change needed |
| E2 | Q1 is not Q2 | The reset exception gave 0 TP and 0/3/2 FP in v3, because 0 of 36 clock/reset inputs are GT. 0 of 112 transaction ports are GT. Interrupt requests 9/9 GT, masks 0/9 | Supported | Some rules are cheap on Q1 because of GT conventions. One rule motivated by Q2 costs Q1 | Tag every rule with where it came from. Report the Q1 cost of each Q2 rule |
| E3 | Original F1 too broad against CWE-1302/1311/1317/1318; "name ports whole" is defensible | Under v2's broad F1 the attribute-decision holders were still reported: acc_priv 3/3 runs, fault_o 3/3, ctrl.buf_dir 1/3. Port-field FP: v1 46/22/30, v2 0/0/0, v3 0/0/0. A grep finds 3 attribute-decision sites and each has a declared holder (cache.vhd:172-173, pmp.vhd:245, pmp.vhd:363) | Partially supported / requires qualification | The breadth worry needs a decision held only in the container. That case is absent from this corpus. "Name ports whole" is supported, but v1→v2 changed 4 rules at once | Keep "a port is a single candidate" |
| E4 | v3 "calls every security attribute a conceptual asset"; proposes attribute → decision → resource | Text of :16 quoted above. No v2 or v3 run reported any field of a port (0 in all 6). The fetched CWE-1302 page summary does use an AES key-access register and a security identifier | Contradicted by the evidence (as a reading of v3) | The proposed ontology is what v3 already says for the decision. The real residue is that the fallback reports the container | Leave the attribute wording. Remove the container fallback (F-2) |
| E5 | No rule attributes a decision that exists only as a condition or expression | Concepts with an empty structural list: 0–2 per run, out of 79–128 concepts. Corpus anchor: imem.vhd:178 `bus_rsp_o.ack <= bus_req_i.stb and (not bus_req_i.rw);`. v2 s0 left that concept empty; v3 reported bus_rsp_o in 3/3 runs, all FP. Line :43 already makes expressions "evidence about declared elements" | Partially supported / requires qualification | The gap is real but small. On this corpus it appears only for decisions whose result reaches only a transaction output | State that case explicitly: keep the concept, leave its list empty (F-2) |
| E6 | Proposed F1 wording: no container asset; report the declared candidate "when one exists" | E6 drops the port fallback, which matches the evidence. "Grouped interface element" would also cover pmp ctrl_i (type ctrl_bus_t, not a transaction record), which is GT | Partially supported / requires qualification | "When one exists" leaves E5 open. The broader scope risks a GT entry | Adopt the container sentence. Keep the scope at transaction records |
| E7 | "an input port … is where that value is set" is wrong; it receives | :13 already says "enters the entity"; :14 says "is where that value is set". The schema enum forces "sets" (:93). The validator's REAL set also holds it. The scorer ignores realization | Mostly supported | The two FIXED sentences disagree in wording. P and R cannot move | Align :14 with :13 and keep the enum (F-6, conditional) |
| E8 | Gate input ports; not primary "merely because it enters" | 26 of 134 input ports are GT. Their objectives: Integrity 22, Availability 4, Confidentiality 0. Oracle removal under three readings of E8 lowers the recall ceiling by 0.090, 0.162 or 0.189 (10, 18 or 21 GT inputs). P falls or stays level in all 12 runs; v2 s0 goes from P .380 / R .829 to .356 / .712 under the strict reading. The GT's reasons are generic, e.g. cfu rs1_i: "does carry operand that directly affects result". v1's generated sentences resembled E8, and v1 found 5/4/1 of 26 GT inputs (confounded) | Contradicted by the evidence (on this benchmark) | Meta v2 and v3 already gate inputs: the input must be read to store, compute or decide, and must belong to an Established concept. The confidentiality sub-point agrees with the GT | Do not add the gate |
| E9 | Restore the clock/reset exception | Already in v3 (:13). v3 reported 0/3/2 reset inputs, all FP; v2 0/0/0. The GT has 0 of 36 clock/reset inputs | Partially supported / requires qualification | Wrong target. Plausible on Q2. Costs at most 3 FP per run on Q1 | Keep v3's exception by default. The GT policy on reset is the user's decision |
| E10 | F3 is too narrow (a key passed to a child) | 65 sub-block connection fields, 4 GT. E10's wording recovers 0 missed GT entries (FN). 13 data-carrying fields that F3 drops are all non-GT, including trng fifo.wdata (trng.vhd:139). An opaque child exists: trng.vhd:145 `rnd_pool_fifo_inst: entity neorv32.neorv32_fifo` is defined in another file | Partially supported / requires qualification | This is a secondary-asset concern. Line :15 defers secondary assets to a connectivity stage | Keep F3. Send E10 to the connectivity stage |
| E11 | F4/F5/F6 must not be generalised | "tick", "interrupt" and "mask" each occur 0 times in meta v1–v3. F6 in `error_analysis_screen1.md:407` is protocol-variant configuration bits; the reset network is in that file's rejected list. Requests 9/9 GT, masks 0/9 | Mostly supported | The principle is right. The targets are not in the meta prompt, and one is mislabelled | Keep F4–F6 out. Mark them as benchmark-derived |
| E12 | F7 (unchanged copy) is sound canonicalisation | 19 strict copy pairs inside one module touch the GT: both ends GT 3, only the copy 7, only the source 9. Oracle "omit the copy": TP −4 to −9 per run, and P falls in 12 of 12 runs. `flatten()` emits every listed element (meta_tools.py:138-152). The FIXED exit-port clause is at :13. The earlier F7 said "report the port", the opposite direction | Contradicted by the evidence | The GT has no canonical side. "Link, don't emit" cannot be expressed in this schema | Do not incorporate |
| E13 | F13 and F14 are output-validity controls | f13_filter changes FP by 0 to −6 per run and P by +0.000 to +0.006. F14 is schema text (:91) | Supported | — | Keep F13 in code and report it separately |
| E14 | "C is rare and does not spread" is too strong | The phrase is in no meta prompt. The GT has 3 Confidentiality entries (key_mem, jtag_tdo_o, trng data_o). The baseline reported the propagations csr_rdata_o, fifo.wdata, fifo.rdata and dmi_ctrl.rdata in 3/3 runs, labelled Confidentiality; all are non-GT | Partially supported / requires qualification | Fair on Q2. Moot for v2 and v3. Would add FP here | No meta change |
| E15 | One objective per asset is a schema limitation | 15 of 113 raw GT rows list two objectives (all Integrity plus Availability). twi_sda_i is listed twice. The FIXED schema allows one objective per concept. The scorer ignores objectives for P and R | Supported | True, but it has no effect on P or R | Evaluation note only |
| E16 | Classify Asset/Control/Carrier/Exposure/Ordinary before deciding primary | v3 already defines carrier, transport, exit port and decision. v3 exec s1 and s2 added a role pass nobody asked for. Nothing measured | Uncertain | "Exposure as non-primary" conflicts with the exit-port clause (:13) | Conditional A/B test with an internal role pass (F-5) |
| E17 | An interface can be location, carrier, access path, boundary or exposure | The FIXED text gives ports roles: entry ("sets"), exit port, transport, carrier. The CWE pages were not checked | Mostly supported | Already reflected in v3 | None |
| E18 | Redefine primary as "directly embodies" | 'exit port' TP: v2 18–20 per run, v3 14–17. 7 GT pairs keep only the copy, e.g. trng.vhd:366 `data_o <= sample_sreg` (GT, Confidentiality). "Context-dependent" already exists (:22) | Partially supported / requires qualification | "Directly embodies" is harder to check than stores/sets/computes/exit. The new secondary wording would demote GT exit copies | Do not incorporate as written |
| E19 | Leakage taxonomy: structural, architecture-class, benchmark-label priors | The label conventions are listed under E2. The earlier analysis marks F4 "hand role set" and F6 "test-specific heuristic" | Supported | — | Tag each rule's provenance in the ablation log, not in the prompt |
| E20 | Use decision rules instead of exclusions | v3's rules are already in exception form. The v3 exception was over-applied: 19 pairs, 0 about an attribute | Partially supported / requires qualification | Each branch licenses a new path, and each path needs a checkable test | Keep exceptions few and syntactic |
| E21 | Pipeline: elements → roles → concepts → representation → objective → evidence | FIXED stage order (:71). :54 "never starts by labeling individual signals as assets" | Uncertain | Roles fit inside "derive relationships" (§2 is OPEN). Untested | F-5 (conditional) |
| E22 | "Security-relevant" is broader than "asset" (CWE-1220) | The fetched CWE-1220 summary separates key registers from key read/write policy registers. The GT includes the pmp policy registers pmpcfg and pmpaddr. :12 includes configuration and decisions | Partially supported / requires qualification | True in CWE. Narrowing would contradict the GT scheme and the FIXED definition | Do not narrow |
| E23 | Blacklists will hit TPs; fix the ontology instead | Shared-role region: 215 of 675 baseline FP (0.319), with 224 TP, so P inside is 0.510. Identical-definition groups with mixed labels explain 1–3 FP per run. A hand-judged same-role GT counterpart exists for between 59 (0.27, strict) and 176 (0.81, strict plus loose) of the 215 rows | Partially supported / requires qualification | Blacklists cost TP about one for one: supported. "Fix the ontology" is untested, and same-role label splits cap any role-level rule | No role blacklists. Handle the GT issues separately |
| E24 | Prompts are clean; the held-out set is contaminated | check_prompt / check_exec_prompt pass for 3 meta and 9 exec prompts. I did not verify the "two conventions". This critique's own verify.py read all 41 GT modules (objectives count; a name-pattern check) | Mostly supported | The contamination risk is real, as this task shows | Freeze an untouched set and log every read of held-out labels |
| E25 | Keep VHDL wording while tooling is VHDL | F3 says "if, case or when" (:17). Comment stripping runs with vhdl=True | Supported | — | No change |
| E26 | Preserve context-dependent candidates | FIXED §8 (:68): they "are decided during the analysis and are not reported". Exec prompts forbid uncertainty fields. `flatten()` reads only the related structural assets | Partially supported / requires qualification | Sound on Q2. In the scored list it adds FP. It needs a separate unscored field plus schema and validator changes | Evaluation-protocol change, later |
| E27 | Four rule layers | F13 is code; F14 is schema | Uncertain | A documentation choice with no behavioural test | Use it in the design doc, not in the prompt |
| E28 | Analyse what the RTL does with a debug field | cache.vhd:172-173 sets `ctrl_nxt.buf_dir` on `host_req_i.debug`. The holder ctrl.buf_dir was reported in baseline 3/3, v1 1/3, v2 1/3, v3 2/3 runs, always scored FP. No run reported a .debug, .priv or .src field. The GT names `cache_o.cmd_dir`, which does not exist in the RTL; only a whole `cache_o` prediction could match it | Supported | The executor already follows this principle. The GT cannot credit it | Fix the GT, not the prompt |
| E29 | Don't freeze v3 F1; rewrite "attribute … is a conceptual asset" | The quoted sentence does not exist. v3 F1 coincided with whole transaction-port FP rows of 8/2/6 against v2's 0/0/1 | Partially supported / requires qualification | Right not to freeze it, but for the wrong reason. The container half of the rewrite matches the evidence | F-1 to F-3 |

---

## C. Validated failure patterns

Each row separates observation (MEASURED), pattern, and proposed mechanism (REASONING).

| # | observation (MEASURED) | pattern | proposed mechanism (REASONING) | cause class | evidence strength |
|---|---|---|---|---|---|
| C1 | Whole transaction ports reported in v3: FP rows 8/2/6 (v2 0/0/1; p = 0.10, the floor). Distinct names 7/2/6. There are 19 pairs: 15 inputs labelled "sets" (7/0/8) and 4 outputs labelled "exit port". 16 of 19 name an internal element in the same concept, and 0 of 19 mention an attribute. 0 of 112 transaction ports are GT | An exclusion was moved out of the rule it limits, so the container comes back through that rule | v3 replaced v2's in-rule exclusion (v2:13 "…and ports whose record type carries complete bus transactions, are not structural references in this way") with a pointer (:13 "…is governed by the Transport definition instead"). The exec-prompt restatements of "sets" follow the counts: s0 L227 "…or the permitted whole-transaction-port case" (7 pairs); s1 L212 "Use "sets" for a non-transport input…" (0); s2 L191 "Use "sets" for an input consumed by its declaring entity…", with no transport clause (8) | conflicting instructions; imprecise criterion | High for the counts. Medium for the mechanism (an association across 3 samples) |
| C2 | The fallback path: imem bus_rsp_o in 3/3 v3 runs, as the "acknowledge decision". imem.vhd:176 `rden <= bus_req_i.stb and (not bus_req_i.rw);` and :178 `bus_rsp_o.ack <= …` hold the same decision. In s0, rden was replaced by bus_rsp_o. imem TP: v2 3/3/3, v3 2/2/2 | The absence test ("with no internal element holding it") was not followed | The model cannot check an absence reliably. "Route an access" (:16) widens "decision" | imprecise criterion; execution-model limitation | Medium (one module) |
| C3 | Record fields rw, amo, amoop, lock, fence and err are in neither v3 class (not payload, not attribute). The record is declared only in the package (package:121, :154), which the executor never receives | The executor classifies fields from names alone. Its concepts cover lock (bus.vhd:111), AMO and fence | Unclassified fields invite "decision" readings | ambiguous RTL; poor intermediate representation | Medium |
| C4 | Reset inputs reported under v3: 0/3/2, all sys rstn_*. The reports comply with the text. The GT has 0 of 36 clock/reset inputs | A rule motivated by Q2 costs Q1 | — | GT labelling limitation | High |
| C5 | The correct bypass decision ctrl.buf_dir is scored FP in every run that reports it | A correct element cannot score | The GT names a non-existent `cache_o.cmd_dir`; also `inval_i` is not declared | GT labelling limitation | High |
| C6 | v3 found 17/9/9 of 26 GT input ports with the same rule text in every sample. Exec prompts share only 0.11–0.18 of their lines. Predicted-set Jaccard similarity is about the same within a version as across versions | Behaviour varies within a version | Meta resampling and executor sampling. The rule wording does not explain it | execution-model limitation | High that it exists; mechanism unknown |
| C7 | Connection fields dropped by F3 are still reported in every v2 and v3 run: 11–19 per run depending on how a plain copy is counted, against 16–29 in the baseline | Partial compliance with the carrier rule | The syntactic exception is applied loosely | imprecise criterion; execution-model limitation | Medium (the count depends on the copy definition) |
| C8 | v1 reported 46/22/30 port fields; v2 and v3 report 0 | Fields of ports treated as candidates | Fixed by "a port is a single candidate" | poor intermediate representation (v1) | High for the counts; attribution confounded |
| C9 | Shared-role FP (see E23) | Same-role elements carry split labels | — | GT labelling limitation (in part); imprecise criterion | Medium (hand labels; see D3) |
| C10 | v3 missed clock-enable outputs: s0 spi and uart clkgen_en_o, s1 sys clk_en_o. v2 found all four in 3/3 runs | A clock rule may spread to outputs | The v3 clock/reset wording may be read as covering outputs | conflicting instructions (?) | Low |
| C11 | Decisions whose result reaches only a transaction output (imem.vhd:178) | No declared non-transport holder exists | v2 left the concept empty (s0); v3 used the port | missing stage / imprecise criterion | Medium; rare (0–2 empty concepts per run) |

---

## D. Questionable or unsupported diagnoses

**D1. The review's own diagnoses.**
- E4 and E29 misread v3 (see B).
- E8, E12 and E18 are contradicted on this benchmark.
- E9, E11, E14 and E15 aim at text that is not in v2 or v3.
- E23's cure ("fix the ontology") is untested. On this GT it would face the same same-role label splits.
- E26 conflicts with FIXED §8 as written.

**D2. The main session's hypotheses (tested).**

| H | verdict | evidence and change |
|---|---|---|
| H1 | Partially supported. **This changes the framing.** | v3 does make the decision the asset. The fallback cannot earn a TP here: 0 of 112 transaction ports are GT, and no site in the corpus needs it. But the fallback is not the main pathway. 14 of 15 input pairs had an internal holder, so they came through the input-port rule once its exclusion moved out. The fallback explains the 4 output pairs and hwspinlock bus_req_i. E6 does drop the fallback |
| H2 | Supported, with a confound | The oracle recall ceiling drops by 0.090–0.189. The GT's rationale for inputs is generic. The screen-1 cost is confounded: v1→v2 also added F1, F3 and F14 |
| H3 | Supported | GT copy pairs: both 3, copy 7, source 9. The FIXED text says "One conceptual asset usually has several structural references along its path" (:13) |
| H4 | Partially supported | E10 recovers 0 FN, and :15 defers secondary assets. But the opaque child is real (trng.vhd:145, a FIFO defined in another file), so the connectivity stage must handle children the executor cannot see |
| H5 | Partially supported | The objective lower bound is 1–3 FP per run. The larger share rests on hand judgement: 0.27 strict, 0.81 strict plus loose |
| H6 | Supported, one nuance | None of the targeted rules is in v2 or v3. But the single objective in E15 is in the FIXED schema. It does not affect P or R |
| H7 | Supported as a placement argument | Untested |
| H8 | Supported | F13's effect is at most +0.006 P |

**D3. Corrections to the three evidence analyses** (each re-derived here):
- Precision permutation p: 0.60 with exact values; 0.70 was computed on rounded values.
- "16 distinct whole transaction ports" is the sum of per-run FP rows (8+2+6). The distinct names per run are 7/2/6.
- The text audit's pair counts were v3 8/4/9 and v2 0/0/3. Mine are v3 8/2/9 and v2 0/0/3; the audit's lower-bound regex gave 4 for v3 s1.
- "`cache_o.cmd_dir` cannot score" is too strong. Only a whole `cache_o` prediction could match it (record↔field near-match rule). Predicting ctrl.buf_dir cannot.
- "pmp ctrl_i vs muldiv ctrl_i supports an attribute ontology": the GT's own reason for pmp ctrl_i is "does carry CSR address/data that program all PMP regions". So the split follows the CSR-write role, not the attribute.
- F3 keep/drop counts change with the definition of a plain copy (36/29 vs 28/37).
- Open caveat: build_table skips case branches after the first `when`. The K-cluster region counts behind E23 were not re-derived with a fix.

---

## E. Validated prompt-engineering principles

1. **Keep an exclusion inside every rule it limits (MEASURED association, n=3).** A pointer ("governed by … instead") was lost when the writer restated the rule (C1).
2. **Do not license a container through an absence test (MEASURED).** 16 of 19 fallback-type pairs named a holder in the same concept, so "no internal element holding it" was not checked.
3. **FIXED definitions copy through; the writer's paraphrases do not (MEASURED).** Definitions came through verbatim 11/11 in every v2 and v3 exec prompt. But any two exec prompts share only 0.11–0.18 of their lines. Constraints must therefore also bind the paraphrases.
4. **At 3 against 3, wording effects smaller than the sampling spread are invisible (MEASURED).** The minimum p is 0.10, and the Jaccard similarity across versions is about the same as within them. Paired designs and executor repeats are needed.
5. **Examples in FIXED text act as licences (REASONING, weak).** "Route an access" coincided with routing concepts being given ports.
6. **The executor never sees types declared outside its file (MEASURED).** No module file declares bus_req_t. Field classes must be defined generically, or supplied as input.
7. **Label provenance and report Q1 cost (MEASURED via E2).** Q1-cheap rules can be label conventions; Q2 rules can cost Q1.
8. **Negative "merely because" sentences around inputs coincided with input-recall collapse (MEASURED, confounded).**

---

## F. Proposed meta-prompt changes (meta level only)

Drafts were built by exact replacement into v3. They are in `critique/report/meta_v4a*_draft.txt`. All four pass `meta_tools.check_prompt`: corpus names, numeric hints and prompts_v2.audit. A planted violation was caught. BANNED_IN_OUTPUT applies to parser prompts only, so it is not relevant here.

**F-1. Restore the transaction-port exclusion in the structural-asset definition** (FIXED, :13).
- **Problem and evidence:** C1.
- **Underlying issue:** conflicting instructions.
- **Text.** Replace "A port whose record type carries complete bus transactions is governed by the Transport definition instead." with: **"Ports whose record type carries complete bus transactions are not structural references in this way either; the Transport definition governs them."**
- **Expected benefit.** Input transaction pairs return to v2 level (0/0/3). The oracle bound, removing all whole transaction ports from v3, gives P .377/.385/.385 against .364/.381/.373. R is unchanged, since none is GT.
- **Failure mode.** The model also drops the internal holders (port_sel, locked). Read bus TP.
- **What it breaks:** new meta sha and new output directories.

**F-2. Rewrite Transport: fields are generic, and no container fallback** (FIXED, :16).
- **Problem and evidence:** C2, C3 and C11, and E5/E6.
- **Underlying issue:** imprecise criterion; ambiguous RTL.
- **Text:** **"- Transport: a port or signal whose record type carries complete read or write transactions between this block and an interconnect is transport. Every field it carries is payload except a security attribute. Payload includes the address, write data, byte enables, strobe, acknowledge and read data, and any operation-type, sequencing or error field. Payload is not a primary asset: do not report it, whole or by field. Do not use a transport element as the exit of a value that a register holds and software can read back, or as the element that sets a value written into this block; report the element inside the block that stores or decides the value. A security attribute carried with a transaction is different: a privilege level, a debug-mode flag, or a source or initiator identifier (the concern of CWE-1302, CWE-1311, CWE-1317 and CWE-1318). When this block decides on such an attribute, for example to allow, deny or bypass an access, that access-control decision is a conceptual asset. Its structural reference is the declared element inside this block whose value is the outcome of that decision, or a port that is not a transaction port through which the decision leaves. A transaction port is never the structural reference of a decision: if the decision reaches only fields of a transaction port, keep the concept and leave its structural references empty. An attribute that is only passed along unchanged is carried, not decided. A port is a single candidate: name it whole; never report a field of a port."**
- **Expected benefit.** It removes the 4 output pairs, plus the hwspinlock case. imem TP may recover (REASONING).
- **Failure mode.** A real decision whose result leaves only through a transaction response would go unreported. That case is absent here and cannot be measured.
- **What it breaks:** v3's fallback semantics, and comparability with v3 at the version level.

**F-3. Validation minimum** (§10, :78).
- **Text.** Replace "…no transport payload and no field of a port may be reported, a transaction port is reported only as the structural reference of an access-control decision taken directly on one of its security attributes, and each name is the bare declared name." with: **"no transaction port, no transport payload and no field of a port may be reported, and each name is the bare declared name."**
- **Reason.** This keeps the validation minimum consistent with F-2.

**F-4 (conditional). Writer-consistency constraint** (DESIGN CONSTRAINTS).
- **Evidence:** C1, the restatements of "sets".
- **Text:** **"- Keep every restatement of a [FIXED] definition consistent with it. Where the execution prompt describes a realization label, a stage, or a validation check in its own words, the description keeps every exclusion and condition of the definitions it draws on, and adds no case that the definitions exclude."**
- **Failure mode.** Longer exec prompts that are no more faithful.
- **Test.** A meta-only text screen (X4).

**F-5 (conditional). Internal role pass** (§2 OPEN guidance). Addresses E16, E21 and E27.
- **Text appended to the §2 [OPEN] line:** **"Include an internal pass that records, for each element of the closed set, the RTL roles it plays before any asset decision: holds a value, holds the outcome of a decision, receives a value the entity reads, emits a value from the entity, passes a value along unchanged or connects to a sub-block, belongs to a transaction record, or times or resets the logic. Roles are observations used during the analysis, not asset labels, and they do not appear in the output."**
- **Schema:** unchanged.
- **Failure mode.** Roles harden into de facto labels, and recall drops. Test X5.

**F-6 (conditional). E7 wording** (FIXED, :14).
- **Text.** "…is where that value is set." becomes **"…is where that value enters the entity; its realization label is "sets"."**
- **Expected effect:** none on P or R. Fold it in only under its own meta id.

---

## G. Execution-prompt implications

After v4a, every generated exec prompt must:
1. Carry all FIXED definitions verbatim. Check with verbatim.py.
2. Describe "sets" without any transaction-port case. It should exclude clock, clock-enable and reset inputs except for a clock or reset controller.
3. Contain no "permitted whole-transaction-port case" or its equivalent.
4. Include a validation check that rejects every transaction port and every port field.
5. Attribute an attribute decision to the element whose value is the outcome. A data register merely updated inside the branch does not qualify. v3 s1's own line 221 already said this.
6. Allow a concept with an empty list.
7. Classify record fields from their use, knowing that the record type declaration is not in the input.
8. Add no uncertainty fields (FIXED §8).
9. Pass `check_exec_prompt`.

---

## H. Additional experiments and analysis protocol

| id | hypotheses separated | design | read | supports / contradicts |
|---|---|---|---|---|
| X1 | The F-1 path drives input pairs **vs** the fallback drives them | Arm A: v3 + F-1 only. Arm B: v4a (F-1+F-2+F-3). 3 meta samples each, 2 executor runs per sample | Whole transaction-port FP rows; input "sets" pairs; output pairs; imem TP; bus TP | A cuts input pairs to v2 level but keeps output pairs, and B cuts both: supports the split. A leaves input pairs at v3 level: contradicts the F-1 mechanism |
| X2 | Meta resampling **vs** executor noise | Rerun each v3 exec prompt twice more | Within-prompt spread of P, R and input TP (now 17/9/9) against the between-prompt spread | If within-prompt spread is close to between-prompt spread, meta wording effects need more runs per prompt |
| X3 | The definition text alone **vs** the writer's paraphrase | Paired test: patch the v4a definitions into the 3 v3 exec prompts by exact string replacement. The Transport definition is verbatim in 3 of 3 | Same metrics as X1, paired per sample | A drop with the paraphrases unchanged: the definitions drive behaviour |
| X4 | F-4 improves the faithfulness of paraphrases **vs** not | Meta calls only; no executor runs | Scripted audit: share of "sets" and validation restatements that keep the exclusions | Higher share with F-4 supports it |
| X5 | A role pass cuts carrier and transport FP **vs** costs recall | v4a against v4a+F-5 | F3-dropped carriers reported; per-class R; input TP /26 | Supports: FP down with no TP loss. Contradicts: recall falls |
| X6 | GT sensitivity | Rescore with cmd_dir→ctrl.buf_dir and inval_i→inv_i, only if the annotators agree | TP change per run | Reported as a sensitivity line only, never as the main metric |
| X7 | Missing record declarations **vs** unclear rules | Input change: prepend the package record declarations. This is not a meta change and needs a new directory | Transaction-port FP; C3 concepts | A fall with the declarations present supports C3 |
| X8 | Do the 0-GT conventions (reset, masks, transport) generalise? | An untouched held-out set, parsed and frozen | FP and TP on each role | Q1 generality only |

**Protocol for newly finished runs:**
1. Check completeness: 15 common modules and 111 GT entries. Run `mt.selftest` and `build_table.selftest`.
2. Score strict, per run. Report TP/FP/FN, P and R with their denominators. Never pool two meta versions.
3. Pre-register 3–5 target metrics per change before looking, as in the table above.
4. Compare against the reference ranges with exact permutation p (floor 0.10). Treat non-overlap as weak: about 10% of metrics fail to overlap by chance.
5. Report per-class P and R, input TP out of 26, and 'exit port' TP.
6. Collateral: check all module × status comparisons, and look for losses in modules the edit does not touch.
7. Text audit of the new exec prompts: verbatim definitions, restatements of the changed rules, check_exec_prompt.
8. Mechanism: read the concept and reasoning for every target FP, and cite the RTL line.
9. Log the meta sha, output directories and any held-out reads.

---

## I. Recommended next iteration

**Meta v4a = v3 + F-1 + F-2 + F-3.** Draft: `critique/report/meta_v4a_draft.txt`, sha12 c36e3731526a. Word similarity to v3 is 0.969.

**Screen.** 3 meta samples × 2 executor runs (X1, arm B), with arm A (v3 + F-1 only) alongside if the budget allows. Add X2 and X3 as cheap noise checks.

**Decision rule.** Adopt v4a as the new base only if all of these hold:
- (a) in every v4a run, whole transaction-port FP rows are ≤ 1 (the v2 range);
- (b) attribute-decision holders are not lost: acc_priv, fault_o and fail each appear in at least 2 of 3 samples, as they do in v3;
- (c) the P and R ranges are not entirely below v3's (P .364–.381; R .649–.721).

If (a) fails in 2 or more runs, reject the text-mechanism hypothesis and look at compliance.

| group | changes |
|---|---|
| **High-confidence** | F-1, F-2, F-3 (one package, one failure). F13 stays in code, reported separately. F14 stays in the schema. Rule-provenance tags in the ablation log (E2, E19). Freeze an untouched held-out set (E24) |
| **Conditional** | F-4 (after X4). F-5 (after X5). F-6 (under its own id). Reset exception: keep v3's text by default. Whether reset belongs in the GT is the user's call. This differs from the v3-results default because the text already exists, is justified on Q2, and costs ≤ 3 FP per run. GT fixes for cmd_dir and inval_i need annotators (X6). E26 unscored uncertainty field, as a later protocol change. E10's opaque child goes to the connectivity stage |
| **Do-not-incorporate** | E8 input gate. E12 copy canonicalisation. E10's looser carrier wording in the primary rule. E18 primary redefinition. E22 narrowing of "asset". E6's "grouped interface element" scope. F4/F5/F6 (E11). Restoring "route" as an example decision |

**Files.**
- Scripts: `critique/report/verify.py`, `build_v4_draft.py`, `run_all.sh`.
- Logs: `verify.log`, `txn_pairs.log`, `empty_concepts.log`, `gt_why.log`, and the `rerun_*/*.log` files. The txn_pairs, empty_concepts and gt_why checks were inline scripts; their output is in those logs.
- Drafts: `meta_v4a_draft.txt`, `meta_v4a_W_draft.txt`, `meta_v4a_R_draft.txt`, `meta_v4a_E7_draft.txt`.

All paths are under `<session scratchpad>/critique/`. The repo was not modified.