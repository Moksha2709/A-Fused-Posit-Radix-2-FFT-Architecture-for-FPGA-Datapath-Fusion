`timescale 1ns / 1ps

module fp16_sub (
    input  wire [11:0] a,
    input  wire [11:0] b,
    output wire [11:0] out
);

    wire [11:0] b_neg = {~b[11], b[10:0]};

    fp16_add adder_inst (
        .a(a),
        .b(b_neg),
        .out(out)
    );

endmodule
