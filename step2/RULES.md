# Step 2 rule list — frozen 2026-09-21, before scoring

Each rule reads only `step1/relation_map/<module>.json` and the reported list. No ground truth is consulted at run
time. Each has a stated basis. Applied in this order.

| # | Rule | Basis |
|---|---|---|
| R1 | **Carrier copy.** An element whose drivers are all a plain copy of one other element, and which no condition reads. If that source is also reported, drop the copy. If it is not, report the source instead. | SAIF (VTS 2021): an element that only helps transfer a value is secondary, not primary. The executor prompt says the same: "An element that only passes the value along … carries the asset but is not its structural reference." |
| R2 | **Carrier field.** A field of a record that no condition in its entity reads and that no logic in its entity computes. Drop it. | Same basis as R1: a field that is only written and read on as part of the whole record passes the value along. |
| R3 | **Port forwarding.** An internal signal whose only driver is a plain copy of a port that is also reported. Drop the signal, keep the port. | Same basis. Keeps the point where the value enters or leaves the entity. |
| R4 | **Clock and reset inputs.** Drop a clock or reset input, unless producing or controlling a clock or reset is the module's function. | SAIF: infrastructure. CWE-1206 covers clock and reset as a security concern for blocks whose function they are, which is why the exception exists. |
| R5 | **Transport records.** Drop an element whose record type carries whole bus transactions, whole or by field. | SAIF p2: "the bus and the decoder are the secondary supports helping to transfer the primary asset". |
| R6 | **Whole record beside its own fields.** If a record signal and its own fields are both reported, keep the fields. | IEEE P3164 §3.1.2: the structural asset is the element that holds the value; the fields hold it, the container groups them. |

## What is honest about this list

- R2 was **chosen after looking at the 15 development modules**: ground-truth record fields are read in a condition or
  computed 85% of the time, against 47% for wrong reports (majority vote of the winner, n = 27 and 111). The basis above
  is real, but the choice was informed by that split, so the 15 modules cannot also be its test. The 26 never-tuned
  ground-truth modules are the test.
- R4 and R5 restate conventions the ground truth follows (0 of 302 entries are transaction ports; 0 are clock or reset
  inputs). They were already reported separately as an evaluation filter, and they are kept separate here too.
- The relation map's known limits carry into the rules: a connection into a sub-block is recorded as `in_port_map`
  rather than as `drives`, and a whole record does not inherit its fields' relations.

## The bar (from the roadmap)

Substantial means precision up by 0.10 or more with recall down by no more than 0.03, measured on the Step 1b winner's
stored runs (m7e194es0ism, 3 runs, 15 modules, 111 ground-truth entries).
