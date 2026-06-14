module sample_ram #(
    parameter N          = 16, // Will be overridden by the top module parameter
    parameter POINTS     = 1024,
    parameter ADDR_WIDTH = 10
)(
    input clk,

    // FFT access
    input [ADDR_WIDTH-1:0] addr_a,
    input [ADDR_WIDTH-1:0] addr_b,
    input we,

    input [N-1:0] din_ar, din_ai,
    input [N-1:0] din_br, din_bi,

    output [N-1:0] dout_ar, dout_ai,
    output [N-1:0] dout_br, dout_bi,

    input load_en,
    input [ADDR_WIDTH-1:0] load_addr,
    input [N-1:0] load_data_r,
    input [N-1:0] load_data_i
);

    // Force Vivado to synthesize this as Block RAM instead of Registers
    (* ram_style = "block" *) reg [N-1:0] real_mem [0:POINTS-1];
    (* ram_style = "block" *) reg [N-1:0] imag_mem [0:POINTS-1];

    integer i;
    initial begin
        for(i=0; i<POINTS; i=i+1) begin
            real_mem[i] = 0;
            imag_mem[i] = 0;
        end
    end

    // Resolve port addresses and write enables
    wire [ADDR_WIDTH-1:0] port_a_addr = load_en ? load_addr : addr_a;
    wire [ADDR_WIDTH-1:0] port_b_addr = addr_b;

    wire we_a = load_en | we;
    wire we_b = ~load_en & we;

    // Resolve port input data
    wire [N-1:0] in_a_r = load_en ? load_data_r : din_ar;
    wire [N-1:0] in_a_i = load_en ? load_data_i : din_ai;

    wire [N-1:0] in_b_r = din_br;
    wire [N-1:0] in_b_i = din_bi;

    // Output registers for registered read (mandatory for BRAM)
    reg [N-1:0] dout_ar_r, dout_ai_r;
    reg [N-1:0] dout_br_r, dout_bi_r;

    // ==========================================
    // PORT A
    // ==========================================
    always @(posedge clk) begin
        if(we_a) begin
            real_mem[port_a_addr] <= in_a_r;
            imag_mem[port_a_addr] <= in_a_i;
        end
        dout_ar_r <= real_mem[port_a_addr];
        dout_ai_r <= imag_mem[port_a_addr];
    end

    // ==========================================
    // PORT B
    // ==========================================
    always @(posedge clk) begin
        if(we_b) begin
            real_mem[port_b_addr] <= in_b_r;
            imag_mem[port_b_addr] <= in_b_i;
        end
        dout_br_r <= real_mem[port_b_addr];
        dout_bi_r <= imag_mem[port_b_addr];
    end

    // Assign outputs
    assign dout_ar = dout_ar_r;
    assign dout_ai = dout_ai_r;
    assign dout_br = dout_br_r;
    assign dout_bi = dout_bi_r;

    // Debug load print
    always @(posedge clk) begin
        // synthesis translate_off
        if(load_en) begin
            $display("LOAD | addr=%0d | data=%0d + j%0d", load_addr, load_data_r, load_data_i);
        end
        // synthesis translate_on
    end

endmodule
