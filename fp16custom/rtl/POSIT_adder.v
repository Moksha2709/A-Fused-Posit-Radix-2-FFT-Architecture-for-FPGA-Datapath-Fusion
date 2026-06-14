module posit_add #(parameter N = 10)(
    input  [N-1:0] a,
    input  [N-1:0] b,
    output [N-1:0] p_out
);

wire sign_a, sign_b;
wire signed [5:0] k_a, k_b;
wire exp_a, exp_b;
wire [N-4:0] frac_a, frac_b;

reg sign_res;
reg signed [6:0] scale_a, scale_b, scale_res;
reg [N-2:0] mant_a, mant_b; // 1 + N-3 + 1 = N-1 bits
reg [N-1:0] mant_sum;       // N bits
reg [N-2:0] mant_norm;      // N-1 bits

reg signed [5:0] k_res;
reg exp_res;
reg [N-4:0] frac_res;

reg nar, zero;

integer shift;
integer i;

posit_decode #(.N(N)) dec_a(
    .p(a),
    .sign(sign_a),
    .k(k_a),
    .exp(exp_a),
    .frac(frac_a)
);

posit_decode #(.N(N)) dec_b(
    .p(b),
    .sign(sign_b),
    .k(k_b),
    .exp(exp_b),
    .frac(frac_b)
);

always @(*) begin

    sign_res = 0;
    scale_a  = 0;
    scale_b  = 0;
    scale_res = 0;

    mant_a = 0;
    mant_b = 0;
    mant_sum = 0;
    mant_norm = 0;

    k_res = 0;
    exp_res = 0;
    frac_res = 0;

    nar = 0;
    zero = 0;

    // Special cases
    if (a == (1 << (N-1)) || b == (1 << (N-1))) begin
        nar = 1'b1;
    end
    else if (a == 0) begin
        if (b == 0) begin
            zero = 1'b1;
        end else begin
            sign_res = sign_b;
            k_res    = k_b;
            exp_res  = exp_b;
            frac_res = frac_b;
        end
    end
    else if (b == 0) begin
        sign_res = sign_a;
        k_res    = k_a;
        exp_res  = exp_a;
        frac_res = frac_a;
    end
    else begin

        // scale = 2*k + exp (since es=1)
        scale_a = (k_a <<< 1) + exp_a;
        scale_b = (k_b <<< 1) + exp_b;

        mant_a = {1'b1, frac_a, 1'b0};   // extra LSB for alignment
        mant_b = {1'b1, frac_b, 1'b0};

        // Align smaller operand
        if (scale_a > scale_b) begin
            shift = scale_a - scale_b;
            if (shift > (N-2))
                mant_b = 0;
            else
                mant_b = mant_b >> shift;

            scale_res = scale_a;
            sign_res  = sign_a;
        end
        else begin
            shift = scale_b - scale_a;
            if (shift > (N-2))
                mant_a = 0;
            else
                mant_a = mant_a >> shift;

            scale_res = scale_b;
            sign_res  = sign_b;
        end

        // Same sign -> add
        if (sign_a == sign_b) begin
            mant_sum = mant_a + mant_b;
            sign_res = sign_a;

            // carry out
            if (mant_sum[N-1]) begin
                mant_norm = mant_sum[N-1:1];
                scale_res = scale_res + 1;
            end
            else begin
                mant_norm = mant_sum[N-2:0];
            end
        end

        // Different signs -> subtract
        else begin
            if (mant_a >= mant_b) begin
                mant_sum = mant_a - mant_b;
                sign_res = sign_a;
            end
            else begin
                mant_sum = mant_b - mant_a;
                sign_res = sign_b;
            end

            if (mant_sum == 0) begin
                zero = 1'b1;
            end
            else begin
                mant_norm = mant_sum[N-2:0];

                // normalize left
                for (i = 0; i < N; i = i + 1) begin
                    if (mant_norm[N-2] == 0 && scale_res > -((N-2)*2)) begin
                        mant_norm = mant_norm << 1;
                        scale_res = scale_res - 1;
                    end
                end
            end
        end

        if (!zero) begin
            // split scale back to regime + exponent
            k_res   = scale_res >>> 1;
            exp_res = scale_res[0];

            frac_res = mant_norm[N-3:1];
        end
    end
end

posit_encode #(.N(N)) enc(
    .sign(sign_res),
    .k(k_res),
    .exp(exp_res),
    .frac(frac_res),
    .nar(nar),
    .zero(zero),
    .p(p_out)
);

endmodule