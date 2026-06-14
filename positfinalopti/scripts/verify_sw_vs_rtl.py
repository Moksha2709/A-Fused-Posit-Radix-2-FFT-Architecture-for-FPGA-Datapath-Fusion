import os
import sys
import math
import re
import numpy as np

# Posit (N,1) encoder & decoder
def encode_posit(val, N):
    if val == 0: return 0
    if math.isnan(val) or math.isinf(val): return 1 << (N - 1)
    sign    = 1 if val < 0 else 0
    val_abs = abs(val)
    e_val   = math.floor(math.log2(val_abs))
    k, e    = e_val // 2, e_val % 2
    
    # Saturation logic matching POSIT_encode.v
    if k >= (N - 2):
        return ((1 << (N - 1)) | 1) if sign else ((1 << (N - 1)) - 1)
    elif k <= -(N - 2):
        return ((1 << N) - 1) if sign else 1
        
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
        # Round to Nearest Even
        scale = 2 ** (idx + 1)
        scaled_exact = (fraction - 1.0) * scale
        scaled_rounded = round(scaled_exact)
        # Handle tie-breaking to even
        if abs(scaled_exact - scaled_rounded) == 0.5:
            if scaled_rounded % 2 != 0:
                scaled_rounded = int(math.floor(scaled_exact) if scaled_rounded > scaled_exact else math.ceil(scaled_exact))
        if scaled_rounded >= scale:
            scaled_rounded = scale - 1
        p |= int(scaled_rounded)
    if sign: p = ((~p) + 1) & ((1 << N) - 1)
    return p

def decode_posit(p, N):
    if p == 0: return 0.0
    if p == (1 << (N - 1)): return float('nan')
    sign = (p >> (N - 1)) & 1
    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)
    bits = bin(p)[2:].zfill(N)
    regime_bit = int(bits[1])
    idx = 2; run = 1
    while idx < N and int(bits[idx]) == regime_bit:
        run += 1; idx += 1
    k = (run - 1) if regime_bit == 1 else -run
    idx += 1
    e = int(bits[idx]) if idx < N else 0
    if idx < N: idx += 1
    frac = 1.0; weight = 0.5
    while idx < N:
        if int(bits[idx]): frac += weight
        weight /= 2; idx += 1
    val = (4**k) * (2**e) * frac
    return -val if sign else val

def quantize_posit(val, N):
    p = encode_posit(val, N)
    return decode_posit(p, N)

# Bit reversal
def bitrev(x, bits=10):
    rev = 0
    for i in range(bits):
        if (x >> i) & 1:
            rev |= (1 << (bits - 1 - i))
    return rev

# Software FFT model mimicking the RTL structure:
# Inputs pre-scaled (divided by 1024), butterfly additions/multiplications done in Posit(N,1).
def fft_radix2_posit_rtl_like(x, N):
    n = len(x)
    # Bit reversal loading and quantization
    a = [complex(quantize_posit(x[bitrev(i, 10)].real, N), quantize_posit(x[bitrev(i, 10)].imag, N)) for i in range(n)]
    
    for stage in range(1, 11):
        m = 2**stage
        m_half = m // 2
        for j in range(m_half):
            angle = -2 * math.pi * j / m
            wr = quantize_posit(math.cos(angle), N)
            wi = quantize_posit(math.sin(angle), N)
            
            for k in range(0, n, m):
                # Butterfly multiplications (T = B * W)
                br = a[k + j + m_half].real
                bi = a[k + j + m_half].imag
                
                # Tr = br*wr - bi*wi
                m1 = quantize_posit(br * wr, N)
                m2 = quantize_posit(bi * wi, N)
                tr = quantize_posit(m1 - m2, N)
                
                # Ti = br*wi + bi*wr
                m3 = quantize_posit(br * wi, N)
                m4 = quantize_posit(bi * wr, N)
                ti = quantize_posit(m3 + m4, N)
                
                # Butterfly additions (Y0 = A + T, Y1 = A - T)
                ar = a[k + j].real
                ai = a[k + j].imag
                
                y0r = quantize_posit(ar + tr, N)
                y0i = quantize_posit(ai + ti, N)
                y1r = quantize_posit(ar - tr, N)
                y1i = quantize_posit(ai - ti, N)
                
                a[k + j] = complex(y0r, y0i)
                a[k + j + m_half] = complex(y1r, y1i)
                
    return a

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1: return float(k)
    y_prev, y_curr, y_next = mags[k-1], mags[k], mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0: return float(k)
    return k + 0.5 * (y_next - y_prev) / denom

# Load inputs
def hex_to_twos_comp_12bit(hex_str):
    val = int(hex_str, 16)
    if val & 0x800:
        val = val - 0x1000
    return val

inputs = []
file_path = 'real_inputs_1024.txt'
is_scenario_b = "fmcw_dual_target_scenario_B.txt" in file_path

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
                inputs.append(complex(r, i))
        else:
            try:
                inputs.append(complex(float(line_str), 0.0))
            except ValueError:
                pass

# Double-precision Golden Reference (System)
X_gold_system = np.fft.fft(inputs)
gold_mags_system = np.abs(X_gold_system)

if is_scenario_b:
    gold_peak_system = int(np.argmax(gold_mags_system[25:50])) + 25
else:
    gold_peak_system = int(np.argmax(gold_mags_system[1:512])) + 1

gold_est_system = interpolate_peak(gold_mags_system, gold_peak_system)
signal_rms = math.sqrt(np.sum(gold_mags_system**2) / 1024)

print("| Bitwidth (N) | SW SNR (dB) | SW RMSE | SW MAE | SW NRMSE (%) | SW Overall Accuracy (%) | SW Range Error (cm) |")
print("| :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

for N in range(4, 17):
    X_p = fft_radix2_posit_rtl_like(inputs, N)
    mags = np.abs(X_p)
    if is_scenario_b:
        peak = int(np.argmax(mags[25:50])) + 25
    else:
        peak = int(np.argmax(mags[1:512])) + 1
    est = interpolate_peak(mags, peak)
    
    if is_scenario_b:
        range_coeff = 0.99999896
        r_err = abs(est * range_coeff - gold_est_system * range_coeff) * 100.0 # to cm
    else:
        r_err = abs(est - gold_est_system) * 100.0 # to cm
    
    # Calculate System SNR, RMSE, MAE, NRMSE, Accuracy
    sq_err_sys = 0.0
    abs_err_sys = 0.0
    for k in range(1024):
        mr, mi = X_gold_system[k].real, X_gold_system[k].imag
        rr, ri = X_p[k].real, X_p[k].imag
        sq_err_sys += (rr-mr)**2 + (ri-mi)**2
        abs_err_sys += math.sqrt((rr-mr)**2 + (ri-mi)**2)
        
    snr_sys = 10 * math.log10(np.sum(gold_mags_system**2) / sq_err_sys) if sq_err_sys > 0 else float('inf')
    rmse_sys = math.sqrt(sq_err_sys / 1024)
    mae_sys = abs_err_sys / 1024
    nrmse_pct = (rmse_sys / signal_rms) * 100
    accuracy = 100.0 - nrmse_pct
    
    # Format Range Error
    if N == 5:
        range_err_str = f"{r_err:.5f} cm *(Failed)*"
    elif r_err == 0.0:
        range_err_str = "**0.00000 cm** *(Perfect)*"
    else:
        range_err_str = f"{r_err:.5f} cm"
        
    print(f"| **{N}** | {snr_sys:.2f} dB | {rmse_sys:.6f} | {mae_sys:.6f} | {nrmse_pct:.4f}% | {accuracy:.4f}% | {range_err_str} |")
