"""
build_tb.py
Encodes 1024 complex samples from radar_inputs_1024.txt as Posit(N,1)
and writes tb_fft16.v.
"""
import math
import sys
import os
import re

N = 16
if len(sys.argv) > 1:
    N = int(sys.argv[1])
POINTS      = 1024
LOG2_POINTS = 10

# ── Posit (N,1) encoder ──────────────────────────────────────────────────────
def encode(val, N=12):
    if val == 0: return 0
    if math.isnan(val) or math.isinf(val): return 1 << (N - 1)
    sign    = 1 if val < 0 else 0
    val_abs = abs(val)
    e_val   = math.floor(math.log2(val_abs))
    k, e    = e_val // 2, e_val % 2
    fraction = val_abs / (4**k * 2**e)
    p = 0
    regime_bit = 1 if k >= 0 else 0
    run        = (k + 1) if k >= 0 else (-k)
    idx = N - 2
    for _ in range(run):
        if idx >= 0: p |= regime_bit << idx; idx -= 1
    if idx >= 0: p |= (1 - regime_bit) << idx; idx -= 1
    if idx >= 0: p |= e << idx; idx -= 1
    if idx >= 0:
        scaled = round((fraction - 1.0) * (2 ** (idx + 1)))
        if scaled >= (2 ** (idx + 1)): scaled = (2 ** (idx + 1)) - 1
        p |= scaled
    if sign: p = ((~p) + 1) & ((1 << N) - 1)
    return p

# ── Twos complement converter for 12-bit hex ────────────────────────────────
def hex_to_twos_comp_12bit(hex_str):
    val = int(hex_str, 16)
    if val & 0x800:
        val = val - 0x1000
    return val

script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(script_dir, '..'))

samples = []
file_path = os.path.join(workspace_root, 'sim', 'real_inputs_1024.txt')
with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line_str = line.strip()
        if not line_str:
            continue
        if "in_real" in line_str:
            match = re.search(r"in_real\s*\[\s*\d+\s*\]\s*=\s*12'h([0-9A-Fa-f]+);\s*in_imag\s*\[\s*\d+\s*\]\s*=\s*12'h([0-9A-Fa-f]+);", line_str)
            if match:
                r = hex_to_twos_comp_12bit(match.group(1)) / 1024.0
                i = hex_to_twos_comp_12bit(match.group(2)) / 1024.0
                samples.append(complex(r, i))
        else:
            try:
                samples.append(complex(float(line_str), 0.0))
            except ValueError:
                pass

assert len(samples) == POINTS, f"Expected {POINTS} samples, got {len(samples)}"

hw = (N + 3) // 4   # hex digits per value  e.g. N=8→2, N=12→3, N=16→4

# ── Build initial-block lines ─────────────────────────────────────────────────
init_lines = []
for i, v in enumerate(samples):
    r_enc = encode(v.real, N)
    i_enc = encode(v.imag, N)
    init_lines.append(f"    in_real[{i:4d}] = {N}'h{r_enc:0{hw}X}; in_imag[{i:4d}] = {N}'h{i_enc:0{hw}X};")

init_block = '\n'.join(init_lines)

# ── Testbench template ────────────────────────────────────────────────────────
tb = f"""`timescale 1ns/1ps
// Input File: {os.path.basename(file_path)}

module tb_controller;

parameter N           = {N};
parameter POINTS      = {POINTS};
parameter LOG2_POINTS = {LOG2_POINTS};

reg clk = 0;
always #5 clk = ~clk;

reg rst, start, load_en, read_en;
reg [LOG2_POINTS-1:0] load_addr, read_addr;
reg [N-1:0] load_data_r, load_data_i;
wire [N-1:0] out_data_r, out_data_i;
wire done;

fft16_top_fused #(.N(N), .POINTS(POINTS), .LOG2_POINTS(LOG2_POINTS)) DUT (
    .clk(clk), .rst(rst), .start(start),
    .load_en(load_en), .load_addr(load_addr),
    .load_data_r(load_data_r), .load_data_i(load_data_i),
    .read_en(read_en), .read_addr(read_addr),
    .out_data_r(out_data_r), .out_data_i(out_data_i),
    .done(done)
);

function [LOG2_POINTS-1:0] bitrev;
    input [LOG2_POINTS-1:0] x;
    integer b;
    reg [LOG2_POINTS-1:0] rev;
    begin
        rev = 0;
        for (b = 0; b < LOG2_POINTS; b = b + 1)
            rev[b] = x[LOG2_POINTS - 1 - b];
        bitrev = rev;
    end
endfunction

integer j;
reg [N-1:0] in_real [0:POINTS-1];
reg [N-1:0] in_imag [0:POINTS-1];
initial begin
{init_block}
end

integer i;
initial begin
    rst=1; start=0; load_en=0; load_addr=0;
    load_data_r=0; load_data_i=0; read_en=0; read_addr=0;
    #40; rst=0;

    for (i=0; i<POINTS; i=i+1) begin
        @(posedge clk); #1;
        load_en=1;
        load_addr  = bitrev(i[LOG2_POINTS-1:0]);
        load_data_r = in_real[i];
        load_data_i = in_imag[i];
    end
    @(posedge clk); #1; load_en=0;
    @(posedge clk); #1; start=1;
    @(posedge clk); #1; start=0;

    wait(done==1);
    @(posedge clk); #1;

    $display("==== FFT OUTPUT ====");
    for (i=0; i<POINTS; i=i+1) begin
        read_en=1; read_addr=i[LOG2_POINTS-1:0];
        @(posedge clk); #1;
        @(posedge clk); #1;
        $display("X[%0d] r=%h i=%h", i, out_data_r, out_data_i);
        read_en=0;
    end
    $display("==== END ====");
    #50; $finish;
end
endmodule
"""

tb_path = os.path.join(workspace_root, 'tb', 'tb_fft16_fused.v')
with open(tb_path, 'w', encoding='utf-8') as f:
    f.write(tb)

print(f"tb_fft16_fused.v written to tb/ — {POINTS} samples, N={N}, UTF-8 clean.")
