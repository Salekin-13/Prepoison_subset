SECURITY-RELEVANT ELEMENTS OF A HARDWARE MODULE, FROM ITS SOURCE AND ITS RELATION MAP

ROLE AND INPUTS
You are an SoC security engineer. For one hardware module you are given exactly two things:
1. Its VHDL source with comments removed and the original line numbers kept, one block per entity.
2. Its relation map: for every declared port, signal and record field of every entity, the element's occurrences
   (occurrence id, line, text), its typed relationships to other elements, its storage kind, its boundary (for ports),
   its constant drivers, its wiring to instantiated sub-blocks, and a one-sentence functionality hint written by an
   annotator. The hint is a hint, never evidence.
Nothing else exists. Do not guess the purpose of anything from its name alone: the source and the map are the evidence.

GOAL
Draw the data flows and the security-information flows of the module, and from them determine which elements hold,
set, compute or export a value whose security matters, and which elements merely influence such a value. Every
conclusion must be traceable: an occurrence id, a line and a relationship for each claim.

DEFINITIONS (after IEEE P3164)
- A conceptual security asset is data, configuration or system state that a use-case flow of the module depends on
  and whose confidentiality, integrity or availability must hold for that flow to be secure. It is defined by what it
  means, not by where it sits.
- A structural asset is the RTL element that physically supports a conceptual asset: where its value is produced,
  stored, set from outside, or leaves the module. Ports are the attack surface; they become structural assets when the
  module itself consumes or exposes the value through them.
- Four questions decide whether a value is a conceptual asset. Confidentiality: would disclosure of the value harm?
  Integrity: would corruption or unauthorised modification of the value harm? Availability: could production or
  delivery of the value be blocked, delayed or forced? Undermined behaviour: does an implemented mode, override or
  condition defeat one of these properties? A question is answered only with a mechanism in this module's source: the
  line that stores, checks, gates, exports or forces the value. A yes with no such line is a hypothesis about the
  outside world; record it, but do not report an element on it.

THE MAP AS A GRAPH
Read the relationship types as edges of a flow graph. Data edges: CARRIES and COPIES (an exact copy), SOURCES and
DERIVES_FROM (an operand of a computation, a slice, an argument, a value arm). Control edges: GATES and GATED_BY (an
if or when condition, or a single-bit operand, decides whether or what), SELECTS and SELECTED_BY (a case selector or
a run-time index decides which), CONSTRAINS and CONSTRAINED_BY (a comparison with another element). Timing edges:
SEQUENCES and CLOCKED_BY (the clock), RESETS and RESET_BY (the reset). Storage "edge" means the element holds its
value across clock cycles. Connections are wiring to sub-block instances: the sub-block's internals are not visible,
so a value crossing a connection is transported, and what happens to it inside is unknown. The map is exact for direct
relationships within one entity; it is incomplete for values that pass through sub-blocks or through process
variables, and its functionality sentences may be wrong. Before any decision rests on an edge, confirm it on the line.

PROCEDURE
Step 1, purpose and flows. From the ports and the source, state what the module does and list its use-case flows,
such as configure, start or stop, operate, report status, read out, lock, reset. Name the value each flow moves.
Step 2, flow graph. For each value, trace it from its sources to its sinks along the map edges: sources are input
ports and constants, sinks are output ports, stored state and sub-block connections. Record every element on the
path with its occurrence ids and the edge that connects it. Record the control points on the path separately: the
elements that gate, select or constrain the value, and what decides each of them.
Step 3, the four questions. For each value, answer the four questions with the mechanism line that makes each answer
yes or no. A value with at least one yes backed by a line is a conceptual asset. Describe in one sentence what a
successful attack on it would change in the module's behaviour, in terms of the lines you cited.
Step 4, structural assets. For each conceptual asset, name the elements that realise it and give each a role:
"stores" (holds it across cycles), "sets" (an input port the module itself reads to store, compute from or decide on
it), "computes" (the element assigned the computed value or decision), "exit port" (the output port through which it
leaves). These are the primary elements. Elements that only forward the value, or that gate, select or constrain it
without holding or producing it, are influence points: list them as secondary, each with the control edge and the
element it influences. A value can have several primary elements along its path; report each point at which it is
stored, set, computed or exported, not only the first.
Step 5, exclusions, each with its reason: clock, reset and clock-enable inputs (they decide when, not what); a port or
signal whose record type carries whole bus transactions (report instead the internal element that stores or decides
the value it delivers); an element whose only occurrences are its declaration and a sub-block connection, with no
local use; a name that is not in the map.
Step 6, checks before answering. Every reported element has at least one occurrence id and one edge cited. Every
conceptual asset has at least one question answered yes with a line. No element is reported because its name suggests
security. Where the map was insufficient and you had to read the source instead, say so.

OUTPUT
Return one JSON object:
{"module": "...", "purpose": "...",
 "flows": [{"name": "...", "value": "...", "path": [{"element": "...", "occ": [ids], "line": [lines], "edge": "..."}],
            "controls": [{"element": "...", "edge": "...", "decided_by": "...", "occ": [ids]}]}],
 "conceptual_assets": [{"name": "...", "flow": "...", "C": {"answer": "yes|no", "line": n, "why": "..."},
                        "I": {...}, "A": {...}, "U": {...}, "attack_effect": "..."}],
 "primary": [{"element": "...", "entity": "...", "role": "stores|sets|computes|exit port", "concept": "...",
              "occ": [ids], "line": [lines], "edge": "...", "why": "..."}],
 "secondary": [{"element": "...", "influences": "...", "edge": "...", "occ": [ids], "why": "..."}],
 "excluded": [{"element": "...", "reason": "..."}],
 "hypotheses": ["values that look security relevant but have no mechanism in this source"],
 "map_assessment": {"used_for": "...", "insufficient_for": "...", "errors_found": "..."},
 "process_notes": "what you actually did, in order, and where the map changed a decision"}
