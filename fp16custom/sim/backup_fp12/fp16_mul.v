`timescale 1ns / 1ps

module fp16_mul (
    input  wire [11:0] a,
    input  wire [11:0] b,
    output reg  [11:0] out
);

    // FP12 Format: 1 sign bit, 5 exponent bits, 6 mantissa bits (bias = 15)
    wire sign_a = a[11];
    wire sign_b = b[11];
    wire [4:0] exp_a = a[10:6];
    wire [4:0] exp_b = b[10:6];
    wire [5:0] frac_a = a[5:0];
    wire [5:0] frac_b = b[5:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Detect infinity or NaN
    wire inf_nan_a = (exp_a == 5'd31);
    wire inf_nan_b = (exp_b == 5'd31);

    // Output sign
    wire sign_out = sign_a ^ sign_b;

    // Implicit leading ones
    wire [6:0] mant_a = {~zero_a, frac_a};
    wire [6:0] mant_b = {~zero_b, frac_b};

    // Multiply mantissas (7 bits * 7 bits = 14 bits)
    wire [13:0] prod = mant_a * mant_b;

    // Intermediate exponent calculation: exp_a + exp_b - 15
    wire signed [6:0] exp_calc = exp_a + exp_b - 7'd15;

    // Normalization & Rounding
    reg [5:0] frac_out;
    reg [13:0] shifted_prod;
    reg signed [6:0] exp_shift;
    reg signed [6:0] final_exp;

    always @(*) begin
        if (zero_a || zero_b) begin
            out = {sign_out, 11'd0};
        end else if (inf_nan_a || inf_nan_b) begin
            if ((inf_nan_a && zero_b) || (inf_nan_b && zero_a)) begin
                out = {sign_out, 5'd31, 6'h20}; // NaN
            end else if (frac_a != 6'd0 || frac_b != 6'd0) begin
                out = {sign_out, 5'd31, 6'h20}; // NaN
            end else begin
                out = {sign_out, 5'd31, 6'd0}; // Inf
            end
        end else begin
            // Shift product so MSB is at bit 13
            if (prod[13]) begin
                shifted_prod = prod;
                exp_shift = exp_calc + 1;
            end else begin
                shifted_prod = prod << 1;
                exp_shift = exp_calc;
            end

            // Rounding check (round-to-nearest-even)
            // 7-bit mantissa is shifted_prod[13:7]
            // LSB is shifted_prod[7], Round is shifted_prod[6], Sticky is |shifted_prod[5:0]
            if (shifted_prod[6] && (shifted_prod[7] || |shifted_prod[5:0])) begin
                if (shifted_prod[13:7] == 7'h7f) begin
                    frac_out = 6'd0;
                    final_exp = exp_shift + 1;
                end else begin
                    frac_out = shifted_prod[12:7] + 1'b1;
                    final_exp = exp_shift;
                end
            end else begin
                frac_out = shifted_prod[12:7];
                final_exp = exp_shift;
            end

            // Check exponent bounds (using signed comparison)
            if (final_exp >= 31) begin
                out = {sign_out, 5'd31, 6'd0}; // Overflow to Inf
            end else if (final_exp <= 0) begin
                out = {sign_out, 11'd0}; // Underflow to Zero (FTZ)
            end else begin
                out = {sign_out, final_exp[4:0], frac_out};
            end
        end
    end

endmodule
