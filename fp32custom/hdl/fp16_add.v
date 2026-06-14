`timescale 1ns / 1ps

module fp16_add (
    input  wire [14:0] a,
    input  wire [14:0] b,
    output reg  [14:0] out
);

    // Unpack fields for FP15 (1 sign, 5 exponent, 9 mantissa)
    wire sign_a = a[14];
    wire sign_b = b[14];
    wire [4:0] exp_a = a[13:9];
    wire [4:0] exp_b = b[13:9];
    wire [8:0] frac_a = a[8:0];
    wire [8:0] frac_b = b[8:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Sorting operands by magnitude
    wire a_greater = (exp_a > exp_b) || ((exp_a == exp_b) && (frac_a >= frac_b));

    reg sign_l, sign_s;
    reg [4:0] exp_l, exp_s;
    reg [8:0] frac_l, frac_s;
    reg zero_l, zero_s;

    always @(*) begin
        if (a_greater) begin
            sign_l = sign_a;  sign_s = sign_b;
            exp_l  = exp_a;   exp_s  = exp_b;
            frac_l = frac_a;  frac_s = frac_b;
            zero_l = zero_a;  zero_s = zero_b;
        end else begin
            sign_l = sign_b;  sign_s = sign_a;
            exp_l  = exp_b;   exp_s  = exp_a;
            frac_l = frac_b;  frac_s = frac_a;
            zero_l = zero_b;  zero_s = zero_a;
        end
    end

    // Alignment and arithmetic wires
    wire [4:0] exp_diff = exp_l - exp_s;
    wire [9:0] mant_l = {~zero_l, frac_l};
    wire [9:0] mant_s = {~zero_s, frac_s};

    // Extended mantissas for high precision alignment (23 bits total: 10 bits + 13 fractional/guard bits)
    wire [22:0] mant_l_ext = {mant_l, 13'd0};
    wire [22:0] mant_s_ext = {mant_s, 13'd0};
    
    // Shift smaller operand mantissa
    wire [22:0] mant_s_aligned = (exp_diff >= 5'd23) ? 23'd0 : (mant_s_ext >> exp_diff);

    // Sum significands
    reg [23:0] sum_mant; // 24 bits to capture carry-out
    wire op_sub = sign_l ^ sign_s;

    always @(*) begin
        if (op_sub) begin
            sum_mant = mant_l_ext - mant_s_aligned;
        end else begin
            sum_mant = mant_l_ext + mant_s_aligned;
        end
    end

    // Normalization logic
    reg [4:0] norm_shift;
    reg [22:0] norm_mant;
    reg signed [5:0] final_exp;

    always @(*) begin
        if (sum_mant == 24'd0) begin
            norm_shift = 5'd0;
            norm_mant  = 23'd0;
        end else if (sum_mant[23]) begin // Addition overflow carry
            norm_shift = 5'd0;
            norm_mant  = sum_mant[23:1];
        end else begin
            // Priority encoder for leading-one detection (subtraction case)
            if (sum_mant[22])      norm_shift = 5'd0;
            else if (sum_mant[21]) norm_shift = 5'd1;
            else if (sum_mant[20]) norm_shift = 5'd2;
            else if (sum_mant[19]) norm_shift = 5'd3;
            else if (sum_mant[18]) norm_shift = 5'd4;
            else if (sum_mant[17]) norm_shift = 5'd5;
            else if (sum_mant[16]) norm_shift = 5'd6;
            else if (sum_mant[15]) norm_shift = 5'd7;
            else if (sum_mant[14]) norm_shift = 5'd8;
            else if (sum_mant[13]) norm_shift = 5'd9;
            else if (sum_mant[12]) norm_shift = 5'd10;
            else if (sum_mant[11]) norm_shift = 5'd11;
            else if (sum_mant[10]) norm_shift = 5'd12;
            else if (sum_mant[9])  norm_shift = 5'd13;
            else if (sum_mant[8])  norm_shift = 5'd14;
            else if (sum_mant[7])  norm_shift = 5'd15;
            else if (sum_mant[6])  norm_shift = 5'd16;
            else if (sum_mant[5])  norm_shift = 5'd17;
            else if (sum_mant[4])  norm_shift = 5'd18;
            else if (sum_mant[3])  norm_shift = 5'd19;
            else if (sum_mant[2])  norm_shift = 5'd20;
            else if (sum_mant[1])  norm_shift = 5'd21;
            else                   norm_shift = 5'd22;

            norm_mant = sum_mant[22:0] << norm_shift;
        end
    end

    // Exponent shift adjustment
    always @(*) begin
        if (zero_l) begin
            final_exp = 6'd0;
        end else if (sum_mant[23]) begin
            final_exp = exp_l + 1;
        end else begin
            final_exp = exp_l - norm_shift;
        end
    end

    // Rounding & final compilation (FP15 has 9 mantissa bits)
    // Leading one is at norm_mant[22]. 9 fractional bits are norm_mant[21:13]
    // Rounding: round bit is norm_mant[12], sticky bit is |norm_mant[11:0]
    reg [8:0] frac_out;
    reg signed [5:0] final_exp_r;
    wire round_up = norm_mant[12] && (norm_mant[13] || |norm_mant[11:0]);
    wire [23:0] rounded_mant = {1'b0, norm_mant} + (round_up << 13);

    always @(*) begin
        if (zero_l || norm_mant == 23'd0) begin
            out = 15'd0;
        end else begin
            if (rounded_mant[23]) begin // Carry-out from rounding propagates to exp
                frac_out = rounded_mant[22:14];
                final_exp_r = final_exp + 1;
            end else begin
                frac_out = rounded_mant[21:13];
                final_exp_r = final_exp;
            end

            // Check bounds (using signed comparison)
            if (final_exp_r >= 31) begin
                out = {sign_l, 5'd31, 9'd0}; // Overflow to infinity
            end else if (final_exp_r <= 0) begin
                out = {sign_l, 14'd0}; // Underflow to zero
            end else begin
                out = {sign_l, final_exp_r[4:0], frac_out};
            end
        end
    end

endmodule
