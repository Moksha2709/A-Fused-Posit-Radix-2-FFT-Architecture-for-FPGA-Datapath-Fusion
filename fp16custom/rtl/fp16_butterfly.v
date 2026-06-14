`timescale 1ns / 1ps

module fp16_butterfly (
    input  wire [14:0] ar, ai,
    input  wire [14:0] br, bi,
    input  wire [14:0] wr, wi,
    
    output wire [14:0] y0r, y0i,
    output wire [14:0] y1r, y1i
);

    wire [14:0] m1, m2, m3, m4;
    wire [14:0] Tr, Ti;

    fp16_mul M1 (.a(br), .b(wr), .out(m1));
    fp16_mul M2 (.a(bi), .b(wi), .out(m2));
    fp16_mul M3 (.a(br), .b(wi), .out(m3));
    fp16_mul M4 (.a(bi), .b(wr), .out(m4));

    fp16_sub S1 (.a(m1), .b(m2), .out(Tr));
    fp16_add A1 (.a(m3), .b(m4), .out(Ti));

    fp16_add A2 (.a(ar), .b(Tr), .out(y0r));
    fp16_add A3 (.a(ai), .b(Ti), .out(y0i));

    fp16_sub S2 (.a(ar), .b(Tr), .out(y1r));
    fp16_sub S3 (.a(ai), .b(Ti), .out(y1i));

endmodule
