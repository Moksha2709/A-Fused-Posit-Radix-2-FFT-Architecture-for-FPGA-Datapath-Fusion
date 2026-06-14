// =============================================================================
// Module  : fp16_op_wrapper
// Project : Pipelined FFT Datapath (FP16)
// Device  : xck24-ubva530-2LV-c (Zynq UltraScale+)
// IP      : Xilinx Floating Point v7.1 rev21  (floating_point_0)
// Config  : Add/Subtract, 16-bit IEEE-754 half precision, latency = 12 cycles
//
// Purpose : Hide the AXI-Stream handshake of floating_point_0 behind a simple,
//           synchronous interface suitable for a pipelined FFT datapath.
//           No backpressure / stalling logic is needed because the downstream
//           consumer is assumed always-ready.
//
// Ports
//   clk       – single clock shared with the rest of the datapath
//   rst       – synchronous active-HIGH reset (converted to active-LOW aresetn)
//   op        – operation select fed to s_axis_operation_tdata
//                 8'h00 = Add   (default when op input is tied to 0)
//                 8'h01 = Subtract
//   a         – 16-bit FP16 operand A  (IEEE-754 half precision)
//   b         – 16-bit FP16 operand B
//   valid_in  – asserted for one cycle when a/b are valid
//   result    – 16-bit FP16 result (available LATENCY cycles after valid_in)
//   valid_out – asserted for one cycle when result is valid
//
// Notes
//   * m_axis_result_tready is tied HIGH (always-ready, no backpressure).
//   * s_axis_operation_tvalid is driven by valid_in (same as a/b channels).
//   * The IP ignores s_axis_a_tready / s_axis_b_tready when
//     C_THROTTLE_SCHEME=1; they are left unconnected here.
// =============================================================================

`timescale 1ns / 1ps

module fp16_op_wrapper (
    // -------------------------------------------------------------------------
    // Clock & Reset
    // -------------------------------------------------------------------------
    input  wire        clk,        // System clock
    input  wire        rst,        // Active-HIGH synchronous reset

    // -------------------------------------------------------------------------
    // Operand Interface  (simple, non-AXI)
    // -------------------------------------------------------------------------
    input  wire [7:0]  op,         // Operation: 8'h00=Add, 8'h01=Subtract
    input  wire [15:0] a,          // FP16 operand A
    input  wire [15:0] b,          // FP16 operand B
    input  wire        valid_in,   // Asserted when a/b/op are valid

    // -------------------------------------------------------------------------
    // Result Interface  (simple, non-AXI)
    // -------------------------------------------------------------------------
    output wire [15:0] result,     // FP16 result (latency = 12 cycles)
    output wire        valid_out   // Asserted when result is valid
);

// =============================================================================
// Internal AXI-Stream wires
// =============================================================================

// --- Slave channel A ---------------------------------------------------------
wire [15:0] s_axis_a_tdata;
wire        s_axis_a_tvalid;
wire        s_axis_a_tready;   // driven by IP; not used (always-ready assumed)

// --- Slave channel B ---------------------------------------------------------
wire [15:0] s_axis_b_tdata;
wire        s_axis_b_tvalid;
wire        s_axis_b_tready;   // driven by IP; not used (always-ready assumed)

// --- Slave operation channel -------------------------------------------------
wire [7:0]  s_axis_operation_tdata;
wire        s_axis_operation_tvalid;
wire        s_axis_operation_tready; // driven by IP; not used

// --- Master result channel ---------------------------------------------------
wire [15:0] m_axis_result_tdata;
wire        m_axis_result_tvalid;
// tready = 1'b1 (downstream is always ready – no backpressure)

// --- Reset -------------------------------------------------------------------
wire        aresetn;           // Active-LOW reset required by IP

// =============================================================================
// Signal Assignments
// =============================================================================

// Convert active-HIGH synchronous rst to active-LOW asynchronous aresetn.
// The IP uses aresetn asynchronously, so we register it once to ease timing.
reg aresetn_r;
always @(posedge clk) begin
    if (rst)
        aresetn_r <= 1'b0;   // Assert reset (active low)
    else
        aresetn_r <= 1'b1;   // Deassert reset
end
assign aresetn = aresetn_r;

// Feed operands straight to the AXI-Stream slave channels
assign s_axis_a_tdata         = a;
assign s_axis_b_tdata         = b;
assign s_axis_operation_tdata = op;

// Drive tvalid on all three slave channels together from valid_in
assign s_axis_a_tvalid         = valid_in;
assign s_axis_b_tvalid         = valid_in;
assign s_axis_operation_tvalid = valid_in;

// Expose the master channel outputs directly
assign result    = m_axis_result_tdata;
assign valid_out = m_axis_result_tvalid;

// =============================================================================
// floating_point_0 Instantiation
// =============================================================================

floating_point_1 u_fp16_op (
    // Clock & reset
    .aclk    (clk),      // input  wire        aclk
    .aresetn (aresetn),  // input  wire        aresetn  (active LOW)

    // Slave channel A  – operand A
    .s_axis_a_tvalid (s_axis_a_tvalid),  // input  wire        s_axis_a_tvalid
    .s_axis_a_tready (s_axis_a_tready),  // output wire        s_axis_a_tready (ignored)
    .s_axis_a_tdata  (s_axis_a_tdata),   // input  wire [15:0] s_axis_a_tdata

    // Slave channel B  – operand B
    .s_axis_b_tvalid (s_axis_b_tvalid),  // input  wire        s_axis_b_tvalid
    .s_axis_b_tready (s_axis_b_tready),  // output wire        s_axis_b_tready (ignored)
    .s_axis_b_tdata  (s_axis_b_tdata),   // input  wire [15:0] s_axis_b_tdata

    // Slave operation channel – selects Add or Subtract
    .s_axis_operation_tvalid (s_axis_operation_tvalid),  // input  wire
    .s_axis_operation_tready (s_axis_operation_tready),  // output wire (ignored)
    .s_axis_operation_tdata  (s_axis_operation_tdata),   // input  wire [7:0]

    // Master result channel
    .m_axis_result_tvalid (m_axis_result_tvalid),  // output wire        valid flag
    .m_axis_result_tready (1'b1),                  // input  wire        always ready
    .m_axis_result_tdata  (m_axis_result_tdata)    // output wire [15:0] result data
);

endmodule
