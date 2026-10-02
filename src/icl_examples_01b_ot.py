"""ICL_ASSET_EXAMPLES_01B_NOPARSE plus a THIRD case study: OpenTitan gpio.

WHY THIS EXISTS. The two existing case studies bind 18 of 18 assets to entity PORTS -- zero
internal signals. Measured against our reference, which is 43% port / 56% internal, that is a
composition the examples cannot teach. v1 measured the consequence when these examples were
introduced (arm A-01): port recall +0.181, signal recall -0.157, the latter unanimously, not
one module improved. A-02 was written to counteract it by instruction and is still carrying
that load alone.

WHAT THE THIRD CASE STUDY ADDS. OpenTitan's gpio was selected by surveying the golden asset
lists of all 21 IPs in Asset_Asset_Dataset_Statistics_IPs.xlsx (credited there to Nath et al.)
and classifying every listed asset against its own RTL declarations. Only three IPs have any
internal-signal assets and this is the only one where they dominate:

    OT_GPIO   5 golden assets: 3 internal (reg_we, reg_re, reg_error) + 2 ports
    keymgr   42 golden assets: 4 internal -- far too large to embed
    apb_gpio  7 golden assets: 1 internal
    the other 18 IPs: zero internal-signal assets

THE TWO GPIO EXAMPLES DO NOT CONTRADICT EACH OTHER -- checked before building, because a
contradiction between worked examples would be worse than no example. Both annotators, on
different designs, made the same two calls:

    omsp_gpio  interface write-enable  per_we  (an input PORT)      -> asset
               per-register strobes    p1out_wr, p1dir_wr ... (24)  -> not assets
    OT_GPIO    interface write-enable  reg_we  (an internal LOGIC)  -> asset
               per-register strobes    direct_out_we ... (23)       -> not assets

The OpenTitan RTL states the derivation outright -- "assign direct_out_we = addr_hit[5] &
reg_we & !reg_error;" -- so the rejected strobes are literally the accepted signal one step
later. The pair therefore demonstrates A-02's thesis (judge the ROLE, not the location) using
two independently produced label sets, and demonstrates it in the direction the current
examples cannot.

THE ASSET LABELS ARE NOT OURS. All five come from the repository's golden listing. Only the
CSA reasoning and the non-asset justifications are written here, and both are grounded in
this IP's own RTL -- no NEORV32 identifier, module name or convention appears. Verified by
audit at import.

BUILT BY TRANSFORMATION, NOT COPY. icl_examples_01b_noparse is imported and appended to, so
this file cannot drift from it and the P-2 input regime (no technical summary, no parsed
port/signal blocks -- RTL only) is inherited rather than re-stated.

RTL PROVENANCE. LAsset-Security-Assets/IP/IP RTL/OT_GPIO/{gpio.sv, gpio_reg_pkg.sv,
gpio_reg_top.sv}, comments stripped exactly as the asset stage strips them for the target
module. Embedded as a literal rather than read from that checkout at import, so this module
has no external dependency.
"""
from __future__ import annotations

import icl_examples_01b_noparse as _base

_CASE3 = """

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
"""

ICL_ASSET_EXAMPLES_01B_OT = _base.ICL_ASSET_EXAMPLES_01B_NOPARSE + _CASE3

# ---------------------------------------------------------------- invariants ---
# The P-2 regime must be inherited intact: no summary block, no parsed JSON blocks.
for _gone in ("=== TECHNICAL SUMMARY ===", "=== PARSED I/O PORTS (JSON) ===",
              "=== PARSED INTERNAL SIGNALS (JSON) ===", '"function":', '"dir":', '"kind":'):
    assert _gone not in ICL_ASSET_EXAMPLES_01B_OT, f"third case study reintroduced {_gone!r}"

# All three case studies present, each with its own RTL block.
for _kept in ("### CASE STUDY 1: omsp_gpio", "### CASE STUDY 2: tiny_aes",
              "### CASE STUDY 3: gpio", "module  omsp_gpio (",
              "module aes_128(clk, state, key, out);", "module gpio"):
    assert _kept in ICL_ASSET_EXAMPLES_01B_OT, f"{_kept!r} missing"
assert ICL_ASSET_EXAMPLES_01B_OT.count("=== RTL ===") == 3, "expected exactly 3 RTL blocks"

# Comments must be stripped from the new RTL, as they are for the target module.
assert "//" not in _CASE3.split("Identify the primary security assets")[0].replace(
    "// ---- gpio.sv ----", "").replace("// ---- gpio_reg_pkg.sv ----", "").replace(
    "// ---- gpio_reg_top.sv ----", ""), "comments survived in the third case study RTL"

# The five asset names are the repository's golden list, unaltered.
import re as _re
_a3 = _re.findall(r'"Asset RTL"\s*:\s*"([^"]+)"', _CASE3)
assert sorted(_a3) == sorted(["reg_we", "reg_re", "reg_error", "intg_err_o",
                              "cio_gpio_en_o"]), f"asset list drifted: {_a3}"
assert ICL_ASSET_EXAMPLES_01B_OT.count('"Asset RTL"') == 23, "expected 18 + 5 asset objects"

# NEORV32 must not appear anywhere in the added text.
for _leak in ("neorv32", "ctrl_i", "bus_req", "bus_rsp", "clkgen_en_o", "rstn_i"):
    assert _leak not in _CASE3, f"third case study leaks {_leak!r}"

# Identifiers may appear in the example IP's OWN RTL -- that is its source, not our claim.
# What must never happen is US naming one in the reasoning, because that is a statement about
# a real element. An earlier draft wrote "clk_i, rst_ni are infrastructure", which
# re-introduced exactly the leak prompts_v2 correction N removed from the core.
_PROSE = _CASE3.split("Identify the primary security assets")[1]
for _named in ("clk_i", "rstn_i", "rst_ni", "ctrl_i", "bus_req_i", "bus_rsp_o"):
    assert _named not in _PROSE, (
        f"the reasoning names {_named!r}; identifiers belong in the RTL, not in our prose")
