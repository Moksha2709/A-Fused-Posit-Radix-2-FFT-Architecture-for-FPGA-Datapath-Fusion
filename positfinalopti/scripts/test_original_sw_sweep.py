import os
import math
import numpy as np

# Path configurations
workspace_dir = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL"
file_path = os.path.join(workspace_dir, "real_inputs_1024.txt")

# Load samples from real_inputs_1024.txt
inputs = []
with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            inputs.append(complex(float(line_str), 0.0))
        except ValueError:
            pass

assert len(inputs) == 1024, f"Expected 1024 samples, got {len(inputs)}"

# Double-precision Golden Reference
X_gold = np.fft.fft(inputs)
mags_gold = np.abs(X_gold)

# Range resolution factor and true peak
range_coeff = 0.99999896

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1: return float(k)
    y_prev, y_curr, y_next = mags[k-1], mags[k], mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0: return float(k)
    return k + 0.5 * (y_next - y_prev) / denom

# Search for peak around bin 18.0
gold_peak_idx = 18
gold_interp = interpolate_peak(mags_gold, gold_peak_idx)
true_range = gold_interp * range_coeff

# Bit reversal
def bitrev(x, bits=10):
    rev = 0
    for i in range(bits):
        if (x >> i) & 1:
            rev |= (1 << (bits - 1 - i))
    return rev

# Posit Encoder/Decoder
def encode_posit(val, N):
    if val == 0: return 0
    if math.isnan(val) or math.isinf(val): return 1 << (N - 1)
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    e_val = math.floor(math.log2(val_abs))
    k = e_val // 2
    e = e_val % 2
    fraction = val_abs / (4**k * 2**e)
    p = 0
    if k >= 0:
        run = k + 1; regime_bit = 1
    else:
        run = -k; regime_bit = 0
    idx = N - 2
    for _ in range(run):
        if idx >= 0: p |= (regime_bit << idx); idx -= 1
    if idx >= 0: p |= ((1 - regime_bit) << idx); idx -= 1
    if idx >= 0: p |= (e << idx); idx -= 1
    if idx >= 0:
        frac_val = fraction - 1.0
        scaled = round(frac_val * (2**(idx + 1)))
        if scaled >= (2**(idx + 1)): scaled = (2**(idx + 1)) - 1
        p |= scaled
    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)
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
    idx += 1  # skip terminator
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

def quantize_float(val, N, E=5):
    if val == 0.0: return 0.0
    M = N - 1 - E # mantissa size
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    e = math.floor(math.log2(val_abs))
    bias = (1 << (E - 1)) - 1
    exp_val = e + bias
    
    if exp_val <= 0: # Subnormal
        shift = 1 - exp_val
        if shift > M + 1: return 0.0
        mant = round(val_abs * (2**bias) * (2**M))
        max_sub = (1 << M) - 1
        if mant > max_sub: mant = max_sub
        decoded = mant * (2**-M) * (2**(1 - bias))
        return -decoded if sign else decoded
        
    max_exp = (1 << E) - 1
    if exp_val >= max_exp: # Overflow
        max_val = (2 - 2**-M) * (2**(max_exp - 1 - bias))
        return -max_val if sign else max_val
        
    frac = val_abs / (2**e)
    mant_scaled = round((frac - 1.0) * (2**M))
    if mant_scaled >= (1 << M):
        mant_scaled = 0
        e += 1
        exp_val += 1
        if exp_val >= max_exp:
            max_val = (2 - 2**-M) * (2**(max_exp - 1 - bias))
            return -max_val if sign else max_val
            
    decoded = (1.0 + mant_scaled * (2**-M)) * (2**e)
    return -decoded if sign else decoded

# RTL-like SW FFT Models (Rounding every single intermediate step)
def fft_radix2_posit_rtl_like(x, N):
    n = len(x)
    a = [complex(quantize_posit(x[bitrev(i, 10)].real, N), quantize_posit(x[bitrev(i, 10)].imag, N)) for i in range(n)]
    for stage in range(1, 11):
        m = 2**stage
        m_half = m // 2
        for j in range(m_half):
            angle = -2 * math.pi * j / m
            wr = quantize_posit(math.cos(angle), N)
            wi = quantize_posit(math.sin(angle), N)
            for k in range(0, n, m):
                br = a[k + j + m_half].real
                bi = a[k + j + m_half].imag
                m1 = quantize_posit(br * wr, N)
                m2 = quantize_posit(bi * wi, N)
                tr = quantize_posit(m1 - m2, N)
                m3 = quantize_posit(br * wi, N)
                m4 = quantize_posit(bi * wr, N)
                ti = quantize_posit(m3 + m4, N)
                ar = a[k + j].real
                ai = a[k + j].imag
                y0r = quantize_posit(ar + tr, N)
                y0i = quantize_posit(ai + ti, N)
                y1r = quantize_posit(ar - tr, N)
                y1i = quantize_posit(ai - ti, N)
                a[k + j] = complex(y0r, y0i)
                a[k + j + m_half] = complex(y1r, y1i)
    return a

def fft_radix2_float_rtl_like(x, N, E=5):
    n = len(x)
    a = [complex(quantize_float(x[bitrev(i, 10)].real, N, E), quantize_float(x[bitrev(i, 10)].imag, N, E)) for i in range(n)]
    for stage in range(1, 11):
        m = 2**stage
        m_half = m // 2
        for j in range(m_half):
            angle = -2 * math.pi * j / m
            wr = quantize_float(math.cos(angle), N, E)
            wi = quantize_float(math.sin(angle), N, E)
            for k in range(0, n, m):
                br = a[k + j + m_half].real
                bi = a[k + j + m_half].imag
                m1 = quantize_float(br * wr, N, E)
                m2 = quantize_float(bi * wi, N, E)
                tr = quantize_float(m1 - m2, N, E)
                m3 = quantize_float(br * wi, N, E)
                m4 = quantize_float(bi * wr, N, E)
                ti = quantize_float(m3 + m4, N, E)
                ar = a[k + j].real
                ai = a[k + j].imag
                y0r = quantize_float(ar + tr, N, E)
                y0i = quantize_float(ai + ti, N, E)
                y1r = quantize_float(ar - tr, N, E)
                y1i = quantize_float(ai - ti, N, E)
                a[k + j] = complex(y0r, y0i)
                a[k + j + m_half] = complex(y1r, y1i)
    return a

def calculate_snr(X_test, X_gold):
    X_test, X_gold = np.array(X_test), np.array(X_gold)
    sq_sig = np.sum(np.abs(X_gold)**2)
    sq_err = np.sum(np.abs(X_test - X_gold)**2)
    snr = 10 * math.log10(sq_sig / sq_err) if sq_err > 0 else float('inf')
    return snr

# Sweeps from 8 to 16
print("\n" + "=" * 80)
print(" SW COMPARISON FOR ORIGINAL RADAR SIGNAL (real_inputs_1024.txt)")
print(" (USING RTL-LIKE BIT-ACCURATE SOFTWARE EMULATION)")
print("=" * 80)
print(f"{'N':>2} | {'Posit SNR (dB)':>15} | {'Posit Range Error':>19} | {'FP SNR (dB)':>12} | {'FP Range Error':>16}")
print("-" * 75)

for N in range(8, 17):
    # 1. Posit
    X_p = fft_radix2_posit_rtl_like(inputs, N)
    snr_p = calculate_snr(X_p, X_gold)
    mags_p = np.abs(X_p)
    peak_p_idx = 18
    interp_p = interpolate_peak(mags_p, peak_p_idx)
    est_range_p = interp_p * range_coeff
    error_p = abs(est_range_p - true_range) * 100.0 # in cm
    
    # 2. Float
    E = 5
    X_f = fft_radix2_float_rtl_like(inputs, N, E)
    snr_f = calculate_snr(X_f, X_gold)
    mags_f = np.abs(X_f)
    peak_f_idx = 18
    interp_f = interpolate_peak(mags_f, peak_f_idx)
    est_range_f = interp_f * range_coeff
    error_f = abs(est_range_f - true_range) * 100.0 # in cm
    
    print(f"{N:>2} | {snr_p:>13.2f} dB | {error_p:>16.4f} cm | {snr_f:>10.2f} dB | {error_f:>13.4f} cm")
print("=========================================================================================")
