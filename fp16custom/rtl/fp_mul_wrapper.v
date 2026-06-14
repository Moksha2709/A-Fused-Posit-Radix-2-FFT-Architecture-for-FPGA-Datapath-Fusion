// =============================================================================
// Module      : fp_mul_wrapper
// Description : Clean Verilog wrapper around the Xilinx AXI-Stream Floating
//               Point IP (floating_point_0).  Hides all AXI-Stream handshake
//               signals and exposes a simple, pipeline-friendly interface.
//
// ---- IP Configuration (read from floating_point_0.xci — updated) ------------
//   IP core     : floating_point_v7_1_21  (Vivado 2025.2)
//   Operation   : Multiply  (C_HAS_MULTIPLY=1)
//   Precision   : Half / FP16 — C_A_WIDTH=16, C_RESULT_WIDTH=16
//                 (A_Precision_Type=Half, exp=5, mantissa=10+1 hidden)
//   Latency     : 7 pipeline stages  (C_LATENCY=7)
//   Reset       : NONE  (C_HAS_ARESETN=0) — IP has no aresetn port.
//                 rst only gates the local valid shift-register.
//   Throttle    : Full-throughput  (C_THROTTLE_SCHEME=1) — tready ignored.
//
// ---- Simple Interface --------------------------------------------------------
//   Inputs  : clk, rst (active-HIGH synchronous), a, b, valid_in
//   Outputs : result, valid_out
//
// ---- Usage Notes -------------------------------------------------------------
//   1. valid_out is asserted exactly LATENCY clocks after valid_in.
//   2. m_axis_result_tready is tied HIGH — no backpressure support needed.
//   3. s_axis_a/b_tready are outputs from the IP and are left unconnected;
//      in full-throughput mode the IP is always ready to accept data.
//   4. rst does NOT reset the IP datapath — it only clears the valid
//      shift-register so valid_out stays de-asserted during reset.
//      Insert a sufficient number of idle cycles after releasing rst before
//      presenting the first valid data.
//
// ---- FFT Integration Notes --------------------------------------------------
//   Instantiate one fp_mul_wrapper per complex multiplication lane.
//   Drive valid_in in lock-step with the butterfly data valid.
//   Use valid_out to re-align the accumulated result into the next FFT stage.
//   Because latency is constant and no stalling occurs, a simple LATENCY-deep
//   shift-register on any sideband signals (e.g., twiddle index, stage counter)
//   keeps everything synchronised without a FIFO.
// =============================================================================

`timescale 1ns / 1ps

// ---------------------------------------------------------------------------
// DATA_W  : matches C_A_TDATA_WIDTH / C_RESULT_TDATA_WIDTH from the XCI.
//           16  = FP16 / Half precision  (current configuration)
//           32  = FP32 / Single precision
// LATENCY : matches C_LATENCY from the XCI.  Must be kept in sync with the
//           IP wizard "Cycles" setting whenever the IP is re-configured.
// ---------------------------------------------------------------------------
`define DATA_W  16
`define LATENCY  7

module fp_mul_wrapper (
    // -------------------------------------------------------------------------
    // Clock & Reset
    // -------------------------------------------------------------------------
    input  wire              clk,       // System clock → drives IP aclk
    input  wire              rst,       // Active-HIGH synchronous reset
                                        // (gates valid_out; does NOT reset IP)

    // -------------------------------------------------------------------------
    // Data Inputs  (IEEE 754, width set by DATA_W)
    // -------------------------------------------------------------------------
    input  wire [`DATA_W-1:0] a,        // Operand A
    input  wire [`DATA_W-1:0] b,        // Operand B
    input  wire               valid_in, // Assert HIGH for one clock to submit a/b

    // -------------------------------------------------------------------------
    // Data Output (IEEE 754, width set by DATA_W)
    // -------------------------------------------------------------------------
    output wire [`DATA_W-1:0] result,   // a * b  (valid LATENCY clocks after valid_in)
    output wire               valid_out // HIGH when result is valid
);

    // =========================================================================
    // Internal AXI-Stream wires
    // =========================================================================

    // --- Slave channel A (operand A) ---
    wire               s_axis_a_tvalid;
    wire               s_axis_a_tready; // IP output — ignored (always-ready IP)
    wire [`DATA_W-1:0] s_axis_a_tdata;

    // --- Slave channel B (operand B) ---
    wire               s_axis_b_tvalid;
    wire               s_axis_b_tready; // IP output — ignored (always-ready IP)
    wire [`DATA_W-1:0] s_axis_b_tdata;

    // --- Master result channel ---
    wire               m_axis_result_tvalid;
    wire               m_axis_result_tready;
    wire [`DATA_W-1:0] m_axis_result_tdata;

    // =========================================================================
    // AXI-Stream Input Assignments
    // =========================================================================

    // Both operands share the same valid strobe; they must always arrive together.
    assign s_axis_a_tvalid = valid_in;
    assign s_axis_a_tdata  = a;

    assign s_axis_b_tvalid = valid_in;
    assign s_axis_b_tdata  = b;

    // =========================================================================
    // AXI-Stream Output Assignments
    // =========================================================================

    // Always accept results — no downstream backpressure.
    assign m_axis_result_tready = 1'b1;

    // Wire IP result bus directly to module output port.
    assign result = m_axis_result_tdata;

    // =========================================================================
    // valid_out — shift-register pipeline
    //
    //   The IP has no reset port (C_HAS_ARESETN=0).  We track valid_in
    //   through a LATENCY-deep shift register that IS synchronously cleared
    //   on rst.  This guarantees valid_out stays LOW during and immediately
    //   after reset, regardless of any residual IP pipeline state.
    //
    //   The shift register MSB is the oldest entry (pushed out after LATENCY
    //   cycles).  On every clock where rst is de-asserted, the register
    //   shifts left, inserting valid_in at the LSB:
    //
    //     Cycle 0 : valid_in=1 → valid_sr = 0000...001
    //     Cycle 1 :             → valid_sr = 0000...010
    //     ...
    //     Cycle LATENCY-1      → valid_sr = 1000...000  ← MSB HIGH
    //     At this point m_axis_result_tvalid also goes HIGH.
    //
    //   We use the IP's own m_axis_result_tvalid as the authoritative source
    //   (gated by ~rst) so the wrapper introduces zero extra timing cycles.
    // =========================================================================

    reg [`LATENCY-1:0] valid_sr;

    always @(posedge clk) begin
        if (rst) begin
            valid_sr <= {`LATENCY{1'b0}};
        end else begin
            // Shift in valid_in at LSB; MSB exits as the earliest-cycle valid.
            valid_sr <= {valid_sr[`LATENCY-2:0], valid_in};
        end
    end

    // Gate IP's own tvalid with ~rst for a clean, reset-safe valid_out.
    assign valid_out = m_axis_result_tvalid & ~rst;

    // =========================================================================
    // Xilinx Floating Point IP Instantiation
    //   Name  : floating_point_0  (must match the IP name in your Vivado project)
    //   Ports : verified against floating_point_0.xci (post FP16 reconfiguration)
    //
    //   Data buses are 16-bit (FP16 / Half precision, C_A_TDATA_WIDTH=16).
    //   If you reconfigure to FP32 change DATA_W to 32, LATENCY to match,
    //   and regenerate output products in Vivado before re-synthesising.
    // =========================================================================
    floating_point_0 u_fp_mul (
        // Clock (IP has no reset port in this configuration)
        .aclk                 ( clk                  ),  // input  wire

        // Slave channel A — operand A
        .s_axis_a_tvalid      ( s_axis_a_tvalid      ),  // input  wire
        .s_axis_a_tready      ( s_axis_a_tready      ),  // output wire (not used)
        .s_axis_a_tdata       ( s_axis_a_tdata       ),  // input  wire [15:0]  FP16

        // Slave channel B — operand B
        .s_axis_b_tvalid      ( s_axis_b_tvalid      ),  // input  wire
        .s_axis_b_tready      ( s_axis_b_tready      ),  // output wire (not used)
        .s_axis_b_tdata       ( s_axis_b_tdata       ),  // input  wire [15:0]  FP16

        // Master result channel
        .m_axis_result_tvalid ( m_axis_result_tvalid ),  // output wire
        .m_axis_result_tready ( m_axis_result_tready ),  // input  wire (tied 1)
        .m_axis_result_tdata  ( m_axis_result_tdata  )   // output wire [15:0]  FP16
    );

endmodule
