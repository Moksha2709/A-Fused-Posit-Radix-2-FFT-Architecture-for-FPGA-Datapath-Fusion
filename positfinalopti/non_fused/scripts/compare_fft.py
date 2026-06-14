"""
compare_fft.py
Parses sim_1024.log, decodes Posit(12,1) RTL outputs to float,
compares against MATLAB FFT golden reference, and reports RMSE.
"""
import sys
import math, re
import numpy as np

import os
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(script_dir, '..'))

N = 16  # Posit word width
log_path = os.path.join(workspace_root, 'sim', 'sim_1024_N16.log')
if len(sys.argv) > 1:
    log_path = sys.argv[1]
    # If the log_path is relative and doesn't exist, try resolving it in the sim/ folder
    if not os.path.isabs(log_path) and not os.path.exists(log_path):
        log_path = os.path.join(workspace_root, 'sim', log_path)
    m = re.search(r'_N(\d+)', log_path)
    if m:
        N = int(m.group(1))
if len(sys.argv) > 2:
    N = int(sys.argv[2])

# ── Posit (N,1) decoder ───────────────────────────────────────────────────────
def decode(p_hex, N=N):
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

# ── MATLAB golden reference (real, imag) dynamically calculated ──────────────
tb_path = os.path.join(workspace_root, 'tb', 'tb_fft16.v')
try:
    with open(tb_path, 'r', encoding='utf-8') as f:
        tb_text = f.read()
except Exception:
    with open(tb_path, 'r') as f:
        tb_text = f.read()

try:
    real_vals = {int(m[0]): int(m[1], 16) for m in re.findall(r"in_real\[\s*(\d+)\s*\]\s*=\s*\d+'h([0-9a-fA-F]+)", tb_text)}
    imag_vals = {int(m[0]): int(m[1], 16) for m in re.findall(r"in_imag\[\s*(\d+)\s*\]\s*=\s*\d+'h([0-9a-fA-F]+)", tb_text)}
    
    # Reconstruct input signals using Posit decoder
    x = []
    for i in range(1024):
        r_hex = f"{real_vals.get(i, 0):04x}"
        i_hex = f"{imag_vals.get(i, 0):04x}"
        r_val = decode(r_hex, N)
        i_val = decode(i_hex, N)
        x.append(complex(r_val, i_val))
    
    # Compute double-precision FFT
    X_mat = np.fft.fft(x)
    matlab = [(X_mat[k].real, X_mat[k].imag) for k in range(1024)]
except Exception as e:
    print(f"Error parsing testbench inputs or running FFT: {e}")
    matlab = [(0.0, 0.0)] * 1024

# ── Parse RTL output from sim log ─────────────────────────────────────────────
pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
rtl = {}
with open(log_path, 'rb') as f:
    raw_bytes = f.read()

# Auto-detect encoding: UTF-16 LE has BOM ff fe, UTF-16 BE has fe ff
if raw_bytes[:2] in (b'\xff\xfe', b'\xfe\xff'):
    raw = raw_bytes.decode('utf-16')
else:
    raw = raw_bytes.decode('utf-8', errors='replace')

for line in raw.splitlines():
    m = pattern.search(line)
    if m:
        idx = int(m.group(1))
        rtl[idx] = (decode(m.group(2), N), decode(m.group(3), N))

print(f"Parsed {len(rtl)} RTL output bins\n")

# ── Compare ───────────────────────────────────────────────────────────────────
sq_err_r = sq_err_i = sq_err_mag = 0.0
max_err_r = max_err_i = max_err_mag = 0.0
max_err_idx_r = max_err_idx_i = 0

print(f"{'Bin':>5}  {'RTL_r':>10} {'MAT_r':>10} {'RTL_i':>10} {'MAT_i':>10}  {'err_r':>8} {'err_i':>8}")
print("-" * 80)

POINTS = 1024
for k in range(POINTS):
    mr, mi = matlab[k]
    if k in rtl:
        rr, ri = rtl[k]
    else:
        rr, ri = 0.0, 0.0

    er = rr - mr;  ei = ri - mi
    em = math.sqrt(er*er + ei*ei)

    sq_err_r   += er * er
    sq_err_i   += ei * ei
    sq_err_mag += em * em

    if abs(er) > max_err_r:   max_err_r = abs(er);   max_err_idx_r = k
    if abs(ei) > max_err_i:   max_err_i = abs(ei);   max_err_idx_i = k
    if em > max_err_mag:       max_err_mag = em

    # Print first 32 and last 4 for a quick look
    if k < 32 or k >= POINTS-4:
        print(f"{k:>5}  {rr:>10.4f} {mr:>10.4f} {ri:>10.4f} {mi:>10.4f}  {er:>8.4f} {ei:>8.4f}")

print("\n" + "=" * 60)

# ── Aggregate error metrics ───────────────────────────────────────────────────
POINTS = 1024
sq_signal = 0.0   # total signal power  (MATLAB)
sq_err    = 0.0   # total error power   (RTL - MATLAB)
abs_err   = 0.0   # mean absolute error (magnitude)

for k in range(POINTS):
    mr, mi = matlab[k]
    rr, ri = rtl.get(k, (0.0, 0.0))
    sq_signal += mr*mr + mi*mi
    sq_err    += (rr-mr)**2 + (ri-mi)**2
    abs_err   += math.sqrt((rr-mr)**2 + (ri-mi)**2)

rmse_r   = math.sqrt(sq_err_r   / POINTS)
rmse_i   = math.sqrt(sq_err_i   / POINTS)
rmse_mag = math.sqrt(sq_err_mag / POINTS)

signal_rms  = math.sqrt(sq_signal / POINTS)   # RMS of MATLAB output
error_rms   = math.sqrt(sq_err    / POINTS)   # RMS of complex error

snr_db      = 10 * math.log10(sq_signal / sq_err) if sq_err > 0 else float('inf')
nrmse_pct   = (error_rms / signal_rms) * 100   # normalized RMSE (%)
accuracy    = 100.0 - nrmse_pct                 # overall accuracy (%)
mae         = abs_err / POINTS                  # mean absolute error

print(f"ACCURACY REPORT  (Posit({N},1)  vs  MATLAB double-precision)")
print("=" * 60)
print(f"  Total bins compared   : {len(rtl)} / {POINTS}")
print()
print(f"  RMSE (real part)      : {rmse_r:.6f}")
print(f"  RMSE (imag part)      : {rmse_i:.6f}")
print(f"  RMSE (magnitude)      : {rmse_mag:.6f}")
print()
print(f"  Mean Absolute Error   : {mae:.6f}")
print(f"  Max |error| real      : {max_err_r:.6f}  @ bin {max_err_idx_r}")
print(f"  Max |error| imag      : {max_err_i:.6f}  @ bin {max_err_idx_i}")
print(f"  Max |error| magnitude : {max_err_mag:.6f}")
print()
print(f"  Signal RMS (MATLAB)   : {signal_rms:.6f}")
print(f"  Error  RMS (RTL-MAT)  : {error_rms:.6f}")
print(f"  SNR                   : {snr_db:.2f} dB")
print(f"  Normalized RMSE       : {nrmse_pct:.4f} %")
print(f"  Overall Accuracy      : {accuracy:.4f} %")
print("=" * 60)

