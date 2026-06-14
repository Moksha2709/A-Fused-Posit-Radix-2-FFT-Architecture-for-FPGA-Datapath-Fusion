import re
import math
import numpy as np

# Path to the unquantized inputs
real_inputs_path = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL\real_inputs_1024.txt"
inputs = []
with open(real_inputs_path, 'r', encoding='utf-8') as f:
    for line in f:
        line_str = line.strip()
        if not line_str: continue
        inputs.append(complex(float(line_str), 0.0))

assert len(inputs) == 1024

# Golden reference FFT
X_gold = np.fft.fft(inputs)
mags_gold = np.abs(X_gold)

range_coeff = 0.99999896

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1: return float(k)
    y_prev, y_curr, y_next = mags[k-1], mags[k], mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0: return float(k)
    return k + 0.5 * (y_next - y_prev) / denom

gold_peak = 18
gold_interp = interpolate_peak(mags_gold, gold_peak)
true_range = gold_interp * range_coeff

# Decoders for FP12, FP15, FP16
def decode_fp12(p):
    if p == 0: return 0.0
    sign = (p >> 11) & 1
    exp = (p >> 6) & 0x1F
    mant = p & 0x3F
    if exp == 0:
        val = (mant / 64.0) * (2**-14)
    elif exp == 0x1F:
        return float('nan')
    else:
        val = (1.0 + mant / 64.0) * (2**(exp - 15))
    return -val if sign else val

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

def decode_fp16(p):
    # Standard IEEE-754 FP16 (1 sign, 5 exponent, 10 mantissa bits)
    if p == 0: return 0.0
    sign = (p >> 15) & 1
    exp = (p >> 10) & 0x1F
    mant = p & 0x3FF
    if exp == 0:
        val = (mant / 1024.0) * (2**-14)
    elif exp == 0x1F:
        return float('nan')
    else:
        val = (1.0 + mant / 1024.0) * (2**(exp - 15))
    return -val if sign else val

def decode_val(hex_str, N):
    p = int(hex_str, 16)
    if N == 12: return decode_fp12(p)
    elif N == 15: return decode_fp15(p)
    elif N == 16: return decode_fp16(p)
    else: raise ValueError(f"N={N} not supported")

# Analyze log files
log_files = {
    12: r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\Floatingpoint_N_1_Corrected (2)\Floatingpoint_N_1_Corrected\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL\sim_1024_fp12.log",
    15: r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\Floatingpoint_N_1_Corrected (2)\Floatingpoint_N_1_Corrected\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL\sim_1024_fp15.log",
    16: r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\Floatingpoint_N_1_Corrected (2)\Floatingpoint_N_1_Corrected\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL\sim_1024_fp16.log"
}

print("=" * 80)
print(" PARSING RTL SIMULATION LOGS FOR FLOATING-POINT")
print("=" * 80)

for N, path in log_files.items():
    pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
    rtl = {}
    # Read file with encoding auto-detection
    try:
        with open(path, 'r', encoding='utf-16') as f:
            lines = f.readlines()
    except UnicodeError:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
    for line in lines:
            m = pattern.search(line)
            if m:
                idx = int(m.group(1))
                rtl[idx] = (decode_val(m.group(2), N), decode_val(m.group(3), N))
    
    if len(rtl) != 1024:
        print(f"Error: N={N} log only parsed {len(rtl)} bins.")
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
    
    print(f"FP{N} RTL results:")
    print(f"  SNR: {snr:.4f} dB")
    print(f"  RMSE: {rmse:.8f}")
    print(f"  MAE: {mae:.8f}")
    print(f"  NRMSE: {nrmse_pct:.4f}%")
    print(f"  Overall Accuracy: {accuracy:.4f}%")
    print(f"  Range Error: {range_error:.6f} cm")
    print("-" * 50)
