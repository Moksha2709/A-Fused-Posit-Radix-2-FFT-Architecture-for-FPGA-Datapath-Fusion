`timescale 1ns / 1ps

module fp32_sub (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] out
);

    wire [31:0] b_neg = {~b[31], b[30:0]};

    fp32_add ADDER (
        .a(a),
        .b(b_neg),
        .out(out)
    );

endmodule
