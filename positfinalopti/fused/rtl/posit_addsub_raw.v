// posit_addsub_raw.v — Posit add/sub in internal (sign, scale, mant) format
// No posit_decode or posit_encode
module posit_addsub_raw #(parameter N = 11, parameter MW = N)(
    input             sign_a,
    input  signed [6:0] scale_a,
    input  [MW-1:0]   mant_a,
    input             zero_a, nar_a,

    input             sign_b,
    input  signed [6:0] scale_b,
    input  [MW-1:0]   mant_b,
    input             zero_b, nar_b,

    input             do_sub,      // 1 = subtract, 0 = add

    output reg            sign_o,
    output reg signed [6:0] scale_o,
    output reg [MW-1:0]   mant_o,
    output reg            zero_o, nar_o
);

reg eff_sign_b;
localparam signed [31:0] MIN_SCALE = -2 * $signed(N-2);
reg sign_l, sign_s;
reg signed [6:0] scale_l, scale_s;
reg [MW-1:0] mant_l, mant_s;
reg zero_l, zero_s;

reg signed [7:0] diff;
reg [MW:0]   sum;       // MW+1 bits for carry
reg [MW-1:0] norm;

integer i;
reg [5:0] lzc;
reg found;

always @(*) begin
    sign_o  = 0;
    scale_o = 0;
    mant_o  = 0;
    zero_o  = 0;
    nar_o   = 0;

    eff_sign_b = do_sub ? ~sign_b : sign_b;

    // Special cases
    if (nar_a || nar_b) begin
        nar_o = 1;
    end
    else if (zero_a && zero_b) begin
        zero_o = 1;
    end
    else if (zero_a) begin
        sign_o  = eff_sign_b;
        scale_o = scale_b;
        mant_o  = mant_b;
    end
    else if (zero_b) begin
        sign_o  = sign_a;
        scale_o = scale_a;
        mant_o  = mant_a;
    end
    else begin
        // Sort by magnitude (scale, then mantissa)
        if ((scale_a > scale_b) || (scale_a == scale_b && mant_a >= mant_b)) begin
            sign_l = sign_a;      sign_s = eff_sign_b;
            scale_l = scale_a;    scale_s = scale_b;
            mant_l = mant_a;      mant_s = mant_b;
        end else begin
            sign_l = eff_sign_b;  sign_s = sign_a;
            scale_l = scale_b;    scale_s = scale_a;
            mant_l = mant_b;      mant_s = mant_a;
        end

        // Align smaller mantissa
        diff = scale_l - scale_s;
        if (diff >= MW)
            mant_s = 0;
        else
            mant_s = mant_s >> diff;

        scale_o = scale_l;

        if (sign_l == sign_s) begin
            // Same sign: add mantissas
            sign_o = sign_l;
            sum = mant_l + mant_s;

            if (sum[MW]) begin
                mant_o  = sum[MW:1];
                scale_o = scale_l + 1;
            end else begin
                mant_o = sum[MW-1:0];
            end
        end
        else begin
            // Different signs: subtract mantissas
            sign_o = sign_l;

            if (mant_l == mant_s) begin
                zero_o = 1;
            end else begin
                sum = mant_l - mant_s;
                norm = sum[MW-1:0];

                // Leading-zero count for normalization
                lzc = 0;
                found = 0;
                for (i = MW-1; i >= 0; i = i - 1) begin
                    if (!found && !norm[i]) begin
                        lzc = lzc + 1;
                    end else begin
                        found = 1;
                    end
                end

                // Clamp shift to avoid underflow
                if (lzc > 0) begin
                    if (scale_l - $signed(lzc) < MIN_SCALE) begin
                        lzc = scale_l - MIN_SCALE;
                    end
                    norm = norm << lzc;
                    scale_o = scale_l - $signed(lzc);
                end

                mant_o = norm;
            end
        end
    end
end
endmodule
