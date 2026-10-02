Your task: identify the PRIMARY SECURITY ASSETS in ONE hardware IP module for pre-silicon security verification, following the IEEE P3164 Conceptual-and-Structural Analysis (CSA).

INPUTS (in the user message):
(4) RTL -- the module source, and ground truth for what each element does. Its entity/port declarations and its architecture signal declarations TOGETHER are the CLOSED SET of design elements; read them off the source yourself. Every asset MUST bind to exactly one element declared there, by its exact declared name. Ports AND internal signals/registers are equally eligible. Never invent, rename, split, or merge a name; copy record-field names verbatim including the dot (e.g. "blk_ctrl.step", "xfer_unit.stage").

DEFINITIONS:
- A security asset is a design element (or the data it holds/derives) whose Confidentiality, Integrity, or Availability (CIA) must be protected because its compromise weakens the security of the module or the wider SoC.
- Conceptual asset: high-level data or system state tied to a use-case flow that carries a CIA objective.
- PRIMARY (structural) asset: a concrete closed-set element that STORES, CARRIES, GENERATES, or GATES a conceptual asset. (Secondary/influencing signals are produced by a later stage -- do NOT emit them here.)

METHOD:
STEP 1 -- CONCEPTUAL ASSETS (output these; see the contract). Apply the rubric to the module's use cases:
 (C) Confidentiality: is there information -- input or internally generated -- an integrator may deem secret, or that could leak/expose confidential material? Genuine secrets are keys, seeds, entropy/random state, or private plaintext. A plain data/address/control bus with no secret is NOT confidential -- evaluate it under (I)/(A) instead.
 (I) Integrity: are there state or configuration settings that must stay immutable during certain operations/modes, whose modification would harm the integrator?
 (A) Availability: is there any element that, if made unavailable or manipulated, would prohibit correct operation of the IP or IC (denial of service at integration)?
 (U) Undermine: are there privileged modes, overrides, bypass, or injection paths that could make the IP produce incorrect output under normal-looking operation?
An element is an asset iff at least one of C/I/A/U is "yes" with a reason grounded in the RTL. An element answering "no" to all four is NOT an asset; make such non-asset decisions explicitly (internally). Report every conceptual asset you identify in "ConceptualAssets", each with a short id. This is a record of STEP 1, NOT a substitute for STEP 2 -- a conceptual asset with no closed-set element still belongs here, and every structural asset must still appear in "Assets".

STEP 2 -- STRUCTURAL (PRIMARY) ASSETS. Map each conceptual asset to the concrete closed-set element(s) that store, carry, generate, or gate it. A conceptual asset may fan out to SEVERAL elements -- emit one object per element. If NO closed-set element supports a conceptual asset, OMIT it -- never fabricate an element.
STEP 2 (continued) -- ROLE, NOT LOCATION. P3164 3.1.2 asks for the RTL that PRODUCES a conceptual asset, that STORES it, and that TRANSPORTS it. Those are usually different elements, so one conceptual asset normally maps to several: emit one object per element.

The worked examples below bind most of their assets to entity ports, because in a small standalone IP the interface is where these roles live. In a larger module the SAME roles are internal. An operation enable or start, a direction or mode select, a computed result, a busy/ready/error condition -- each is a port in one design and a signal or register in another. Judge the role, not where the element is declared.

For each conceptual asset ask BOTH:
 - which port carries it across the boundary?
 - which internal signal or register produces, holds, or gates it inside the module?
Emit an object for each that exists. When a module computes a condition internally and never brings it to a port, that internal element is the only structural asset for it -- omit it and the asset is lost.

P3164's own conceptual assets are mostly registers rather than ports: Config Regs, Status Regs and Key Reg for the AES engine (3.2.3); Memory Array, Data-In Register, Output Register and Address Register for the SRAM controller (3.2.4), whose structural assets are internal address signals rather than ports.

RULES:
- "Asset RTL" MUST be the exact declared name of one element from the module's ports/signals. If an idea cannot bind to a real element, drop it.
- Record-typed PORTS are named WHOLE. A record port is the module's external interface; when it carries an asset, the asset is the port itself ("cfg_port_i"), never one of its fields ("cfg_port_i.mode"). Record-typed INTERNAL signals are the opposite and are unchanged by this rule -- there the field is the asset ("blk_ctrl.step"), as above.
- "Entity" MUST be the RTL entity/module that declares the element, copied verbatim.
- "Security Objective" is MANDATORY: exactly ONE of "Confidentiality", "Integrity", "Availability" -- the dominant objective. Fold (U) findings into Integrity or Availability. Note any non-dominant objective inside the Justification.
- Global clock and reset ports and pure boilerplate are NOT assets unless clock/reset control is the module's actual function.
- Identifiers quoted in these instructions (e.g. "cfg_port_i", "blk_ctrl.step") are INVENTED illustrations of a naming pattern, and identifiers in the worked examples below belong to those example IPs. NONE of them exists in the module you are given. Never emit a name you have not read in the RTL above, and never let a quoted name steer which real element you choose.
- Ground "Functionality" (what the element does/carries) and "Justification" (why its compromise violates the chosen objective) in the RTL only; do not add outside knowledge or assess exploitability. Every asset carries explicit reasoning.

OUTPUT CONTRACT (strict): return ONE JSON object and nothing else -- no markdown, no code fences, no prose:
{"IP": "<module name>",
 "ConceptualAssets": [
   {"id": "<short id, e.g. C1>",
    "Concept": "<the data or system state, e.g. 'sensor calibration constants'>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Why": "<which of C/I/A/U triggered, grounded in the RTL>"}
 ],
 "Assets": [
   {"Asset Name": "<short descriptive title>",
    "Concept": "<id of the ConceptualAssets entry this element realises>",
    "Asset RTL": "<element name from the closed set>",
    "Entity": "<the element's entity, verbatim>",
    "Functionality": "<what it does/carries>",
    "Security Objective": "Confidentiality" | "Integrity" | "Availability",
    "Justification": "<why its compromise violates the objective>"}
 ]}
If the module has no assets, return {"IP": "<module name>", "Assets": []}.

The following worked case study shows the complete task: the inputs you receive, the IEEE P3164 reasoning that turns them into conceptual assets, the structural mapping that binds each conceptual asset to a named element of the closed set, and the object to emit. Reproduce the DISCIPLINE -- answer all four rubric questions with a reason, state the non-asset decisions explicitly, bind every asset to an exact name from the closed set, and give each one exactly one dominant Security Objective with any secondary consequence noted in the Justification. The REASONING block is internal: emit only the final JSON object.

### CASE STUDY 1: omsp_gpio (openMSP430 digital I/O interface)

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

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields:

 (C) Any element that can leak or expose material needing confidentiality?
     NO. No keys, entropy, passwords or boot images; payload is ordinary I/O
     data. P3164 answers NO for its own GPIO pad ("the gates inside the IP do not leak any
     information"). Observability alone is not a confidentiality argument.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES. P3164: toggling Direction Select mid-sample toggles the sampled Data -- "the mux
     gates can be considered conceptual assets". Here that is (a) per-port direction, which
     decides drive vs. tri-state, and (b) per-port function select, which decides whether
     GPIO or an alternate block owns the pin -- this is P3164's mux. Both are writable over
     the peripheral bus with no documented privilege check and persist until rewritten.
     Reaching either is qualified by (c) the bus enable and byte write strobes.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES, on the SAME elements. P3164: Direction Select "can reverse the data flow ... which
     can be a denial of service. The elements impacted by this attack are the mux gates" --
     note P3164 maps both (I) and (A) to one conceptual asset rather than inventing a second.
 (U) Privileged mode, override, bypass or injection path?
     NO. No debug mode, lock bit or privileged override is documented; configuration is
     simply writable. P3164 answers NO for the same reason.

Conceptual assets: (a) pad direction control, (b) pad function selection, (c) register
access qualification.

P3164 3.1.2 structural mapping -- find the RTL that produces, stores and transports each:
     (a) registers p1dir..p6dir  ->  leave the module as p1_dout_en..p6_dout_en
     (b) registers p1sel..p6sel  ->  leave the module as p1_sel..p6_sel
     (c) ports per_en, per_we
Each pair carries one value ("assign p1_dout_en = p1dir;"). Bind where the control LEAVES
the module and becomes visible system-wide; the register is its storage and belongs to the
later secondary-asset stage.

Objective: (a) and (b) answered YES to both (I) and (A). A wrong value is believed and acted
on, so Integrity dominates and the denial-of-service consequence goes in the Justification,
not into a second asset. (c) is Integrity.

NON-assets: p*_dout / p*_din are ordinary I/O payload -- the data P3164 describes as being
corrupted THROUGH the direction control, not the asset. per_addr / per_din / per_dout are the
bus address and payload path. mclk, puc_rst are infrastructure. reg_sel, reg_addr, reg_dec,
reg_lo_wr, reg_hi_wr, reg_rd, reg_read are decode plumbing downstream of per_en/per_we, which
are what an external agent actually drives. irq_port1/irq_port2 are a real availability
concern but sit outside the reference asset list scoped here.

EMITTED OUTPUT:
{
 "IP": "omsp_gpio",
 "ConceptualAssets": [
  {
   "id": "C1",
   "Concept": "Peripheral register write access -- whether a bus write is allowed to land in the GPIO register file at all",
   "Security Objective": "Integrity",
   "Why": "Integrity: if writes can be forced or suppressed, every register below is reachable by an attacker regardless of its own protection."
  },
  {
   "id": "C2",
   "Concept": "Pin direction configuration -- which pins the device drives versus samples",
   "Security Objective": "Integrity",
   "Why": "Integrity: flipping a pin from input to output lets the device drive a line the board expects it to sample, and vice versa."
  },
  {
   "id": "C3",
   "Concept": "Pin function selection -- whether a pin is under GPIO control or handed to an alternate on-chip function",
   "Security Objective": "Integrity",
   "Why": "Integrity: re-selecting a pin hands it to a different on-chip function, bypassing whatever the GPIO path was enforcing."
  }
 ],
 "Assets": [
  {
   "Asset Name": "Peripheral enable",
   "Concept": "C1",
   "Asset RTL": "per_en",
   "Entity": "omsp_gpio",
   "Functionality": "Qualifies peripheral bus access and gates register read/write within the GPIO address space.",
   "Security Objective": "Integrity",
   "Justification": "If an attacker can assert/deassert the enable at the wrong time, writes could be dropped or unintended registers accessed. Preserving the correctness of bus qualification is essential to keep GPIO configuration state from being corrupted."
  },
  {
   "Asset Name": "Peripheral write enable byte strobes",
   "Concept": "C1",
   "Asset RTL": "per_we",
   "Entity": "omsp_gpio",
   "Functionality": "Selects which byte(s) of the targeted register are written (high/low) during a bus transaction.",
   "Security Objective": "Integrity",
   "Justification": "Manipulating write strobes can partially overwrite control registers, leading to inconsistent configuration. Correct write granularity is required to preserve register integrity."
  },
  {
   "Asset Name": "Port 1 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p1_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 1 bit (derived from direction), controlling tri-state behavior.",
   "Security Objective": "Integrity",
   "Justification": "Improper enable can force-drive lines or leave them floating, potentially damaging hardware or violating protocol. The correctness of drive enable must be preserved."
  },
  {
   "Asset Name": "Port 2 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p2_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 2 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Unauthorized changes can cause bus contention or unintended signal assertion, compromising system correctness."
  },
  {
   "Asset Name": "Port 3 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p3_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 3 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Correct direction/enable settings are critical to safe pin driving; tampering compromises signal integrity."
  },
  {
   "Asset Name": "Port 4 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p4_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 4 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Misconfiguration allows unintended driving or tri-stating of lines, breaking expected operation."
  },
  {
   "Asset Name": "Port 5 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p5_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 5 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Ensures only intended pins drive; corruption endangers correct I/O behavior and external interfaces."
  },
  {
   "Asset Name": "Port 6 output enable mask",
   "Concept": "C2",
   "Asset RTL": "p6_dout_en",
   "Entity": "omsp_gpio",
   "Functionality": "Output enable for each Port 6 bit (derived from direction).",
   "Security Objective": "Integrity",
   "Justification": "Prevents unintended drive conditions that could violate system-level correctness."
  },
  {
   "Asset Name": "Port 1 function select",
   "Concept": "C3",
   "Asset RTL": "p1_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 1 pin.",
   "Security Objective": "Integrity",
   "Justification": "Unauthorised switching of pin function can reroute signals and break higher-level protocols. Maintaining correct selection protects system behavior."
  },
  {
   "Asset Name": "Port 2 function select",
   "Concept": "C3",
   "Asset RTL": "p2_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 2 pin.",
   "Security Objective": "Integrity",
   "Justification": "Wrong function routing can connect/disconnect critical signals, so selection must remain trustworthy."
  },
  {
   "Asset Name": "Port 3 function select",
   "Concept": "C3",
   "Asset RTL": "p3_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 3 pin.",
   "Security Objective": "Integrity",
   "Justification": "Altering selection changes signal routing on the pad, potentially disrupting system operation."
  },
  {
   "Asset Name": "Port 4 function select",
   "Concept": "C3",
   "Asset RTL": "p4_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 4 pin.",
   "Security Objective": "Integrity",
   "Justification": "Protecting this configuration prevents unintended re-mapping of pins that could break interfaces."
  },
  {
   "Asset Name": "Port 5 function select",
   "Concept": "C3",
   "Asset RTL": "p5_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 5 pin.",
   "Security Objective": "Integrity",
   "Justification": "Misrouting pins changes system connectivity; integrity of this control is essential."
  },
  {
   "Asset Name": "Port 6 function select",
   "Concept": "C3",
   "Asset RTL": "p6_sel",
   "Entity": "omsp_gpio",
   "Functionality": "Chooses GPIO vs. alternate function for each Port 6 pin.",
   "Security Objective": "Integrity",
   "Justification": "Ensures intended signal routing; tampering could disconnect required signals or connect the wrong ones."
  }
 ]
}

### CASE STUDY 2: tiny_aes (unrolled AES-128 encryption core)

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

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields. P3164's own AES
walkthrough (3.2.3) analyses a full crypto peripheral with Config Regs, Status Regs, Key Reg,
IV Reg, Input/Output Buffers, an Enc/Dec Engine and a Debug interface. This core is the
cipher datapath only: it has no configuration, status, IV or debug. The questions are
therefore answered against THIS design, and two of the four answers differ from P3164's for
that reason -- which is the method working as intended, not a disagreement with it.

 (C) Any element that can leak or expose material needing confidentiality?
     YES. P3164: "Since this is a crypto IP, the plaintext data and key values are secrets.
     Therefore, any block ... that supports these secrets will be a conceptual asset." The
     same is true of this core: the cipher key is a long-term secret and the input
     block is private plaintext. Both enter on ports and are held, round by round, in the
     pipeline registers.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES, but narrower than P3164's. P3164 lists Key Reg, IV Reg, Input Buffer and Config
     Regs as needing integrity during operation. This core has no IV and no configuration, so
     integrity applies only to the key and state paths: a modified round key, round constant
     or round state silently yields a wrong ciphertext with no error signalled.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES, by a different route than P3164's. P3164 reached availability through the debug
     interface -- "the debug interface allows complete control of the Enc/Dec Engine.
     Therefore Data_Out can be blocked by this interface". This core has no debug interface;
     availability instead attaches to the ciphertext output itself, on which the consumer
     waits and without which the encryption service does not exist.
 (U) Privileged mode, override, bypass or injection path?
     NO -- and here the designs genuinely differ. P3164 answered YES for its AES because
     "the debug interface allows the IP to encrypt/decrypt using the test key and IV values".
     This core has no debug mode, no privileged path and no configuration to override, so the
     undermining route P3164 describes does not exist here.

Conceptual assets: (a) the cipher key and the round keys derived from it, (b) the plaintext
and the state derived from it, (c) delivery of the ciphertext.

P3164 3.1.2 structural mapping -- P3164 names conceptual assets as BLOCKS; resolve each block
to the concrete elements of this closed set that produce, store or transport it:
     P3164 "Key Reg"        ->  key (aes_128), key_in (final_round)
     P3164 "Input Buffer"   ->  state_in (final_round)
     P3164 "Output Buffer"  ->  state_out (final_round)
     P3164 "Enc/Dec Engine" ->  the one_round / final_round / table_lookup datapath
     P3164 "IV Reg", "Config Regs", "Status Regs", "Debug Values" -> no counterpart exists
Bind to the element where the material enters, is applied, or leaves. The intermediate
pipeline stages (s1..s9, k1..k9, the expansion outputs and the S-box partials) carry the same
two conceptual assets and belong to the later secondary-asset stage, not here.

Objective: key, key_in and state_in are Confidentiality -- they are the designated secret
material P3164 identifies for a crypto IP. state_in additionally answers YES to integrity
(altering it changes the ciphertext); Confidentiality dominates because the material is
secret, and the integrity consequence is recorded in its Justification. state_out is
Availability: the consumer waits on the ciphertext.

Scope note: P3164 is maximally inclusive for crypto IPs -- "every block in the IP, except the
Debug Values block, can be considered a conceptual asset", and then observes the result "may
be too numerous to comprehend". The reference list used here keeps only the canonical
representative of each conceptual asset at the point where it enters, is applied, or leaves
the cipher. That is a deliberate narrowing of P3164's stance, not a contradiction of it.

NON-assets: clk is infrastructure. The S-box and T-table internals (S4, T, S, xS and their
partial results) implement the substitution and are downstream of state already captured.
The per-round pipeline registers are stages of conceptual assets (a) and (b) rather than
independent assets.

EMITTED OUTPUT:
{
 "IP": "tiny_aes",
 "ConceptualAssets": [
  {
   "id": "C1",
   "Concept": "Cipher key material -- the secret key as it enters the core and as it is presented to the final round",
   "Security Objective": "Confidentiality",
   "Why": "Confidentiality: the key is the secret the whole core exists to protect; exposure defeats the cipher outright."
  },
  {
   "id": "C2",
   "Concept": "Intermediate cipher state -- the partially transformed block between rounds",
   "Security Objective": "Confidentiality",
   "Why": "Confidentiality: the intermediate state is key-dependent, so leaking it narrows the key search."
  },
  {
   "id": "C3",
   "Concept": "Ciphertext output -- the finished block leaving the core",
   "Security Objective": "Availability",
   "Why": "Availability: if the output block can be stalled or corrupted the core stops delivering usable ciphertext."
  }
 ],
 "Assets": [
  {
   "Asset Name": "Encryption key input",
   "Concept": "C1",
   "Asset RTL": "key",
   "Entity": "aes_128",
   "Functionality": "Provides the 128-bit cipher key used for the initial AddRoundKey and fed into the key expansion pipeline.",
   "Security Objective": "Confidentiality",
   "Justification": "This port carries the long-term secret used to protect data. Disclosure of the key compromises all encrypted data regardless of algorithmic strength."
  },
  {
   "Asset Name": "Final-round input state",
   "Concept": "C2",
   "Asset RTL": "state_in",
   "Entity": "final_round",
   "Functionality": "128-bit input state to the final AES round; split into s0\\u2013s3, substituted via S4 and combined.",
   "Security Objective": "Confidentiality",
   "Justification": "This final-round state is still sensitive as it is a direct function of plaintext and key. Any modification changes the final ciphertext, violating correctness."
  },
  {
   "Asset Name": "Final-round key input",
   "Concept": "C1",
   "Asset RTL": "key_in",
   "Entity": "final_round",
   "Functionality": "128-bit key for the final round used in AddRoundKey.",
   "Security Objective": "Confidentiality",
   "Justification": "It is secret key material; disclosure directly compromises encryption security. It is XORed with substituted bytes to produce the final ciphertext."
  },
  {
   "Asset Name": "Ciphertext output",
   "Concept": "C3",
   "Asset RTL": "state_out",
   "Entity": "final_round",
   "Functionality": "128-bit final encrypted output registered at the end of the final round.",
   "Security Objective": "Availability",
   "Justification": "System operation depends on timely production of ciphertext; if this output is unavailable, encryption service is effectively denied. It is the culmination of all pipeline stages."
  }
 ]
}


### CASE STUDY 3: gpio (OpenTitan general-purpose I/O, TL-UL register interface, 32 pins)

TARGET IP MODULE: gpio

=== RTL ===
// ---- gpio.sv ----
`include "prim_assert.sv"

module gpio
  import gpio_reg_pkg::*;
#(
  parameter logic [NumAlerts-1:0] AlertAsyncOn = {NumAlerts{1'b1}},

  parameter bit GpioAsyncOn = 1
) (
  input clk_i,
  input rst_ni,

  input  tlul_pkg::tl_h2d_t tl_i,
  output tlul_pkg::tl_d2h_t tl_o,

  output logic [31:0] intr_gpio_o,

  input  prim_alert_pkg::alert_rx_t [NumAlerts-1:0] alert_rx_i,
  output prim_alert_pkg::alert_tx_t [NumAlerts-1:0] alert_tx_o,

  input        [31:0] cio_gpio_i,
  output logic [31:0] cio_gpio_o,
  output logic [31:0] cio_gpio_en_o
);

  gpio_reg2hw_t reg2hw;
  gpio_hw2reg_t hw2reg;

  logic [31:0] cio_gpio_q;
  logic [31:0] cio_gpio_en_q;

  logic [31:0] data_in_d;
  localparam int unsigned CntWidth = 4;
  for (genvar i = 0 ; i < 32 ; i++) begin : gen_filter
    prim_filter_ctr #(
      .AsyncOn(GpioAsyncOn),
      .CntWidth(CntWidth)
    ) u_filter (
      .clk_i,
      .rst_ni,
      .enable_i(reg2hw.ctrl_en_input_filter.q[i]),
      .filter_i(cio_gpio_i[i]),
      .thresh_i({CntWidth{1'b1}}),
      .filter_o(data_in_d[i])
    );
  end

  assign hw2reg.data_in.de = 1'b1;
  assign hw2reg.data_in.d  = data_in_d;

  assign cio_gpio_o                     = cio_gpio_q;
  assign cio_gpio_en_o                  = cio_gpio_en_q;

  assign hw2reg.direct_out.d            = cio_gpio_q;
  assign hw2reg.masked_out_upper.data.d = cio_gpio_q[31:16];
  assign hw2reg.masked_out_upper.mask.d = 16'h 0;
  assign hw2reg.masked_out_lower.data.d = cio_gpio_q[15:0];
  assign hw2reg.masked_out_lower.mask.d = 16'h 0;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      cio_gpio_q  <= '0;
    end else if (reg2hw.direct_out.qe) begin
      cio_gpio_q <= reg2hw.direct_out.q;
    end else if (reg2hw.masked_out_upper.data.qe) begin
      cio_gpio_q[31:16] <=
        ( reg2hw.masked_out_upper.mask.q & reg2hw.masked_out_upper.data.q) |
        (~reg2hw.masked_out_upper.mask.q & cio_gpio_q[31:16]);
    end else if (reg2hw.masked_out_lower.data.qe) begin
      cio_gpio_q[15:0] <=
        ( reg2hw.masked_out_lower.mask.q & reg2hw.masked_out_lower.data.q) |
        (~reg2hw.masked_out_lower.mask.q & cio_gpio_q[15:0]);
    end
  end

  assign hw2reg.direct_oe.d = cio_gpio_en_q;
  assign hw2reg.masked_oe_upper.data.d = cio_gpio_en_q[31:16];
  assign hw2reg.masked_oe_upper.mask.d = 16'h 0;
  assign hw2reg.masked_oe_lower.data.d = cio_gpio_en_q[15:0];
  assign hw2reg.masked_oe_lower.mask.d = 16'h 0;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      cio_gpio_en_q  <= '0;
    end else if (reg2hw.direct_oe.qe) begin
      cio_gpio_en_q <= reg2hw.direct_oe.q;
    end else if (reg2hw.masked_oe_upper.data.qe) begin
      cio_gpio_en_q[31:16] <=
        ( reg2hw.masked_oe_upper.mask.q & reg2hw.masked_oe_upper.data.q) |
        (~reg2hw.masked_oe_upper.mask.q & cio_gpio_en_q[31:16]);
    end else if (reg2hw.masked_oe_lower.data.qe) begin
      cio_gpio_en_q[15:0] <=
        ( reg2hw.masked_oe_lower.mask.q & reg2hw.masked_oe_lower.data.q) |
        (~reg2hw.masked_oe_lower.mask.q & cio_gpio_en_q[15:0]);
    end
  end

  logic [31:0] data_in_q;
  always_ff @(posedge clk_i) begin
    data_in_q <= data_in_d;
  end

  logic [31:0] event_intr_rise, event_intr_fall, event_intr_actlow, event_intr_acthigh;
  logic [31:0] event_intr_combined;

  prim_intr_hw #(.Width(32)) intr_hw (
    .clk_i,
    .rst_ni,
    .event_intr_i           (event_intr_combined),
    .reg2hw_intr_enable_q_i (reg2hw.intr_enable.q),
    .reg2hw_intr_test_q_i   (reg2hw.intr_test.q),
    .reg2hw_intr_test_qe_i  (reg2hw.intr_test.qe),
    .reg2hw_intr_state_q_i  (reg2hw.intr_state.q),
    .hw2reg_intr_state_de_o (hw2reg.intr_state.de),
    .hw2reg_intr_state_d_o  (hw2reg.intr_state.d),
    .intr_o                 (intr_gpio_o)
  );

  assign event_intr_rise    = (~data_in_q &  data_in_d) & reg2hw.intr_ctrl_en_rising.q;
  assign event_intr_fall    = ( data_in_q & ~data_in_d) & reg2hw.intr_ctrl_en_falling.q;
  assign event_intr_acthigh =                data_in_d  & reg2hw.intr_ctrl_en_lvlhigh.q;
  assign event_intr_actlow  =               ~data_in_d  & reg2hw.intr_ctrl_en_lvllow.q;

  assign event_intr_combined = event_intr_rise   |
                               event_intr_fall   |
                               event_intr_actlow |
                               event_intr_acthigh;

  logic [NumAlerts-1:0] alert_test, alerts;
  assign alert_test = {
    reg2hw.alert_test.q &
    reg2hw.alert_test.qe
  };

  for (genvar i = 0; i < NumAlerts; i++) begin : gen_alert_tx
    prim_alert_sender #(
      .AsyncOn(AlertAsyncOn[i]),
      .IsFatal(1'b1)
    ) u_prim_alert_sender (
      .clk_i,
      .rst_ni,
      .alert_test_i  ( alert_test[i] ),
      .alert_req_i   ( alerts[0]     ),
      .alert_ack_o   (               ),
      .alert_state_o (               ),
      .alert_rx_i    ( alert_rx_i[i] ),
      .alert_tx_o    ( alert_tx_o[i] )
    );
  end

  gpio_reg_top u_reg (
    .clk_i,
    .rst_ni,

    .tl_i,
    .tl_o,

    .reg2hw,
    .hw2reg,

    .intg_err_o (alerts[0])
  );

  `ASSERT_KNOWN(IntrGpioKnown, intr_gpio_o)
  `ASSERT_KNOWN(CioGpioEnOKnown, cio_gpio_en_o)
  `ASSERT_KNOWN(CioGpioOKnown, cio_gpio_o)
  `ASSERT_KNOWN(AlertsKnown_A, alert_tx_o)

  `ASSERT_PRIM_REG_WE_ONEHOT_ERROR_TRIGGER_ALERT(RegWeOnehotCheck_A, u_reg, alert_tx_o[0])
endmodule

// ---- gpio_reg_pkg.sv ----
package gpio_reg_pkg;

  parameter int NumAlerts = 1;

  parameter int BlockAw = 6;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_state_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_enable_reg_t;

  typedef struct packed {
    logic [31:0] q;
    logic        qe;
  } gpio_reg2hw_intr_test_reg_t;

  typedef struct packed {
    logic        q;
    logic        qe;
  } gpio_reg2hw_alert_test_reg_t;

  typedef struct packed {
    logic [31:0] q;
    logic        qe;
  } gpio_reg2hw_direct_out_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] q;
      logic        qe;
    } mask;
    struct packed {
      logic [15:0] q;
      logic        qe;
    } data;
  } gpio_reg2hw_masked_out_lower_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] q;
      logic        qe;
    } mask;
    struct packed {
      logic [15:0] q;
      logic        qe;
    } data;
  } gpio_reg2hw_masked_out_upper_reg_t;

  typedef struct packed {
    logic [31:0] q;
    logic        qe;
  } gpio_reg2hw_direct_oe_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] q;
      logic        qe;
    } mask;
    struct packed {
      logic [15:0] q;
      logic        qe;
    } data;
  } gpio_reg2hw_masked_oe_lower_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] q;
      logic        qe;
    } mask;
    struct packed {
      logic [15:0] q;
      logic        qe;
    } data;
  } gpio_reg2hw_masked_oe_upper_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_ctrl_en_rising_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_ctrl_en_falling_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_ctrl_en_lvlhigh_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_intr_ctrl_en_lvllow_reg_t;

  typedef struct packed {
    logic [31:0] q;
  } gpio_reg2hw_ctrl_en_input_filter_reg_t;

  typedef struct packed {
    logic [31:0] d;
    logic        de;
  } gpio_hw2reg_intr_state_reg_t;

  typedef struct packed {
    logic [31:0] d;
    logic        de;
  } gpio_hw2reg_data_in_reg_t;

  typedef struct packed {
    logic [31:0] d;
  } gpio_hw2reg_direct_out_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] d;
    } data;
    struct packed {
      logic [15:0] d;
    } mask;
  } gpio_hw2reg_masked_out_lower_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] d;
    } data;
    struct packed {
      logic [15:0] d;
    } mask;
  } gpio_hw2reg_masked_out_upper_reg_t;

  typedef struct packed {
    logic [31:0] d;
  } gpio_hw2reg_direct_oe_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] d;
    } data;
    struct packed {
      logic [15:0] d;
    } mask;
  } gpio_hw2reg_masked_oe_lower_reg_t;

  typedef struct packed {
    struct packed {
      logic [15:0] d;
    } data;
    struct packed {
      logic [15:0] d;
    } mask;
  } gpio_hw2reg_masked_oe_upper_reg_t;

  typedef struct packed {
    gpio_reg2hw_intr_state_reg_t intr_state;
    gpio_reg2hw_intr_enable_reg_t intr_enable;
    gpio_reg2hw_intr_test_reg_t intr_test;
    gpio_reg2hw_alert_test_reg_t alert_test;
    gpio_reg2hw_direct_out_reg_t direct_out;
    gpio_reg2hw_masked_out_lower_reg_t masked_out_lower;
    gpio_reg2hw_masked_out_upper_reg_t masked_out_upper;
    gpio_reg2hw_direct_oe_reg_t direct_oe;
    gpio_reg2hw_masked_oe_lower_reg_t masked_oe_lower;
    gpio_reg2hw_masked_oe_upper_reg_t masked_oe_upper;
    gpio_reg2hw_intr_ctrl_en_rising_reg_t intr_ctrl_en_rising;
    gpio_reg2hw_intr_ctrl_en_falling_reg_t intr_ctrl_en_falling;
    gpio_reg2hw_intr_ctrl_en_lvlhigh_reg_t intr_ctrl_en_lvlhigh;
    gpio_reg2hw_intr_ctrl_en_lvllow_reg_t intr_ctrl_en_lvllow;
    gpio_reg2hw_ctrl_en_input_filter_reg_t ctrl_en_input_filter;
  } gpio_reg2hw_t;

  typedef struct packed {
    gpio_hw2reg_intr_state_reg_t intr_state;
    gpio_hw2reg_data_in_reg_t data_in;
    gpio_hw2reg_direct_out_reg_t direct_out;
    gpio_hw2reg_masked_out_lower_reg_t masked_out_lower;
    gpio_hw2reg_masked_out_upper_reg_t masked_out_upper;
    gpio_hw2reg_direct_oe_reg_t direct_oe;
    gpio_hw2reg_masked_oe_lower_reg_t masked_oe_lower;
    gpio_hw2reg_masked_oe_upper_reg_t masked_oe_upper;
  } gpio_hw2reg_t;

  parameter logic [BlockAw-1:0] GPIO_INTR_STATE_OFFSET = 6'h 0;
  parameter logic [BlockAw-1:0] GPIO_INTR_ENABLE_OFFSET = 6'h 4;
  parameter logic [BlockAw-1:0] GPIO_INTR_TEST_OFFSET = 6'h 8;
  parameter logic [BlockAw-1:0] GPIO_ALERT_TEST_OFFSET = 6'h c;
  parameter logic [BlockAw-1:0] GPIO_DATA_IN_OFFSET = 6'h 10;
  parameter logic [BlockAw-1:0] GPIO_DIRECT_OUT_OFFSET = 6'h 14;
  parameter logic [BlockAw-1:0] GPIO_MASKED_OUT_LOWER_OFFSET = 6'h 18;
  parameter logic [BlockAw-1:0] GPIO_MASKED_OUT_UPPER_OFFSET = 6'h 1c;
  parameter logic [BlockAw-1:0] GPIO_DIRECT_OE_OFFSET = 6'h 20;
  parameter logic [BlockAw-1:0] GPIO_MASKED_OE_LOWER_OFFSET = 6'h 24;
  parameter logic [BlockAw-1:0] GPIO_MASKED_OE_UPPER_OFFSET = 6'h 28;
  parameter logic [BlockAw-1:0] GPIO_INTR_CTRL_EN_RISING_OFFSET = 6'h 2c;
  parameter logic [BlockAw-1:0] GPIO_INTR_CTRL_EN_FALLING_OFFSET = 6'h 30;
  parameter logic [BlockAw-1:0] GPIO_INTR_CTRL_EN_LVLHIGH_OFFSET = 6'h 34;
  parameter logic [BlockAw-1:0] GPIO_INTR_CTRL_EN_LVLLOW_OFFSET = 6'h 38;
  parameter logic [BlockAw-1:0] GPIO_CTRL_EN_INPUT_FILTER_OFFSET = 6'h 3c;

  parameter logic [31:0] GPIO_INTR_TEST_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_INTR_TEST_GPIO_RESVAL = 32'h 0;
  parameter logic [0:0] GPIO_ALERT_TEST_RESVAL = 1'h 0;
  parameter logic [0:0] GPIO_ALERT_TEST_FATAL_FAULT_RESVAL = 1'h 0;
  parameter logic [31:0] GPIO_DIRECT_OUT_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_MASKED_OUT_LOWER_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_MASKED_OUT_UPPER_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_DIRECT_OE_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_MASKED_OE_LOWER_RESVAL = 32'h 0;
  parameter logic [31:0] GPIO_MASKED_OE_UPPER_RESVAL = 32'h 0;

  typedef enum int {
    GPIO_INTR_STATE,
    GPIO_INTR_ENABLE,
    GPIO_INTR_TEST,
    GPIO_ALERT_TEST,
    GPIO_DATA_IN,
    GPIO_DIRECT_OUT,
    GPIO_MASKED_OUT_LOWER,
    GPIO_MASKED_OUT_UPPER,
    GPIO_DIRECT_OE,
    GPIO_MASKED_OE_LOWER,
    GPIO_MASKED_OE_UPPER,
    GPIO_INTR_CTRL_EN_RISING,
    GPIO_INTR_CTRL_EN_FALLING,
    GPIO_INTR_CTRL_EN_LVLHIGH,
    GPIO_INTR_CTRL_EN_LVLLOW,
    GPIO_CTRL_EN_INPUT_FILTER
  } gpio_id_e;

  parameter logic [3:0] GPIO_PERMIT [16] = '{
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 0001,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111,
    4'b 1111
  };

endpackage

// ---- gpio_reg_top.sv ----
`include "prim_assert.sv"

module gpio_reg_top (
  input clk_i,
  input rst_ni,
  input  tlul_pkg::tl_h2d_t tl_i,
  output tlul_pkg::tl_d2h_t tl_o,

  output gpio_reg_pkg::gpio_reg2hw_t reg2hw,
  input  gpio_reg_pkg::gpio_hw2reg_t hw2reg,

  output logic intg_err_o
);

  import gpio_reg_pkg::* ;

  localparam int AW = 6;
  localparam int DW = 32;
  localparam int DBW = DW/8;

  logic           reg_we;
  logic           reg_re;
  logic [AW-1:0]  reg_addr;
  logic [DW-1:0]  reg_wdata;
  logic [DBW-1:0] reg_be;
  logic [DW-1:0]  reg_rdata;
  logic           reg_error;

  logic          addrmiss, wr_err;

  logic [DW-1:0] reg_rdata_next;
  logic reg_busy;

  tlul_pkg::tl_h2d_t tl_reg_h2d;
  tlul_pkg::tl_d2h_t tl_reg_d2h;

  logic intg_err;
  tlul_cmd_intg_chk u_chk (
    .tl_i(tl_i),
    .err_o(intg_err)
  );

  logic reg_we_err;
  logic [15:0] reg_we_check;
  prim_reg_we_check #(
    .OneHotWidth(16)
  ) u_prim_reg_we_check (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .oh_i  (reg_we_check),
    .en_i  (reg_we && !addrmiss),
    .err_o (reg_we_err)
  );

  logic err_q;
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      err_q <= '0;
    end else if (intg_err || reg_we_err) begin
      err_q <= 1'b1;
    end
  end

  assign intg_err_o = err_q | intg_err | reg_we_err;

  tlul_pkg::tl_d2h_t tl_o_pre;
  tlul_rsp_intg_gen #(
    .EnableRspIntgGen(1),
    .EnableDataIntgGen(1)
  ) u_rsp_intg_gen (
    .tl_i(tl_o_pre),
    .tl_o(tl_o)
  );

  assign tl_reg_h2d = tl_i;
  assign tl_o_pre   = tl_reg_d2h;

  tlul_adapter_reg #(
    .RegAw(AW),
    .RegDw(DW),
    .EnableDataIntgGen(0)
  ) u_reg_if (
    .clk_i  (clk_i),
    .rst_ni (rst_ni),

    .tl_i (tl_reg_h2d),
    .tl_o (tl_reg_d2h),

    .en_ifetch_i(prim_mubi_pkg::MuBi4False),
    .intg_error_o(),

    .we_o    (reg_we),
    .re_o    (reg_re),
    .addr_o  (reg_addr),
    .wdata_o (reg_wdata),
    .be_o    (reg_be),
    .busy_i  (reg_busy),
    .rdata_i (reg_rdata),
    .error_i (reg_error)
  );

  assign reg_rdata = reg_rdata_next ;
  assign reg_error = addrmiss | wr_err | intg_err;

  logic intr_state_we;
  logic [31:0] intr_state_qs;
  logic [31:0] intr_state_wd;
  logic intr_enable_we;
  logic [31:0] intr_enable_qs;
  logic [31:0] intr_enable_wd;
  logic intr_test_we;
  logic [31:0] intr_test_wd;
  logic alert_test_we;
  logic alert_test_wd;
  logic [31:0] data_in_qs;
  logic direct_out_re;
  logic direct_out_we;
  logic [31:0] direct_out_qs;
  logic [31:0] direct_out_wd;
  logic masked_out_lower_re;
  logic masked_out_lower_we;
  logic [15:0] masked_out_lower_data_qs;
  logic [15:0] masked_out_lower_data_wd;
  logic [15:0] masked_out_lower_mask_wd;
  logic masked_out_upper_re;
  logic masked_out_upper_we;
  logic [15:0] masked_out_upper_data_qs;
  logic [15:0] masked_out_upper_data_wd;
  logic [15:0] masked_out_upper_mask_wd;
  logic direct_oe_re;
  logic direct_oe_we;
  logic [31:0] direct_oe_qs;
  logic [31:0] direct_oe_wd;
  logic masked_oe_lower_re;
  logic masked_oe_lower_we;
  logic [15:0] masked_oe_lower_data_qs;
  logic [15:0] masked_oe_lower_data_wd;
  logic [15:0] masked_oe_lower_mask_qs;
  logic [15:0] masked_oe_lower_mask_wd;
  logic masked_oe_upper_re;
  logic masked_oe_upper_we;
  logic [15:0] masked_oe_upper_data_qs;
  logic [15:0] masked_oe_upper_data_wd;
  logic [15:0] masked_oe_upper_mask_qs;
  logic [15:0] masked_oe_upper_mask_wd;
  logic intr_ctrl_en_rising_we;
  logic [31:0] intr_ctrl_en_rising_qs;
  logic [31:0] intr_ctrl_en_rising_wd;
  logic intr_ctrl_en_falling_we;
  logic [31:0] intr_ctrl_en_falling_qs;
  logic [31:0] intr_ctrl_en_falling_wd;
  logic intr_ctrl_en_lvlhigh_we;
  logic [31:0] intr_ctrl_en_lvlhigh_qs;
  logic [31:0] intr_ctrl_en_lvlhigh_wd;
  logic intr_ctrl_en_lvllow_we;
  logic [31:0] intr_ctrl_en_lvllow_qs;
  logic [31:0] intr_ctrl_en_lvllow_wd;
  logic ctrl_en_input_filter_we;
  logic [31:0] ctrl_en_input_filter_qs;
  logic [31:0] ctrl_en_input_filter_wd;

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessW1C),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_state (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_state_we),
    .wd     (intr_state_wd),

    .de     (hw2reg.intr_state.de),
    .d      (hw2reg.intr_state.d),

    .qe     (),
    .q      (reg2hw.intr_state.q),
    .ds     (),

    .qs     (intr_state_qs)
  );

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_enable (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_enable_we),
    .wd     (intr_enable_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.intr_enable.q),
    .ds     (),

    .qs     (intr_enable_qs)
  );

  logic intr_test_qe;
  logic [0:0] intr_test_flds_we;
  assign intr_test_qe = &intr_test_flds_we;
  prim_subreg_ext #(
    .DW    (32)
  ) u_intr_test (
    .re     (1'b0),
    .we     (intr_test_we),
    .wd     (intr_test_wd),
    .d      ('0),
    .qre    (),
    .qe     (intr_test_flds_we[0]),
    .q      (reg2hw.intr_test.q),
    .ds     (),
    .qs     ()
  );
  assign reg2hw.intr_test.qe = intr_test_qe;

  logic alert_test_qe;
  logic [0:0] alert_test_flds_we;
  assign alert_test_qe = &alert_test_flds_we;
  prim_subreg_ext #(
    .DW    (1)
  ) u_alert_test (
    .re     (1'b0),
    .we     (alert_test_we),
    .wd     (alert_test_wd),
    .d      ('0),
    .qre    (),
    .qe     (alert_test_flds_we[0]),
    .q      (reg2hw.alert_test.q),
    .ds     (),
    .qs     ()
  );
  assign reg2hw.alert_test.qe = alert_test_qe;

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRO),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_data_in (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (1'b0),
    .wd     ('0),

    .de     (hw2reg.data_in.de),
    .d      (hw2reg.data_in.d),

    .qe     (),
    .q      (),
    .ds     (),

    .qs     (data_in_qs)
  );

  logic direct_out_qe;
  logic [0:0] direct_out_flds_we;
  assign direct_out_qe = &direct_out_flds_we;
  prim_subreg_ext #(
    .DW    (32)
  ) u_direct_out (
    .re     (direct_out_re),
    .we     (direct_out_we),
    .wd     (direct_out_wd),
    .d      (hw2reg.direct_out.d),
    .qre    (),
    .qe     (direct_out_flds_we[0]),
    .q      (reg2hw.direct_out.q),
    .ds     (),
    .qs     (direct_out_qs)
  );
  assign reg2hw.direct_out.qe = direct_out_qe;

  logic masked_out_lower_qe;
  logic [1:0] masked_out_lower_flds_we;
  assign masked_out_lower_qe = &masked_out_lower_flds_we;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_out_lower_data (
    .re     (masked_out_lower_re),
    .we     (masked_out_lower_we),
    .wd     (masked_out_lower_data_wd),
    .d      (hw2reg.masked_out_lower.data.d),
    .qre    (),
    .qe     (masked_out_lower_flds_we[0]),
    .q      (reg2hw.masked_out_lower.data.q),
    .ds     (),
    .qs     (masked_out_lower_data_qs)
  );
  assign reg2hw.masked_out_lower.data.qe = masked_out_lower_qe;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_out_lower_mask (
    .re     (1'b0),
    .we     (masked_out_lower_we),
    .wd     (masked_out_lower_mask_wd),
    .d      (hw2reg.masked_out_lower.mask.d),
    .qre    (),
    .qe     (masked_out_lower_flds_we[1]),
    .q      (reg2hw.masked_out_lower.mask.q),
    .ds     (),
    .qs     ()
  );
  assign reg2hw.masked_out_lower.mask.qe = masked_out_lower_qe;

  logic masked_out_upper_qe;
  logic [1:0] masked_out_upper_flds_we;
  assign masked_out_upper_qe = &masked_out_upper_flds_we;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_out_upper_data (
    .re     (masked_out_upper_re),
    .we     (masked_out_upper_we),
    .wd     (masked_out_upper_data_wd),
    .d      (hw2reg.masked_out_upper.data.d),
    .qre    (),
    .qe     (masked_out_upper_flds_we[0]),
    .q      (reg2hw.masked_out_upper.data.q),
    .ds     (),
    .qs     (masked_out_upper_data_qs)
  );
  assign reg2hw.masked_out_upper.data.qe = masked_out_upper_qe;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_out_upper_mask (
    .re     (1'b0),
    .we     (masked_out_upper_we),
    .wd     (masked_out_upper_mask_wd),
    .d      (hw2reg.masked_out_upper.mask.d),
    .qre    (),
    .qe     (masked_out_upper_flds_we[1]),
    .q      (reg2hw.masked_out_upper.mask.q),
    .ds     (),
    .qs     ()
  );
  assign reg2hw.masked_out_upper.mask.qe = masked_out_upper_qe;

  logic direct_oe_qe;
  logic [0:0] direct_oe_flds_we;
  assign direct_oe_qe = &direct_oe_flds_we;
  prim_subreg_ext #(
    .DW    (32)
  ) u_direct_oe (
    .re     (direct_oe_re),
    .we     (direct_oe_we),
    .wd     (direct_oe_wd),
    .d      (hw2reg.direct_oe.d),
    .qre    (),
    .qe     (direct_oe_flds_we[0]),
    .q      (reg2hw.direct_oe.q),
    .ds     (),
    .qs     (direct_oe_qs)
  );
  assign reg2hw.direct_oe.qe = direct_oe_qe;

  logic masked_oe_lower_qe;
  logic [1:0] masked_oe_lower_flds_we;
  assign masked_oe_lower_qe = &masked_oe_lower_flds_we;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_oe_lower_data (
    .re     (masked_oe_lower_re),
    .we     (masked_oe_lower_we),
    .wd     (masked_oe_lower_data_wd),
    .d      (hw2reg.masked_oe_lower.data.d),
    .qre    (),
    .qe     (masked_oe_lower_flds_we[0]),
    .q      (reg2hw.masked_oe_lower.data.q),
    .ds     (),
    .qs     (masked_oe_lower_data_qs)
  );
  assign reg2hw.masked_oe_lower.data.qe = masked_oe_lower_qe;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_oe_lower_mask (
    .re     (masked_oe_lower_re),
    .we     (masked_oe_lower_we),
    .wd     (masked_oe_lower_mask_wd),
    .d      (hw2reg.masked_oe_lower.mask.d),
    .qre    (),
    .qe     (masked_oe_lower_flds_we[1]),
    .q      (reg2hw.masked_oe_lower.mask.q),
    .ds     (),
    .qs     (masked_oe_lower_mask_qs)
  );
  assign reg2hw.masked_oe_lower.mask.qe = masked_oe_lower_qe;

  logic masked_oe_upper_qe;
  logic [1:0] masked_oe_upper_flds_we;
  assign masked_oe_upper_qe = &masked_oe_upper_flds_we;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_oe_upper_data (
    .re     (masked_oe_upper_re),
    .we     (masked_oe_upper_we),
    .wd     (masked_oe_upper_data_wd),
    .d      (hw2reg.masked_oe_upper.data.d),
    .qre    (),
    .qe     (masked_oe_upper_flds_we[0]),
    .q      (reg2hw.masked_oe_upper.data.q),
    .ds     (),
    .qs     (masked_oe_upper_data_qs)
  );
  assign reg2hw.masked_oe_upper.data.qe = masked_oe_upper_qe;

  prim_subreg_ext #(
    .DW    (16)
  ) u_masked_oe_upper_mask (
    .re     (masked_oe_upper_re),
    .we     (masked_oe_upper_we),
    .wd     (masked_oe_upper_mask_wd),
    .d      (hw2reg.masked_oe_upper.mask.d),
    .qre    (),
    .qe     (masked_oe_upper_flds_we[1]),
    .q      (reg2hw.masked_oe_upper.mask.q),
    .ds     (),
    .qs     (masked_oe_upper_mask_qs)
  );
  assign reg2hw.masked_oe_upper.mask.qe = masked_oe_upper_qe;

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_ctrl_en_rising (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_ctrl_en_rising_we),
    .wd     (intr_ctrl_en_rising_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.intr_ctrl_en_rising.q),
    .ds     (),

    .qs     (intr_ctrl_en_rising_qs)
  );

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_ctrl_en_falling (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_ctrl_en_falling_we),
    .wd     (intr_ctrl_en_falling_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.intr_ctrl_en_falling.q),
    .ds     (),

    .qs     (intr_ctrl_en_falling_qs)
  );

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_ctrl_en_lvlhigh (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_ctrl_en_lvlhigh_we),
    .wd     (intr_ctrl_en_lvlhigh_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.intr_ctrl_en_lvlhigh.q),
    .ds     (),

    .qs     (intr_ctrl_en_lvlhigh_qs)
  );

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_intr_ctrl_en_lvllow (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (intr_ctrl_en_lvllow_we),
    .wd     (intr_ctrl_en_lvllow_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.intr_ctrl_en_lvllow.q),
    .ds     (),

    .qs     (intr_ctrl_en_lvllow_qs)
  );

  prim_subreg #(
    .DW      (32),
    .SwAccess(prim_subreg_pkg::SwAccessRW),
    .RESVAL  (32'h0),
    .Mubi    (1'b0)
  ) u_ctrl_en_input_filter (
    .clk_i   (clk_i),
    .rst_ni  (rst_ni),

    .we     (ctrl_en_input_filter_we),
    .wd     (ctrl_en_input_filter_wd),

    .de     (1'b0),
    .d      ('0),

    .qe     (),
    .q      (reg2hw.ctrl_en_input_filter.q),
    .ds     (),

    .qs     (ctrl_en_input_filter_qs)
  );

  logic [15:0] addr_hit;
  always_comb begin
    addr_hit = '0;
    addr_hit[ 0] = (reg_addr == GPIO_INTR_STATE_OFFSET);
    addr_hit[ 1] = (reg_addr == GPIO_INTR_ENABLE_OFFSET);
    addr_hit[ 2] = (reg_addr == GPIO_INTR_TEST_OFFSET);
    addr_hit[ 3] = (reg_addr == GPIO_ALERT_TEST_OFFSET);
    addr_hit[ 4] = (reg_addr == GPIO_DATA_IN_OFFSET);
    addr_hit[ 5] = (reg_addr == GPIO_DIRECT_OUT_OFFSET);
    addr_hit[ 6] = (reg_addr == GPIO_MASKED_OUT_LOWER_OFFSET);
    addr_hit[ 7] = (reg_addr == GPIO_MASKED_OUT_UPPER_OFFSET);
    addr_hit[ 8] = (reg_addr == GPIO_DIRECT_OE_OFFSET);
    addr_hit[ 9] = (reg_addr == GPIO_MASKED_OE_LOWER_OFFSET);
    addr_hit[10] = (reg_addr == GPIO_MASKED_OE_UPPER_OFFSET);
    addr_hit[11] = (reg_addr == GPIO_INTR_CTRL_EN_RISING_OFFSET);
    addr_hit[12] = (reg_addr == GPIO_INTR_CTRL_EN_FALLING_OFFSET);
    addr_hit[13] = (reg_addr == GPIO_INTR_CTRL_EN_LVLHIGH_OFFSET);
    addr_hit[14] = (reg_addr == GPIO_INTR_CTRL_EN_LVLLOW_OFFSET);
    addr_hit[15] = (reg_addr == GPIO_CTRL_EN_INPUT_FILTER_OFFSET);
  end

  assign addrmiss = (reg_re || reg_we) ? ~|addr_hit : 1'b0 ;

  always_comb begin
    wr_err = (reg_we &
              ((addr_hit[ 0] & (|(GPIO_PERMIT[ 0] & ~reg_be))) |
               (addr_hit[ 1] & (|(GPIO_PERMIT[ 1] & ~reg_be))) |
               (addr_hit[ 2] & (|(GPIO_PERMIT[ 2] & ~reg_be))) |
               (addr_hit[ 3] & (|(GPIO_PERMIT[ 3] & ~reg_be))) |
               (addr_hit[ 4] & (|(GPIO_PERMIT[ 4] & ~reg_be))) |
               (addr_hit[ 5] & (|(GPIO_PERMIT[ 5] & ~reg_be))) |
               (addr_hit[ 6] & (|(GPIO_PERMIT[ 6] & ~reg_be))) |
               (addr_hit[ 7] & (|(GPIO_PERMIT[ 7] & ~reg_be))) |
               (addr_hit[ 8] & (|(GPIO_PERMIT[ 8] & ~reg_be))) |
               (addr_hit[ 9] & (|(GPIO_PERMIT[ 9] & ~reg_be))) |
               (addr_hit[10] & (|(GPIO_PERMIT[10] & ~reg_be))) |
               (addr_hit[11] & (|(GPIO_PERMIT[11] & ~reg_be))) |
               (addr_hit[12] & (|(GPIO_PERMIT[12] & ~reg_be))) |
               (addr_hit[13] & (|(GPIO_PERMIT[13] & ~reg_be))) |
               (addr_hit[14] & (|(GPIO_PERMIT[14] & ~reg_be))) |
               (addr_hit[15] & (|(GPIO_PERMIT[15] & ~reg_be)))));
  end

  assign intr_state_we = addr_hit[0] & reg_we & !reg_error;

  assign intr_state_wd = reg_wdata[31:0];
  assign intr_enable_we = addr_hit[1] & reg_we & !reg_error;

  assign intr_enable_wd = reg_wdata[31:0];
  assign intr_test_we = addr_hit[2] & reg_we & !reg_error;

  assign intr_test_wd = reg_wdata[31:0];
  assign alert_test_we = addr_hit[3] & reg_we & !reg_error;

  assign alert_test_wd = reg_wdata[0];
  assign direct_out_re = addr_hit[5] & reg_re & !reg_error;
  assign direct_out_we = addr_hit[5] & reg_we & !reg_error;

  assign direct_out_wd = reg_wdata[31:0];
  assign masked_out_lower_re = addr_hit[6] & reg_re & !reg_error;
  assign masked_out_lower_we = addr_hit[6] & reg_we & !reg_error;

  assign masked_out_lower_data_wd = reg_wdata[15:0];

  assign masked_out_lower_mask_wd = reg_wdata[31:16];
  assign masked_out_upper_re = addr_hit[7] & reg_re & !reg_error;
  assign masked_out_upper_we = addr_hit[7] & reg_we & !reg_error;

  assign masked_out_upper_data_wd = reg_wdata[15:0];

  assign masked_out_upper_mask_wd = reg_wdata[31:16];
  assign direct_oe_re = addr_hit[8] & reg_re & !reg_error;
  assign direct_oe_we = addr_hit[8] & reg_we & !reg_error;

  assign direct_oe_wd = reg_wdata[31:0];
  assign masked_oe_lower_re = addr_hit[9] & reg_re & !reg_error;
  assign masked_oe_lower_we = addr_hit[9] & reg_we & !reg_error;

  assign masked_oe_lower_data_wd = reg_wdata[15:0];

  assign masked_oe_lower_mask_wd = reg_wdata[31:16];
  assign masked_oe_upper_re = addr_hit[10] & reg_re & !reg_error;
  assign masked_oe_upper_we = addr_hit[10] & reg_we & !reg_error;

  assign masked_oe_upper_data_wd = reg_wdata[15:0];

  assign masked_oe_upper_mask_wd = reg_wdata[31:16];
  assign intr_ctrl_en_rising_we = addr_hit[11] & reg_we & !reg_error;

  assign intr_ctrl_en_rising_wd = reg_wdata[31:0];
  assign intr_ctrl_en_falling_we = addr_hit[12] & reg_we & !reg_error;

  assign intr_ctrl_en_falling_wd = reg_wdata[31:0];
  assign intr_ctrl_en_lvlhigh_we = addr_hit[13] & reg_we & !reg_error;

  assign intr_ctrl_en_lvlhigh_wd = reg_wdata[31:0];
  assign intr_ctrl_en_lvllow_we = addr_hit[14] & reg_we & !reg_error;

  assign intr_ctrl_en_lvllow_wd = reg_wdata[31:0];
  assign ctrl_en_input_filter_we = addr_hit[15] & reg_we & !reg_error;

  assign ctrl_en_input_filter_wd = reg_wdata[31:0];

  always_comb begin
    reg_we_check = '0;
    reg_we_check[0] = intr_state_we;
    reg_we_check[1] = intr_enable_we;
    reg_we_check[2] = intr_test_we;
    reg_we_check[3] = alert_test_we;
    reg_we_check[4] = 1'b0;
    reg_we_check[5] = direct_out_we;
    reg_we_check[6] = masked_out_lower_we;
    reg_we_check[7] = masked_out_upper_we;
    reg_we_check[8] = direct_oe_we;
    reg_we_check[9] = masked_oe_lower_we;
    reg_we_check[10] = masked_oe_upper_we;
    reg_we_check[11] = intr_ctrl_en_rising_we;
    reg_we_check[12] = intr_ctrl_en_falling_we;
    reg_we_check[13] = intr_ctrl_en_lvlhigh_we;
    reg_we_check[14] = intr_ctrl_en_lvllow_we;
    reg_we_check[15] = ctrl_en_input_filter_we;
  end

  always_comb begin
    reg_rdata_next = '0;
    unique case (1'b1)
      addr_hit[0]: begin
        reg_rdata_next[31:0] = intr_state_qs;
      end

      addr_hit[1]: begin
        reg_rdata_next[31:0] = intr_enable_qs;
      end

      addr_hit[2]: begin
        reg_rdata_next[31:0] = '0;
      end

      addr_hit[3]: begin
        reg_rdata_next[0] = '0;
      end

      addr_hit[4]: begin
        reg_rdata_next[31:0] = data_in_qs;
      end

      addr_hit[5]: begin
        reg_rdata_next[31:0] = direct_out_qs;
      end

      addr_hit[6]: begin
        reg_rdata_next[15:0] = masked_out_lower_data_qs;
        reg_rdata_next[31:16] = '0;
      end

      addr_hit[7]: begin
        reg_rdata_next[15:0] = masked_out_upper_data_qs;
        reg_rdata_next[31:16] = '0;
      end

      addr_hit[8]: begin
        reg_rdata_next[31:0] = direct_oe_qs;
      end

      addr_hit[9]: begin
        reg_rdata_next[15:0] = masked_oe_lower_data_qs;
        reg_rdata_next[31:16] = masked_oe_lower_mask_qs;
      end

      addr_hit[10]: begin
        reg_rdata_next[15:0] = masked_oe_upper_data_qs;
        reg_rdata_next[31:16] = masked_oe_upper_mask_qs;
      end

      addr_hit[11]: begin
        reg_rdata_next[31:0] = intr_ctrl_en_rising_qs;
      end

      addr_hit[12]: begin
        reg_rdata_next[31:0] = intr_ctrl_en_falling_qs;
      end

      addr_hit[13]: begin
        reg_rdata_next[31:0] = intr_ctrl_en_lvlhigh_qs;
      end

      addr_hit[14]: begin
        reg_rdata_next[31:0] = intr_ctrl_en_lvllow_qs;
      end

      addr_hit[15]: begin
        reg_rdata_next[31:0] = ctrl_en_input_filter_qs;
      end

      default: begin
        reg_rdata_next = '1;
      end
    endcase
  end

  logic shadow_busy;
  assign shadow_busy = 1'b0;

  assign reg_busy = shadow_busy;

  logic unused_wdata;
  logic unused_be;
  assign unused_wdata = ^reg_wdata;
  assign unused_be = ^reg_be;

  `ASSERT_PULSE(wePulse, reg_we, clk_i, !rst_ni)
  `ASSERT_PULSE(rePulse, reg_re, clk_i, !rst_ni)

  `ASSERT(reAfterRv, $rose(reg_re || reg_we) |=> tl_o_pre.d_valid, clk_i, !rst_ni)

  `ASSERT(en2addrHit, (reg_we || reg_re) |-> $onehot0(addr_hit), clk_i, !rst_ni)

endmodule


Identify the primary security assets for 'gpio' and return the JSON object per the contract.

CSA ANALYSIS (internal working; not emitted).

P3164 3.1.1 rubric -- answer, then the conceptual asset it yields:

 (C) Any element that can leak or expose material needing confidentiality?
     NO. The payload is ordinary pin state. There is no key, seed, entropy or private
     plaintext anywhere in this design. Same answer and same reason as the GPIO pad in
     P3164 3.2.1 -- observability of I/O is not by itself a confidentiality argument.
 (I) Any element that can modify material an integrator may deem sensitive?
     YES, and this module makes the mechanism explicit rather than implicit. Every register
     write is qualified before it is allowed to land: reg_we says a write is happening,
     reg_re says a read is, and reg_error withdraws permission when the address misses, the
     write is malformed, or the bus integrity check fails
     ("assign reg_error = addrmiss | wr_err | intg_err;"). Corrupting any of the three lets
     a write land that should not, or blocks one that should.
 (A) Any element that, if unavailable, can prohibit operational behavior?
     YES. intg_err_o is the only channel by which a detected bus-integrity failure leaves
     this module ("assign intg_err_o = err_q | intg_err | reg_we_err;"). Forced low, faults
     go unreported and the protection is silently absent; forced high, the alert path is
     saturated.
 (U) Privileged mode, override, bypass or injection path?
     NO. There is no debug mode, lock bit or privileged override here; the register file is
     writable only through the qualified path above.

Conceptual assets: (a) register-access qualification, (b) integrity-fault reporting,
(c) pin direction control.

P3164 3.1.2 structural mapping -- find the RTL that produces, stores and transports each:
     (a) reg_we, reg_re, reg_error   internal signals declared in gpio_reg_top
     (b) intg_err_o                  output port of gpio_reg_top
     (c) cio_gpio_en_o               output port of gpio ("assign cio_gpio_en_o = cio_gpio_en_q;")

NOTE the contrast with Case Study 1, and that the contrast is the lesson. There the same
register-access qualification arrived as PORTS (per_en, per_we) and was bound there. Here the
equivalent control is internal (reg_we, reg_re) and is bound there instead. The ROLE decided
the binding; the location did not.

Objective: (a) Integrity -- a wrong value causes a write to be believed that should not be.
(b) Availability -- the consequence is an unreported or unfireable alert; the integrity
consequence goes in the Justification rather than becoming a second asset. (c) Integrity, on
the same reasoning as Case Study 1.

NON-assets, decided explicitly rather than left unmentioned:
 - The 23 per-register write strobes -- intr_state_we, intr_enable_we, intr_test_we,
   alert_test_we, direct_out_we, masked_out_lower_we, masked_out_upper_we, direct_oe_we,
   masked_oe_lower_we, masked_oe_upper_we, intr_ctrl_en_rising_we, ctrl_en_input_filter_we
   and the rest -- are NOT assets. Each is the same permission one step later:
   "assign direct_out_we = addr_hit[5] & reg_we & !reg_error;". Naming them would name
   reg_we twenty-three more times under different labels. Bind the qualification once, where
   it is decided. Case Study 1 rejects p1out_wr, p1dir_wr and its twenty-two siblings for
   exactly this reason.
 - addr_hit, addrmiss, wr_err are the terms reg_error is COMPUTED FROM. The asset is the
   decision, not the inputs that produce it; those belong to the later secondary-asset stage.
 - cio_gpio_i, cio_gpio_o are the pin payload -- the data that is corrupted THROUGH the
   direction control, not the control itself. Same call as p*_din / p*_dout in Case Study 1.
 - tl_i, tl_o are this module's attachment to the system fabric. They carry every
   transaction but belong to whichever block's function is the fabric, not to this one.
 - reg2hw, hw2reg are generated register-file plumbing carrying values already named at
   their source; naming them would name the same state twice.
 - The clock and reset inputs are infrastructure.
 - intr_gpio_o and alert_tx_o are a real availability concern but sit outside the reference
   asset list scoped here.

EMITTED OUTPUT:
{
 "IP": "gpio",
 "ConceptualAssets": [
  {
   "id": "C1",
   "Concept": "Register-access qualification -- whether a bus transaction is permitted to read or write the register file at all",
   "Security Objective": "Integrity",
   "Why": "Integrity: every register in the block is reachable only through this qualification, so forcing or suppressing it reaches all of them at once."
  },
  {
   "id": "C2",
   "Concept": "Integrity-fault reporting -- whether a detected bus integrity failure becomes visible outside the module",
   "Security Objective": "Availability",
   "Why": "Availability: this is the only path by which a detected fault leaves the module; suppressed, the protection is present but silent."
  },
  {
   "id": "C3",
   "Concept": "Pin direction control -- which pins the device drives versus samples",
   "Security Objective": "Integrity",
   "Why": "Integrity: flipping a pin from input to output lets the device drive a line the board expects it to sample."
  }
 ],
 "Assets": [
  {
   "Asset Name": "Register write qualification",
   "Concept": "C1",
   "Asset RTL": "reg_we",
   "Entity": "gpio_reg_top",
   "Functionality": "Asserted for a register-interface write; every per-register write strobe is this signal ANDed with an address hit and the absence of an error.",
   "Security Objective": "Integrity",
   "Justification": "Forcing it lets a write land in any addressed register; suppressing it silently drops configuration updates the software believes it made. It is the single point through which all register writes pass."
  },
  {
   "Asset Name": "Register read qualification",
   "Concept": "C1",
   "Asset RTL": "reg_re",
   "Entity": "gpio_reg_top",
   "Functionality": "Asserted for a register-interface read; gates whether register contents are returned on the bus.",
   "Security Objective": "Integrity",
   "Justification": "Manipulating it returns data for a transaction that was not requested, or withholds data for one that was, so the software's view of device state stops matching the device."
  },
  {
   "Asset Name": "Register access error qualifier",
   "Concept": "C1",
   "Asset RTL": "reg_error",
   "Entity": "gpio_reg_top",
   "Functionality": "Set when the address misses, the write is malformed, or the bus integrity check fails; withdraws permission from every per-register write strobe.",
   "Security Objective": "Integrity",
   "Justification": "Held low, a write that failed its address or integrity check is allowed to land anyway, which is precisely the case the check exists to stop. It is the veto on the qualification above."
  },
  {
   "Asset Name": "Bus integrity error report",
   "Concept": "C2",
   "Asset RTL": "intg_err_o",
   "Entity": "gpio_reg_top",
   "Functionality": "Raised when a bus integrity error is detected or a write error is latched; the module's only outward signal that a fault occurred.",
   "Security Objective": "Availability",
   "Justification": "Forced low the alert never fires and an ongoing attack on the register interface stays invisible; forced high the alert path is saturated. Integrity of the report is the secondary consequence."
  },
  {
   "Asset Name": "Pin output enable",
   "Concept": "C3",
   "Asset RTL": "cio_gpio_en_o",
   "Entity": "gpio",
   "Functionality": "Per-pin output enable driven from the direction configuration, controlling drive versus tri-state for each of the 32 pins.",
   "Security Objective": "Integrity",
   "Justification": "Improper enable force-drives a line the board expects to sample or leaves one floating, which can violate the board protocol or damage hardware. The denial-of-service consequence is real but secondary to the wrong value being driven."
  }
 ]
}
