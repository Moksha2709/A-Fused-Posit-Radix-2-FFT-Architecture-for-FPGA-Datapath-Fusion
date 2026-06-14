`timescale 1ns / 1ps

module fp16_mul (
    input  wire [14:0] a,
    input  wire [14:0] b,
    output reg  [14:0] out
);

    // FP15 Format: 1 sign bit, 5 exponent bits, 9 mantissa bits (bias = 15)
    wire sign_a = a[14];
    wire sign_b = b[14];
    wire [4:0] exp_a = a[13:9];
    wire [4:0] exp_b = b[13:9];
    wire [8:0] frac_a = a[8:0];
    wire [8:0] frac_b = b[8:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Detect infinity or NaN
    wire inf_nan_a = (exp_a == 5'd31);
    wire inf_nan_b = (exp_b == 5'd31);

    // Output sign
    wire sign_out = sign_a ^ sign_b;

    // Implicit leading ones
    wire [9:0] mant_a = {~zero_a, frac_a};
    wire [9:0] mant_b = {~zero_b, frac_b};

    // Multiply mantissas (10 bits * 10 bits = 20 bits)
    wire [19:0] prod = mant_a * mant_b;

    // Intermediate exponent calculation: exp_a + exp_b - 15
    wire signed [6:0] exp_calc = exp_a + exp_b - 7'd15;

    // Normalization & Rounding
    reg [8:0] frac_out;
    reg [19:0] shifted_prod;
    reg signed [6:0] exp_shift;
    reg signed [6:0] final_exp;

    always @(*) begin
        if (zero_a || zero_b) begin
            out = {sign_out, 14'd0};
        end else if (inf_nan_a || inf_nan_b) begin
            if ((inf_nan_a && zero_b) || (inf_nan_b && zero_a)) begin
                out = {sign_out, 5'd31, 9'h100}; // NaN
            end else if (frac_a != 9'd0 || frac_b != 9'd0) begin
                out = {sign_out, 5'd31, 9'h100}; // NaN
            end else begin
                out = {sign_out, 5'd31, 9'd0}; // Inf
            end
        end else begin
            // Shift product so MSB is at bit 19
            if (prod[19]) begin
                shifted_prod = prod;
                exp_shift = exp_calc + 1;
            end else begin
                shifted_prod = prod << 1;
                exp_shift = exp_calc;
            end

            // Rounding check (round-to-nearest-even)
            // 10-bit mantissa is shifted_prod[19:10]
            // LSB is shifted_prod[10], Round is shifted_prod[9], Sticky is |shifted_prod[8:0]
            if (shifted_prod[9] && (shifted_prod[10] || |shifted_prod[8:0])) begin
                if (shifted_prod[19:10] == 10'h3ff) begin
                    frac_out = 9'd0;
                    final_exp = exp_shift + 1;
                end else begin
                    frac_out = shifted_prod[18:10] + 1'b1;
                    final_exp = exp_shift;
                end
            end else begin
                frac_out = shifted_prod[18:10];
                final_exp = exp_shift;
            end

            // Check exponent bounds (using signed comparison)
            if (final_exp >= 31) begin
                out = {sign_out, 5'd31, 9'd0}; // Overflow to Inf
            end else if (final_exp <= 0) begin
                out = {sign_out, 14'd0}; // Underflow to Zero (FTZ)
            end else begin
                out = {sign_out, final_exp[4:0], frac_out};
            end
        end
    end

endmodule
