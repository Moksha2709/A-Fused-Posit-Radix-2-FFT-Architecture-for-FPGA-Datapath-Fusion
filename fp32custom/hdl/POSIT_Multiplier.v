module posit_mul #(parameter N = 10)(
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
reg signed [5:0] k_res;
reg exp_res;
reg [N-4:0] frac_res;
reg nar, zero;

reg [N-3:0] mant_a, mant_b;            // N-2 bits
reg [(2*N)-5:0] mant_prod;             // (N-2) * (N-2) = 2N - 4 bits
reg [N-4:0] mant_norm;                 // N-3 bits (just the fraction)

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

    sign_res  = 0;
    scale_a   = 0;
    scale_b   = 0;
    scale_res = 0;

    k_res     = 0;
    exp_res   = 0;
    frac_res  = 0;

    mant_a    = 0;
    mant_b    = 0;
    mant_prod = 0;
    mant_norm = 0;

    nar       = 0;
    zero      = 0;

    // special cases
    if (a == (1 << (N-1)) || b == (1 << (N-1))) begin
        nar = 1'b1;
    end
    else if (a == 0 || b == 0) begin
        zero = 1'b1;
    end
    else begin

        sign_res = sign_a ^ sign_b;

        // scale = 2*k + exp because es = 1
        scale_a = ($signed(k_a) * 2) + $signed({1'b0, exp_a});
        scale_b = ($signed(k_b) * 2) + $signed({1'b0, exp_b});
        scale_res = scale_a + scale_b;

        // hidden bit + fraction => 1.xxx
        mant_a = {1'b1, frac_a};
        mant_b = {1'b1, frac_b};

        // Q1.(N-3) × Q1.(N-3) = Q2.(2N-6)
        mant_prod = mant_a * mant_b;

        // normalize
        // MSB is at (2N-5). If bit[2N-5] = 1 => value in [2,4)
        if (mant_prod[(2*N)-5]) begin
            mant_norm = mant_prod[(2*N)-6 -: (N-3)];
            scale_res = scale_res + 1;
        end
        else begin
            mant_norm = mant_prod[(2*N)-7 -: (N-3)];
        end

        // scale = 2*k + exp
        k_res = scale_res >>> 1;

        if ((scale_res - (k_res <<< 1)) != 0)
            exp_res = 1'b1;
        else
            exp_res = 1'b0;

        frac_res = mant_norm;
    end
end

reg signed [5:0] enc_k;

always @(*) begin
    // Saturate k_res 
    if (k_res >= (N-2))
        enc_k = N-2; 
    else if (k_res <= -(N-2))
        enc_k = -(N-2); 
    else
        enc_k = k_res;
end

posit_encode #(.N(N)) enc(
    .sign(sign_res),
    .k(enc_k),
    .exp(exp_res),
    .frac(frac_res),
    .nar(nar),
    .zero(zero),
    .p(p_out)
);

endmodule