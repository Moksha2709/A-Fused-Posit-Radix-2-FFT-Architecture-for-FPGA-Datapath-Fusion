`timescale 1ns / 1ps

module fp32_add (
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

    // Sorting operands by magnitude
    wire a_greater = (exp_a > exp_b) || ((exp_a == exp_b) && (frac_a >= frac_b));

    reg sign_l, sign_s;
    reg [7:0] exp_l, exp_s;
    reg [22:0] frac_l, frac_s;
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
    wire [7:0] exp_diff = exp_l - exp_s;
    wire [23:0] mant_l = {~zero_l, frac_l};
    wire [23:0] mant_s = {~zero_s, frac_s};

    // Extended mantissas for high precision alignment (50 bits total: 24 bits + 26 fractional/guard bits)
    wire [49:0] mant_l_ext = {mant_l, 26'd0};
    wire [49:0] mant_s_ext = {mant_s, 26'd0};
    
    // Shift smaller operand mantissa
    wire [49:0] mant_s_aligned = (exp_diff >= 8'd50) ? 50'd0 : (mant_s_ext >> exp_diff);

    // Sum significands
    reg [50:0] sum_mant; // carries over
    wire op_sub = sign_l ^ sign_s;

    always @(*) begin
        if (op_sub) begin
            sum_mant = mant_l_ext - mant_s_aligned;
        end else begin
            sum_mant = mant_l_ext + mant_s_aligned;
        end
    end

    // Normalization logic
    reg [5:0] norm_shift;
    reg [49:0] norm_mant;
    reg signed [8:0] final_exp;

    always @(*) begin
        if (sum_mant == 51'd0) begin
            norm_shift = 6'd0;
            norm_mant  = 50'd0;
        end else if (sum_mant[50]) begin // Addition overflow carry
            norm_shift = 6'd0;
            norm_mant  = sum_mant[50:1];
        end else begin
            if (sum_mant[49]) norm_shift = 6'd0;
            else if (sum_mant[48]) norm_shift = 6'd1;
            else if (sum_mant[47]) norm_shift = 6'd2;
            else if (sum_mant[46]) norm_shift = 6'd3;
            else if (sum_mant[45]) norm_shift = 6'd4;
            else if (sum_mant[44]) norm_shift = 6'd5;
            else if (sum_mant[43]) norm_shift = 6'd6;
            else if (sum_mant[42]) norm_shift = 6'd7;
            else if (sum_mant[41]) norm_shift = 6'd8;
            else if (sum_mant[40]) norm_shift = 6'd9;
            else if (sum_mant[39]) norm_shift = 6'd10;
            else if (sum_mant[38]) norm_shift = 6'd11;
            else if (sum_mant[37]) norm_shift = 6'd12;
            else if (sum_mant[36]) norm_shift = 6'd13;
            else if (sum_mant[35]) norm_shift = 6'd14;
            else if (sum_mant[34]) norm_shift = 6'd15;
            else if (sum_mant[33]) norm_shift = 6'd16;
            else if (sum_mant[32]) norm_shift = 6'd17;
            else if (sum_mant[31]) norm_shift = 6'd18;
            else if (sum_mant[30]) norm_shift = 6'd19;
            else if (sum_mant[29]) norm_shift = 6'd20;
            else if (sum_mant[28]) norm_shift = 6'd21;
            else if (sum_mant[27]) norm_shift = 6'd22;
            else if (sum_mant[26]) norm_shift = 6'd23;
            else if (sum_mant[25]) norm_shift = 6'd24;
            else if (sum_mant[24]) norm_shift = 6'd25;
            else if (sum_mant[23]) norm_shift = 6'd26;
            else if (sum_mant[22]) norm_shift = 6'd27;
            else if (sum_mant[21]) norm_shift = 6'd28;
            else if (sum_mant[20]) norm_shift = 6'd29;
            else if (sum_mant[19]) norm_shift = 6'd30;
            else if (sum_mant[18]) norm_shift = 6'd31;
            else if (sum_mant[17]) norm_shift = 6'd32;
            else if (sum_mant[16]) norm_shift = 6'd33;
            else if (sum_mant[15]) norm_shift = 6'd34;
            else if (sum_mant[14]) norm_shift = 6'd35;
            else if (sum_mant[13]) norm_shift = 6'd36;
            else if (sum_mant[12]) norm_shift = 6'd37;
            else if (sum_mant[11]) norm_shift = 6'd38;
            else if (sum_mant[10]) norm_shift = 6'd39;
            else if (sum_mant[9]) norm_shift = 6'd40;
            else if (sum_mant[8]) norm_shift = 6'd41;
            else if (sum_mant[7]) norm_shift = 6'd42;
            else if (sum_mant[6]) norm_shift = 6'd43;
            else if (sum_mant[5]) norm_shift = 6'd44;
            else if (sum_mant[4]) norm_shift = 6'd45;
            else if (sum_mant[3]) norm_shift = 6'd46;
            else if (sum_mant[2]) norm_shift = 6'd47;
            else if (sum_mant[1]) norm_shift = 6'd48;
            else if (sum_mant[0]) norm_shift = 6'd49;
            else norm_shift = 6'd49;
            norm_mant = sum_mant[49:0] << norm_shift;
        end
    end

    // Exponent shift adjustment
    always @(*) begin
        if (zero_l) begin
            final_exp = 9'd0;
        end else if (sum_mant[50]) begin
            final_exp = exp_l + 1;
        end else begin
            final_exp = exp_l - norm_shift;
        end
    end

    // Rounding & final compilation
    reg [22:0] frac_out;
    reg signed [8:0] final_exp_r;
    wire round_up = norm_mant[25] && (norm_mant[26] || |norm_mant[24:0]);
    wire [50:0] rounded_mant = {1'b0, norm_mant} + (round_up << 26);

    always @(*) begin
        if (zero_l || norm_mant == 50'd0) begin
            out = 32'd0;
        end else begin
            if (rounded_mant[50]) begin // Carry-out from rounding propagates to exp
                frac_out = rounded_mant[49:27];
                final_exp_r = final_exp + 1;
            end else begin
                frac_out = rounded_mant[48:26];
                final_exp_r = final_exp;
            end

            // Check bounds (using signed comparison)
            if (final_exp_r >= 255) begin
                out = {sign_l, 8'd255, 23'd0}; // Overflow to infinity
            end else if (final_exp_r <= 0) begin
                out = {sign_l, 31'd0}; // Underflow to zero
            end else begin
                out = {sign_l, final_exp_r[7:0], frac_out};
            end
        end
    end

endmodule
