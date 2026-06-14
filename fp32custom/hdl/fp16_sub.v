`timescale 1ns / 1ps

module fp16_sub (
    input  wire [14:0] a,
    input  wire [14:0] b,
    output wire [14:0] out
);

    wire [14:0] b_neg = {~b[14], b[13:0]};

    fp16_add adder_inst (
        .a(a),
        .b(b_neg),
        .out(out)
    );

endmodule
