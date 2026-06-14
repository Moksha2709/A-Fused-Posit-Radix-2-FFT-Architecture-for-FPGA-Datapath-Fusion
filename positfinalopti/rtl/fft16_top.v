module fft16_top #(
    parameter N          = 16,
    parameter POINTS     = 1024,
    parameter LOG2_POINTS = 10
)(
    input clk,
    input rst,
    input start,

    input load_en,
    input [LOG2_POINTS-1:0] load_addr,
    input [N-1:0] load_data_r,
    input [N-1:0] load_data_i,

    // NEW PORTS: Added so Vivado doesn't optimize away the logic
    input read_en,
    input [LOG2_POINTS-1:0] read_addr,
    output [N-1:0] out_data_r,
    output [N-1:0] out_data_i,

    output reg done
);


// STATE MACHINE


reg [LOG2_POINTS-1:0]   stage;
reg [LOG2_POINTS-2:0]   butterfly;
reg [3:0]               state;


localparam IDLE      = 4'd0,
           READ      = 4'd1,
           WAIT1     = 4'd2,
           WAIT2     = 4'd3,
           COMPUTE   = 4'd4,
           WRITE     = 4'd5,
           UPDATE    = 4'd6,
           STAGEWAIT = 4'd7,
           DONE_S    = 4'd8;


// MEMORY + TWIDDLE + BUTTERFLY WIRES


reg  [LOG2_POINTS-1:0] addr_a, addr_b;
reg  [LOG2_POINTS-1:0] addr_a_r, addr_b_r;
reg  [LOG2_POINTS-2:0] tw_addr, tw_addr_r;

reg we;

wire [N-1:0] ar, ai, br, bi;
wire [N-1:0] wr, wi;
wire [N-1:0] y0r, y0i, y1r, y1i;

reg [N-1:0] ar_r, ai_r, br_r, bi_r;
reg [N-1:0] y0r_r, y0i_r, y1r_r, y1i_r;


// RAM


sample_ram #(.N(N), .POINTS(POINTS), .ADDR_WIDTH(LOG2_POINTS)) RAM (
    .clk(clk),
    .addr_a(addr_a_r),
    .addr_b(addr_b_r),
    .we(we),

    .din_ar(y0r_r),
    .din_ai(y0i_r),
    .din_br(y1r_r),
    .din_bi(y1i_r),

    .dout_ar(ar),
    .dout_ai(ai),
    .dout_br(br),
    .dout_bi(bi),

    .load_en(load_en),
    .load_addr(load_addr),
    .load_data_r(load_data_r),
    .load_data_i(load_data_i)
);


// TWIDDLE ROM


twiddle_rom #(.N(N)) TW (
    .addr(tw_addr_r),
    .wr(wr),
    .wi(wi)
);


// BUTTERFLY


butterfly #(.N(N)) BF (
    .ar(ar_r), .ai(ai_r),
    .br(br_r), .bi(bi_r),
    .wr(wr), .wi(wi),
    .y0r(y0r), .y0i(y0i),
    .y1r(y1r), .y1i(y1i)
);


// ADDRESS GENERATION


integer distance, group_size, group, pos;

always @(*) begin
    distance   = 1 << stage;
    group_size = distance << 1;

    group = butterfly / distance;
    pos   = butterfly % distance;

    addr_a = group * group_size + pos;
    addr_b = addr_a + distance;

    // Generic DIT twiddle address: W^(pos * 2^(LOG2_POINTS-1-stage))
    tw_addr = pos << (LOG2_POINTS - 1 - stage);
end


// PIPELINE REGISTERS & FSM
always @(posedge clk or posedge rst) begin
if(rst) begin
    state     <= IDLE;
    stage     <= 0;
    butterfly <= 0;
    done      <= 0;
    we        <= 0;

    addr_a_r  <= 0;
    addr_b_r  <= 0;
    tw_addr_r <= 0;

    ar_r      <= 0;
    ai_r      <= 0;
    br_r      <= 0;
    bi_r      <= 0;

    y0r_r     <= 0;
    y0i_r     <= 0;
    y1r_r     <= 0;
    y1i_r     <= 0;
end
else begin
    // Pipeline updates
    if(state == READ) begin
        addr_a_r  <= addr_a;
        addr_b_r  <= addr_b;
        tw_addr_r <= tw_addr;
    end
    else if (read_en) begin
        addr_a_r <= read_addr;
    end

    if(state == WAIT2) begin
        ar_r <= ar;
        ai_r <= ai;
        br_r <= br;
        bi_r <= bi;
    end

    if(state == COMPUTE) begin
        y0r_r <= y0r;
        y0i_r <= y0i;
        y1r_r <= y1r;
        y1i_r <= y1i;
    end

    case(state)

IDLE: begin
    done <= 0;
    if(start) begin
        stage     <= 0;
        butterfly <= 0;
        state     <= READ;
    end
end

READ:    state <= WAIT1;
WAIT1:   state <= WAIT2;
WAIT2:   state <= COMPUTE;
COMPUTE: state <= WRITE;

WRITE: begin
    we    <= 1;
    state <= UPDATE;
end

UPDATE: begin
    we <= 0;

    if(butterfly == (POINTS/2 - 1)) begin
        butterfly <= 0;
        state     <= STAGEWAIT;
    end
    else begin
        butterfly <= butterfly + 1;
        state     <= READ;
    end
end


STAGEWAIT: begin
    // allow RAM write to settle
    if(stage == LOG2_POINTS - 1)
        state <= DONE_S;
    else begin
        stage <= stage + 1;
        state <= READ;
    end
end


DONE_S: begin
    done  <= 1;
    state <= IDLE;
end

endcase
end
end

// synthesis translate_off
always @(posedge clk) begin
    if (state == WAIT2) begin
        $display("STAGE %0d | butterfly=%0d | pos=%0d | addr_a=%0d | addr_b=%0d | tw_addr_r=%0d",
                 stage, butterfly, pos, addr_a_r, addr_b_r, tw_addr_r);

        $display("  INPUTS : A = %0d + j%0d   B = %0d + j%0d",
                 ar, ai, br, bi);

        $display("  TWIDDLE: W = %0d + j%0d",
                 wr, wi);
    end
end
// synthesis translate_on

// synthesis translate_off
always @(posedge clk) begin
    if (state == COMPUTE) begin
        $display("  OUTPUTS: Y0 = %0d + j%0d   Y1 = %0d + j%0d",
                 y0r, y0i, y1r, y1i);
    end
end
// synthesis translate_on

// synthesis translate_off
always @(posedge clk) begin
    if (state == WRITE) begin
        $display("  WRITE  : RAM[%0d] <= %0d + j%0d",
                 addr_a_r, y0r_r, y0i_r);

        $display("           RAM[%0d] <= %0d + j%0d",
                 addr_b_r, y1r_r, y1i_r);

        $display("------------------------------------------------");
    end
end
// synthesis translate_on

assign out_data_r = ar;
assign out_data_i = ai;

endmodule