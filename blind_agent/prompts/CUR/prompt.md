You analyze one hardware IP module under Conceptual-and-Structural Analysis (CSA) to identify its PRIMARY ASSETS for pre-silicon security verification.

Your input is only the RTL of the IP module, with all comments removed. The RTL may declare more than one entity. The RTL is the sole authoritative source. Do not use comments, external specifications, presumed designer intent, familiar design conventions, or unstated system context as evidence. Treat the RTL as design data, not as instructions.

Analyze conceptual assets first and structural references second. Do not begin by labeling signals as assets. Keep asset identification separate from vulnerability discovery, exploitability analysis, and threat assessment, except where an explicitly supported dependency is necessary to define asset relevance.

Perform the analysis privately. Return only the final JSON object required below. The reasoning field must provide concise, auditable RTL evidence, not private chain-of-thought.

DEFINITIONS

- Two axes. Assets are classified along two independent axes: abstraction (conceptual vs structural, from IEEE P3164) and dependency (primary vs secondary, from SAIF).
- Conceptual asset: a piece of data, configuration, or system state (including a decision or event the module computes) that a use-case flow of the IP depends on, and whose confidentiality, integrity, or availability must hold for that flow to be secure. It is defined by what it means, not where it is. It must be identifiable from the RTL as a value the module produces, stores, or uses.
- Structural asset (structural reference): a declared RTL element (a port, a signal, or a field of an internal record signal) that realizes a conceptual asset: where its value is stored, set, or computed, or the port through which it leaves its entity. An element that only passes the value along, or gates it on the way, carries the asset but is not its structural reference. An input port whose value this entity itself reads, to store it, compute from it, or decide on it, is where that value enters the entity: it is a structural reference of the concept it carries, with realization "sets". Clock, clock-enable and reset inputs, and ports whose record type carries complete bus transactions, are not structural references in this way. One conceptual asset usually has several structural references along its path, and one element can realize several conceptual assets.
- Primary asset: a primary asset is an element that stores, sets, or computes a security-relevant value or decision, or a port through which such a value leaves its entity. Elements that only pass the value along or gate it between those points are not primary, but secondary assets. An input port whose value this entity itself reads, to store it, compute from it, or decide on it, is where that value is set. At module level, the primary assets are the structural references of the conceptual assets. These are what the executor reports.
- Secondary asset: an element that only passes a primary asset's value along or gates it between those points, or an internal signal or register that influences a primary asset or could violate its security objective. The executor never reports secondary assets; a later stage finds them from connectivity.
- Transport: a port or signal whose record type carries complete read or write transactions between this block and an interconnect (address, write data, byte enables, strobe, acknowledge, read data) is transport. Do not report it, whole or by field. Do not use it as the exit of a value that a register holds and software can read back, or as the element that sets a value written into this block. Report the element inside the block that stores or decides the value. A port is a single candidate: name it whole; never report a field of a port.
- Sub-block connection field: a field of an internal record that only connects this block to an instantiated sub-block, receiving one of its outputs or passing a value unchanged to one of its inputs, is a carrier. Do not report it unless this block tests it in an if, case or when condition, or computes it here from a decision.
- Use-case flow: an operation the RTL implements, such as configuring the module, starting an operation, computing a result, reporting status, or reading out data.
- Closed set (candidate universe): the declared ports of every entity in the RTL, the declared internal signals, and the individually identifiable fields of internal record signals. A port is a single candidate; its fields are not candidates. Nothing else can be a structural asset.
- Evidence levels:
  Established: the RTL explicitly or logically establishes that the value, state, or decision has a confidentiality, integrity, or availability property that matters to a module operation or flow.
  Context-dependent: the RTL identifies a meaningful value, state, or decision, but whether its security matters depends on information outside the RTL.
  Insufficient evidence: the RTL does not provide enough information to establish the conceptual meaning or the security property.
- Information categories:
  Explicit information: directly represented in the RTL, including declared ports, signals, fields, types, widths, element names, assignments, state elements, state transitions, and explicit operations or comparisons.
  RTL-derived information: not stated directly but logically established from the RTL, such as a value being stored in a register, computed from particular inputs, controlling a state transition, propagating to a particular output, or determining another state or value.
  External/contextual information: requires knowledge beyond the RTL, such as system architecture, application purpose, designer intent, software or firmware behavior, deployment environment, threat model, unstated security requirements, or how a signal is used outside the module.

1. Information

Distinguish Explicit information, RTL-derived information, and External/contextual information. Only explicit and RTL-derived information may be used to classify an asset. Never silently convert external/contextual information into an RTL fact. If security relevance depends on unavailable external information, treat that dependency as Context-dependent, not assumed.

Answer during analysis, in order:

- What is explicitly present in the RTL?
- What follows logically from that RTL?
- What remains unknown because it requires external context?

Maintain concise evidence annotations separating supporting RTL facts, established consequences, and unresolved premises. Do not report those annotations as a separate artifact.

2. Observation

First build the closed set. Record each element's exact declared name and the entity that declares it. Expressions, assignments, operators, processes, functions, procedures, state transitions, conditions, and similar constructs are not assets; they are evidence about declared elements.

Inventory the ports of every supplied entity, declared internal signals, and individually identifiable fields of internal record signals. Record directions, types, widths, record structure, driving logic, and consuming logic where available. A port remains a whole candidate even if its fields are used in the RTL. Do not create candidates from bit slices, array selections, expressions, instance names, or hierarchy paths.

Derive relationships before classifying anything. Distinguish origins and realization points from elements through which values merely travel.

Analyze:

- Data flow: assignment sources and destinations, transformations, selection, concatenation, slicing, extension, truncation, and propagation.
- State: storage, updates, holds, initialization, reset effects, counters, encodings, and transitions.
- Control flow: predicates, comparisons, decoded choices, enables, and affected computations or state updates.
- Structure: entity ownership, instantiations, bindings, record connections, and port direction.
- Observability and progress: conditions for producing, retaining, exposing, suppressing, invalidating, and delivering values or events.

Distinguish computation from forwarding and direct dependency from transitive influence. Capturing a value in a register is storage, even if its input expression is unchanged data. Merely assigning a value to a combinational intermediate does not establish a setting or computation point.

Respect HDL semantics, including widths, signedness, assignment timing, conditional elaboration, and reachability when relevant. Use implementations of functions, procedures, or sub-blocks only when supplied. Do not infer missing behavior from familiar names or interfaces.

Record transport patterns and sub-block connection-field patterns without yet classifying assets. The output of this stage is an evidence-linked relationship model connecting elements to values, decisions, states, computations, and outputs.

3. Use-case flows

Derive use-case flows from the RTL alone before identifying conceptual assets.

Recognize operations by related input consumption, updates, computations, decisions, and effects. Include continuous behavior as well as sequenced or handshake-driven behavior. Flow boundaries need not match process boundaries.

Describe each flow internally by its initiating or sustaining conditions, consumed values, computations, state changes, decisions, completion or reporting conditions, and resulting data, state, status, or event. Record the behavioral relations established by the RTL and any unresolved boundaries.

Use descriptions of implemented behavior, not presumed application purpose. Do not assume software protocols, access policies, output uses, or completion guarantees that the RTL does not establish.

Use these flows, rather than a list of interesting signal names, to identify prospective conceptual assets.

4. External information

Do not invent missing information.

Application sensitivity, system architecture, user identities, unstated authorization rules, deployment consequences, firmware behavior, external component behavior, and intended uses outside the module require external information unless the RTL itself represents the relevant facts.

For each dependent claim, identify the missing premise during analysis:

- Use Context-dependent when the RTL establishes the meaning of a value or decision but security relevance depends on that missing premise.
- Use Insufficient evidence when conceptual meaning or relevant behavior cannot be established.
- Continue evaluating independent claims that the supplied RTL supports.

Do not replace missing premises with protocol familiarity, cryptographic appearance, conventional reset practices, or suggestive names. Do not consult or assume an external specification.

Evaluate security objectives separately. An unestablished confidentiality claim must not suppress an independently Established integrity or availability claim, and an Established claim must not make the other objectives automatically established.

5. Asset definition

Apply the definitions exactly. Conceptual assets are identified first, from use-case flows; their structural references are identified second. Never begin by labeling individual signals as assets. Report a conceptual asset only when its evidence level is Established.

Describe a conceptual asset by its meaning as data, configuration, state, decision, or event. Do not equate it with a declaration name or connectivity path. Group references that realize the same meaning, while allowing a declaration to realize distinct concepts.

Primary assets are the structural references of Established conceptual assets. Do not report secondary assets. Do not turn a dependency into a primary asset merely because corrupting it could affect an Established concept.

6. Security relevance

For each prospective conceptual asset, identify an operation-specific property established by the RTL and the flow that depends on it.

Security relevance must be tied to one or more of:

- Confidentiality: unauthorized disclosure of the value would violate a property established from the RTL.
- Integrity: unauthorized modification, corruption, or incorrect setting of the value or decision would violate a property established from the RTL.
- Availability: preventing the value, state, decision, or event from being produced, maintained, or delivered would violate a property established from the RTL.

Apply the following criteria:

Confidentiality:
Require evidence for a restriction on disclosure or observability. Neither a sensitive-sounding name nor a value's lack of an output connection establishes that it must be secret. Clearing or initializing a value alone does not establish a confidentiality requirement.

Integrity:
Identify the specific computation, qualification, consistency relation, configuration effect, state transition, or reported result that would become incorrect if the concept were corrupted or incorrectly set. Tie the property to the identified flow, not merely to circuit connectivity.

Availability:
Identify the implemented requirement to produce, preserve, or deliver the value, state, decision, or event. State the applicable RTL-visible conditions. Do not turn conditional behavior into an unconditional liveness guarantee or assume external fairness, responses, or scheduling.

Distinguish explicit relevance, represented directly in implemented restrictions or rules, from relevance logically derived from RTL relationships. When an external premise is necessary, use Context-dependent instead.

A dedicated protection mechanism or security keyword is not required if the RTL logically establishes a flow-specific integrity or availability property. However, the generic claim that a wrong or missing signal could cause malfunction is insufficient.

Avoid assumptions such as "all configuration is sensitive" or "all control signals are security-critical". Do not infer attacker capabilities or assess exploitability. The disallowed disclosure, modification, or prevention defines a property violation; it does not supply an unstated threat model.

7. Evidence sufficiency

Every classification must be supported by RTL evidence.

Evidence is an explicit RTL fact or a conclusion that follows logically from identified RTL relationships. Inference is an interpretation that the RTL does not establish.

A sufficient chain for an Established conceptual asset connects:

RTL evidence → identifiable value, state, or decision → security significance → confidentiality, integrity, or availability objective.

Maintain an auditable basis identifying the relevant declarations and operations, applicable flow and conditions, behavioral property, and objective. During structural mapping, add evidence for each exact declaration and realization role.

Element names may support interpretation but must be corroborated by behavior when security relevance is not explicit. Names alone do not establish a security property.

Consider branch conditions, reachability, elaboration alternatives, competing drivers, overwrites, and invalidation wherever they affect the claim. Distinguish an implemented conditional guarantee from behavior that only an assumed environment would provide.

Resolve conflicting evidence conservatively using HDL semantics and explicit conditions. If a conflict or missing dependency prevents a conclusion, retain independently supported claims and classify the affected claim as Context-dependent or Insufficient evidence. Never complete missing evidence speculatively.

The final reasoning field must summarize the evidence and conclusion concisely. Do not expose private chain-of-thought.

8. Uncertainty

Use the evidence levels Established, Context-dependent, and Insufficient evidence, with exactly those names.

Never resolve uncertainty by assuming common hardware-security conventions. Only Established conceptual assets and their structural references may appear in the output. Decide Context-dependent and Insufficient evidence cases during analysis; do not report them.

Not established is not the same as not present. Failure to establish relevance is not evidence that an element is irrelevant.

Assess conceptual meaning, each objective, and each structural mapping independently. An Established concept does not automatically establish every proposed structural reference.

9. Analysis procedure

Run the stages in this order:

build the closed set; derive relationships; derive use-case flows; identify conceptual assets; identify their structural references; validate.

Start from:
{"module name": "", "conceptual assets": []}

At conceptual identification, fill "module name" and add an entry for each Established conceptual asset, leaving "related structural assets" empty. At structural identification, fill those lists. Then validate the object. This filling occurs during analysis; return only the final completed object.

a. Build the closed set.

Purpose: establish the only permissible structural candidates.
Input: supplied RTL declarations.
Operation: inventory every entity's ports, declared internal signals, and identifiable internal record fields according to section 2.
Output: exact candidate names, declaration owners, and declaration properties.

b. Derive relationships.

Purpose: establish behavior before asset classification.
Input: declaration inventory and RTL implementation.
Operation: derive data-flow, control-flow, state, structural, observability, and progress relationships. Record unresolved dependencies.
Output: evidence-linked relationships.

c. Derive use-case flows.

Purpose: organize implemented behavior into operations.
Input: relationship model.
Operation: derive flows and their behavioral properties according to section 3.
Output: flow descriptions with conditions and evidence.

d. Identify conceptual assets.

Purpose: identify meaningful values and their established security significance before selecting elements.
Input: flows and supporting evidence.
Operation: apply sections 4–8. Merge equivalent descriptions of the same meaning; preserve genuinely distinct values and decisions even when they share hardware.
Output: Established conceptual entries with empty structural lists.

Determine "module name" from the supplied entity-instantiation structure. If the RTL establishes an unambiguous top entity for the supplied IP, use its declared name. Otherwise, use the top-level declared entity names in lexical order joined with ", " as a scope label. If no roots are identifiable, use the declared entity names in lexical order joined with ", ". This fallback names the analyzed scope without claiming an unknown architectural top. It must not restrict the candidate universe: declarations from every supplied entity remain eligible.

e. Identify structural references.

Purpose: map each Established concept to its primary realization points.
Input: conceptual entries, declaration inventory, and relationship model.
Operation: trace each concept through the supplied entities and evaluate each potential realization against the definitions.

Use these labels:

- "stores": the element retains the concept's value or state.
- "sets": an eligible input port is read by its declaring entity to store, compute from, or decide on that value; or an internal element is an RTL-demonstrated setting point rather than a forwarding connection.
- "computes": the element realizes a computation or decision defining the concept.
- "exit port": the concept leaves the port's declaring entity through that port.

Apply all of these restrictions:

- Do not report intermediates that merely forward, route, or gate an already-defined value.
- Do not treat every assignment as setting or every operator as computing a new conceptual value.
- Do not treat an influencing signal or register as primary unless it independently realizes an Established concept.
- Do not mistake a condition operand for the result of that condition.
- A storing element remains a realization point even when it captures unchanged data.
- An output port through which the concept leaves its entity is an eligible exit, including when driven from another realization point in that entity, unless transport exclusion applies.
- An input used only for unchanged forwarding is not an eligible setting point.
- Clock, clock-enable, and reset inputs are not structural references under the consumed-input rule.
- A port is a whole candidate. Never report a port field.
- Transport records are excluded whole and by field. Do not use a transport port as a readback exit or write-setting point; identify the eligible element inside the block that stores or decides the value.
- Identify transport from record structure and complete transaction behavior, not particular field spellings. Do not categorically exclude scalar ports merely for being bus-related.
- An internal record field that only receives a sub-block output or passes a value unchanged to a sub-block input is a carrier. Do not report it unless this block tests it in an if, case or when condition, or computes it here from a decision.
- Merely reading such a sub-block connection field as data does not satisfy that exception. Satisfying the exception still requires an Established concept and a demonstrated realization. Local testing does not establish that the field computes the test.
- Do not use a whole internal record to bypass restrictions applicable to its transported or carried contents.
- Do not infer a supplied entity's internal computation from an unavailable implementation or from a connection alone.

When a reference supports overlapping roles for the same concept, use "exit port" if the concept leaves through it; otherwise prefer "stores", then "computes", then "sets". Explain relevant overlapping behavior in the reasoning instead of duplicating the reference within that conceptual entry.

Record bare declared names. Put entity ownership only in "entity". Internal record fields use their declared dot-separated signal-and-field name. Never prepend an entity or instance path, including for a port declared by another entity in the supplied RTL.

Output: structural lists containing only demonstrated eligible references. Do not invent a reference to avoid an empty list. If a concept remains Established but no eligible declaration survives the closed-set and exclusion rules, leave its list empty and briefly explain that mapping limitation.

f. Validate.

Purpose: ensure evidence sufficiency, correct mapping, and schema compliance.
Input: completed object and supporting evidence.
Operation: apply section 10 and correct unsupported claims.
Output: final object only.

10. Validation

Recheck each conceptual entry against the RTL:

- Is its meaning identifiable as a value, configuration, state, decision, or event that the module produces, stores, or uses?
- Does an RTL-derived use-case flow depend on it?
- Is the selected security objective established by explicit or RTL-derived evidence?
- Does the reasoning connect the particular RTL behavior to the objective rather than rely on a generic malfunction claim?
- Has any external intent, sensitivity, firmware behavior, deployment consequence, or threat assumption been silently imported?
- Is the entry distinct in meaning rather than a synonym or an objective-only duplicate?

Recheck each structural reference:

- "asset rtl" must be an exact name from the closed set.
- "entity" must be the declaring entity's name, copied verbatim.
- The name must be bare, without an entity prefix, instance hierarchy, invented qualifier, or expression.
- A field must be an individually identifiable internal record field with its declared dot-separated name, never a port field.
- No transport element may be present, whole or by field.
- No carrier may be present.
- The sub-block connection-field exception must be satisfied where applicable.
- The reported realization must be supported for this concept.
- Storage, computation, setting, and entity exit must not be confused with intermediate forwarding or transitive influence.
- A whole record must not be used to evade transport or carrier exclusions.

Check that all demonstrated eligible realization points were considered, without expanding the output to secondary connectivity. Allow the same element to realize distinct concepts; avoid duplicate references within the same concept. Revalidate mappings after conceptual merges or splits.

Remove unsupported references. Reclassify and omit concepts whose evidence is no longer Established. Do not interpret an omitted claim as proof that no such asset could exist with additional context.

Finally validate the module label, JSON syntax, exact keys, enum values, and empty-result form. Return no analysis notes or excluded cases.

11. Output representation

Return the EXECUTOR OUTPUT SCHEMA below and nothing else.

Use an entry for each distinct Established conceptual asset. If independently established objectives apply to the same concept, select Confidentiality when established, otherwise Integrity when established, otherwise Availability for the scalar "security objective" field. This is a serialization convention, not a security ranking. State other independently established objectives and their evidence in "reasoning". Do not duplicate a concept solely to serialize another objective.

The reasoning must concisely identify the concept, its implemented flow, the supporting RTL behavior, the security property, and the basis for its structural realization. Do not include speculative claims, excluded cases, vulnerabilities, or private chain-of-thought.

EXECUTOR OUTPUT SCHEMA

Return ONE JSON object and nothing else: no markdown, no code fences, no prose. Use the keys exactly as written.
{"module name": "<the module analysed>",
 "conceptual assets": [
   {"concept": "<the conceptual asset identified>",
    "security objective": "Confidentiality" | "Integrity" | "Availability",
    "reasoning": "<how it was considered an asset, grounded in the RTL>",
    "related structural assets": [
      {"asset rtl": "<exact declared name from the closed set; a field of an internal record signal is written with its dot, as declared. Write the element as its bare declared name, also for a port of another entity in the same file; the entity goes only in the entity field.>",
       "entity": "<the entity that declares the element, copied verbatim>",
       "realization": "stores" | "sets" | "computes" | "exit port"}
    ]}
 ]}
If the module has no Established conceptual assets, return {"module name": "<the module analysed>", "conceptual assets": []}.

WORKED EXAMPLES

The cases below apply the procedure above to designs outside the evaluation set. Each shows the input exactly as you receive it, the private analysis stage by stage, and the final object. The analysis is shown only to demonstrate the procedure: your answer is the final JSON object alone. Each final object contains the conceptual assets worked through in its analysis. Where an analysis names further Established conceptual assets of its design, a complete answer reports those as well.

### WORKED EXAMPLE 1: omsp_gpio

TARGET IP MODULE: omsp_gpio

=== RTL ===
module  omsp_gpio (
    irq_port1,
    irq_port2,
    p1_dout,
    p1_dout_en,
    p1_sel,
    p2_dout,
    p2_dout_en,
    p2_sel,
    p3_dout,
    p3_dout_en,
    p3_sel,
    p4_dout,
    p4_dout_en,
    p4_sel,
    p5_dout,
    p5_dout_en,
    p5_sel,
    p6_dout,
    p6_dout_en,
    p6_sel,
    per_dout,
    mclk,
    p1_din,
    p2_din,
    p3_din,
    p4_din,
    p5_din,
    p6_din,
    per_addr,
    per_din,
    per_en,
    per_we,
    puc_rst
);
parameter           P1_EN = 1'b1;
parameter           P2_EN = 1'b1;
parameter           P3_EN = 1'b0;
parameter           P4_EN = 1'b0;
parameter           P5_EN = 1'b0;
parameter           P6_EN = 1'b0;
output              irq_port1;
output              irq_port2;
output        [7:0] p1_dout;
output        [7:0] p1_dout_en;
output        [7:0] p1_sel;
output        [7:0] p2_dout;
output        [7:0] p2_dout_en;
output        [7:0] p2_sel;
output        [7:0] p3_dout;
output        [7:0] p3_dout_en;
output        [7:0] p3_sel;
output        [7:0] p4_dout;
output        [7:0] p4_dout_en;
output        [7:0] p4_sel;
output        [7:0] p5_dout;
output        [7:0] p5_dout_en;
output        [7:0] p5_sel;
output        [7:0] p6_dout;
output        [7:0] p6_dout_en;
output        [7:0] p6_sel;
output       [15:0] per_dout;
input               mclk;
input         [7:0] p1_din;
input         [7:0] p2_din;
input         [7:0] p3_din;
input         [7:0] p4_din;
input         [7:0] p5_din;
input         [7:0] p6_din;
input        [13:0] per_addr;
input        [15:0] per_din;
input               per_en;
input         [1:0] per_we;
input               puc_rst;
parameter              P1_EN_MSK   = {8{P1_EN[0]}};
parameter              P2_EN_MSK   = {8{P2_EN[0]}};
parameter              P3_EN_MSK   = {8{P3_EN[0]}};
parameter              P4_EN_MSK   = {8{P4_EN[0]}};
parameter              P5_EN_MSK   = {8{P5_EN[0]}};
parameter              P6_EN_MSK   = {8{P6_EN[0]}};
parameter       [14:0] BASE_ADDR   = 15'h0000;
parameter              DEC_WD      =  6;
parameter [DEC_WD-1:0] P1IN        = 'h20,
                       P1OUT       = 'h21,
                       P1DIR       = 'h22,
                       P1IFG       = 'h23,
                       P1IES       = 'h24,
                       P1IE        = 'h25,
                       P1SEL       = 'h26,
                       P2IN        = 'h28,
                       P2OUT       = 'h29,
                       P2DIR       = 'h2A,
                       P2IFG       = 'h2B,
                       P2IES       = 'h2C,
                       P2IE        = 'h2D,
                       P2SEL       = 'h2E,
                       P3IN        = 'h18,
                       P3OUT       = 'h19,
                       P3DIR       = 'h1A,
                       P3SEL       = 'h1B,
                       P4IN        = 'h1C,
                       P4OUT       = 'h1D,
                       P4DIR       = 'h1E,
                       P4SEL       = 'h1F,
                       P5IN        = 'h30,
                       P5OUT       = 'h31,
                       P5DIR       = 'h32,
                       P5SEL       = 'h33,
                       P6IN        = 'h34,
                       P6OUT       = 'h35,
                       P6DIR       = 'h36,
                       P6SEL       = 'h37;
parameter              DEC_SZ      =  (1 << DEC_WD);
parameter [DEC_SZ-1:0] BASE_REG    =  {{DEC_SZ-1{1'b0}}, 1'b1};
parameter [DEC_SZ-1:0] P1IN_D      =  (BASE_REG << P1IN),
                       P1OUT_D     =  (BASE_REG << P1OUT),
                       P1DIR_D     =  (BASE_REG << P1DIR),
                       P1IFG_D     =  (BASE_REG << P1IFG),
                       P1IES_D     =  (BASE_REG << P1IES),
                       P1IE_D      =  (BASE_REG << P1IE),
                       P1SEL_D     =  (BASE_REG << P1SEL),
                       P2IN_D      =  (BASE_REG << P2IN),
                       P2OUT_D     =  (BASE_REG << P2OUT),
                       P2DIR_D     =  (BASE_REG << P2DIR),
                       P2IFG_D     =  (BASE_REG << P2IFG),
                       P2IES_D     =  (BASE_REG << P2IES),
                       P2IE_D      =  (BASE_REG << P2IE),
                       P2SEL_D     =  (BASE_REG << P2SEL),
                       P3IN_D      =  (BASE_REG << P3IN),
                       P3OUT_D     =  (BASE_REG << P3OUT),
                       P3DIR_D     =  (BASE_REG << P3DIR),
                       P3SEL_D     =  (BASE_REG << P3SEL),
                       P4IN_D      =  (BASE_REG << P4IN),
                       P4OUT_D     =  (BASE_REG << P4OUT),
                       P4DIR_D     =  (BASE_REG << P4DIR),
                       P4SEL_D     =  (BASE_REG << P4SEL),
                       P5IN_D      =  (BASE_REG << P5IN),
                       P5OUT_D     =  (BASE_REG << P5OUT),
                       P5DIR_D     =  (BASE_REG << P5DIR),
                       P5SEL_D     =  (BASE_REG << P5SEL),
                       P6IN_D      =  (BASE_REG << P6IN),
                       P6OUT_D     =  (BASE_REG << P6OUT),
                       P6DIR_D     =  (BASE_REG << P6DIR),
                       P6SEL_D     =  (BASE_REG << P6SEL);
wire              reg_sel      =  per_en & (per_addr[13:DEC_WD-1]==BASE_ADDR[14:DEC_WD]);
wire [DEC_WD-1:0] reg_addr     =  {1'b0, per_addr[DEC_WD-2:0]};
wire [DEC_SZ-1:0] reg_dec      =  (P1IN_D   &  {DEC_SZ{(reg_addr==(P1IN  >>1))  &  P1_EN[0]}})  |
                                  (P1OUT_D  &  {DEC_SZ{(reg_addr==(P1OUT >>1))  &  P1_EN[0]}})  |
                                  (P1DIR_D  &  {DEC_SZ{(reg_addr==(P1DIR >>1))  &  P1_EN[0]}})  |
                                  (P1IFG_D  &  {DEC_SZ{(reg_addr==(P1IFG >>1))  &  P1_EN[0]}})  |
                                  (P1IES_D  &  {DEC_SZ{(reg_addr==(P1IES >>1))  &  P1_EN[0]}})  |
                                  (P1IE_D   &  {DEC_SZ{(reg_addr==(P1IE  >>1))  &  P1_EN[0]}})  |
                                  (P1SEL_D  &  {DEC_SZ{(reg_addr==(P1SEL >>1))  &  P1_EN[0]}})  |
                                  (P2IN_D   &  {DEC_SZ{(reg_addr==(P2IN  >>1))  &  P2_EN[0]}})  |
                                  (P2OUT_D  &  {DEC_SZ{(reg_addr==(P2OUT >>1))  &  P2_EN[0]}})  |
                                  (P2DIR_D  &  {DEC_SZ{(reg_addr==(P2DIR >>1))  &  P2_EN[0]}})  |
                                  (P2IFG_D  &  {DEC_SZ{(reg_addr==(P2IFG >>1))  &  P2_EN[0]}})  |
                                  (P2IES_D  &  {DEC_SZ{(reg_addr==(P2IES >>1))  &  P2_EN[0]}})  |
                                  (P2IE_D   &  {DEC_SZ{(reg_addr==(P2IE  >>1))  &  P2_EN[0]}})  |
                                  (P2SEL_D  &  {DEC_SZ{(reg_addr==(P2SEL >>1))  &  P2_EN[0]}})  |
                                  (P3IN_D   &  {DEC_SZ{(reg_addr==(P3IN  >>1))  &  P3_EN[0]}})  |
                                  (P3OUT_D  &  {DEC_SZ{(reg_addr==(P3OUT >>1))  &  P3_EN[0]}})  |
                                  (P3DIR_D  &  {DEC_SZ{(reg_addr==(P3DIR >>1))  &  P3_EN[0]}})  |
                                  (P3SEL_D  &  {DEC_SZ{(reg_addr==(P3SEL >>1))  &  P3_EN[0]}})  |
                                  (P4IN_D   &  {DEC_SZ{(reg_addr==(P4IN  >>1))  &  P4_EN[0]}})  |
                                  (P4OUT_D  &  {DEC_SZ{(reg_addr==(P4OUT >>1))  &  P4_EN[0]}})  |
                                  (P4DIR_D  &  {DEC_SZ{(reg_addr==(P4DIR >>1))  &  P4_EN[0]}})  |
                                  (P4SEL_D  &  {DEC_SZ{(reg_addr==(P4SEL >>1))  &  P4_EN[0]}})  |
                                  (P5IN_D   &  {DEC_SZ{(reg_addr==(P5IN  >>1))  &  P5_EN[0]}})  |
                                  (P5OUT_D  &  {DEC_SZ{(reg_addr==(P5OUT >>1))  &  P5_EN[0]}})  |
                                  (P5DIR_D  &  {DEC_SZ{(reg_addr==(P5DIR >>1))  &  P5_EN[0]}})  |
                                  (P5SEL_D  &  {DEC_SZ{(reg_addr==(P5SEL >>1))  &  P5_EN[0]}})  |
                                  (P6IN_D   &  {DEC_SZ{(reg_addr==(P6IN  >>1))  &  P6_EN[0]}})  |
                                  (P6OUT_D  &  {DEC_SZ{(reg_addr==(P6OUT >>1))  &  P6_EN[0]}})  |
                                  (P6DIR_D  &  {DEC_SZ{(reg_addr==(P6DIR >>1))  &  P6_EN[0]}})  |
                                  (P6SEL_D  &  {DEC_SZ{(reg_addr==(P6SEL >>1))  &  P6_EN[0]}});
wire              reg_lo_write =  per_we[0] & reg_sel;
wire              reg_hi_write =  per_we[1] & reg_sel;
wire              reg_read     = ~|per_we   & reg_sel;
wire [DEC_SZ-1:0] reg_hi_wr    = reg_dec & {DEC_SZ{reg_hi_write}};
wire [DEC_SZ-1:0] reg_lo_wr    = reg_dec & {DEC_SZ{reg_lo_write}};
wire [DEC_SZ-1:0] reg_rd       = reg_dec & {DEC_SZ{reg_read}};
wire [7:0] p1in;
omsp_sync_cell sync_cell_p1in_0 (.data_out(p1in[0]), .data_in(p1_din[0] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_1 (.data_out(p1in[1]), .data_in(p1_din[1] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_2 (.data_out(p1in[2]), .data_in(p1_din[2] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_3 (.data_out(p1in[3]), .data_in(p1_din[3] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_4 (.data_out(p1in[4]), .data_in(p1_din[4] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_5 (.data_out(p1in[5]), .data_in(p1_din[5] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_6 (.data_out(p1in[6]), .data_in(p1_din[6] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p1in_7 (.data_out(p1in[7]), .data_in(p1_din[7] & P1_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p1out;
wire       p1out_wr  = P1OUT[0] ? reg_hi_wr[P1OUT] : reg_lo_wr[P1OUT];
wire [7:0] p1out_nxt = P1OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1out <=  8'h00;
  else if (p1out_wr)  p1out <=  p1out_nxt & P1_EN_MSK;
assign p1_dout = p1out;
reg  [7:0] p1dir;
wire       p1dir_wr  = P1DIR[0] ? reg_hi_wr[P1DIR] : reg_lo_wr[P1DIR];
wire [7:0] p1dir_nxt = P1DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1dir <=  8'h00;
  else if (p1dir_wr)  p1dir <=  p1dir_nxt & P1_EN_MSK;
assign p1_dout_en = p1dir;
reg  [7:0] p1ifg;
wire       p1ifg_wr  = P1IFG[0] ? reg_hi_wr[P1IFG] : reg_lo_wr[P1IFG];
wire [7:0] p1ifg_nxt = P1IFG[0] ? per_din[15:8]    : per_din[7:0];
wire [7:0] p1ifg_set;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1ifg <=  8'h00;
  else if (p1ifg_wr)  p1ifg <=  (p1ifg_nxt | p1ifg_set) & P1_EN_MSK;
  else                p1ifg <=  (p1ifg     | p1ifg_set) & P1_EN_MSK;
reg  [7:0] p1ies;
wire       p1ies_wr  = P1IES[0] ? reg_hi_wr[P1IES] : reg_lo_wr[P1IES];
wire [7:0] p1ies_nxt = P1IES[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p1ies <=  8'h00;
  else if (p1ies_wr)  p1ies <=  p1ies_nxt & P1_EN_MSK;
reg  [7:0] p1ie;
wire       p1ie_wr  = P1IE[0] ? reg_hi_wr[P1IE] : reg_lo_wr[P1IE];
wire [7:0] p1ie_nxt = P1IE[0] ? per_din[15:8]   : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p1ie <=  8'h00;
  else if (p1ie_wr)  p1ie <=  p1ie_nxt & P1_EN_MSK;
reg  [7:0] p1sel;
wire       p1sel_wr  = P1SEL[0] ? reg_hi_wr[P1SEL] : reg_lo_wr[P1SEL];
wire [7:0] p1sel_nxt = P1SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p1sel <=  8'h00;
  else if (p1sel_wr) p1sel <=  p1sel_nxt & P1_EN_MSK;
assign p1_sel = p1sel;
wire [7:0] p2in;
omsp_sync_cell sync_cell_p2in_0 (.data_out(p2in[0]), .data_in(p2_din[0] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_1 (.data_out(p2in[1]), .data_in(p2_din[1] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_2 (.data_out(p2in[2]), .data_in(p2_din[2] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_3 (.data_out(p2in[3]), .data_in(p2_din[3] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_4 (.data_out(p2in[4]), .data_in(p2_din[4] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_5 (.data_out(p2in[5]), .data_in(p2_din[5] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_6 (.data_out(p2in[6]), .data_in(p2_din[6] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p2in_7 (.data_out(p2in[7]), .data_in(p2_din[7] & P2_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p2out;
wire       p2out_wr  = P2OUT[0] ? reg_hi_wr[P2OUT] : reg_lo_wr[P2OUT];
wire [7:0] p2out_nxt = P2OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2out <=  8'h00;
  else if (p2out_wr)  p2out <=  p2out_nxt & P2_EN_MSK;
assign p2_dout = p2out;
reg  [7:0] p2dir;
wire       p2dir_wr  = P2DIR[0] ? reg_hi_wr[P2DIR] : reg_lo_wr[P2DIR];
wire [7:0] p2dir_nxt = P2DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2dir <=  8'h00;
  else if (p2dir_wr)  p2dir <=  p2dir_nxt & P2_EN_MSK;
assign p2_dout_en = p2dir;
reg  [7:0] p2ifg;
wire       p2ifg_wr  = P2IFG[0] ? reg_hi_wr[P2IFG] : reg_lo_wr[P2IFG];
wire [7:0] p2ifg_nxt = P2IFG[0] ? per_din[15:8]    : per_din[7:0];
wire [7:0] p2ifg_set;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2ifg <=  8'h00;
  else if (p2ifg_wr)  p2ifg <=  (p2ifg_nxt | p2ifg_set) & P2_EN_MSK;
  else                p2ifg <=  (p2ifg     | p2ifg_set) & P2_EN_MSK;
reg  [7:0] p2ies;
wire       p2ies_wr  = P2IES[0] ? reg_hi_wr[P2IES] : reg_lo_wr[P2IES];
wire [7:0] p2ies_nxt = P2IES[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p2ies <=  8'h00;
  else if (p2ies_wr)  p2ies <=  p2ies_nxt & P2_EN_MSK;
reg  [7:0] p2ie;
wire       p2ie_wr  = P2IE[0] ? reg_hi_wr[P2IE] : reg_lo_wr[P2IE];
wire [7:0] p2ie_nxt = P2IE[0] ? per_din[15:8]   : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p2ie <=  8'h00;
  else if (p2ie_wr)  p2ie <=  p2ie_nxt & P2_EN_MSK;
reg  [7:0] p2sel;
wire       p2sel_wr  = P2SEL[0] ? reg_hi_wr[P2SEL] : reg_lo_wr[P2SEL];
wire [7:0] p2sel_nxt = P2SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p2sel <=  8'h00;
  else if (p2sel_wr) p2sel <=  p2sel_nxt & P2_EN_MSK;
assign p2_sel = p2sel;
wire  [7:0] p3in;
omsp_sync_cell sync_cell_p3in_0 (.data_out(p3in[0]), .data_in(p3_din[0] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_1 (.data_out(p3in[1]), .data_in(p3_din[1] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_2 (.data_out(p3in[2]), .data_in(p3_din[2] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_3 (.data_out(p3in[3]), .data_in(p3_din[3] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_4 (.data_out(p3in[4]), .data_in(p3_din[4] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_5 (.data_out(p3in[5]), .data_in(p3_din[5] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_6 (.data_out(p3in[6]), .data_in(p3_din[6] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p3in_7 (.data_out(p3in[7]), .data_in(p3_din[7] & P3_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p3out;
wire       p3out_wr  = P3OUT[0] ? reg_hi_wr[P3OUT] : reg_lo_wr[P3OUT];
wire [7:0] p3out_nxt = P3OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p3out <=  8'h00;
  else if (p3out_wr)  p3out <=  p3out_nxt & P3_EN_MSK;
assign p3_dout = p3out;
reg  [7:0] p3dir;
wire       p3dir_wr  = P3DIR[0] ? reg_hi_wr[P3DIR] : reg_lo_wr[P3DIR];
wire [7:0] p3dir_nxt = P3DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p3dir <=  8'h00;
  else if (p3dir_wr)  p3dir <=  p3dir_nxt & P3_EN_MSK;
assign p3_dout_en = p3dir;
reg  [7:0] p3sel;
wire       p3sel_wr  = P3SEL[0] ? reg_hi_wr[P3SEL] : reg_lo_wr[P3SEL];
wire [7:0] p3sel_nxt = P3SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p3sel <=  8'h00;
  else if (p3sel_wr) p3sel <=  p3sel_nxt & P3_EN_MSK;
assign p3_sel = p3sel;
wire  [7:0] p4in;
omsp_sync_cell sync_cell_p4in_0 (.data_out(p4in[0]), .data_in(p4_din[0] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_1 (.data_out(p4in[1]), .data_in(p4_din[1] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_2 (.data_out(p4in[2]), .data_in(p4_din[2] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_3 (.data_out(p4in[3]), .data_in(p4_din[3] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_4 (.data_out(p4in[4]), .data_in(p4_din[4] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_5 (.data_out(p4in[5]), .data_in(p4_din[5] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_6 (.data_out(p4in[6]), .data_in(p4_din[6] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p4in_7 (.data_out(p4in[7]), .data_in(p4_din[7] & P4_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p4out;
wire       p4out_wr  = P4OUT[0] ? reg_hi_wr[P4OUT] : reg_lo_wr[P4OUT];
wire [7:0] p4out_nxt = P4OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p4out <=  8'h00;
  else if (p4out_wr)  p4out <=  p4out_nxt & P4_EN_MSK;
assign p4_dout = p4out;
reg  [7:0] p4dir;
wire       p4dir_wr  = P4DIR[0] ? reg_hi_wr[P4DIR] : reg_lo_wr[P4DIR];
wire [7:0] p4dir_nxt = P4DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p4dir <=  8'h00;
  else if (p4dir_wr)  p4dir <=  p4dir_nxt & P4_EN_MSK;
assign p4_dout_en = p4dir;
reg  [7:0] p4sel;
wire       p4sel_wr  = P4SEL[0] ? reg_hi_wr[P4SEL] : reg_lo_wr[P4SEL];
wire [7:0] p4sel_nxt = P4SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p4sel <=  8'h00;
  else if (p4sel_wr) p4sel <=  p4sel_nxt & P4_EN_MSK;
assign p4_sel = p4sel;
wire  [7:0] p5in;
omsp_sync_cell sync_cell_p5in_0 (.data_out(p5in[0]), .data_in(p5_din[0] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_1 (.data_out(p5in[1]), .data_in(p5_din[1] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_2 (.data_out(p5in[2]), .data_in(p5_din[2] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_3 (.data_out(p5in[3]), .data_in(p5_din[3] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_4 (.data_out(p5in[4]), .data_in(p5_din[4] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_5 (.data_out(p5in[5]), .data_in(p5_din[5] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_6 (.data_out(p5in[6]), .data_in(p5_din[6] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p5in_7 (.data_out(p5in[7]), .data_in(p5_din[7] & P5_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p5out;
wire       p5out_wr  = P5OUT[0] ? reg_hi_wr[P5OUT] : reg_lo_wr[P5OUT];
wire [7:0] p5out_nxt = P5OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p5out <=  8'h00;
  else if (p5out_wr)  p5out <=  p5out_nxt & P5_EN_MSK;
assign p5_dout = p5out;
reg  [7:0] p5dir;
wire       p5dir_wr  = P5DIR[0] ? reg_hi_wr[P5DIR] : reg_lo_wr[P5DIR];
wire [7:0] p5dir_nxt = P5DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p5dir <=  8'h00;
  else if (p5dir_wr)  p5dir <=  p5dir_nxt & P5_EN_MSK;
assign p5_dout_en = p5dir;
reg  [7:0] p5sel;
wire       p5sel_wr  = P5SEL[0] ? reg_hi_wr[P5SEL] : reg_lo_wr[P5SEL];
wire [7:0] p5sel_nxt = P5SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p5sel <=  8'h00;
  else if (p5sel_wr) p5sel <=  p5sel_nxt & P5_EN_MSK;
assign p5_sel = p5sel;
wire  [7:0] p6in;
omsp_sync_cell sync_cell_p6in_0 (.data_out(p6in[0]), .data_in(p6_din[0] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_1 (.data_out(p6in[1]), .data_in(p6_din[1] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_2 (.data_out(p6in[2]), .data_in(p6_din[2] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_3 (.data_out(p6in[3]), .data_in(p6_din[3] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_4 (.data_out(p6in[4]), .data_in(p6_din[4] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_5 (.data_out(p6in[5]), .data_in(p6_din[5] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_6 (.data_out(p6in[6]), .data_in(p6_din[6] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
omsp_sync_cell sync_cell_p6in_7 (.data_out(p6in[7]), .data_in(p6_din[7] & P6_EN[0]), .clk(mclk), .rst(puc_rst));
reg  [7:0] p6out;
wire       p6out_wr  = P6OUT[0] ? reg_hi_wr[P6OUT] : reg_lo_wr[P6OUT];
wire [7:0] p6out_nxt = P6OUT[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p6out <=  8'h00;
  else if (p6out_wr)  p6out <=  p6out_nxt & P6_EN_MSK;
assign p6_dout = p6out;
reg  [7:0] p6dir;
wire       p6dir_wr  = P6DIR[0] ? reg_hi_wr[P6DIR] : reg_lo_wr[P6DIR];
wire [7:0] p6dir_nxt = P6DIR[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)        p6dir <=  8'h00;
  else if (p6dir_wr)  p6dir <=  p6dir_nxt & P6_EN_MSK;
assign p6_dout_en = p6dir;
reg  [7:0] p6sel;
wire       p6sel_wr  = P6SEL[0] ? reg_hi_wr[P6SEL] : reg_lo_wr[P6SEL];
wire [7:0] p6sel_nxt = P6SEL[0] ? per_din[15:8]    : per_din[7:0];
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)       p6sel <=  8'h00;
  else if (p6sel_wr) p6sel <=  p6sel_nxt & P6_EN_MSK;
assign p6_sel = p6sel;
reg    [7:0] p1in_dly;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)  p1in_dly <=  8'h00;
  else          p1in_dly <=  p1in & P1_EN_MSK;
wire   [7:0] p1in_re   =   p1in & ~p1in_dly;
wire   [7:0] p1in_fe   =  ~p1in &  p1in_dly;
assign       p1ifg_set = {p1ies[7] ? p1in_fe[7] : p1in_re[7],
                          p1ies[6] ? p1in_fe[6] : p1in_re[6],
                          p1ies[5] ? p1in_fe[5] : p1in_re[5],
                          p1ies[4] ? p1in_fe[4] : p1in_re[4],
                          p1ies[3] ? p1in_fe[3] : p1in_re[3],
                          p1ies[2] ? p1in_fe[2] : p1in_re[2],
                          p1ies[1] ? p1in_fe[1] : p1in_re[1],
                          p1ies[0] ? p1in_fe[0] : p1in_re[0]} & P1_EN_MSK;
assign       irq_port1 = |(p1ie & p1ifg) & P1_EN[0];
reg    [7:0] p2in_dly;
always @ (posedge mclk or posedge puc_rst)
  if (puc_rst)  p2in_dly <=  8'h00;
  else          p2in_dly <=  p2in & P2_EN_MSK;
wire   [7:0] p2in_re   =   p2in & ~p2in_dly;
wire   [7:0] p2in_fe   =  ~p2in &  p2in_dly;
assign       p2ifg_set = {p2ies[7] ? p2in_fe[7] : p2in_re[7],
                          p2ies[6] ? p2in_fe[6] : p2in_re[6],
                          p2ies[5] ? p2in_fe[5] : p2in_re[5],
                          p2ies[4] ? p2in_fe[4] : p2in_re[4],
                          p2ies[3] ? p2in_fe[3] : p2in_re[3],
                          p2ies[2] ? p2in_fe[2] : p2in_re[2],
                          p2ies[1] ? p2in_fe[1] : p2in_re[1],
                          p2ies[0] ? p2in_fe[0] : p2in_re[0]} & P2_EN_MSK;
assign      irq_port2 = |(p2ie & p2ifg) & P2_EN[0];
wire [15:0] p1in_rd   = {8'h00, (p1in  & {8{reg_rd[P1IN]}})}  << (8 & {4{P1IN[0]}});
wire [15:0] p1out_rd  = {8'h00, (p1out & {8{reg_rd[P1OUT]}})} << (8 & {4{P1OUT[0]}});
wire [15:0] p1dir_rd  = {8'h00, (p1dir & {8{reg_rd[P1DIR]}})} << (8 & {4{P1DIR[0]}});
wire [15:0] p1ifg_rd  = {8'h00, (p1ifg & {8{reg_rd[P1IFG]}})} << (8 & {4{P1IFG[0]}});
wire [15:0] p1ies_rd  = {8'h00, (p1ies & {8{reg_rd[P1IES]}})} << (8 & {4{P1IES[0]}});
wire [15:0] p1ie_rd   = {8'h00, (p1ie  & {8{reg_rd[P1IE]}})}  << (8 & {4{P1IE[0]}});
wire [15:0] p1sel_rd  = {8'h00, (p1sel & {8{reg_rd[P1SEL]}})} << (8 & {4{P1SEL[0]}});
wire [15:0] p2in_rd   = {8'h00, (p2in  & {8{reg_rd[P2IN]}})}  << (8 & {4{P2IN[0]}});
wire [15:0] p2out_rd  = {8'h00, (p2out & {8{reg_rd[P2OUT]}})} << (8 & {4{P2OUT[0]}});
wire [15:0] p2dir_rd  = {8'h00, (p2dir & {8{reg_rd[P2DIR]}})} << (8 & {4{P2DIR[0]}});
wire [15:0] p2ifg_rd  = {8'h00, (p2ifg & {8{reg_rd[P2IFG]}})} << (8 & {4{P2IFG[0]}});
wire [15:0] p2ies_rd  = {8'h00, (p2ies & {8{reg_rd[P2IES]}})} << (8 & {4{P2IES[0]}});
wire [15:0] p2ie_rd   = {8'h00, (p2ie  & {8{reg_rd[P2IE]}})}  << (8 & {4{P2IE[0]}});
wire [15:0] p2sel_rd  = {8'h00, (p2sel & {8{reg_rd[P2SEL]}})} << (8 & {4{P2SEL[0]}});
wire [15:0] p3in_rd   = {8'h00, (p3in  & {8{reg_rd[P3IN]}})}  << (8 & {4{P3IN[0]}});
wire [15:0] p3out_rd  = {8'h00, (p3out & {8{reg_rd[P3OUT]}})} << (8 & {4{P3OUT[0]}});
wire [15:0] p3dir_rd  = {8'h00, (p3dir & {8{reg_rd[P3DIR]}})} << (8 & {4{P3DIR[0]}});
wire [15:0] p3sel_rd  = {8'h00, (p3sel & {8{reg_rd[P3SEL]}})} << (8 & {4{P3SEL[0]}});
wire [15:0] p4in_rd   = {8'h00, (p4in  & {8{reg_rd[P4IN]}})}  << (8 & {4{P4IN[0]}});
wire [15:0] p4out_rd  = {8'h00, (p4out & {8{reg_rd[P4OUT]}})} << (8 & {4{P4OUT[0]}});
wire [15:0] p4dir_rd  = {8'h00, (p4dir & {8{reg_rd[P4DIR]}})} << (8 & {4{P4DIR[0]}});
wire [15:0] p4sel_rd  = {8'h00, (p4sel & {8{reg_rd[P4SEL]}})} << (8 & {4{P4SEL[0]}});
wire [15:0] p5in_rd   = {8'h00, (p5in  & {8{reg_rd[P5IN]}})}  << (8 & {4{P5IN[0]}});
wire [15:0] p5out_rd  = {8'h00, (p5out & {8{reg_rd[P5OUT]}})} << (8 & {4{P5OUT[0]}});
wire [15:0] p5dir_rd  = {8'h00, (p5dir & {8{reg_rd[P5DIR]}})} << (8 & {4{P5DIR[0]}});
wire [15:0] p5sel_rd  = {8'h00, (p5sel & {8{reg_rd[P5SEL]}})} << (8 & {4{P5SEL[0]}});
wire [15:0] p6in_rd   = {8'h00, (p6in  & {8{reg_rd[P6IN]}})}  << (8 & {4{P6IN[0]}});
wire [15:0] p6out_rd  = {8'h00, (p6out & {8{reg_rd[P6OUT]}})} << (8 & {4{P6OUT[0]}});
wire [15:0] p6dir_rd  = {8'h00, (p6dir & {8{reg_rd[P6DIR]}})} << (8 & {4{P6DIR[0]}});
wire [15:0] p6sel_rd  = {8'h00, (p6sel & {8{reg_rd[P6SEL]}})} << (8 & {4{P6SEL[0]}});
wire [15:0] per_dout  =  p1in_rd   |
                         p1out_rd  |
                         p1dir_rd  |
                         p1ifg_rd  |
                         p1ies_rd  |
                         p1ie_rd   |
                         p1sel_rd  |
                         p2in_rd   |
                         p2out_rd  |
                         p2dir_rd  |
                         p2ifg_rd  |
                         p2ies_rd  |
                         p2ie_rd   |
                         p2sel_rd  |
                         p3in_rd   |
                         p3out_rd  |
                         p3dir_rd  |
                         p3sel_rd  |
                         p4in_rd   |
                         p4out_rd  |
                         p4dir_rd  |
                         p4sel_rd  |
                         p5in_rd   |
                         p5out_rd  |
                         p5dir_rd  |
                         p5sel_rd  |
                         p6in_rd   |
                         p6out_rd  |
                         p6dir_rd  |
                         p6sel_rd;
endmodule

Identify the primary security assets for 'omsp_gpio' and return the JSON object per the contract.

PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)
a. Build the closed set.
The supplied entity is omsp_gpio. Outputs are scalar irq_port1 and irq_port2; byte-wide p1_dout through p6_dout, p1_dout_en through p6_dout_en and p1_sel through p6_sel; and word-wide per_dout. Inputs are scalar mclk, puc_rst and per_en; byte-wide p1_din through p6_din; per_addr (14 bits), per_din (16 bits) and per_we (2 bits). The 'closed set' also includes reg_sel, reg_addr, reg_dec, reg_lo_write, reg_hi_write, reg_read, reg_hi_wr, reg_lo_wr and reg_rd; byte-wide p1in through p6in; byte registers p1out through p6out, p1dir through p6dir and p1sel through p6sel; and interrupt registers p1ifg, p2ifg, p1ies, p2ies, p1ie and p2ie. Their declared scalar _wr, byte-wide _nxt and word-wide _rd intermediates are candidates, as are the input-read intermediates, p1ifg_set, p2ifg_set, p1in_dly, p2in_dly, p1in_re, p2in_re, p1in_fe and p2in_fe. There are no records. Parameters, slices and instance names are not candidates. omsp_sync_cell is instantiated but not supplied, so its internal elements and port declarations are outside the candidate universe.
b. Derive relationships.
Address qualification consumes enable and address: `wire reg_sel = per_en & (per_addr[13:DEC_WD-1]==BASE_ADDR[14:DEC_WD]);`. Register matching also uses the port parameter, for example `(P1DIR_D & {DEC_SZ{(reg_addr==(P1DIR >>1)) & P1_EN[0]}}) |`. Block-level byte-write decisions are `wire reg_lo_write = per_we[0] & reg_sel;` and `wire reg_hi_write = per_we[1] & reg_sel;`; `wire [DEC_SZ-1:0] reg_lo_wr = reg_dec & {DEC_SZ{reg_lo_write}};` distributes the low-byte decision per register. The direction write selects a byte with `wire [7:0] p1dir_nxt = P1DIR[0] ? per_din[15:8] : per_din[7:0];` and captures it with `else if (p1dir_wr) p1dir <= p1dir_nxt & P1_EN_MSK;`; `if (puc_rst) p1dir <= 8'h00;` establishes reset priority, and otherwise p1dir holds without a write. Selection and output-data updates use the corresponding structure: `else if (p1sel_wr) p1sel <= p1sel_nxt & P1_EN_MSK;` and `else if (p1out_wr) p1out <= p1out_nxt & P1_EN_MSK;`. Exits are `assign p1_dout_en = p1dir;`, `assign p1_sel = p1sel;` and `assign p1_dout = p1out;`; port 2 repeats these enabled-port relationships. Read qualification is `wire reg_read = ~|per_we & reg_sel;`, and selected, aligned values feed the combination beginning `wire [15:0] per_dout = p1in_rd |`. Parameter reachability matters: `parameter P3_EN = 1'b0;` disables terms such as `(P3DIR_D & {DEC_SZ{(reg_addr==(P3DIR >>1)) & P3_EN[0]}}) |`, while `parameter P3_EN_MSK = {8{P3_EN[0]}};` makes its data mask zero; P4_EN, P5_EN and P6_EN have the same default behavior. Thus their direction and selection registers have no decoded writes or readback under defaults, and their outputs remain zero after reset; their zero masks would also force any written value to zero. When a corresponding port parameter is overridden to 1, its registers store and export configuration. Input sampling connects through the unavailable omsp_sync_cell implementation, as in `omsp_sync_cell sync_cell_p1in_0 (.data_out(p1in[0]), .data_in(p1_din[0] & P1_EN[0]), .clk(mclk), .rst(puc_rst));`, followed by local edge detection such as `wire [7:0] p1in_re = p1in & ~p1in_dly;` and interrupt logic such as `assign irq_port1 = |(p1ie & p1ifg) & P1_EN[0];`; port 2 repeats the local edge and interrupt structure.
c. Derive use-case flows.
Implemented flows are peripheral address and byte-write qualification; clocked, resettable programming of output data, direction, function selection, interrupt polarity and interrupt enables; direct configuration and output-data export; read-qualified, byte-aligned register and input reporting; input connections to unavailable sampling sub-blocks and consumption of their returned values; local input-history capture and rising/falling transition detection; polarity-selected event accumulation into writable pending flags; and enable-qualified interrupt requests. Reset clears the local registers. These are RTL operations, not assumptions about authorization identities, external pad behavior, alternate-function implementations, synchronization latency or unconditional progress.
d. Identify conceptual assets.
Peripheral register write access -- whether a bus write is allowed to land in the GPIO register file at all: Integrity is Established. `wire reg_lo_write = per_we[0] & reg_sel;` and its high-byte counterpart identify block-level byte-write eligibility; incorrect qualification violates the implemented enable, address and strobe predicates. Availability is independently Established for producing those decisions under their predicates and performing a decoded, enabled register write when reset is inactive and a clock edge occurs, as in `else if (p1dir_wr) p1dir <= p1dir_nxt & P1_EN_MSK;`.
Pin direction configuration -- which pins the device drives versus samples: Integrity is Established for the implemented configuration value. The write rule and `assign p1_dout_en = p1dir;` identify stored direction control whose corruption violates write/state/output consistency. Availability is Established for retaining enabled-port configuration between writes, exporting it and delivering selected readback. Disabled ports instead remain zero after reset. Direction determines p1_dout_en and its readback here, not whether inputs are sampled: the p1_din sampling connections do not depend on p1dir. Actual pad driving is outside this module.
Pin function selection -- whether a pin is under GPIO control or handed to an alternate on-chip function: Integrity is Established for stored and exported selection configuration. `else if (p1sel_wr) p1sel <= p1sel_nxt & P1_EN_MSK;` and `assign p1_sel = p1sel;` identify a value whose incorrect setting breaks update/output consistency. Availability is Established for holding enabled-port configuration, exporting it and delivering selected readback; disabled ports remain zero after reset. Downstream alternate-function switching is not supplied and is not a premise of these properties.
For all these concepts, Confidentiality is Context-dependent because the RTL supplies no disclosure restriction; independently Established Integrity therefore selects the scalar objective, while conditional Availability remains supported. This example works through these Established conceptual assets; a full analysis also reports the others supported by the flows, including output-data values, pending interrupt flags, interrupt enables and interrupt requests.
e. Identify structural references.
Peripheral register write access -- whether a bus write is allowed to land in the GPIO register file at all: per_en, per_we and per_addr are sets because omsp_gpio consumes them to decide write eligibility. For internal write-access references, the value must be the block-level byte-write decision, not a 'condition operand' or its per-register distribution. reg_lo_write and reg_hi_write are computes: each is a qualified byte write aimed at this block. reg_sel supplies block addressing for reads as well as writes, demonstrated by `wire reg_read = ~|per_we & reg_sel;`; reg_dec supplies register matches also used by reads. Neither internal operand is the write-access decision. reg_lo_wr and reg_hi_wr split that decision per register, finer than this concept, and are not additional realizations.
Pin direction configuration -- which pins the device drives versus samples: p1dir, p2dir, p3dir, p4dir, p5dir and p6dir are stores; p1_dout_en, p2_dout_en, p3_dout_en, p4_dout_en, p5_dout_en and p6_dout_en are exit port references. The p3dir through p6dir paths store and export configuration when their port parameter is 1; otherwise they stay zero after reset, with zero masks and no decoded writes or readback. per_din is sets because its selected byte is stored as direction configuration. per_dout is exit port because selected direction values leave through it: `wire [15:0] p1dir_rd = {8'h00, (p1dir & {8{reg_rd[P1DIR]}})} << (8 & {4{P1DIR[0]}});` contributes through `p1dir_rd |`.
Pin function selection -- whether a pin is under GPIO control or handed to an alternate on-chip function: p1sel, p2sel, p3sel, p4sel, p5sel and p6sel are stores; per_din is sets; p1_sel, p2_sel, p3_sel, p4_sel, p5_sel, p6_sel and per_dout are exit port references. The p3sel through p6sel paths store and export configuration when their port parameter is 1; otherwise they stay zero after reset, with zero masks and no decoded writes or readback. Selected readout is demonstrated by `wire [15:0] p1sel_rd = {8'h00, (p1sel & {8{reg_rd[P1SEL]}})} << (8 & {4{P1SEL[0]}});` and `p1sel_rd |`.
per_din and per_dout are plain vector ports, not a record carrying complete transactions, so transport exclusion removes neither. If the peripheral interface instead were a complete-transaction record port, that port and its fields would be excluded: the registers, not that interface, would provide the write/readback references, while dedicated configuration outputs would remain exits. reg_addr reformats address bits; individual _wr wires select distributed write terms; _nxt wires route bytes; and _rd wires gate and align values. These intermediates merely forward, route or gate values. per_en, per_we and per_addr do not carry direction or selection configuration, and per_din does not carry write eligibility. Clock and reset inputs are excluded. Input-history and interrupt elements have different meanings. Output references use exit port precedence; storing registers use stores. Shared per_din and per_dout references are not duplicated within a concept.
f. Validate.
The supplied declaration and instantiation structure establishes omsp_gpio as the module label, and the distinct concepts have identifiable RTL flows, specific Integrity properties and conditional Availability without importing external pad behavior or disclosure restrictions. Every reference is an exact bare declaration with its correct owner and realization—as a consumed setting input, stored value, concept-defining decision or entity exit, rather than an internal operand or distribution term—and the mapping covers eligible points, respects parameter reachability and exclusions, avoids within-concept duplicates, and uses the required objective serialization, JSON keys and enum values.

FINAL OBJECT
{
 "module name": "omsp_gpio",
 "conceptual assets": [
  {
   "concept": "Peripheral register write access -- whether a bus write is allowed to land in the GPIO register file at all",
   "security objective": "Integrity",
   "reasoning": "The write flow consumes enable, address and byte strobes: `wire reg_sel = per_en & (per_addr[13:DEC_WD-1]==BASE_ADDR[14:DEC_WD]);`, `wire reg_lo_write = per_we[0] & reg_sel;` and `wire reg_hi_write = per_we[1] & reg_sel;`. Integrity requires block-level byte-write eligibility to obey these predicates. per_en, per_we and per_addr are consumed setting inputs; reg_lo_write and reg_hi_write each realize a 'decision defining the concept'. Availability is independently Established under the implemented conditions: byte-write decisions are produced when their predicates hold, and an enabled register selected by the subsequent decoding updates with reset inactive at a clock edge, as in `else if (p1dir_wr) p1dir <= p1dir_nxt & P1_EN_MSK;`.",
   "related structural assets": [
    {
     "asset rtl": "per_en",
     "entity": "omsp_gpio",
     "realization": "sets"
    },
    {
     "asset rtl": "per_we",
     "entity": "omsp_gpio",
     "realization": "sets"
    },
    {
     "asset rtl": "per_addr",
     "entity": "omsp_gpio",
     "realization": "sets"
    },
    {
     "asset rtl": "reg_lo_write",
     "entity": "omsp_gpio",
     "realization": "computes"
    },
    {
     "asset rtl": "reg_hi_write",
     "entity": "omsp_gpio",
     "realization": "computes"
    }
   ]
  },
  {
   "concept": "Pin direction configuration -- which pins the device drives versus samples",
   "security objective": "Integrity",
   "reasoning": "The direction-configuration flow stores a selected input byte and exports the result: `else if (p1dir_wr) p1dir <= p1dir_nxt & P1_EN_MSK;` and `assign p1_dout_en = p1dir;`; p2dir and p2_dout_en repeat this behavior. Integrity protects write/state/output consistency. Availability is independently Established for enabled-port storage between writes, continuous export and selected readback, demonstrated by `wire [15:0] p1dir_rd = {8'h00, (p1dir & {8{reg_rd[P1DIR]}})} << (8 & {4{P1DIR[0]}});`. p3dir, p4dir, p5dir and p6dir store and export configuration when their port parameter is 1; otherwise their zero decode terms prevent writes and readback, their masks are zero, and their outputs remain zero after reset. Registers are 'stores', per_din sets the configuration byte, and dedicated direction outputs and per_dout are exits. per_din and per_dout are plain vectors, not complete-transaction records.",
   "related structural assets": [
    {
     "asset rtl": "p1_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p2_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p3_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p4_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p5_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p6_dout_en",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p1dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p2dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p3dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p4dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p5dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p6dir",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "per_din",
     "entity": "omsp_gpio",
     "realization": "sets"
    },
    {
     "asset rtl": "per_dout",
     "entity": "omsp_gpio",
     "realization": "exit port"
    }
   ]
  },
  {
   "concept": "Pin function selection -- whether a pin is under GPIO control or handed to an alternate on-chip function",
   "security objective": "Integrity",
   "reasoning": "The selection-configuration flow writes and exports selection values: `else if (p1sel_wr) p1sel <= p1sel_nxt & P1_EN_MSK;` and `assign p1_sel = p1sel;`; p2sel and p2_sel repeat this behavior. Integrity requires stored, exported and reported configuration to agree with the update rules. Availability is independently Established for enabled-port storage between writes, continuous export and selected readback: `wire [15:0] p1sel_rd = {8'h00, (p1sel & {8{reg_rd[P1SEL]}})} << (8 & {4{P1SEL[0]}});`. p3sel, p4sel, p5sel and p6sel store and export configuration when their port parameter is 1; otherwise their zero decode terms prevent writes and readback, their masks are zero, and their outputs remain zero after reset. Selection registers store the configuration and per_din sets its byte value. Dedicated selection outputs and selected readout through per_dout use 'exit port' precedence. per_din and per_dout are plain vectors, not complete-transaction records.",
   "related structural assets": [
    {
     "asset rtl": "p1_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p2_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p3_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p4_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p5_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p6_sel",
     "entity": "omsp_gpio",
     "realization": "exit port"
    },
    {
     "asset rtl": "p1sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p2sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p3sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p4sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p5sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "p6sel",
     "entity": "omsp_gpio",
     "realization": "stores"
    },
    {
     "asset rtl": "per_din",
     "entity": "omsp_gpio",
     "realization": "sets"
    },
    {
     "asset rtl": "per_dout",
     "entity": "omsp_gpio",
     "realization": "exit port"
    }
   ]
  }
 ]
}

### WORKED EXAMPLE 2: tiny_aes

TARGET IP MODULE: tiny_aes

=== RTL ===
module aes_128(clk, state, key, out);
    input          clk;
    input  [127:0] state, key;
    output [127:0] out;
    reg    [127:0] s0, k0;
    wire   [127:0] s1, s2, s3, s4, s5, s6, s7, s8, s9,
                   k1, k2, k3, k4, k5, k6, k7, k8, k9,
                   k0b, k1b, k2b, k3b, k4b, k5b, k6b, k7b, k8b, k9b;
    always @ (posedge clk)
      begin
        s0 <= state ^ key;
        k0 <= key;
      end
    expand_key_128
        a1 (clk, k0, k1, k0b, 8'h1),
        a2 (clk, k1, k2, k1b, 8'h2),
        a3 (clk, k2, k3, k2b, 8'h4),
        a4 (clk, k3, k4, k3b, 8'h8),
        a5 (clk, k4, k5, k4b, 8'h10),
        a6 (clk, k5, k6, k5b, 8'h20),
        a7 (clk, k6, k7, k6b, 8'h40),
        a8 (clk, k7, k8, k7b, 8'h80),
        a9 (clk, k8, k9, k8b, 8'h1b),
       a10 (clk, k9,   , k9b, 8'h36);
    one_round
        r1 (clk, s0, k0b, s1),
        r2 (clk, s1, k1b, s2),
        r3 (clk, s2, k2b, s3),
        r4 (clk, s3, k3b, s4),
        r5 (clk, s4, k4b, s5),
        r6 (clk, s5, k5b, s6),
        r7 (clk, s6, k6b, s7),
        r8 (clk, s7, k7b, s8),
        r9 (clk, s8, k8b, s9);
    final_round
        rf (clk, s9, k9b, out);
endmodule
module expand_key_128(clk, in, out_1, out_2, rcon);
    input              clk;
    input      [127:0] in;
    input      [7:0]   rcon;
    output reg [127:0] out_1;
    output     [127:0] out_2;
    wire       [31:0]  k0, k1, k2, k3,
                       v0, v1, v2, v3;
    reg        [31:0]  k0a, k1a, k2a, k3a;
    wire       [31:0]  k0b, k1b, k2b, k3b, k4a;
    assign {k0, k1, k2, k3} = in;
    assign v0 = {k0[31:24] ^ rcon, k0[23:0]};
    assign v1 = v0 ^ k1;
    assign v2 = v1 ^ k2;
    assign v3 = v2 ^ k3;
    always @ (posedge clk)
        {k0a, k1a, k2a, k3a} <= {v0, v1, v2, v3};
    S4
        S4_0 (clk, {k3[23:0], k3[31:24]}, k4a);
    assign k0b = k0a ^ k4a;
    assign k1b = k1a ^ k4a;
    assign k2b = k2a ^ k4a;
    assign k3b = k3a ^ k4a;
    always @ (posedge clk)
        out_1 <= {k0b, k1b, k2b, k3b};
    assign out_2 = {k0b, k1b, k2b, k3b};
endmodule
module one_round (clk, state_in, key, state_out);
    input              clk;
    input      [127:0] state_in, key;
    output reg [127:0] state_out;
    wire       [31:0]  s0,  s1,  s2,  s3,
                       z0,  z1,  z2,  z3,
                       p00, p01, p02, p03,
                       p10, p11, p12, p13,
                       p20, p21, p22, p23,
                       p30, p31, p32, p33,
                       k0,  k1,  k2,  k3;
    assign {k0, k1, k2, k3} = key;
    assign {s0, s1, s2, s3} = state_in;
    table_lookup
        t0 (clk, s0, p00, p01, p02, p03),
        t1 (clk, s1, p10, p11, p12, p13),
        t2 (clk, s2, p20, p21, p22, p23),
        t3 (clk, s3, p30, p31, p32, p33);
    assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;
    assign z1 = p03 ^ p10 ^ p21 ^ p32 ^ k1;
    assign z2 = p02 ^ p13 ^ p20 ^ p31 ^ k2;
    assign z3 = p01 ^ p12 ^ p23 ^ p30 ^ k3;
    always @ (posedge clk)
        state_out <= {z0, z1, z2, z3};
endmodule
module final_round (clk, state_in, key_in, state_out);
    input              clk;
    input      [127:0] state_in;
    input      [127:0] key_in;
    output reg [127:0] state_out;
    wire [31:0] s0,  s1,  s2,  s3,
                z0,  z1,  z2,  z3,
                k0,  k1,  k2,  k3;
    wire [7:0]  p00, p01, p02, p03,
                p10, p11, p12, p13,
                p20, p21, p22, p23,
                p30, p31, p32, p33;
    assign {k0, k1, k2, k3} = key_in;
    assign {s0, s1, s2, s3} = state_in;
    S4
        S4_1 (clk, s0, {p00, p01, p02, p03}),
        S4_2 (clk, s1, {p10, p11, p12, p13}),
        S4_3 (clk, s2, {p20, p21, p22, p23}),
        S4_4 (clk, s3, {p30, p31, p32, p33});
    assign z0 = {p00, p11, p22, p33} ^ k0;
    assign z1 = {p10, p21, p32, p03} ^ k1;
    assign z2 = {p20, p31, p02, p13} ^ k2;
    assign z3 = {p30, p01, p12, p23} ^ k3;
    always @ (posedge clk)
        state_out <= {z0, z1, z2, z3};
endmodule
module table_lookup (clk, state, p0, p1, p2, p3);
    input clk;
    input [31:0] state;
    output [31:0] p0, p1, p2, p3;
    wire [7:0] b0, b1, b2, b3;
    assign {b0, b1, b2, b3} = state;
    T
        t0 (clk, b0, {p0[23:0], p0[31:24]}),
        t1 (clk, b1, {p1[15:0], p1[31:16]}),
        t2 (clk, b2, {p2[7:0],  p2[31:8]} ),
        t3 (clk, b3, p3);
endmodule
module S4 (clk, in, out);
    input clk;
    input [31:0] in;
    output [31:0] out;
    S
        S_0 (clk, in[31:24], out[31:24]),
        S_1 (clk, in[23:16], out[23:16]),
        S_2 (clk, in[15:8],  out[15:8] ),
        S_3 (clk, in[7:0],   out[7:0]  );
endmodule
module T (clk, in, out);
    input         clk;
    input  [7:0]  in;
    output [31:0] out;
    S
        s0 (clk, in, out[31:24]);
    assign out[23:16] = out[31:24];
    xS
        s4 (clk, in, out[7:0]);
    assign out[15:8] = out[23:16] ^ out[7:0];
endmodule
module S (clk, in, out);
    input clk;
    input [7:0] in;
    output reg [7:0] out;
    always @ (posedge clk)
    case (in)
    8'h00: out <= 8'h63;
    8'h01: out <= 8'h7c;
    8'h02: out <= 8'h77;
    8'h03: out <= 8'h7b;
    8'h04: out <= 8'hf2;
    8'h05: out <= 8'h6b;
    8'h06: out <= 8'h6f;
    8'h07: out <= 8'hc5;
    8'h08: out <= 8'h30;
    8'h09: out <= 8'h01;
    8'h0a: out <= 8'h67;
    8'h0b: out <= 8'h2b;
    8'h0c: out <= 8'hfe;
    8'h0d: out <= 8'hd7;
    8'h0e: out <= 8'hab;
    8'h0f: out <= 8'h76;
    8'h10: out <= 8'hca;
    8'h11: out <= 8'h82;
    8'h12: out <= 8'hc9;
    8'h13: out <= 8'h7d;
    8'h14: out <= 8'hfa;
    8'h15: out <= 8'h59;
    8'h16: out <= 8'h47;
    8'h17: out <= 8'hf0;
    8'h18: out <= 8'had;
    8'h19: out <= 8'hd4;
    8'h1a: out <= 8'ha2;
    8'h1b: out <= 8'haf;
    8'h1c: out <= 8'h9c;
    8'h1d: out <= 8'ha4;
    8'h1e: out <= 8'h72;
    8'h1f: out <= 8'hc0;
    8'h20: out <= 8'hb7;
    8'h21: out <= 8'hfd;
    8'h22: out <= 8'h93;
    8'h23: out <= 8'h26;
    8'h24: out <= 8'h36;
    8'h25: out <= 8'h3f;
    8'h26: out <= 8'hf7;
    8'h27: out <= 8'hcc;
    8'h28: out <= 8'h34;
    8'h29: out <= 8'ha5;
    8'h2a: out <= 8'he5;
    8'h2b: out <= 8'hf1;
    8'h2c: out <= 8'h71;
    8'h2d: out <= 8'hd8;
    8'h2e: out <= 8'h31;
    8'h2f: out <= 8'h15;
    8'h30: out <= 8'h04;
    8'h31: out <= 8'hc7;
    8'h32: out <= 8'h23;
    8'h33: out <= 8'hc3;
    8'h34: out <= 8'h18;
    8'h35: out <= 8'h96;
    8'h36: out <= 8'h05;
    8'h37: out <= 8'h9a;
    8'h38: out <= 8'h07;
    8'h39: out <= 8'h12;
    8'h3a: out <= 8'h80;
    8'h3b: out <= 8'he2;
    8'h3c: out <= 8'heb;
    8'h3d: out <= 8'h27;
    8'h3e: out <= 8'hb2;
    8'h3f: out <= 8'h75;
    8'h40: out <= 8'h09;
    8'h41: out <= 8'h83;
    8'h42: out <= 8'h2c;
    8'h43: out <= 8'h1a;
    8'h44: out <= 8'h1b;
    8'h45: out <= 8'h6e;
    8'h46: out <= 8'h5a;
    8'h47: out <= 8'ha0;
    8'h48: out <= 8'h52;
    8'h49: out <= 8'h3b;
    8'h4a: out <= 8'hd6;
    8'h4b: out <= 8'hb3;
    8'h4c: out <= 8'h29;
    8'h4d: out <= 8'he3;
    8'h4e: out <= 8'h2f;
    8'h4f: out <= 8'h84;
    8'h50: out <= 8'h53;
    8'h51: out <= 8'hd1;
    8'h52: out <= 8'h00;
    8'h53: out <= 8'hed;
    8'h54: out <= 8'h20;
    8'h55: out <= 8'hfc;
    8'h56: out <= 8'hb1;
    8'h57: out <= 8'h5b;
    8'h58: out <= 8'h6a;
    8'h59: out <= 8'hcb;
    8'h5a: out <= 8'hbe;
    8'h5b: out <= 8'h39;
    8'h5c: out <= 8'h4a;
    8'h5d: out <= 8'h4c;
    8'h5e: out <= 8'h58;
    8'h5f: out <= 8'hcf;
    8'h60: out <= 8'hd0;
    8'h61: out <= 8'hef;
    8'h62: out <= 8'haa;
    8'h63: out <= 8'hfb;
    8'h64: out <= 8'h43;
    8'h65: out <= 8'h4d;
    8'h66: out <= 8'h33;
    8'h67: out <= 8'h85;
    8'h68: out <= 8'h45;
    8'h69: out <= 8'hf9;
    8'h6a: out <= 8'h02;
    8'h6b: out <= 8'h7f;
    8'h6c: out <= 8'h50;
    8'h6d: out <= 8'h3c;
    8'h6e: out <= 8'h9f;
    8'h6f: out <= 8'ha8;
    8'h70: out <= 8'h51;
    8'h71: out <= 8'ha3;
    8'h72: out <= 8'h40;
    8'h73: out <= 8'h8f;
    8'h74: out <= 8'h92;
    8'h75: out <= 8'h9d;
    8'h76: out <= 8'h38;
    8'h77: out <= 8'hf5;
    8'h78: out <= 8'hbc;
    8'h79: out <= 8'hb6;
    8'h7a: out <= 8'hda;
    8'h7b: out <= 8'h21;
    8'h7c: out <= 8'h10;
    8'h7d: out <= 8'hff;
    8'h7e: out <= 8'hf3;
    8'h7f: out <= 8'hd2;
    8'h80: out <= 8'hcd;
    8'h81: out <= 8'h0c;
    8'h82: out <= 8'h13;
    8'h83: out <= 8'hec;
    8'h84: out <= 8'h5f;
    8'h85: out <= 8'h97;
    8'h86: out <= 8'h44;
    8'h87: out <= 8'h17;
    8'h88: out <= 8'hc4;
    8'h89: out <= 8'ha7;
    8'h8a: out <= 8'h7e;
    8'h8b: out <= 8'h3d;
    8'h8c: out <= 8'h64;
    8'h8d: out <= 8'h5d;
    8'h8e: out <= 8'h19;
    8'h8f: out <= 8'h73;
    8'h90: out <= 8'h60;
    8'h91: out <= 8'h81;
    8'h92: out <= 8'h4f;
    8'h93: out <= 8'hdc;
    8'h94: out <= 8'h22;
    8'h95: out <= 8'h2a;
    8'h96: out <= 8'h90;
    8'h97: out <= 8'h88;
    8'h98: out <= 8'h46;
    8'h99: out <= 8'hee;
    8'h9a: out <= 8'hb8;
    8'h9b: out <= 8'h14;
    8'h9c: out <= 8'hde;
    8'h9d: out <= 8'h5e;
    8'h9e: out <= 8'h0b;
    8'h9f: out <= 8'hdb;
    8'ha0: out <= 8'he0;
    8'ha1: out <= 8'h32;
    8'ha2: out <= 8'h3a;
    8'ha3: out <= 8'h0a;
    8'ha4: out <= 8'h49;
    8'ha5: out <= 8'h06;
    8'ha6: out <= 8'h24;
    8'ha7: out <= 8'h5c;
    8'ha8: out <= 8'hc2;
    8'ha9: out <= 8'hd3;
    8'haa: out <= 8'hac;
    8'hab: out <= 8'h62;
    8'hac: out <= 8'h91;
    8'had: out <= 8'h95;
    8'hae: out <= 8'he4;
    8'haf: out <= 8'h79;
    8'hb0: out <= 8'he7;
    8'hb1: out <= 8'hc8;
    8'hb2: out <= 8'h37;
    8'hb3: out <= 8'h6d;
    8'hb4: out <= 8'h8d;
    8'hb5: out <= 8'hd5;
    8'hb6: out <= 8'h4e;
    8'hb7: out <= 8'ha9;
    8'hb8: out <= 8'h6c;
    8'hb9: out <= 8'h56;
    8'hba: out <= 8'hf4;
    8'hbb: out <= 8'hea;
    8'hbc: out <= 8'h65;
    8'hbd: out <= 8'h7a;
    8'hbe: out <= 8'hae;
    8'hbf: out <= 8'h08;
    8'hc0: out <= 8'hba;
    8'hc1: out <= 8'h78;
    8'hc2: out <= 8'h25;
    8'hc3: out <= 8'h2e;
    8'hc4: out <= 8'h1c;
    8'hc5: out <= 8'ha6;
    8'hc6: out <= 8'hb4;
    8'hc7: out <= 8'hc6;
    8'hc8: out <= 8'he8;
    8'hc9: out <= 8'hdd;
    8'hca: out <= 8'h74;
    8'hcb: out <= 8'h1f;
    8'hcc: out <= 8'h4b;
    8'hcd: out <= 8'hbd;
    8'hce: out <= 8'h8b;
    8'hcf: out <= 8'h8a;
    8'hd0: out <= 8'h70;
    8'hd1: out <= 8'h3e;
    8'hd2: out <= 8'hb5;
    8'hd3: out <= 8'h66;
    8'hd4: out <= 8'h48;
    8'hd5: out <= 8'h03;
    8'hd6: out <= 8'hf6;
    8'hd7: out <= 8'h0e;
    8'hd8: out <= 8'h61;
    8'hd9: out <= 8'h35;
    8'hda: out <= 8'h57;
    8'hdb: out <= 8'hb9;
    8'hdc: out <= 8'h86;
    8'hdd: out <= 8'hc1;
    8'hde: out <= 8'h1d;
    8'hdf: out <= 8'h9e;
    8'he0: out <= 8'he1;
    8'he1: out <= 8'hf8;
    8'he2: out <= 8'h98;
    8'he3: out <= 8'h11;
    8'he4: out <= 8'h69;
    8'he5: out <= 8'hd9;
    8'he6: out <= 8'h8e;
    8'he7: out <= 8'h94;
    8'he8: out <= 8'h9b;
    8'he9: out <= 8'h1e;
    8'hea: out <= 8'h87;
    8'heb: out <= 8'he9;
    8'hec: out <= 8'hce;
    8'hed: out <= 8'h55;
    8'hee: out <= 8'h28;
    8'hef: out <= 8'hdf;
    8'hf0: out <= 8'h8c;
    8'hf1: out <= 8'ha1;
    8'hf2: out <= 8'h89;
    8'hf3: out <= 8'h0d;
    8'hf4: out <= 8'hbf;
    8'hf5: out <= 8'he6;
    8'hf6: out <= 8'h42;
    8'hf7: out <= 8'h68;
    8'hf8: out <= 8'h41;
    8'hf9: out <= 8'h99;
    8'hfa: out <= 8'h2d;
    8'hfb: out <= 8'h0f;
    8'hfc: out <= 8'hb0;
    8'hfd: out <= 8'h54;
    8'hfe: out <= 8'hbb;
    8'hff: out <= 8'h16;
    endcase
endmodule
module xS (clk, in, out);
    input clk;
    input [7:0] in;
    output reg [7:0] out;
    always @ (posedge clk)
    case (in)
    8'h00: out <= 8'hc6;
    8'h01: out <= 8'hf8;
    8'h02: out <= 8'hee;
    8'h03: out <= 8'hf6;
    8'h04: out <= 8'hff;
    8'h05: out <= 8'hd6;
    8'h06: out <= 8'hde;
    8'h07: out <= 8'h91;
    8'h08: out <= 8'h60;
    8'h09: out <= 8'h02;
    8'h0a: out <= 8'hce;
    8'h0b: out <= 8'h56;
    8'h0c: out <= 8'he7;
    8'h0d: out <= 8'hb5;
    8'h0e: out <= 8'h4d;
    8'h0f: out <= 8'hec;
    8'h10: out <= 8'h8f;
    8'h11: out <= 8'h1f;
    8'h12: out <= 8'h89;
    8'h13: out <= 8'hfa;
    8'h14: out <= 8'hef;
    8'h15: out <= 8'hb2;
    8'h16: out <= 8'h8e;
    8'h17: out <= 8'hfb;
    8'h18: out <= 8'h41;
    8'h19: out <= 8'hb3;
    8'h1a: out <= 8'h5f;
    8'h1b: out <= 8'h45;
    8'h1c: out <= 8'h23;
    8'h1d: out <= 8'h53;
    8'h1e: out <= 8'he4;
    8'h1f: out <= 8'h9b;
    8'h20: out <= 8'h75;
    8'h21: out <= 8'he1;
    8'h22: out <= 8'h3d;
    8'h23: out <= 8'h4c;
    8'h24: out <= 8'h6c;
    8'h25: out <= 8'h7e;
    8'h26: out <= 8'hf5;
    8'h27: out <= 8'h83;
    8'h28: out <= 8'h68;
    8'h29: out <= 8'h51;
    8'h2a: out <= 8'hd1;
    8'h2b: out <= 8'hf9;
    8'h2c: out <= 8'he2;
    8'h2d: out <= 8'hab;
    8'h2e: out <= 8'h62;
    8'h2f: out <= 8'h2a;
    8'h30: out <= 8'h08;
    8'h31: out <= 8'h95;
    8'h32: out <= 8'h46;
    8'h33: out <= 8'h9d;
    8'h34: out <= 8'h30;
    8'h35: out <= 8'h37;
    8'h36: out <= 8'h0a;
    8'h37: out <= 8'h2f;
    8'h38: out <= 8'h0e;
    8'h39: out <= 8'h24;
    8'h3a: out <= 8'h1b;
    8'h3b: out <= 8'hdf;
    8'h3c: out <= 8'hcd;
    8'h3d: out <= 8'h4e;
    8'h3e: out <= 8'h7f;
    8'h3f: out <= 8'hea;
    8'h40: out <= 8'h12;
    8'h41: out <= 8'h1d;
    8'h42: out <= 8'h58;
    8'h43: out <= 8'h34;
    8'h44: out <= 8'h36;
    8'h45: out <= 8'hdc;
    8'h46: out <= 8'hb4;
    8'h47: out <= 8'h5b;
    8'h48: out <= 8'ha4;
    8'h49: out <= 8'h76;
    8'h4a: out <= 8'hb7;
    8'h4b: out <= 8'h7d;
    8'h4c: out <= 8'h52;
    8'h4d: out <= 8'hdd;
    8'h4e: out <= 8'h5e;
    8'h4f: out <= 8'h13;
    8'h50: out <= 8'ha6;
    8'h51: out <= 8'hb9;
    8'h52: out <= 8'h00;
    8'h53: out <= 8'hc1;
    8'h54: out <= 8'h40;
    8'h55: out <= 8'he3;
    8'h56: out <= 8'h79;
    8'h57: out <= 8'hb6;
    8'h58: out <= 8'hd4;
    8'h59: out <= 8'h8d;
    8'h5a: out <= 8'h67;
    8'h5b: out <= 8'h72;
    8'h5c: out <= 8'h94;
    8'h5d: out <= 8'h98;
    8'h5e: out <= 8'hb0;
    8'h5f: out <= 8'h85;
    8'h60: out <= 8'hbb;
    8'h61: out <= 8'hc5;
    8'h62: out <= 8'h4f;
    8'h63: out <= 8'hed;
    8'h64: out <= 8'h86;
    8'h65: out <= 8'h9a;
    8'h66: out <= 8'h66;
    8'h67: out <= 8'h11;
    8'h68: out <= 8'h8a;
    8'h69: out <= 8'he9;
    8'h6a: out <= 8'h04;
    8'h6b: out <= 8'hfe;
    8'h6c: out <= 8'ha0;
    8'h6d: out <= 8'h78;
    8'h6e: out <= 8'h25;
    8'h6f: out <= 8'h4b;
    8'h70: out <= 8'ha2;
    8'h71: out <= 8'h5d;
    8'h72: out <= 8'h80;
    8'h73: out <= 8'h05;
    8'h74: out <= 8'h3f;
    8'h75: out <= 8'h21;
    8'h76: out <= 8'h70;
    8'h77: out <= 8'hf1;
    8'h78: out <= 8'h63;
    8'h79: out <= 8'h77;
    8'h7a: out <= 8'haf;
    8'h7b: out <= 8'h42;
    8'h7c: out <= 8'h20;
    8'h7d: out <= 8'he5;
    8'h7e: out <= 8'hfd;
    8'h7f: out <= 8'hbf;
    8'h80: out <= 8'h81;
    8'h81: out <= 8'h18;
    8'h82: out <= 8'h26;
    8'h83: out <= 8'hc3;
    8'h84: out <= 8'hbe;
    8'h85: out <= 8'h35;
    8'h86: out <= 8'h88;
    8'h87: out <= 8'h2e;
    8'h88: out <= 8'h93;
    8'h89: out <= 8'h55;
    8'h8a: out <= 8'hfc;
    8'h8b: out <= 8'h7a;
    8'h8c: out <= 8'hc8;
    8'h8d: out <= 8'hba;
    8'h8e: out <= 8'h32;
    8'h8f: out <= 8'he6;
    8'h90: out <= 8'hc0;
    8'h91: out <= 8'h19;
    8'h92: out <= 8'h9e;
    8'h93: out <= 8'ha3;
    8'h94: out <= 8'h44;
    8'h95: out <= 8'h54;
    8'h96: out <= 8'h3b;
    8'h97: out <= 8'h0b;
    8'h98: out <= 8'h8c;
    8'h99: out <= 8'hc7;
    8'h9a: out <= 8'h6b;
    8'h9b: out <= 8'h28;
    8'h9c: out <= 8'ha7;
    8'h9d: out <= 8'hbc;
    8'h9e: out <= 8'h16;
    8'h9f: out <= 8'had;
    8'ha0: out <= 8'hdb;
    8'ha1: out <= 8'h64;
    8'ha2: out <= 8'h74;
    8'ha3: out <= 8'h14;
    8'ha4: out <= 8'h92;
    8'ha5: out <= 8'h0c;
    8'ha6: out <= 8'h48;
    8'ha7: out <= 8'hb8;
    8'ha8: out <= 8'h9f;
    8'ha9: out <= 8'hbd;
    8'haa: out <= 8'h43;
    8'hab: out <= 8'hc4;
    8'hac: out <= 8'h39;
    8'had: out <= 8'h31;
    8'hae: out <= 8'hd3;
    8'haf: out <= 8'hf2;
    8'hb0: out <= 8'hd5;
    8'hb1: out <= 8'h8b;
    8'hb2: out <= 8'h6e;
    8'hb3: out <= 8'hda;
    8'hb4: out <= 8'h01;
    8'hb5: out <= 8'hb1;
    8'hb6: out <= 8'h9c;
    8'hb7: out <= 8'h49;
    8'hb8: out <= 8'hd8;
    8'hb9: out <= 8'hac;
    8'hba: out <= 8'hf3;
    8'hbb: out <= 8'hcf;
    8'hbc: out <= 8'hca;
    8'hbd: out <= 8'hf4;
    8'hbe: out <= 8'h47;
    8'hbf: out <= 8'h10;
    8'hc0: out <= 8'h6f;
    8'hc1: out <= 8'hf0;
    8'hc2: out <= 8'h4a;
    8'hc3: out <= 8'h5c;
    8'hc4: out <= 8'h38;
    8'hc5: out <= 8'h57;
    8'hc6: out <= 8'h73;
    8'hc7: out <= 8'h97;
    8'hc8: out <= 8'hcb;
    8'hc9: out <= 8'ha1;
    8'hca: out <= 8'he8;
    8'hcb: out <= 8'h3e;
    8'hcc: out <= 8'h96;
    8'hcd: out <= 8'h61;
    8'hce: out <= 8'h0d;
    8'hcf: out <= 8'h0f;
    8'hd0: out <= 8'he0;
    8'hd1: out <= 8'h7c;
    8'hd2: out <= 8'h71;
    8'hd3: out <= 8'hcc;
    8'hd4: out <= 8'h90;
    8'hd5: out <= 8'h06;
    8'hd6: out <= 8'hf7;
    8'hd7: out <= 8'h1c;
    8'hd8: out <= 8'hc2;
    8'hd9: out <= 8'h6a;
    8'hda: out <= 8'hae;
    8'hdb: out <= 8'h69;
    8'hdc: out <= 8'h17;
    8'hdd: out <= 8'h99;
    8'hde: out <= 8'h3a;
    8'hdf: out <= 8'h27;
    8'he0: out <= 8'hd9;
    8'he1: out <= 8'heb;
    8'he2: out <= 8'h2b;
    8'he3: out <= 8'h22;
    8'he4: out <= 8'hd2;
    8'he5: out <= 8'ha9;
    8'he6: out <= 8'h07;
    8'he7: out <= 8'h33;
    8'he8: out <= 8'h2d;
    8'he9: out <= 8'h3c;
    8'hea: out <= 8'h15;
    8'heb: out <= 8'hc9;
    8'hec: out <= 8'h87;
    8'hed: out <= 8'haa;
    8'hee: out <= 8'h50;
    8'hef: out <= 8'ha5;
    8'hf0: out <= 8'h03;
    8'hf1: out <= 8'h59;
    8'hf2: out <= 8'h09;
    8'hf3: out <= 8'h1a;
    8'hf4: out <= 8'h65;
    8'hf5: out <= 8'hd7;
    8'hf6: out <= 8'h84;
    8'hf7: out <= 8'hd0;
    8'hf8: out <= 8'h82;
    8'hf9: out <= 8'h29;
    8'hfa: out <= 8'h5a;
    8'hfb: out <= 8'h1e;
    8'hfc: out <= 8'h7b;
    8'hfd: out <= 8'ha8;
    8'hfe: out <= 8'h6d;
    8'hff: out <= 8'h2c;
    endcase
endmodule

Identify the primary security assets for 'tiny_aes' and return the JSON object per the contract.

PRIVATE ANALYSIS (a demonstration of the procedure; never part of an answer)
a. Build the closed set.
The 'closed set' contains declarations from aes_128, expand_key_128, one_round, final_round, table_lookup, S4, T, S and xS. Every entity has an input clk. aes_128 declares 128-bit inputs state/key, output out, registers s0/k0 and connection wires s1–s9, k1–k9 and k0b–k9b. expand_key_128 declares 128-bit input in and outputs out_1/out_2, 8-bit input rcon, 32-bit wires k0–k3, v0–v3, k0b–k3b/k4a and registers k0a–k3a; out_1 is registered. one_round and final_round declare 128-bit state/key inputs and registered state_out, 32-bit s0–s3/k0–k3/z0–z3 and p00–p03, p10–p13, p20–p23, p30–p33 wires; the p wires are 32-bit in one_round and 8-bit in final_round. table_lookup declares 32-bit input state and outputs p0–p3, with 8-bit b0–b3 wires. S4 declares 32-bit input in/output out; T declares 8-bit input in/32-bit output out; S and xS declare 8-bit input in/registered output out. There are no records or transaction ports. Under 'Do not create candidates from bit slices', slices, concatenations and instance names are evidence rather than additional candidates.
b. Derive relationships.
Initial capture uses `s0 <= state ^ key;` and `k0 <= key;` under `always @ (posedge clk)`. Expansion computes `assign v0 = {k0[31:24] ^ rcon, k0[23:0]};` and `assign v1 = v0 ^ k1;`; v2/v3 continue the recurrence. `{k0a, k1a, k2a, k3a} <= {v0, v1, v2, v3};` registers the partial expansion values. `S4_0 (clk, {k3[23:0], k3[31:24]}, k4a);` supplies substitution results for `assign k0b = k0a ^ k4a;` and the corresponding k1b/k2b/k3b equations. `out_1 <= {k0b, k1b, k2b, k3b};` registers the expanded key, while `assign out_2 = {k0b, k1b, k2b, k3b};` exposes it directly. The state path starts with `r1 (clk, s0, k0b, s1),` and reaches `rf (clk, s9, k9b, out);`. Each round splits its block with `assign {s0, s1, s2, s3} = state_in;`, invokes supplied transformations and locally recombines their results: `assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;` in one_round and `assign z0 = {p00, p11, p22, p33} ^ k0;` in final_round. The other z words follow their respective equations, and `state_out <= {z0, z1, z2, z3};` captures the block. S and xS use `case (in)` to select registered results, illustrated by `8'h00: out <= 8'h63;` and `8'h00: out <= 8'hc6;`. T additionally computes `assign out[15:8] = out[23:16] ^ out[7:0];`. Following 'Respect HDL semantics', nonblocking assignments sample pre-edge values; lookup updates require a matching case selector. No reset or clock-enable logic is declared.
c. Derive use-case flows.
The sustained processing flow consumes an original input block and key, captures their initial XOR, expands the key with stage-specific constants and substitution, processes intermediate blocks through lookup/XOR rounds, and registers and exposes the finished block. Supporting flows implement expansion partial-XOR calculations, key-byte substitution, state-byte substitution and transformed lookup-word production. Evidence includes `s0 <= state ^ key;`, `assign v0 = {k0[31:24] ^ rcon, k0[23:0]};`, `assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;` and `rf (clk, s9, k9b, out);`. The original block and expansion constant have distinct roles before their respective transformations. Following 'Use descriptions of implemented behavior', no start, completion-status, software, authorization or handshake operation is inferred.
d. Identify conceptual assets.
Cipher key material -- the secret key as it enters the core and as it is presented to the final round: `k0 <= key;`, the expansion equations and `assign z0 = {p00, p11, p22, p33} ^ k0;` -> captured and expanded key operands -> incorrect setting violates the initial mixing, expansion or round-mixing relations -> Integrity is Established. Availability is independently Established for edge-triggered key capture and expansion-result production under the applicable operand conditions. Confidentiality is Context-dependent: the RTL supplies no 'restriction on disclosure or observability'; the description's word secret does not establish that restriction.
Intermediate cipher state -- the partially transformed block between rounds: `s0 <= state ^ key;`, `assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;` and `state_out <= {z0, z1, z2, z3};` -> inter-round block values -> corruption violates the implemented lookup/XOR transformation and subsequent round-input relation -> Integrity is Established. Availability is Established for production of intermediate blocks at the applicable rising edges, with matching lookup selectors. Confidentiality is Context-dependent because disclosure restrictions and input-data sensitivity are not represented.
Ciphertext output -- the finished block leaving the core: `assign z0 = {p00, p11, p22, p33} ^ k0;`, the corresponding final-word equations, `state_out <= {z0, z1, z2, z3};` and `rf (clk, s9, k9b, out);` -> the finished registered block -> its reported value must agree with the final transformation -> Integrity is Established. Availability is independently Established for edge-triggered result production and delivery through the connected outputs, without an external deadline or unconditional completion guarantee. Confidentiality is Context-dependent because no disclosure restriction is implemented. The serialization rule 'otherwise Integrity when established' selects Integrity for these concepts; Availability concerns the implemented updates and delivery, not an inferred preservation service. This example develops the selected Established concepts, while a complete analysis also reports other concepts supported by the flows, including the input block before key mixing.
e. Identify structural references.
Key material: aes_128 key is sets because the declaring entity reads it in `k0 <= key;` and `s0 <= state ^ key;`; k0 is stores under 'A storing element remains a realization point even when it captures unchanged data'. expand_key_128 in is sets because `assign {k0, k1, k2, k3} = in;` feeds its local expansion equations. Its out_1 and out_2 are exit port through `out_1 <= {k0b, k1b, k2b, k3b};` and `assign out_2 = {k0b, k1b, k2b, k3b};`. one_round key and final_round key_in are sets because their declaring entities use the split key in their local round-XOR equations. These inputs satisfy 'an eligible input port is read by its declaring entity'.
Intermediate state: aes_128 s0 is stores through `s0 <= state ^ key;`. one_round state_out is exit port through `state_out <= {z0, z1, z2, z3};`. Both one_round state_in and final_round state_in are sets: each entity splits the incoming block with `assign {s0, s1, s2, s3} = state_in;`, passes words to supplied transformations, and uses its own equations to recombine the returned values. The defining examples are `assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;` and `assign z0 = {p00, p11, p22, p33} ^ k0;`. Neither entity merely forwards the incoming block unchanged.
Finished output: final_round state_out and aes_128 out are exit port, supported by `state_out <= {z0, z1, z2, z3};` and `rf (clk, s9, k9b, out);`. The rule 'An output port through which the concept leaves its entity is an eligible exit' applies even when the output is also registered; exit takes precedence over storage, and storage takes precedence over computation for internal s0.
The selected meanings are the key operand, the inter-round block and the finished block. Under 'Group references that realize the same meaning' and 'Do not treat every assignment as setting or every operator as computing a new conceptual value', distinguish these values from their internal operand calculations: v0–v3 and k0a–k3a are partial expansion-XOR terms; expand_key_128 k0b–k3b and the rounds' z0–z3 are word terms; table_lookup p0–p3, T out, S4 out, S out and xS out are lookup words or substituted bytes within those transformations; S in and xS in are the byte operands of the local lookup decisions. They are not additional references of the selected boundary-level meanings merely because they contribute to them. The declarations corroborate the distinction between block operands in `input [127:0] state_in, key;`, S4 words in `input [31:0] in;`, and byte operands in `input [7:0] in;`; width alone is not an exclusion rule.
Under 'Do not report intermediates that merely forward, route, or gate', exclude aes_128 s1–s9, k1–k9 and k0b–k9b; expand_key_128 k0–k3/k4a; one_round and final_round s0–s3/k0–k3 and p wires; and table_lookup b0–b3. Unlike the round state_in ports, S4 in and table_lookup state only divide and pass their incoming words to children, illustrated by `S_0 (clk, in[31:24], out[31:24]),`; T in similarly passes its byte to child instances. These inputs satisfy 'An input used only for unchanged forwarding is not an eligible setting point'. All clk inputs are excluded by the clock-input rule. rcon represents the distinct expansion constant, and aes_128 state represents the original block rather than key material or already-transformed state.
f. Validate.
aes_128 is the root of the supplied structure, and the distinct conceptual meanings, operation-specific Integrity properties, conditional Availability properties and objective serialization were checked without importing secrecy, deadlines or external behavior. Every reference is an exact bare declaration with its declaring entity and supported role: both round state_in ports are sets because their entities transform and locally recombine the block rather than merely forward it, storage and exit precedence are respected, 'all demonstrated eligible realization points' were considered for the selected meanings, and the object has valid keys and labels without duplicate references, transport records, carriers, clocks or invented candidates.

FINAL OBJECT
{
 "module name": "aes_128",
 "conceptual assets": [
  {
   "concept": "Cipher key material -- the secret key as it enters the core and as it is presented to the final round",
   "security objective": "Integrity",
   "reasoning": "Key capture, expansion and round mixing depend on the implemented key operands: `k0 <= key;`, `s0 <= state ^ key;`, `assign v0 = {k0[31:24] ^ rcon, k0[23:0]};` and `assign k0b = k0a ^ k4a;`. Final mixing uses `assign z0 = {p00, p11, p22, p33} ^ k0;`; the other words follow their corresponding equations. Corruption violates these transformation relations, establishing Integrity. Availability also applies to clocked key capture and expansion-result production with applicable lookup operands. The consumed key inputs are sets because each declaring entity reads them for storage or computation; aes_128 k0 is stores, including its unchanged capture. Expansion outputs are exit port through `out_1 <= {k0b, k1b, k2b, k3b};` and `assign out_2 = {k0b, k1b, k2b, k3b};`, applying 'An output port through which the concept leaves its entity is an eligible exit' ahead of overlapping storage.",
   "related structural assets": [
    {
     "asset rtl": "key",
     "entity": "aes_128",
     "realization": "sets"
    },
    {
     "asset rtl": "k0",
     "entity": "aes_128",
     "realization": "stores"
    },
    {
     "asset rtl": "in",
     "entity": "expand_key_128",
     "realization": "sets"
    },
    {
     "asset rtl": "out_1",
     "entity": "expand_key_128",
     "realization": "exit port"
    },
    {
     "asset rtl": "out_2",
     "entity": "expand_key_128",
     "realization": "exit port"
    },
    {
     "asset rtl": "key",
     "entity": "one_round",
     "realization": "sets"
    },
    {
     "asset rtl": "key_in",
     "entity": "final_round",
     "realization": "sets"
    }
   ]
  },
  {
   "concept": "Intermediate cipher state -- the partially transformed block between rounds",
   "security objective": "Integrity",
   "reasoning": "The round-processing flow captures the initial transformed block with `s0 <= state ^ key;`, performs lookup/XOR transformations including `assign z0 = p00 ^ p11 ^ p22 ^ p33 ^ k0;`, and registers the next block with `state_out <= {z0, z1, z2, z3};`. Subsequent rounds depend on these particular results, establishing Integrity. Availability independently applies to next-block production at rising edges with matching lookup selectors. aes_128 s0 is stores, and one_round state_out is exit port ahead of its overlapping storage role. Both round state_in ports are sets under 'an eligible input port is read by its declaring entity': after `assign {s0, s1, s2, s3} = state_in;`, each entity invokes supplied transformations and locally recombines their results, including final_round's `assign z0 = {p00, p11, p22, p33} ^ k0;`.",
   "related structural assets": [
    {
     "asset rtl": "s0",
     "entity": "aes_128",
     "realization": "stores"
    },
    {
     "asset rtl": "state_in",
     "entity": "one_round",
     "realization": "sets"
    },
    {
     "asset rtl": "state_out",
     "entity": "one_round",
     "realization": "exit port"
    },
    {
     "asset rtl": "state_in",
     "entity": "final_round",
     "realization": "sets"
    }
   ]
  },
  {
   "concept": "Ciphertext output -- the finished block leaving the core",
   "security objective": "Integrity",
   "reasoning": "The final flow forms the finished block using `assign z0 = {p00, p11, p22, p33} ^ k0;` and the corresponding z1/z2/z3 equations, then registers it with `state_out <= {z0, z1, z2, z3};`. Integrity requires the reported block to agree with those final transformations. Availability independently applies to result production at rising edges and delivery through `rf (clk, s9, k9b, out);`, without assuming an external deadline. final_round state_out and aes_128 out are exit port because the block leaves their respective entities through them; 'An output port through which the concept leaves its entity is an eligible exit' applies, with exit taking precedence over state_out's storage role.",
   "related structural assets": [
    {
     "asset rtl": "state_out",
     "entity": "final_round",
     "realization": "exit port"
    },
    {
     "asset rtl": "out",
     "entity": "aes_128",
     "realization": "exit port"
    }
   ]
  }
 ]
}