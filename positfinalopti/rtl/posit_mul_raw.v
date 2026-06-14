// posit_mul_raw.v — Posit multiply in internal (sign, scale, mant) format
// No posit_decode or posit_encode — works on pre-decoded fields
module posit_mul_raw #(parameter N = 11, parameter MW = N)(
    input             sign_a,
    input  signed [6:0] scale_a,
    input  [N-3:0]    mant_a,     // {1, frac} = N-2 bits
    input             zero_a, nar_a,

    input             sign_b,
    input  signed [6:0] scale_b,
    input  [N-3:0]    mant_b,
    input             zero_b, nar_b,

    output reg            sign_o,
    output reg signed [6:0] scale_o,
    output reg [MW-1:0]   mant_o,   // normalized mantissa with leading 1 at MSB
    output reg            zero_o, nar_o
);

localparam PW = 2*(N-2);  // product width

reg [PW-1:0] prod;

always @(*) begin
    sign_o  = 0;
    scale_o = 0;
    mant_o  = 0;
    zero_o  = 0;
    nar_o   = 0;

    if (nar_a || nar_b) begin
        nar_o = 1;
    end
    else if (zero_a || zero_b) begin
        zero_o = 1;
    end
    else begin
        sign_o = sign_a ^ sign_b;
        prod   = mant_a * mant_b;

        // Normalize: MSB of prod is at PW-1
        if (prod[PW-1]) begin
            scale_o = scale_a + scale_b + 1;
            mant_o  = prod[PW-1 -: MW];
        end else begin
            scale_o = scale_a + scale_b;
            mant_o  = prod[PW-2 -: MW];
        end
    end
end
endmodule
