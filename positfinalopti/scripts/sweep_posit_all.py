import math
import numpy as np

def bitrev(x, bits=10):
    rev = 0
    for i in range(bits):
        if (x >> i) & 1:
            rev |= (1 << (bits - 1 - i))
    return rev

def quantize_posit_reengineered(val, N):
    if val == 0: return 0.0
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    e_val = math.floor(math.log2(val_abs))
    k = e_val // 2
    e = e_val % 2
    fraction = val_abs / (4**k * 2**e)
    if k >= 0:
        run = k + 1; regime_bit = 1
    else:
        run = -k; regime_bit = 0
    p = 0
    idx = N - 2
    for _ in range(run):
        if idx >= 0: p |= regime_bit << idx; idx -= 1
    if idx >= 0: p |= (1 - regime_bit) << idx; idx -= 1
    if idx >= 0: p |= e << idx; idx -= 1
    if idx >= 0:
        frac_val = fraction - 1.0
        scale = 2**(idx + 1)
        scaled_exact = frac_val * scale
        scaled_rounded = round(scaled_exact)
        if abs(scaled_exact - scaled_rounded) == 0.5:
            if scaled_rounded % 2 != 0:
                scaled_rounded = int(math.floor(scaled_exact) if scaled_rounded > scaled_exact else math.ceil(scaled_exact))
        if scaled_rounded >= scale:
            scaled_rounded = scale - 1
        p |= int(scaled_rounded)
    p_string = bin(p)[2:].zfill(N)
    regime_bit = int(p_string[1])
    idx_dec = 2; run_dec = 1
    while idx_dec < N and int(p_string[idx_dec]) == regime_bit:
        run_dec += 1; idx_dec += 1
    k_dec = (run_dec - 1) if regime_bit == 1 else -run_dec
    idx_dec += 1
    e_dec = int(p_string[idx_dec]) if idx_dec < N else 0
    if idx_dec < N: idx_dec += 1
    frac_dec = 1.0; weight = 0.5
    while idx_dec < N:
        if int(p_string[idx_dec]) == 1: frac_dec += weight
        weight /= 2; idx_dec += 1
    decoded_val = (4**k_dec) * (2**e_dec) * frac_dec
    return -decoded_val if sign else decoded_val

def fft_radix2_posit(x, N):
    n = len(x)
    a = [complex(quantize_posit_reengineered(x[bitrev(i, 10)].real, N), quantize_posit_reengineered(x[bitrev(i, 10)].imag, N)) for i in range(n)]
    for stage in range(1, 11):
        m = 2**stage; m_half = m // 2
        for j in range(m_half):
            angle = -2 * math.pi * j / m
            w_q = complex(quantize_posit_reengineered(math.cos(angle), N), quantize_posit_reengineered(math.sin(angle), N))
            for k in range(0, n, m):
                t = a[k + j + m_half] * w_q
                t_q = complex(quantize_posit_reengineered(t.real, N), quantize_posit_reengineered(t.imag, N))
                u = a[k + j]
                add_val = u + t_q
                sub_val = u - t_q
                a[k + j] = complex(quantize_posit_reengineered(add_val.real, N), quantize_posit_reengineered(add_val.imag, N))
                a[k + j + m_half] = complex(quantize_posit_reengineered(sub_val.real, N), quantize_posit_reengineered(sub_val.imag, N))
    return a

def interpolate_peak(mags, k):
    if k <= 0 or k >= len(mags)-1: return float(k)
    y_prev, y_curr, y_next = mags[k-1], mags[k], mags[k+1]
    denom = (2 * y_curr - y_next - y_prev)
    if denom == 0: return float(k)
    return k + 0.5 * (y_next - y_prev) / denom

# Generate new signal
R = 18.86226
phi = 0.57362
x = [complex(math.cos(2*math.pi*R*i/1024 + phi), 0) for i in range(1024)]

# Golden Reference
X_gold = np.fft.fft([val.real for val in x])
gold_mags = np.abs(X_gold)
gold_peak = int(np.argmax(gold_mags[1:512])) + 1
gold_est = interpolate_peak(gold_mags, gold_peak)

print(f"{'N':>2} | {'SNR (dB)':>10} | {'RMSE':>10} | {'MAE':>10} | {'Range Error (cm)':>20}")
print("-" * 65)

for N in range(4, 17):
    X_p = fft_radix2_posit(x, N)
    mags = np.abs(X_p)
    peak = int(np.argmax(mags[1:512])) + 1
    est = interpolate_peak(mags, peak)
    r_err = abs(est - gold_est) * 100.0 # to cm
    
    # Calculate SNR, RMSE, MAE
    sq_err = 0.0
    sq_signal = 0.0
    abs_err = 0.0
    for k in range(1024):
        mr, mi = X_gold[k].real, X_gold[k].imag
        rr, ri = X_p[k].real, X_p[k].imag
        sq_err += (rr-mr)**2 + (ri-mi)**2
        sq_signal += mr*mr + mi*mi
        abs_err += math.sqrt((rr-mr)**2 + (ri-mi)**2)
        
    snr = 10 * math.log10(sq_signal / sq_err) if sq_err > 0 else float('inf')
    rmse = math.sqrt(sq_err / 1024)
    mae = abs_err / 1024
    
    print(f"{N:>2} | {snr:10.2f} | {rmse:10.6f} | {mae:10.6f} | {r_err:20.6f}")
