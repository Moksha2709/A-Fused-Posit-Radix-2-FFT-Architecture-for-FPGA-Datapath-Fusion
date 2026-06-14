import math
import numpy as np

# Path to the unquantized inputs
real_inputs_path = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL\real_inputs_1024.txt"
inputs = []
with open(real_inputs_path, 'r', encoding='utf-8') as f:
    for line in f:
        line_str = line.strip()
        if not line_str: continue
        inputs.append(float(line_str))

assert len(inputs) == 1024

# Golden reference FFT
X_gold = np.fft.fft([complex(x, 0.0) for x in inputs])
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

# Quantize operation to represent FP(N) arithmetic
def quantize_fp(val, N):
    if isinstance(val, complex):
        return complex(quantize_fp(val.real, N), quantize_fp(val.imag, N))
    return decode_fp(encode_fp(val, N), N)

def fft_1024_fp(x, N):
    # Radix-2 decimation-in-time FFT in FP(N)
    a = [complex(c.real, c.imag) for c in x]
    n = len(a)
    
    # Bit reversal
    j = 0
    for i in range(n):
        if i < j:
            a[i], a[j] = a[j], a[i]
        m = n >> 1
        while m >= 2 and j >= m:
            j -= m
            m >>= 1
        j += m
        
    # FFT Stages
    for stage in range(10):
        m = 1 << stage
        m2 = m << 1
        # Twiddle factors for this stage
        w_real = [math.cos(2 * math.pi * k / m2) for k in range(m)]
        w_imag = [-math.sin(2 * math.pi * k / m2) for k in range(m)]
        
        # Quantize twiddle factors
        w_real = [quantize_fp(w, N) for w in w_real]
        w_imag = [quantize_fp(w, N) for w in w_imag]
        
        for k in range(0, n, m2):
            for i in range(m):
                # Complex multiplication in FP(N)
                # (ar + j ai) * (wr + j wi) = (ar*wr - ai*wi) + j (ar*wi + ai*wr)
                t_r = a[k + i + m].real
                t_i = a[k + i + m].imag
                w_r = w_real[i]
                w_i = w_imag[i]
                
                # We emulate the 6 rounding steps per complex multiply:
                p1 = quantize_fp(t_r * w_r, N)
                p2 = quantize_fp(t_i * w_i, N)
                p3 = quantize_fp(t_r * w_i, N)
                p4 = quantize_fp(t_i * w_r, N)
                
                tr_mult = quantize_fp(p1 - p2, N)
                ti_mult = quantize_fp(p3 + p4, N)
                
                # Butterfly additions
                u_r = a[k + i].real
                u_i = a[k + i].imag
                
                a[k + i] = complex(quantize_fp(u_r + tr_mult, N), quantize_fp(u_i + ti_mult, N))
                a[k + i + m] = complex(quantize_fp(u_r - tr_mult, N), quantize_fp(u_i - ti_mult, N))
                
    return a

# Sweep FP13 and FP14
for N in [13, 14]:
    print(f"\nEvaluating FP{N} Software Model...")
    X_fp = fft_1024_fp([complex(x, 0.0) for x in inputs], N)
    
    sq_signal = 0.0
    sq_err = 0.0
    abs_err = 0.0
    mags = np.zeros(1024)
    
    for k in range(1024):
        gr, gi = X_gold[k].real, X_gold[k].imag
        rr, ri = X_fp[k].real, X_fp[k].imag
        sq_signal += gr*gr + gi*gi
        sq_err += (rr-gr)**2 + (ri-gi)**2
        abs_err += math.sqrt((rr-gr)**2 + (ri-gi)**2)
        mags[k] = math.sqrt(rr*rr + ri*ri)
        
    rmse = math.sqrt(sq_err / 1024)
    mae = abs_err / 1024
    signal_rms = math.sqrt(sq_signal / 1024)
    nrmse_pct = (rmse / signal_rms) * 100
    accuracy = 100.0 - nrmse_pct
    snr = 10 * math.log10(sq_signal / sq_err)
    
    peak = int(np.argmax(mags[1:512])) + 1
    interp = interpolate_peak(mags, peak)
    range_error = abs(interp * range_coeff - true_range) * 100.0
    
    print(f"| **FP{N}** | **{N}** | {snr:.2f} dB | {rmse:.6f} | {mae:.6f} | {nrmse_pct:.4f}% | {accuracy:.4f}% | {range_error:.4f} cm |")
