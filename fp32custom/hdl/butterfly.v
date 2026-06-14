module butterfly #(parameter N = 10)(
    input  [N-1:0] ar, ai,
    input  [N-1:0] br, bi,
    input  [N-1:0] wr, wi,
    output [N-1:0] y0r, y0i, // A + W*B
    output [N-1:0] y1r, y1i  // A - W*B
);

// T = W * B
wire [N-1:0] m1, m2, m3, m4;
wire [N-1:0] Tr, Ti;

posit_mul #(.N(N)) M1 (.a(br), .b(wr), .p_out(m1));
posit_mul #(.N(N)) M2 (.a(bi), .b(wi), .p_out(m2));
posit_mul #(.N(N)) M3 (.a(br), .b(wi), .p_out(m3));
posit_mul #(.N(N)) M4 (.a(bi), .b(wr), .p_out(m4));

// Tr = m1 - m2
posit_sub #(.N(N)) S1 (.a(m1), .b(m2), .p_out(Tr));

// Ti = m3 + m4
posit_add #(.N(N)) A1 (.a(m3), .b(m4), .p_out(Ti));

// y0 = A + T
posit_add #(.N(N)) A2 (.a(ar), .b(Tr), .p_out(y0r));
posit_add #(.N(N)) A3 (.a(ai), .b(Ti), .p_out(y0i));

// y1 = A - T
posit_sub #(.N(N)) S2 (.a(ar), .b(Tr), .p_out(y1r));
posit_sub #(.N(N)) S3 (.a(ai), .b(Ti), .p_out(y1i));

endmodule