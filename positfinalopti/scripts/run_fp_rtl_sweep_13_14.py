import os
import math
import subprocess
import re
import numpy as np

# Directory configurations
fp_dir = r"C:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\Floatingpoint_N_1_Corrected (2)\Floatingpoint_N_1_Corrected\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL"
os.chdir(fp_dir)

# Read original radar input samples from real_inputs_1024.txt
workspace_dir = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL"
real_inputs_path = os.path.join(workspace_dir, "real_inputs_1024.txt")

inputs = []
with open(real_inputs_path, 'r', encoding='utf-8') as f:
    for line in f:
        line_str = line.strip()
        if not line_str: continue
        inputs.append(float(line_str))

assert len(inputs) == 1024

# Golden reference
X_gold = np.fft.fft([complex(x, 0.0) for x in inputs])
mags_gold = np.abs(X_gold)

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1: return float(k)
    y_prev, y_curr, y_next = mags[k-1], mags[k], mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0: return float(k)
    return k + 0.5 * (y_next - y_prev) / denom

gold_peak = 18
gold_interp = interpolate_peak(mags_gold, gold_peak)
range_coeff = 0.99999896
true_range = gold_interp * range_coeff

# Float Encoding/Decoding Helpers
def encode_fp(val, N):
    if val == 0.0: return 0
    M = N - 6
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    exp_val = math.floor(math.log2(val_abs))
    exp = exp_val + 15  # Bias = 15
    max_mant = (1 << M) - 1
    
    if exp <= 0: # Subnormal
        mant = round((val_abs / (2**-14)) * (2**M))
        if mant >= (2**M):
            mant = 0; exp = 1
        else:
            exp = 0
    elif exp >= 31: # Overflow
        exp = 30; mant = max_mant
    else: # Normal
        mant = round(((val_abs / (2**exp_val)) - 1.0) * (2**M))
        if mant == (1 << M):
            mant = 0; exp += 1
            if exp >= 31: exp = 30; mant = max_mant
            
    return (sign << (N-1)) | (exp << M) | mant

def decode_fp(p, N):
    if p == 0: return 0.0
    M = N - 6
    sign = (p >> (N - 1)) & 1
    exp = (p >> M) & 0x1F
    mant = p & ((1 << M) - 1)
    if exp == 0:
        val = (mant / (2**M)) * (2**-14)
    elif exp == 0x1F:
        return float('nan')
    else:
        val = (1.0 + mant / (2**M)) * (2**(exp - 15))
    return -val if sign else val

def generate_add_verilog(N):
    M = N - 6
    W_ext = M + 14
    
    # Priority encoder logic
    pe_lines = []
    for shift in range(W_ext):
        bit = W_ext - 1 - shift
        if shift == 0:
            pe_lines.append(f"            if (sum_mant[{bit}]) norm_shift = 5'd{shift};")
        else:
            pe_lines.append(f"            else if (sum_mant[{bit}]) norm_shift = 5'd{shift};")
    pe_lines.append(f"            else norm_shift = 5'd{W_ext-1};")
    pe_str = "\n".join(pe_lines)
    
    code = f"""`timescale 1ns / 1ps

module fp16_add (
    input  wire [{N-1}:0] a,
    input  wire [{N-1}:0] b,
    output reg  [{N-1}:0] out
);

    // Unpack fields for FP{N} (1 sign, 5 exponent, {M} mantissa)
    wire sign_a = a[{N-1}];
    wire sign_b = b[{N-1}];
    wire [4:0] exp_a = a[{N-2}:{M}];
    wire [4:0] exp_b = b[{N-2}:{M}];
    wire [{M-1}:0] frac_a = a[{M-1}:0];
    wire [{M-1}:0] frac_b = b[{M-1}:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Sorting operands by magnitude
    wire a_greater = (exp_a > exp_b) || ((exp_a == exp_b) && (frac_a >= frac_b));

    reg sign_l, sign_s;
    reg [4:0] exp_l, exp_s;
    reg [{M-1}:0] frac_l, frac_s;
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
    wire [{M}:0] mant_l = {{~zero_l, frac_l}};
    wire [{M}:0] mant_s = {{~zero_s, frac_s}};

    // Extended mantissas for high precision alignment ({W_ext} bits total: {M+1} bits + 13 fractional/guard bits)
    wire [{W_ext-1}:0] mant_l_ext = {{mant_l, 13'd0}};
    wire [{W_ext-1}:0] mant_s_ext = {{mant_s, 13'd0}};
    
    // Shift smaller operand mantissa
    wire [{W_ext-1}:0] mant_s_aligned = (exp_diff >= 5'd{W_ext}) ? {W_ext}'d0 : (mant_s_ext >> exp_diff);

    // Sum significands
    reg [{W_ext}:0] sum_mant; // carries over
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
    reg [{W_ext-1}:0] norm_mant;
    reg signed [5:0] final_exp;

    always @(*) begin
        if (sum_mant == {W_ext+1}'d0) begin
            norm_shift = 5'd0;
            norm_mant  = {W_ext}'d0;
        end else if (sum_mant[{W_ext}]) begin // Addition overflow carry
            norm_shift = 5'd0;
            norm_mant  = sum_mant[{W_ext}:1];
        end else begin
{pe_str}
            norm_mant = sum_mant[{W_ext-1}:0] << norm_shift;
        end
    end

    // Exponent shift adjustment
    always @(*) begin
        if (zero_l) begin
            final_exp = 6'd0;
        end else if (sum_mant[{W_ext}]) begin
            final_exp = exp_l + 1;
        end else begin
            final_exp = exp_l - norm_shift;
        end
    end

    // Rounding & final compilation
    reg [{M-1}:0] frac_out;
    reg signed [5:0] final_exp_r;
    wire round_up = norm_mant[12] && (norm_mant[13] || |norm_mant[11:0]);
    wire [{W_ext}:0] rounded_mant = {{1'b0, norm_mant}} + (round_up << {W_ext-1-M});

    always @(*) begin
        if (zero_l || norm_mant == {W_ext}'d0) begin
            out = {N}'d0;
        end else begin
            if (rounded_mant[{W_ext}]) begin // Carry-out from rounding propagates to exp
                frac_out = rounded_mant[{W_ext-1}:{W_ext-M}];
                final_exp_r = final_exp + 1;
            end else begin
                frac_out = rounded_mant[{W_ext-2}:{W_ext-1-M}];
                final_exp_r = final_exp;
            end

            // Check bounds (using signed comparison)
            if (final_exp_r >= 31) begin
                out = {{sign_l, 5'd31, {M}'d0}}; // Overflow to infinity
            end else if (final_exp_r <= 0) begin
                out = {{sign_l, {N-1}'d0}}; // Underflow to zero
            end else begin
                out = {{sign_l, final_exp_r[4:0], frac_out}};
            end
        end
    end

endmodule
"""
    return code

def generate_mul_verilog(N):
    M = N - 6
    code = f"""`timescale 1ns / 1ps

module fp16_mul (
    input  wire [{N-1}:0] a,
    input  wire [{N-1}:0] b,
    output reg  [{N-1}:0] out
);

    // Unpack fields for FP{N} (1 sign, 5 exponent, {M} mantissa)
    wire sign_a = a[{N-1}];
    wire sign_b = b[{N-1}];
    wire [4:0] exp_a = a[{N-2}:{M}];
    wire [4:0] exp_b = b[{N-2}:{M}];
    wire [{M-1}:0] frac_a = a[{M-1}:0];
    wire [{M-1}:0] frac_b = b[{M-1}:0];

    // Detect zero operands
    wire zero_a = (exp_a == 5'd0);
    wire zero_b = (exp_b == 5'd0);

    // Detect infinity or NaN
    wire inf_nan_a = (exp_a == 5'd31);
    wire inf_nan_b = (exp_b == 5'd31);

    // Output sign
    wire sign_out = sign_a ^ sign_b;

    // Implicit leading ones
    wire [{M}:0] mant_a = {{~zero_a, frac_a}};
    wire [{M}:0] mant_b = {{~zero_b, frac_b}};

    // Multiply mantissas ({M+1} bits * {M+1} bits = {2*M+2} bits)
    wire [{2*M+1}:0] prod = mant_a * mant_b;

    // Intermediate exponent calculation: exp_a + exp_b - 15
    wire signed [6:0] exp_calc = exp_a + exp_b - 7'd15;

    // Normalization & Rounding
    reg [{M-1}:0] frac_out;
    reg [{2*M+1}:0] shifted_prod;
    reg signed [6:0] exp_shift;
    reg signed [6:0] final_exp;

    always @(*) begin
        if (zero_a || zero_b) begin
            out = {{sign_out, {N-1}'d0}};
        end else if (inf_nan_a || inf_nan_b) begin
            if ((inf_nan_a && zero_b) || (inf_nan_b && zero_a)) begin
                out = {{sign_out, 5'd31, {M}'h{1<<(M-1):X}}}; // NaN
            end else if (frac_a != {M}'d0 || frac_b != {M}'d0) begin
                out = {{sign_out, 5'd31, {M}'h{1<<(M-1):X}}}; // NaN
            end else begin
                out = {{sign_out, 5'd31, {M}'d0}}; // Inf
            end
        end else begin
            // Shift product so MSB is at top bit
            if (prod[{2*M+1}]) begin
                shifted_prod = prod;
                exp_shift = exp_calc + 1;
            end else begin
                shifted_prod = prod << 1;
                exp_shift = exp_calc;
            end

            // Rounding check (round-to-nearest-even)
            if (shifted_prod[{M}] && (shifted_prod[{M+1}] || |shifted_prod[{M-1}:0])) begin
                if (shifted_prod[{2*M+1}:{M+1}] == {M+1}'h{((1<<(M+1))-1):X}) begin
                    frac_out = {M}'d0;
                    final_exp = exp_shift + 1;
                end else begin
                    frac_out = shifted_prod[{2*M}:{M+1}] + 1'b1;
                    final_exp = exp_shift;
                end
            end else begin
                frac_out = shifted_prod[{2*M}:{M+1}];
                final_exp = exp_shift;
            end

            // Check exponent bounds (using signed comparison)
            if (final_exp >= 31) begin
                out = {{sign_out, 5'd31, {M}'d0}}; // Overflow to Inf
            end else if (final_exp <= 0) begin
                out = {{sign_out, {N-1}'d0}}; // Underflow to Zero (FTZ)
            end else begin
                out = {{sign_out, final_exp[4:0], frac_out}};
            end
        end
    end

endmodule
"""
    return code

def generate_sub_verilog(N):
    return f"""`timescale 1ns / 1ps

module fp16_sub (
    input  wire [{N-1}:0] a,
    input  wire [{N-1}:0] b,
    output wire [{N-1}:0] out
);

    wire [{N-1}:0] b_neg = {{~b[{N-1}], b[{N-2}:0]}};

    fp16_add adder_inst (
        .a(a),
        .b(b_neg),
        .out(out)
    );

endmodule
"""

def generate_butterfly_verilog(N):
    return f"""`timescale 1ns / 1ps

module fp16_butterfly (
    input  wire [{N-1}:0] ar, ai,
    input  wire [{N-1}:0] br, bi,
    input  wire [{N-1}:0] wr, wi,
    
    output wire [{N-1}:0] y0r, y0i,
    output wire [{N-1}:0] y1r, y1i
);

    wire [{N-1}:0] m1, m2, m3, m4;
    wire [{N-1}:0] Tr, Ti;

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

# Sweep FP13 and FP14
results = {}

for N in [13, 14]:
    print(f"\n--- Running RTL Simulation for FP{N} ---")
    
    # 1. Generate Twiddle ROM
    twiddle_lines = [
        "`timescale 1ns/1ps",
        "module fp16_twiddle_rom (",
        "    input clk,",
        "    input  [8:0] addr,",
        f"    output reg [{N-1}:0] wr,",
        f"    output reg [{N-1}:0] wi",
        ");",
        "always @(*) begin",
        "    case(addr)"
    ]
    for i in range(512):
        c =  math.cos(2 * math.pi * i / 1024)
        s = -math.sin(2 * math.pi * i / 1024)
        c_enc = encode_fp(c, N)
        s_enc = encode_fp(s, N)
        twiddle_lines.append(f"        9'd{i}: begin wr = {N}'h{c_enc:X}; wi = {N}'h{s_enc:X}; end")
    twiddle_lines.append(f"        default: begin wr = {N}'d0; wi = {N}'d0; end")
    twiddle_lines.append("    endcase")
    twiddle_lines.append("end")
    twiddle_lines.append("endmodule")
    
    with open('fp16_twiddle_rom.v', 'w', encoding='utf-8') as f:
        f.write('\n'.join(twiddle_lines) + '\n')
    print("Generated Twiddle ROM")

    # 2. Generate Adder, Multiplier, Subtractor, Butterfly
    with open('fp16_add.v', 'w', encoding='utf-8') as f:
        f.write(generate_add_verilog(N))
    with open('fp16_mul.v', 'w', encoding='utf-8') as f:
        f.write(generate_mul_verilog(N))
    with open('fp16_sub.v', 'w', encoding='utf-8') as f:
        f.write(generate_sub_verilog(N))
    with open('fp16_butterfly.v', 'w', encoding='utf-8') as f:
        f.write(generate_butterfly_verilog(N))
    print("Generated Operators")

    # 3. Update top parameter
    with open('fp16_fft16_top.v', 'r', encoding='utf-8') as f:
        top_code = f.read()
    top_code = re.sub(r'parameter N\s*=\s*\d+', f'parameter N          = {N}', top_code)
    with open('fp16_fft16_top.v', 'w', encoding='utf-8') as f:
        f.write(top_code)

    # 4. Update testbench parameters and inputs
    with open('tb_fft16.v', 'r', encoding='utf-8') as f:
        tb_code = f.read()
    tb_code = re.sub(r'parameter N\s*=\s*\d+', f'parameter N           = {N}', tb_code)
    
    assignments = []
    for i, val in enumerate(inputs):
        r_enc = encode_fp(val, N)
        i_enc = encode_fp(0.0, N)
        assignments.append(f"    in_real[{i:4d}] = {N}'h{r_enc:X}; in_imag[{i:4d}] = {N}'h{i_enc:X};")
        
    assignments_block = "\n".join(assignments)
    # Replace the entire initial block of assignments
    tb_code_new = re.sub(
        r'initial begin\s+in_real\[\s*0\s*\].*?end',
        "initial begin\n" + assignments_block + "\n    end",
        tb_code,
        flags=re.DOTALL
    )
    
    with open('tb_fft16.v', 'w', encoding='utf-8') as f:
        f.write(tb_code_new)
    print("Generated Testbench")

    # 5. Compile and Simulate
    log_file = f"sim_1024_fp{N}.log"
    print("Compiling...")
    subprocess.run("iverilog -o sim.out fp16_add.v fp16_sub.v fp16_mul.v fp16_butterfly.v fp16_twiddle_rom.v sample_ram.v fp16_fft16_top.v tb_fft16.v", shell=True, check=True)
    print("Simulating...")
    subprocess.run(f"vvp sim.out > {log_file}", shell=True, check=True)
    print("Simulation complete")

    # 6. Parse Log and Calculate Metrics
    pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
    rtl = {}
    
    # Try UTF-16 first, then UTF-8 fallback
    try:
        with open(log_file, 'r', encoding='utf-16') as f:
            lines = f.readlines()
    except UnicodeError:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
    for line in lines:
        m = pattern.search(line)
        if m:
            idx = int(m.group(1))
            rtl[idx] = (decode_fp(int(m.group(2), 16), N), decode_fp(int(m.group(3), 16), N))
            
    if len(rtl) != 1024:
        print(f"Error: FP{N} parsed only {len(rtl)} bins")
        continue

    sq_signal = 0.0
    sq_err = 0.0
    abs_err = 0.0
    rtl_mags = np.zeros(1024)
    
    for k in range(1024):
        gr, gi = X_gold[k].real, X_gold[k].imag
        rr, ri = rtl[k]
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
    
    rtl_peak = int(np.argmax(rtl_mags[1:512])) + 1
    rtl_interp = interpolate_peak(rtl_mags, rtl_peak)
    range_error = abs(rtl_interp * range_coeff - true_range) * 100.0
    
    results[N] = {
        'snr': snr,
        'rmse': rmse,
        'mae': mae,
        'nrmse': nrmse_pct,
        'accuracy': accuracy,
        'range_error': range_error
    }
    
    print(f"FP{N} RESULTS:")
    print(f"  SNR: {snr:.4f} dB")
    print(f"  RMSE: {rmse:.8f}")
    print(f"  Range Error: {range_error:.6f} cm")

print("\nSweep Complete!")
for N, res in results.items():
    print(f"| **FP{N}** | **{N}** | {res['snr']:.2f} dB | {res['rmse']:.6f} | {res['mae']:.6f} | {res['nrmse']:.4f}% | {res['accuracy']:.4f}% | {res['range_error']:.4f} cm |")
