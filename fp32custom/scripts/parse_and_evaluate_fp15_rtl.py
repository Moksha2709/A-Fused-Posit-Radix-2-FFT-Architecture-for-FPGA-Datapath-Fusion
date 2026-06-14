import os
import math
import subprocess
import re
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# Try loading original samples from analyze_previous_signal.py
analyze_path = os.path.join(project_root, 'scripts', 'scratch', 'analyze_previous_signal.py')
unquantized_inputs = None

if os.path.exists(analyze_path):
    try:
        with open(analyze_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r"prev_samples\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            prev_samples_str = match.group(1).strip()
            unquantized_inputs = [float(x.strip()) for x in prev_samples_str.split(',') if x.strip()]
    except Exception as e:
        print(f"Could not load samples from analyze_previous_signal.py: {e}")

if unquantized_inputs is None:
    # Fallback to local FMCW single target input file
    fallback_data_path = os.path.join(project_root, 'data', 'fmcw_single_target_1024.txt')
    if os.path.exists(fallback_data_path):
        with open(fallback_data_path, 'r') as f:
            unquantized_inputs = [float(line.strip()) for line in f if line.strip()]
    else:
        # Generate default inputs if everything else fails
        unquantized_inputs = [math.sin(2 * math.pi * 3 * i / 1024) for i in range(1024)]

# Golden Reference Double-Precision FFT
X_golden = np.fft.fft(unquantized_inputs)
golden_mags = np.abs(X_golden)
golden_peak_idx = int(np.argmax(golden_mags[1:512])) + 1

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1:
        return float(k)
    y_prev = mags[k-1]
    y_curr = mags[k]
    y_next = mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0:
        return float(k)
    offset = 0.5 * (y_next - y_prev) / denom
    return k + offset

golden_interp = interpolate_peak(golden_mags, golden_peak_idx)

# FP15 Encoder Helper
def encode_fp15(val):
    if val == 0.0: return 0
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    exp_val = math.floor(math.log2(val_abs))
    exp = exp_val + 15
    
    if exp <= 0:
        mant = round((val_abs / (2**-14)) * 512)
        if mant >= 512:
            mant = 0; exp = 1
        else:
            exp = 0
    elif exp >= 31:
        exp = 30; mant = 511
    else:
        mant = round(((val_abs / 2**exp_val) - 1.0) * 512)
        if mant == 512:
            mant = 0; exp += 1
            if exp >= 31: exp = 30; mant = 511
    return (sign << 14) | (exp << 9) | mant

def decode_fp15(p):
    if p == 0: return 0.0
    sign = (p >> 14) & 1
    exp = (p >> 9) & 0x1F
    mant = p & 0x1FF
    if exp == 0:
        val = (mant / 512.0) * (2**-14)
    elif exp == 0x1F:
        return float('nan')
    else:
        val = (1.0 + mant / 512.0) * (2**(exp - 15))
    return -val if sign else val

# 2. Corrected FP15 adder design (proper rounding and fraction bits extraction)
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

    // Rounding & final compilation (FP15 has 9 mantissa bits)
    // Leading one is at norm_mant[22]. 9 fractional bits are norm_mant[21:13]
    // Rounding: round bit is norm_mant[12], sticky bit is |norm_mant[11:0]
    reg [8:0] frac_out;
    reg signed [5:0] final_exp_r;
    wire round_up = norm_mant[12] && (norm_mant[13] || |norm_mant[11:0]);
    wire [23:0] rounded_mant = {1'b0, norm_mant} + (round_up << 13);

    always @(*) begin
        if (zero_l || norm_mant == 23'd0) begin
            out = 15'd0;
        end else begin
            if (rounded_mant[23]) begin // Carry-out from rounding propagates to exp
                frac_out = rounded_mant[22:14];
                final_exp_r = final_exp + 1;
            end else begin
                frac_out = rounded_mant[21:13];
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
with open('hdl/fp16_add.v', 'w', encoding='utf-8') as f:
    f.write(fp15_add_code)
print("Updated hdl/fp16_add.v with CORRECTED FP15 adder design")

# 3. Compile and Run
print("Running iverilog compilation...")
subprocess.run("iverilog -o sim/sim.out hdl/fp16_add.v hdl/fp16_sub.v hdl/fp16_mul.v hdl/fp16_butterfly.v hdl/fp16_twiddle_rom.v hdl/sample_ram.v hdl/fp16_fft16_top.v sim/tb_fft16.v", shell=True, check=True)
print("Running simulation...")
subprocess.run("vvp sim/sim.out > sim/sim_1024_fp15.log", shell=True, check=True)
print("Simulation done!")

# 4. Parse the log file and calculate metrics
log_file = "sim/sim_1024_fp15.log"
pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
rtl = {}
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        m = pattern.search(line)
        if m:
            idx = int(m.group(1))
            rtl[idx] = (decode_fp15(int(m.group(2), 16)), decode_fp15(int(m.group(3), 16)))

print(f"Parsed {len(rtl)} bins from RTL log.")

# Compute metrics vs unquantized golden FFT
sq_signal = 0.0
sq_err = 0.0
abs_err = 0.0
rtl_mags = np.zeros(1024)

for k in range(1024):
    gr, gi = X_golden[k].real, X_golden[k].imag
    rr, ri = rtl.get(k, (0.0, 0.0))
    sq_signal += gr*gr + gi*gi
    sq_err += (rr-gr)**2 + (ri-gi)**2
    abs_err += math.sqrt((rr-gr)**2 + (ri-gi)**2)
    rtl_mags[k] = math.sqrt(rr*rr + ri*ri)

rmse = math.sqrt(sq_err / 1024)
mae = abs_err / 1024
signal_rms = math.sqrt(sq_signal / 1024)
nrmse_pct = (rmse / signal_rms) * 100
accuracy = 100.0 - nrmse_pct
snr = 10 * math.log10(sq_signal / sq_err)

rtl_peak_idx = int(np.argmax(rtl_mags[1:512])) + 1
rtl_interp = interpolate_peak(rtl_mags, rtl_peak_idx)
range_error = abs(rtl_interp - golden_interp) * 100.0 # in cm

print("\n=================================================================================")
print(" FINAL FP15 (e5m9) RTL ACCURACY REPORT (CORRECTED)")
print("=================================================================================")
print(f"  End-to-End SNR (dB)           : {snr:.2f} dB")
print(f"  RMSE                          : {rmse:.6f}")
print(f"  MAE                           : {mae:.6f}")
print(f"  NRMSE (%)                     : {nrmse_pct:.4f}%")
print(f"  Overall Accuracy (%)          : {accuracy:.4f}%")
print(f"  Estimated Peak Range (m)      : {rtl_interp:.6f} m")
print(f"  Range Error vs Golden (cm)    : {range_error:.4f} cm")
print("=================================================================================")
