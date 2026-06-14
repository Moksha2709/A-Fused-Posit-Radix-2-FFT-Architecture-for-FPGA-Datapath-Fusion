import os
import math
import subprocess
import re
import numpy as np

# Set path to the floating point directory dynamically
script_dir = os.path.dirname(os.path.abspath(__file__))
fp_dir = os.path.dirname(script_dir)
os.chdir(fp_dir)

# 1. Read original float samples from local copy
analyze_path = os.path.join(script_dir, "analyze_previous_signal.py")
with open(analyze_path, 'r', encoding='utf-8') as f:
    content = f.read()
match = re.search(r"prev_samples\s*=\s*\[(.*?)\]", content, re.DOTALL)
prev_samples_str = match.group(1).strip()
unquantized_inputs = [float(x.strip()) for x in prev_samples_str.split(',') if x.strip()]

# 2. FP15 Encoding Helper
def encode_fp15(val):
    if val == 0.0: return 0
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    exp_val = math.floor(math.log2(val_abs))
    exp = exp_val + 15 # Bias = 15
    
    if exp <= 0: # Subnormal
        mant = round((val_abs / (2**-14)) * 512)
        if mant >= 512:
            mant = 0
            exp = 1
        else:
            exp = 0
    elif exp >= 31: # Overflow
        exp = 30
        mant = 511
    else: # Normal
        mant = round(((val_abs / 2**exp_val) - 1.0) * 512)
        if mant == 512:
            mant = 0
            exp += 1
            if exp >= 31:
                exp = 30
                mant = 511
                
    return (sign << 14) | (exp << 9) | mant

# 3. Create backup folder and backup original files if not done already
backup_dir = os.path.join(fp_dir, "sim", "backup_fp12")
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)
    files_to_backup = ["fp16_add.v", "fp16_sub.v", "fp16_mul.v", "fp16_butterfly.v", "fp16_fft16_top.v", "tb_fft16.v", "fp16_twiddle_rom.v"]
    for file in files_to_backup:
        if file == "tb_fft16.v":
            src = os.path.join(fp_dir, "sim", file)
        else:
            src = os.path.join(fp_dir, "rtl", file)
        dst = os.path.join(backup_dir, file)
        if os.path.exists(src):
            with open(src, 'rb') as sf, open(dst, 'wb') as df:
                df.write(sf.read())
            print(f"Backed up {file} to sim/backup_fp12/")

# 4. Generate FP15 Twiddle ROM
twiddle_lines = []
twiddle_lines.append("`timescale 1ns/1ps")
twiddle_lines.append("module fp16_twiddle_rom (")
twiddle_lines.append("    input clk,")
twiddle_lines.append("    input  [8:0] addr,")
twiddle_lines.append("    output reg [14:0] wr,")
twiddle_lines.append("    output reg [14:0] wi")
twiddle_lines.append(");")
twiddle_lines.append("always @(*) begin")
twiddle_lines.append("    case(addr)")

for i in range(512):
    c =  math.cos(2 * math.pi * i / 1024)
    s = -math.sin(2 * math.pi * i / 1024)
    c_enc = encode_fp15(c)
    s_enc = encode_fp15(s)
    twiddle_lines.append(f"        9'd{i}: begin wr = 15'h{c_enc:04X}; wi = 15'h{s_enc:04X}; end")

twiddle_lines.append("        default: begin wr = 0; wi = 0; end")
twiddle_lines.append("    endcase")
twiddle_lines.append("end")
twiddle_lines.append("endmodule")

with open('rtl/fp16_twiddle_rom.v', 'w', encoding='utf-8') as f:
    f.write('\n'.join(twiddle_lines) + '\n')
print("Generated FP15 twiddle ROM in rtl/fp16_twiddle_rom.v")

# 5. Overwrite fp16_add.v with FP15 adder
fp15_add_code = """`timescale 1ns / 1ps

module fp16_add (
    input  wire [14:0] a,
    input  wire [14:0] b,
    output reg  [14:0] out
);

    // Unpack fields for FP15 (1 sign, 5 exponent, 9 mantissa)
    wire sign_a = a[14];
    wire sign_b = b[14];
    wire [4:0] exp_a = a[13:9];
    wire [4:0] exp_b = b[13:9];
    wire [8:0] frac_a = a[8:0];
    wire [8:0] frac_b = b[8:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Sorting operands by magnitude
    wire a_greater = (exp_a > exp_b) || ((exp_a == exp_b) && (frac_a >= frac_b));

    reg sign_l, sign_s;
    reg [4:0] exp_l, exp_s;
    reg [8:0] frac_l, frac_s;
    reg zero_l, zero_s;

    always @(*) begin
        if (a_greater) begin
            sign_l = sign_a;  sign_s = sign_b;
            exp_l  = exp_a;   exp_s  = exp_b;
            frac_l = frac_a;  frac_s = frac_b;
            zero_l = zero_a;  zero_s = zero_b;
        end else begin
            sign_l = sign_b;  sign_s = sign_a;
            exp_l  = exp_b;   exp_s  = exp_a;
            frac_l = frac_b;  frac_s = frac_a;
            zero_l = zero_b;  zero_s = zero_a;
        end
    end

    // Alignment and arithmetic wires
    wire [4:0] exp_diff = exp_l - exp_s;
    wire [9:0] mant_l = {~zero_l, frac_l};
    wire [9:0] mant_s = {~zero_s, frac_s};

    // Extended mantissas for high precision alignment (23 bits total: 10 bits + 13 fractional/guard bits)
    wire [22:0] mant_l_ext = {mant_l, 13'd0};
    wire [22:0] mant_s_ext = {mant_s, 13'd0};
    
    // Shift smaller operand mantissa
    wire [22:0] mant_s_aligned = (exp_diff >= 5'd23) ? 23'd0 : (mant_s_ext >> exp_diff);

    // Sum significands
    reg [23:0] sum_mant; // 24 bits to capture carry-out
    wire op_sub = sign_l ^ sign_s;

    always @(*) begin
        if (op_sub) begin
            sum_mant = mant_l_ext - mant_s_aligned;
        end else begin
            sum_mant = mant_l_ext + mant_s_aligned;
        end
    end

    // Normalization logic
    reg [4:0] norm_shift;
    reg [22:0] norm_mant;
    reg signed [5:0] final_exp;

    always @(*) begin
        if (sum_mant == 24'd0) begin
            norm_shift = 5'd0;
            norm_mant  = 23'd0;
        end else if (sum_mant[23]) begin // Addition overflow carry
            norm_shift = 5'd0;
            norm_mant  = sum_mant[23:1];
        end else begin
            // Priority encoder for leading-one detection (subtraction case)
            if (sum_mant[22])      norm_shift = 5'd0;
            else if (sum_mant[21]) norm_shift = 5'd1;
            else if (sum_mant[20]) norm_shift = 5'd2;
            else if (sum_mant[19]) norm_shift = 5'd3;
            else if (sum_mant[18]) norm_shift = 5'd4;
            else if (sum_mant[17]) norm_shift = 5'd5;
            else if (sum_mant[16]) norm_shift = 5'd6;
            else if (sum_mant[15]) norm_shift = 5'd7;
            else if (sum_mant[14]) norm_shift = 5'd8;
            else if (sum_mant[13]) norm_shift = 5'd9;
            else if (sum_mant[12]) norm_shift = 5'd10;
            else if (sum_mant[11]) norm_shift = 5'd11;
            else if (sum_mant[10]) norm_shift = 5'd12;
            else if (sum_mant[9])  norm_shift = 5'd13;
            else if (sum_mant[8])  norm_shift = 5'd14;
            else if (sum_mant[7])  norm_shift = 5'd15;
            else if (sum_mant[6])  norm_shift = 5'd16;
            else if (sum_mant[5])  norm_shift = 5'd17;
            else if (sum_mant[4])  norm_shift = 5'd18;
            else if (sum_mant[3])  norm_shift = 5'd19;
            else if (sum_mant[2])  norm_shift = 5'd20;
            else if (sum_mant[1])  norm_shift = 5'd21;
            else                   norm_shift = 5'd22;

            norm_mant = sum_mant[22:0] << norm_shift;
        end
    end

    // Exponent shift adjustment
    always @(*) begin
        if (zero_l) begin
            final_exp = 6'd0;
        end else if (sum_mant[23]) begin
            final_exp = exp_l + 1;
        end else begin
            final_exp = exp_l - norm_shift;
        end
    end

    // Rounding & final compilation (FP15 has 9 mantissa bits, which corresponds to norm_mant[22:14])
    reg [8:0] frac_out;
    reg signed [5:0] final_exp_r;
    // Rounding: round bit is norm_mant[13], sticky bit is |norm_mant[12:0]
    wire round_up = norm_mant[13] && (norm_mant[14] || |norm_mant[12:0]);
    wire [23:0] rounded_mant = {1'b0, norm_mant} + (round_up << 14);

    always @(*) begin
        if (zero_l || norm_mant == 23'd0) begin
            out = 15'd0;
        end else begin
            if (rounded_mant[23]) begin
                frac_out = 9'd0;
                final_exp_r = final_exp + 1;
            end else begin
                frac_out = rounded_mant[22:14];
                final_exp_r = final_exp;
            end

            // Check bounds (using signed comparison)
            if (final_exp_r >= 31) begin
                out = {sign_l, 5'd31, 9'd0}; // Overflow to infinity
            end else if (final_exp_r <= 0) begin
                out = {sign_l, 14'd0}; // Underflow to zero
            end else begin
                out = {sign_l, final_exp_r[4:0], frac_out};
            end
        end
    end

endmodule
"""
with open('rtl/fp16_add.v', 'w', encoding='utf-8') as f:
    f.write(fp15_add_code)
print("Updated rtl/fp16_add.v with FP15 design")

# 6. Overwrite fp16_sub.v with FP15 subtractor
fp15_sub_code = """`timescale 1ns / 1ps

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
"""
with open('rtl/fp16_sub.v', 'w', encoding='utf-8') as f:
    f.write(fp15_sub_code)
print("Updated rtl/fp16_sub.v with FP15 design")

# 7. Overwrite fp16_mul.v with FP15 multiplier
fp15_mul_code = """`timescale 1ns / 1ps

module fp16_mul (
    input  wire [14:0] a,
    input  wire [14:0] b,
    output reg  [14:0] out
);

    // FP15 Format: 1 sign bit, 5 exponent bits, 9 mantissa bits (bias = 15)
    wire sign_a = a[14];
    wire sign_b = b[14];
    wire [4:0] exp_a = a[13:9];
    wire [4:0] exp_b = b[13:9];
    wire [8:0] frac_a = a[8:0];
    wire [8:0] frac_b = b[8:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Detect infinity or NaN
    wire inf_nan_a = (exp_a == 5'd31);
    wire inf_nan_b = (exp_b == 5'd31);

    // Output sign
    wire sign_out = sign_a ^ sign_b;

    // Implicit leading ones
    wire [9:0] mant_a = {~zero_a, frac_a};
    wire [9:0] mant_b = {~zero_b, frac_b};

    // Multiply mantissas (10 bits * 10 bits = 20 bits)
    wire [19:0] prod = mant_a * mant_b;

    // Intermediate exponent calculation: exp_a + exp_b - 15
    wire signed [6:0] exp_calc = exp_a + exp_b - 7'd15;

    // Normalization & Rounding
    reg [8:0] frac_out;
    reg [19:0] shifted_prod;
    reg signed [6:0] exp_shift;
    reg signed [6:0] final_exp;

    always @(*) begin
        if (zero_a || zero_b) begin
            out = {sign_out, 14'd0};
        end else if (inf_nan_a || inf_nan_b) begin
            if ((inf_nan_a && zero_b) || (inf_nan_b && zero_a)) begin
                out = {sign_out, 5'd31, 9'h100}; // NaN
            end else if (frac_a != 9'd0 || frac_b != 9'd0) begin
                out = {sign_out, 5'd31, 9'h100}; // NaN
            end else begin
                out = {sign_out, 5'd31, 9'd0}; // Inf
            end
        end else begin
            // Shift product so MSB is at bit 19
            if (prod[19]) begin
                shifted_prod = prod;
                exp_shift = exp_calc + 1;
            end else begin
                shifted_prod = prod << 1;
                exp_shift = exp_calc;
            end

            // Rounding check (round-to-nearest-even)
            // 10-bit mantissa is shifted_prod[19:10]
            // LSB is shifted_prod[10], Round is shifted_prod[9], Sticky is |shifted_prod[8:0]
            if (shifted_prod[9] && (shifted_prod[10] || |shifted_prod[8:0])) begin
                if (shifted_prod[19:10] == 10'h3ff) begin
                    frac_out = 9'd0;
                    final_exp = exp_shift + 1;
                end else begin
                    frac_out = shifted_prod[18:10] + 1'b1;
                    final_exp = exp_shift;
                end
            end else begin
                frac_out = shifted_prod[18:10];
                final_exp = exp_shift;
            end

            // Check exponent bounds (using signed comparison)
            if (final_exp >= 31) begin
                out = {sign_out, 5'd31, 9'd0}; // Overflow to Inf
            end else if (final_exp <= 0) begin
                out = {sign_out, 14'd0}; // Underflow to Zero (FTZ)
            end else begin
                out = {sign_out, final_exp[4:0], frac_out};
            end
        end
    end

endmodule
"""
with open('rtl/fp16_mul.v', 'w', encoding='utf-8') as f:
    f.write(fp15_mul_code)
print("Updated rtl/fp16_mul.v with FP15 design")

# 8. Overwrite fp16_butterfly.v with FP15 butterfly
fp15_butterfly_code = """`timescale 1ns / 1ps

module fp16_butterfly (
    input  wire [14:0] ar, ai,
    input  wire [14:0] br, bi,
    input  wire [14:0] wr, wi,
    
    output wire [14:0] y0r, y0i,
    output wire [14:0] y1r, y1i
);

    wire [14:0] m1, m2, m3, m4;
    wire [14:0] Tr, Ti;

    fp16_mul M1 (.a(br), .b(wr), .out(m1));
    fp16_mul M2 (.a(bi), .b(wi), .out(m2));
    fp16_mul M3 (.a(br), .b(wi), .out(m3));
    fp16_mul M4 (.a(bi), .b(wr), .out(m4));

    fp16_sub S1 (.a(m1), .b(m2), .out(Tr));
    fp16_add A1 (.a(m3), .b(m4), .out(Ti));

    fp16_add A2 (.a(ar), .b(Tr), .out(y0r));
    fp16_add A3 (.a(ai), .b(Ti), .out(y0i));

    fp16_sub S2 (.a(ar), .b(Tr), .out(y1r));
    fp16_sub S3 (.a(ai), .b(Ti), .out(y1i));

endmodule
"""
with open('rtl/fp16_butterfly.v', 'w', encoding='utf-8') as f:
    f.write(fp15_butterfly_code)
print("Updated rtl/fp16_butterfly.v with FP15 design")

# 9. Modify fp16_fft16_top.v to change default N=15
with open('rtl/fp16_fft16_top.v', 'r', encoding='utf-8') as f:
    top_code = f.read()
top_code = re.sub(r'parameter N\s*=\s*\d+', 'parameter N          = 15', top_code)
with open('rtl/fp16_fft16_top.v', 'w', encoding='utf-8') as f:
    f.write(top_code)
print("Updated rtl/fp16_fft16_top.v default parameter N = 15")

# 10. Update tb_fft16.v with N=15 and new encoded inputs
with open('sim/tb_fft16.v', 'r', encoding='utf-8') as f:
    tb_code = f.read()
tb_code = re.sub(r'parameter N\s*=\s*\d+', 'parameter N           = 15', tb_code)

# Generate hex input assignments for tb_fft16.v
assignments = []
for i, val in enumerate(unquantized_inputs):
    r_enc = encode_fp15(val)
    i_enc = encode_fp15(0.0)
    assignments.append(f"    in_real[{i:4d}] = 15'h{r_enc:04X}; in_imag[{i:4d}] = 15'h{i_enc:04X};")

# Find the block where in_real assignments start and end
# Let's replace the entire block between initial begin and end
assignments_block_str = "\n".join(assignments)
tb_code = re.sub(
    r'initial begin\s*in_real\[\s*0\s*\].*?end',
    f"initial begin\n{assignments_block_str}\nend",
    tb_code,
    flags=re.DOTALL
)

with open('sim/tb_fft16.v', 'w', encoding='utf-8') as f:
    f.write(tb_code)
print("Updated sim/tb_fft16.v with FP15 input data assignments")

# 11. Run compilation and simulation
print("Compiling and executing simulation via iverilog & vvp...")
cmd_compile = "iverilog -o sim/sim.out rtl/fp16_add.v rtl/fp16_sub.v rtl/fp16_mul.v rtl/fp16_butterfly.v rtl/fp16_twiddle_rom.v rtl/sample_ram.v rtl/fp16_fft16_top.v sim/tb_fft16.v"
subprocess.run(cmd_compile, shell=True, check=True)

cmd_run = "vvp sim/sim.out > sim/sim_1024_fp15.log"
subprocess.run(cmd_run, shell=True, check=True)
print("Simulation complete. Log written to sim/sim_1024_fp15.log")
