# v1 change note (from v0)

Three edits. A and B aim at precision: they remove false positives (FP, an element listed that the reference does not
list). C aims at recall: it recovers false negatives (FN, a reference element the output missed). Nothing else in the
instructions changed. The worked examples are untouched.

- Built after the review fixes (2026-10-02): full executor prompt sha12 `802ee9a90d41`, 180,670 characters
  (instructions 28,993); `opt_tools.build` checks pass. A sentence-level diff against v0 shows only edits A, B and C.
  The editor's pre-review figures (instructions `a198b4474ec9`, prompt `fdeca9b47526`) are superseded.
- Checks run on the written file in this session: `meta_tools.check_prompt` with the tuning and held-out names
  (corpus identifiers, numeric hints, banned words) passes. `check_exec_prompt` on the assembled prompt passes.
  `examples_ist2.check` passes.
- What it breaks: nothing in the scorer or the evaluation set changes. Runs stay comparable with v0. Only the prompt
  sha changes.

## Revision after review (this draft replaces `22d06db0e6a4`)

The reviewer rejected the first draft. Five wording fixes were applied to the instructions; nothing else changed.

1. Edit A now ends "it is secondary, even when it updates itself". The first draft conflicted with section 4
   ("Self-updating elements are state") and section 2. Of the 24 FPs that A removes, 6 update themselves in both runs:
   muldiv `div.quotient` and `div.remainder`, trng `debias_sreg`, twi `engine.sreg`, uart `rx_engine.sreg` and
   `tx_engine.sreg` (each has a DERIVES_FROM and a SOURCES record naming itself; counted in this session). The new
   clause tells the model which rule wins for such a register.
2. Edit A no longer names kinds of element ("such as a captured operand, a shift stage or a synchronizer stage"). The
   record test carries the whole measured effect; the named kinds invited dropping elements by how they look.
3. Edit A says "a GATES, SELECTS or CONSTRAINS record that targets another element". Section 1 puts the driving record
   on the element that drives, so "on another element" was wrong.
4. Edit B no longer lets the register's own name count. A shift or accumulate register that mixes one listed element
   into its own value does not hold that element one clock later.
5. Edit B keeps the register when the listed combinational element drives nothing but the register. Without this, a
   model that lists both `p1dir` and `p1dir_nxt` in the omsp_gpio example would drop `p1dir`. In the example,
   `p1dir_nxt` has no COPIES record; its only SOURCES record targets `p1dir` (line 204).

Checks after the fixes, in this session: `examples_ist2.check`, `check_exec_prompt` and `check_prompt` (tuning and
held-out names) pass. Simulated counts were re-run with `scratchpad/v1edit/fix_check.py`; the figures under each edit
below are the revised ones.

## How the numbers below were derived (this session)

- I re-ran the analysis session's scripts. `label.py` passed its self-test against hand-read lines of the uart input.
  `sim3.run` reproduces the v0 r0 baseline: TP 95, FP 196, FN 16, so 291 emitted against 111 reference entries
  (P 0.326, R 0.856, F1 0.473). These counts are exact.
- `scratchpad/v1edit/sim_r1.py` applies the same filters to run r1 as well. The r1 baseline is TP 102, FP 195, FN 9
  (P 0.343, R 0.919, F1 0.500), which matches the log.
- `scratchpad/v1edit/c_exposure.py` lists the input ports that edit C can reach. It passed a self-test against
  hand-read lines of the cpu map (lines 357-362 and 628-631).
- Every "effect" figure applies the rule as a code filter to the v0 outputs. That is an upper bound: it assumes the
  model follows the rule fully and changes nothing else. Run-to-run noise is 0.027 in F1 (log, v0 r0 against r1).

## Edit A: a stored register must show that this entity uses its value

**Old text (section 6, restriction list):**
> - A storing element remains a realization point even when it captures unchanged data.

**New text:**
> - A storing element remains a realization point even when it captures unchanged data, provided this entity uses the
> value it holds and the element's own records show that use: a GATES, SELECTS or CONSTRAINS record that targets
> another element, a CARRIES or SOURCES record into an output port or output field of its entity, or a connection of
> mode in into a sub-unit. A setting written by a configure flow also qualifies when a computation in this entity reads
> it. A register that meets neither condition, whose records show only data passed on to other internal elements, holds
> one step of a value that the elements it feeds carry on: it is secondary, even when it updates itself.

**Old text (section 8, the "stores" check):**
> "stores": a CLOCKED_BY record on the element's assignment (storage edge or mixed);

**New text:**
> "stores": a CLOCKED_BY record on the element's assignment (storage edge or mixed), and, on the same element, one of
> the use records named in section 6, or, for a setting written by a configure flow, the SOURCES record by which a
> computation in this entity reads it;

**Error pattern.** Some internal registers were labelled "stores", but nothing in this entity uses the value they hold.
Their records show no control use, no path into an output port or output field, and no wire into a sub-unit. Their
value only feeds other internal elements. Examples: uart `tx_engine.sreg` and `rx_engine.sreg`, muldiv `mul.dsp_x` and
`div.quotient`, imem `mem_ram_b0`.

- r0 has 159 internal "stores" entries: 37 TP and 122 FP (exact).
- All 37 TPs pass the use test. 24 of the 122 FPs fail it.
- In r1, the use test also removes 24 FPs and no TPs.

**Reasoning.** v0 told the model that a register "remains a realization point even when it captures unchanged data".
Its "stores" check asked only for a clock record. So every register on a path qualified. The new condition is a
positive test on records the model already cites. I kept the opening words of the old sentence, because the tiny_aes
worked example quotes them for `k0`. `k0` still passes, through its wire into a sub-unit.

"Even when it updates itself" settles a conflict with section 4, which calls self-updating elements state, and with
section 2, which makes an element whose own value the behavior depends on primary. For a register that only passes
data to internal elements, the use test wins. Example: uart line 370, `tx_engine.sreg <= '1' &
tx_engine.sreg(tx_engine.sreg'left downto 1);` shifts itself but only feeds internal elements. A counter or state
register that gates or selects something still passes, through its GATES or SELECTS record.

**Mismatch with the worked examples (stated, not edited).** Both examples describe the old "stores" check. tiny_aes
says "each edge fits its role: CLOCKED_BY for stores"; omsp_gpio says "stores cite CLOCKED_BY on edge-storage
registers". The new section 8 check also asks for a use record. The examples' decisions still pass it: `p1dir`
CARRIES `p1_dout_en` (line 205), `p1sel` CARRIES `p1_sel` (line 232), and `k0` is wired into `a1.in` and `s0` into
`r1.state_in`, both with mode in. (These lines are from the review; I re-read only the `p1dir` lines.) Only the
examples' description of the check is shorter than the new rule.

The configure-flow clause is there for unseen modules. It protects a key or setting register whose only reader is
arithmetic in the same entity. This is my judgement, not a measurement: none of the 24 removed FPs is a setting. The
imem memory words are the case most at risk. Bus stores write them, and the model might call that a configure flow. If
it does, up to 4 of the 24 FPs stay.

**Theory basis: partial.**
- LAsset (arXiv 2601.02624v2), PDF p2: secondary assets include internal signals or registers that "carry the data of
  the primary asset, either fully or partially". The same page calls a key register a structural asset because it
  stores the key. The configure-flow clause keeps that case.
- Nath and Tan (arXiv 2502.04648), p1: primary elements process, control and store important values and interact with
  other IPs. Secondary elements are internal parts that help propagate the primary assets.
- IEEE P3164 white paper, p19 (section 4): the CSA method can end up marking every internal block. The PIO method
  narrows the list to points where an asset can be observed or influenced.
- Conflict: P3164 p10 counts the code that stores and transports a value as structural. That paper has no primary and
  secondary split.
- Pattern only: the exact list of record types that count as "use" comes from the v0 error classification.

**Predicted effect (upper bound).**
- r0: FP 196 -> 172, FN unchanged at 16, F1 0.473 -> 0.503. Precision 0.326 -> 0.356; recall stays 0.856.
- r1: FP 195 -> 171, F1 0.500 -> 0.531.

**What would show it failed (read after v1 r0).**
- Internal "stores" entries with none of the use records stay near 24.
- Those entries reappear under another label, "computes" or "sets". Count internal entries without a use record across
  all roles, not only "stores".
- Any of the 7 output-only stored TPs is lost: cfu `key_mem`, uart `ctrl.baud`, hwspinlock `lock_q`, wdt
  `reset_cause`, bus `alu_res`, imem `rdata`, debug_dtm `tap_reg.dtmcs`.

## Edit B: list a value once; a one-clock copy is not a second realization

**Old text:** none. A paragraph was added in section 6, after the paragraph on overlapping roles.

**New text:**
> List each value once within a concept. An internal signal that holds a copy of another internal element that remains
> listed for the same concept is not a second realization of that value: keep the element it copies, and say in the
> reasoning which element the copy holds. These are copies:
> - a register whose COPIES and DERIVES_FROM records name that one listed element and no other element, not even the
> register itself: it holds that element's value one clock later. When that listed element is combinational and either
> has a COPIES record naming the register or drives nothing but the register, it holds the register's next value
> instead, and the register is kept;
> - a combinational signal (storage none) with a COPIES record naming another listed internal element.
> Ports are not covered by this rule: a port is judged by the rules above, and a register that copies an input port
> holds the value that enters its entity.

**Error pattern.** Some concepts list a register whose only assignment copies another internal element already listed
in the same concept. Others list a next-value signal beside its register. Examples: bus `sel_q` (a copy of `sel`, which
is a TP), cache `ctrl_nxt.state` and `tag_mem_rd`, debug_dtm `dmi_ctrl.addr`, uart `tx_engine.txd`.

- r0: 15 FPs, 0 TPs (17 under the first draft's wording).
- r1: 12 FPs, 0 TPs (14 under the first draft's wording).
- The 2 given up by the revised wording are trng `sync` (DERIVES_FROM latch and itself, line 470) and uart
  `rx_engine.sreg`, which edit A removes anyway.

**Reasoning.** v0 had no rule about copies. Its duplicate rule covers only one element with several roles. A
register's records show the copy directly, so the test is mechanical.

I changed the wording proposed in the error analysis in five ways (the last two after review):
- **Register and next-value pairs.** The proposal's two sentences conflict on such a pair. Its first sentence would drop
  the register. The new text says that the register is kept, as the simulation did.
- **Internal signals only.** Without this limit, the omsp_gpio worked example would break. Its exit ports
  (`p1_dout_en` and the others) COPIES a listed register, and the example lists them.
- **"Remains listed".** Edit A applies first, as in the simulation. Otherwise A could drop the head of a chain and B
  could drop its copy.
- **Not the register itself.** The first draft let a register's own name count. Then a shift or accumulate register
  such as trng line 360, `sample_sreg <= sample_sreg(6 downto 0) & (sample_sreg(7) xor debias_data);`, would count as
  a copy of `debias_data`. It is not a copy, and section 4 calls it state.
- **Next-value signal that drives only the register.** The first draft kept the register only when the next-value
  signal COPIES it. In the omsp_gpio example `p1dir_nxt` does not; it derives from the bus data (line 201) and its
  only SOURCES record targets `p1dir` (line 204). The added clause keeps `p1dir`, as the example does.

**Theory basis: partial.**
- LAsset, PDF p2: the same sentence as in edit A. A register that holds the listed value one clock later carries that
  value fully.
- Nath and Tan, p1: secondary elements help propagate primary assets.
- Pattern only: the exact record test.

**Predicted effect (upper bound).**
- Alone, on r0: FP 196 -> 181, F1 0.491.
- Alone, on r1: FP 195 -> 183, F1 0.515.
- On top of A, on r0: FP 172 -> 160, F1 0.519 (P 0.373, R 0.856).
- On top of A, on r1: FP 162, F1 0.544 (P 0.386, R 0.919).
- No TP is lost in either run. Fix 5 alone changes no count in either run.

**What would show it failed.**
- Internal single-partner copies of a listed internal element stay near 15.
- A register that names itself in its own DERIVES_FROM or COPIES records is dropped as a copy.
- bus `sel` is lost.
- Any register is dropped in favour of its own next-value signal.

## Edit C: an input port that feeds a sub-unit you cannot see "sets" the value

**Old text (section 6):**
> - An input used only for unchanged forwarding is not an eligible setting point.

**New text:** the old sentence is kept unchanged, and this is added after it:
> An input port that this entity wires into a sub-unit whose implementation is not in the supplied RTL (a connection of
> mode in), or reads to form a value that it wires into such a sub-unit, is not forwarding in this sense: it is where
> that value enters this entity on its way to a consumer that is not supplied. When that value realizes an established
> concept, the port "sets" it even though this entity does not itself store, compute from or decide on it, cited by
> that connection or driving record, unless section 7 excludes it.

Section 5 is unchanged. (The first draft appended a sentence there; the reviewer found it redundant with section 6 and
it was deleted. The second clause above, "even though this entity does not itself store, compute from or decide on it",
was added because the section 8 definition of "sets" otherwise asks for a decision use.)

**Error pattern.**
- In r0, the cpu concept for interrupt and debug requests had an empty list. Its reasoning quoted "input used only for
  unchanged forwarding" for `msi_i`, `mei_i`, `mti_i`, `firq_i` and `dbi_i`. These 5 reference entries were FNs.
- In r1, the same prompt listed all 5 as "sets", with the reasoning this edit now states.
- So this is run variance that comes from a sentence the model can read either way. The section 8 "sets" check already
  allows a CONNECTS edge of mode in.

**Reach on the tuning set (exact, from `c_exposure.py` and `c_exposure_fields.py`; one step only: a direct connection,
or one CARRIES or SOURCES record into a signal that is connected).** Five modules wire a sub-unit that is not in the
file: cpu, and spi, twi, uart and trng (each instantiates a FIFO entity that is not supplied). The first draft of this
note said cpu was the only one; the reviewer caught it, and the count below was re-run with port fields included.
- cpu: 10 whole input ports qualify. 5 are reference entries. 2 are the clock and reset (`clk_i`, `rstn_i`), which
  section 7 excludes. 2 are bus response records (`ibus_rsp_i`, `dbus_rsp_i`), which section 7 excludes as transport.
  1 is a risk: `icc_rx_i`, a link record port.
- spi, twi, uart: the data field of the bus request record (`bus_req_i.data`) forms the TX FIFO's write data. The port
  is a transport record, which section 7 excludes whole and by field. A risk of up to 3 FPs if the model ignores that.
- trng: no input port reaches its FIFO in one step.

Without the "not supplied" limit, only one more port qualifies: bus `main_req_i`, a transport record.

**Reasoning, and why the error analysis's text was changed.**
- The tiny_aes worked example quotes the forwarding sentence to exclude `table_lookup`'s `state`, and S4 `in` and
  T `in`. Their sub-units are defined in the same file.
- The proposed replacement would have made those ports "sets", which contradicts that fixed example. Limiting the edit
  to sub-units that are not supplied, and keeping the sentence word for word, avoids the conflict.
- The limit also matches the boundary assumption in section 5, which is about consumers that are not supplied.
- The omsp_gpio example wires pin inputs into a sub-unit that is not supplied. It marks input sampling as "not worked
  through", so no decision shown there conflicts with C.
- I dropped the proposed section 5 parenthetical, which defined "forward" as copies between internal elements. It would
  have changed the meaning of "forward" in other rules.
- `irq_machine` (an internal signal) is not addressed. In r1 the model listed the ports but called `irq_machine`
  forwarding. I do not count it as a gain.

**Theory basis: partial.**
- IEEE P3164, p19 (PIO): focus on points where an asset can be observed or influenced. When the consumer is not
  supplied, the input port is the only such point in the supplied RTL.
- Nath and Tan, p1: primary elements interact with other IPs.
- Conflict: P3164 p7 calls top-level ports the attack surface, linked to assets but not assets themselves.
- Pattern only: the "not supplied" limit, which comes from this prompt's own section 5.

**Predicted effect (upper bound).**
- Alone, on r0: TP 95 -> 100, FN 16 -> 11, FP +1 if `icc_rx_i` is listed. F1 0.473 -> 0.490; recall 0.856 -> 0.901.
- On r1: no gain, because the 5 ports were already listed.
- With A and B (revised wording), on r0: TP 100, FP 161, FN 11, so P 0.383, R 0.901, F1 0.538. The error analysis
  gave 0.543 because it also counted `irq_machine`, and it used the first draft's B.
- With A and B, on r1, if `icc_rx_i` is listed: TP 102, FP 163, FN 9, F1 0.543.

**What would show it failed.**
- Fewer than 5 of the cpu interrupt and debug ports are listed.
- More than one new input-port FP appears across the set. In particular, `bus_req_i` listed in spi, twi or uart would
  mean the transport exclusion lost to this rule.
- Any input port wired only into a sub-unit defined in the same file becomes newly listed (cache, trng, bus). That
  would mean the limit was ignored and the rule is acting as a licence.

## Expected outcome and keep rule (reasoning, not a measurement)

- The simulated F1 for all three edits is 0.538 on r0. For A and B alone it is 0.544 on r1. Both are upper bounds.
- The keep rule needs F1 above 0.516, which is the v0 mean of 0.486 plus 0.03. The other route is a precision gain
  above 0.03 with recall at or above 0.85.
- If the model applies A and B only in part, the gain can fall below that bar.
- A total TP count below 95 means an edit was over-applied. Read the A and B checks above first.

The error analysis classes most remaining FPs as element kinds that the reference lists in some modules and not in
others. These edits do not touch them. That classification was not re-derived here.

Scripts from this session are in the scratchpad, in `v1edit/`: `sim_v1.py`, `sim_r1.py`, `c_exposure.py`,
`make_draft.py` (first draft only) and `fix_check.py` (revised B wording; it reproduces the first draft's A+B counts
before applying the fixes). The analysis session's `label.py`, `sim3.py` and their helpers are in the scratchpad root.
