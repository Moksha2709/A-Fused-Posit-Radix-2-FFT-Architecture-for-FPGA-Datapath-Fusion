import sys
import os
import math
import re
import numpy as np

# Posit decoder N, es=1
def decode_posit(p_hex, N):
    p = int(p_hex, 16)
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

# Load the raw double-precision inputs from the workspace
sys.path.append(r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL")
from encode_1024_inputs import user_inputs

x_double = [complex(val, 0.0) for val in user_inputs]
X_golden = np.fft.fft(x_double)
matlab = [(X_golden[k].real, X_golden[k].imag) for k in range(1024)]

# Calculate MATLAB Golden peak range
mat_mags = np.array([math.sqrt(m[0]**2 + m[1]**2) for m in matlab])
mat_peak_idx = int(np.argmax(mat_mags[1:512])) + 1

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

true_range = interpolate_peak(mat_mags, mat_peak_idx)

# Path to Posit15 log
posit_dir = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL"
posit15_log = os.path.join(posit_dir, "sim_1024_N15.log")

if not os.path.exists(posit15_log):
    print("Error: sim_1024_N15.log not found!")
    sys.exit(1)

with open(posit15_log, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-16') if b'\x00' in raw else raw.decode('utf-8', errors='replace')
rtl = {}
pattern = re.compile(r'X\[(\d+)\]r=([0-9a-fA-F]+)i=([0-9a-fA-F]+)')
for line in text.splitlines():
    compact = "".join(line.split())
    m = pattern.search(compact)
    if m:
        idx = int(m.group(1))
        rtl[idx] = (decode_posit(m.group(2), 15), decode_posit(m.group(3), 15))

if not rtl:
    print("Error: Could not parse any RTL bins from sim_1024_N15.log")
    sys.exit(1)

sq_err = 0.0
sq_signal = 0.0
rtl_mags = np.zeros(1024)
abs_err = 0.0

for k in range(1024):
    mr, mi = matlab[k]
    rr, ri = rtl.get(k, (0.0, 0.0))
    er = rr - mr
    ei = ri - mi
    em = math.sqrt(er*er + ei*ei)
    sq_err += em*em
    sq_signal += mr*mr + mi*mi
    rtl_mags[k] = math.sqrt(rr*rr + ri*ri)
    abs_err += em

rmse = math.sqrt(sq_err / 1024.0)
mae = abs_err / 1024.0
sig_rms = math.sqrt(sq_signal / 1024.0)
nrmse = (rmse / sig_rms) * 100
acc = 100.0 - nrmse
snr = 10 * math.log10(sq_signal / sq_err) if sq_err > 0 else float('inf')

# Calculate Range Estimation
rtl_peak_idx = int(np.argmax(rtl_mags[1:512])) + 1
est_range = interpolate_peak(rtl_mags, rtl_peak_idx)
range_error_m = abs(est_range - true_range)

print("=== Posit(15,1) Accuracy Metrics ===")
print(f"RMSE (Magnitude)       : {rmse:.6f}")
print(f"MAE (Magnitude)        : {mae:.6f}")
print(f"NRMSE (%)              : {nrmse:.6f}%")
print(f"Overall Accuracy (%)   : {acc:.6f}%")
print(f"SNR (dB)               : {snr:.2f} dB")
print(f"True Target Range      : {true_range:.5f} m")
print(f"Estimated Range (RTL)  : {est_range:.5f} m")
print(f"Range Error            : {range_error_m * 100.0:.5f} cm")
