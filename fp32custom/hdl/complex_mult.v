module complex_mult #(parameter N = 10)(
    input  [N-1:0] ar, ai,
    input  [N-1:0] br, bi,
    output [N-1:0] pr, pi
);

wire [N-1:0] m1, m2, m3, m4;

posit_mul #(.N(N)) M1 (.a(ar), .b(br), .p_out(m1));
posit_mul #(.N(N)) M2 (.a(ai), .b(bi), .p_out(m2));
posit_mul #(.N(N)) M3 (.a(ar), .b(bi), .p_out(m3));
posit_mul #(.N(N)) M4 (.a(ai), .b(br), .p_out(m4));

posit_sub #(.N(N)) S1 (.a(m1), .b(m2), .p_out(pr));
posit_add #(.N(N)) A1 (.a(m3), .b(m4), .p_out(pi));

endmodule