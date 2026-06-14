`timescale 1ns/1ps

module tb_fp32_mul;

reg [31:0] a, b;
wire [31:0] out;

fp32_mul DUT (.a(a), .b(b), .out(out));

initial begin
    // Test 1: 2.0 * 3.0 = 6.0
    // 2.0 = 0x40000000, 3.0 = 0x40400000, 6.0 = 0x40C00000
    a = 32'h40000000; b = 32'h40400000;
    #10;
    $display("2.0 * 3.0 = %h (expected 40C00000)", out);

    // Test 2: 1.0 * 1.0 = 1.0
    a = 32'h3F800000; b = 32'h3F800000;
    #10;
    $display("1.0 * 1.0 = %h (expected 3F800000)", out);

    // Test 3: -1.0 * 2.0 = -2.0
    a = 32'hBF800000; b = 32'h40000000;
    #10;
    $display("-1.0 * 2.0 = %h (expected C0000000)", out);

    // Test 4: 0.5 * 0.5 = 0.25
    // 0.5 = 0x3F000000, 0.25 = 0x3E800000
    a = 32'h3F000000; b = 32'h3F000000;
    #10;
    $display("0.5 * 0.5 = %h (expected 3E800000)", out);

    // Test 5: 1.5 * 2.5 = 3.75
    // 1.5 = 0x3FC00000, 2.5 = 0x40200000, 3.75 = 0x40700000
    a = 32'h3FC00000; b = 32'h40200000;
    #10;
    $display("1.5 * 2.5 = %h (expected 40700000)", out);

    // Test 6: cos(pi/4) * cos(pi/4) = 0.5
    // cos(pi/4) = 0.707107 = 0x3F3504F3, 0.5 = 0x3F000000
    a = 32'h3F3504F3; b = 32'h3F3504F3;
    #10;
    $display("0.707107^2 = %h (expected ~3F000000)", out);

    // Test 7: 0 * 5.0 = 0
    a = 32'h00000000; b = 32'h40A00000;
    #10;
    $display("0 * 5.0 = %h (expected 00000000)", out);

    $finish;
end
endmodule
