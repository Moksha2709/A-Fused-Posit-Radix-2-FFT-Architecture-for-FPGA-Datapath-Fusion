module posit_sub #(parameter N = 10)(
    input  [N-1:0] a,
    input  [N-1:0] b,
    output [N-1:0] p_out
);

    // Two's complement of b
    // Special case NaR: NaR (1 followed by 0s) two's complement is NaR, which is perfectly correct.
    wire [N-1:0] neg_b = (~b) + 1'b1;

    // Instantiate the existing adder
    posit_add #(.N(N)) adder_inst (
        .a(a),
        .b(neg_b),
        .p_out(p_out)
    );

endmodule
