`timescale 1ns / 1ps

module fp32_butterfly (
    input  wire [31:0] ar, ai,
    input  wire [31:0] br, bi,
    input  wire [31:0] wr, wi,
    
    output wire [31:0] y0r, y0i,
    output wire [31:0] y1r, y1i
);

    wire [31:0] m1, m2, m3, m4;
    wire [31:0] Tr, Ti;

    fp32_mul M1 (.a(br), .b(wr), .out(m1));
    fp32_mul M2 (.a(bi), .b(wi), .out(m2));
    fp32_mul M3 (.a(br), .b(wi), .out(m3));
    fp32_mul M4 (.a(bi), .b(wr), .out(m4));

    fp32_sub S1 (.a(m1), .b(m2), .out(Tr));
    fp32_add A1 (.a(m3), .b(m4), .out(Ti));

    fp32_add A2 (.a(ar), .b(Tr), .out(y0r));
    fp32_add A3 (.a(ai), .b(Ti), .out(y0i));

    fp32_sub S2 (.a(ar), .b(Tr), .out(y1r));
    fp32_sub S3 (.a(ai), .b(Ti), .out(y1i));

endmodule
