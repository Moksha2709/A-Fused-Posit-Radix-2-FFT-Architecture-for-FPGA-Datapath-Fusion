`timescale 1ns / 1ps

module fp32_mul (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] out
);

    // Unpack fields for FP32 (1 sign, 8 exponent, 23 mantissa)
    wire sign_a = a[31];
    wire sign_b = b[31];
    wire [7:0] exp_a = a[30:23];
    wire [7:0] exp_b = b[30:23];
    wire [22:0] frac_a = a[22:0];
    wire [22:0] frac_b = b[22:0];

    // Detect zero operands
    wire zero_a = (exp_a == 8'd0);
    wire zero_b = (exp_b == 8'd0);

    // Detect infinity or NaN
    wire inf_nan_a = (exp_a == 8'd255);
    wire inf_nan_b = (exp_b == 8'd255);

    // Output sign
    wire sign_out = sign_a ^ sign_b;

    // Implicit leading ones
    wire [23:0] mant_a = {~zero_a, frac_a};
    wire [23:0] mant_b = {~zero_b, frac_b};

    // Multiply mantissas (24 bits * 24 bits = 48 bits)
    wire [47:0] prod = mant_a * mant_b;

    // Intermediate exponent calculation: exp_a + exp_b - 127
    wire signed [9:0] exp_calc = exp_a + exp_b - 10'd127;

    // Normalization & Rounding
    reg [22:0] frac_out;
    reg [47:0] shifted_prod;
    reg signed [9:0] exp_shift;
    reg signed [9:0] final_exp;

    always @(*) begin
        if (zero_a || zero_b) begin
            out = {sign_out, 31'd0};
        end else if (inf_nan_a || inf_nan_b) begin
            if ((inf_nan_a && zero_b) || (inf_nan_b && zero_a)) begin
                out = {sign_out, 8'd255, 23'h400000}; // NaN
            end else if (frac_a != 23'd0 || frac_b != 23'd0) begin
                out = {sign_out, 8'd255, 23'h400000}; // NaN
            end else begin
                out = {sign_out, 8'd255, 23'd0}; // Inf
            end
        end else begin
            // Shift product so MSB is at top bit
            if (prod[47]) begin
                shifted_prod = prod;
                exp_shift = exp_calc + 1;
            end else begin
                shifted_prod = prod << 1;
                exp_shift = exp_calc;
            end

            // Rounding check (round-to-nearest-even)
            // After normalization, implicit 1 is at bit 47.
            // Fraction bits are [46:24] (23 bits).
            // Round bit is shifted_prod[23].
            // Sticky bits are shifted_prod[22:0].
            if (shifted_prod[23] && (shifted_prod[24] || |shifted_prod[22:0])) begin
                if (shifted_prod[47:24] == 24'hFFFFFF) begin
                    frac_out = 23'd0;
                    final_exp = exp_shift + 1;
                end else begin
                    frac_out = shifted_prod[46:24] + 1'b1;
                    final_exp = exp_shift;
                end
            end else begin
                frac_out = shifted_prod[46:24];
                final_exp = exp_shift;
            end

            // Check exponent bounds (using signed comparison)
            if (final_exp >= 255) begin
                out = {sign_out, 8'd255, 23'd0}; // Overflow to Inf
            end else if (final_exp <= 0) begin
                out = {sign_out, 31'd0}; // Underflow to Zero (FTZ)
            end else begin
                out = {sign_out, final_exp[7:0], frac_out};
            end
        end
    end

endmodule
