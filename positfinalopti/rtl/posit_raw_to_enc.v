// posit_raw_to_enc.v — Convert internal (sign, scale, mant) back to posit_encode inputs
module posit_raw_to_enc #(parameter N = 11, parameter MW = N)(
    input             sign_i,
    input  signed [6:0] scale_i,
    input  [MW-1:0]   mant_i,
    input             zero_i, nar_i,
    output [N-1:0]    p
);

reg signed [5:0] k_val;
reg exp_val;
reg [N-4:0] frac_val;

always @(*) begin
    // Split scale into k and exp: scale = 2*k + exp
    k_val   = scale_i >>> 1;
    exp_val = scale_i[0];

    // Extract fraction from mantissa (drop the leading 1)
    // mant_i has leading 1 at bit MW-1
    // We need N-3 bits of fraction = mant_i[MW-2 : MW-2-(N-4)]
    if (MW >= N-2)
        frac_val = mant_i[MW-2 -: (N-3)];
    else
        frac_val = mant_i[MW-2:0] << (N-3-MW+1);
end

// Saturate k
reg signed [5:0] enc_k;
always @(*) begin
    if (k_val >= (N-2))
        enc_k = N-2;
    else if (k_val <= -(N-2))
        enc_k = -(N-2);
    else
        enc_k = k_val;
end

posit_encode #(.N(N), .W_FRAC(N-3)) enc(
    .sign(sign_i),
    .k(enc_k),
    .exp(exp_val),
    .frac(frac_val),
    .nar(nar_i),
    .zero(zero_i),
    .p(p)
);

endmodule
