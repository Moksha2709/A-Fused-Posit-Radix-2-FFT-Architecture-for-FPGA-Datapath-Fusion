`timescale 1ns/1ps

module tb_fp32_add;

reg [31:0] a, b;
wire [31:0] out;

fp32_add DUT (.a(a), .b(b), .out(out));

initial begin
    // Test 1: 1.0 + 1.0 = 2.0
    // 1.0 = 0x3F800000, 2.0 = 0x40000000
    a = 32'h3F800000; b = 32'h3F800000;
    #10;
    $display("1.0 + 1.0 = %h (expected 40000000)", out);

    // Test 2: 1.0 + 0.0 = 1.0
    a = 32'h3F800000; b = 32'h00000000;
    #10;
    $display("1.0 + 0.0 = %h (expected 3F800000)", out);

    // Test 3: 1.0 - 1.0 = 0.0
    a = 32'h3F800000; b = 32'hBF800000;
    #10;
    $display("1.0 + (-1.0) = %h (expected 00000000)", out);

    // Test 4: 3.0 + 4.0 = 7.0
    // 3.0 = 0x40400000, 4.0 = 0x40800000, 7.0 = 0x40E00000
    a = 32'h40400000; b = 32'h40800000;
    #10;
    $display("3.0 + 4.0 = %h (expected 40E00000)", out);

    // Test 5: 0.5 + 0.25 = 0.75
    // 0.5 = 0x3F000000, 0.25 = 0x3E800000, 0.75 = 0x3F400000
    a = 32'h3F000000; b = 32'h3E800000;
    #10;
    $display("0.5 + 0.25 = %h (expected 3F400000)", out);

    // Test 6: 1.0 - 0.5 = 0.5
    a = 32'h3F800000; b = 32'hBF000000;
    #10;
    $display("1.0 - 0.5 = %h (expected 3F000000)", out);

    // Test 7: -2.5 + 1.5 = -1.0
    // -2.5 = 0xC0200000, 1.5 = 0x3FC00000, -1.0 = 0xBF800000
    a = 32'hC0200000; b = 32'h3FC00000;
    #10;
    $display("-2.5 + 1.5 = %h (expected BF800000)", out);

    $finish;
end
endmodule
