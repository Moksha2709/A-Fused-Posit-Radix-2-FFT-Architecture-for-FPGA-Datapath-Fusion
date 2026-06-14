import re
import math
import numpy as np
import os

# Set working directory dynamically
script_dir = os.path.dirname(os.path.abspath(__file__))
fp_dir = os.path.dirname(script_dir)
os.chdir(fp_dir)

import sys

N = 16  # Default FP word width
log_path = 'sim/sim_1024_fp16.log'
if len(sys.argv) > 1:
    log_path = sys.argv[1]
    m = re.search(r'_fp(\d+)', log_path)
    if m:
        N = int(m.group(1))
if len(sys.argv) > 2:
    N = int(sys.argv[2])

# Parse N from tb_fft16.v if not overridden
tb_path = 'sim/tb_fft16.v'
try:
    with open(tb_path, 'r') as f:
        tb_text = f.read()
    if len(sys.argv) <= 1:
        m_n = re.search(r'parameter\s+N\s*=\s*(\d+)', tb_text)
        if m_n:
            N = int(m_n.group(1))
except Exception:
    tb_text = ""

print(f"Detected word-width N = {N} from testbench.")

def decode_fp(hex_str, N=N):
    val_uint = int(hex_str, 16)
    if N == 16:
        return float(np.uint16(val_uint).view(np.float16))
    elif N == 12:
        # Custom FP12 (1 sign, 5 exponent, 6 mantissa bits)
        p = val_uint
        if p == 0: return 0.0
        sign = (p >> 11) & 1
        exp = (p >> 6) & 0x1F
        mant = p & 0x3F
        if exp == 0:
            val = (mant / 64.0) * (2**-14)
        elif exp == 0x1F:
            if mant == 0:
                return float('inf') if sign == 0 else float('-inf')
            else:
                return float('nan')
        else:
            val = (1.0 + mant / 64.0) * (2**(exp - 15))
        return -val if sign else val
    elif N == 15:
        # Custom FP15 (1 sign, 5 exponent, 9 mantissa bits)
        p = val_uint
        if p == 0: return 0.0
        sign = (p >> 14) & 1
        exp = (p >> 9) & 0x1F
        mant = p & 0x1FF
        if exp == 0:
            val = (mant / 512.0) * (2**-14)
        elif exp == 0x1F:
            if mant == 0:
                return float('inf') if sign == 0 else float('-inf')
            else:
                return float('nan')
        else:
            val = (1.0 + mant / 512.0) * (2**(exp - 15))
        return -val if sign else val
    else:
        raise ValueError(f"Unsupported bit width N={N}")

# Reconstruct inputs from tb_fft16.v dynamically to construct golden reference
try:
    real_vals = {int(m[0]): int(m[1], 16) for m in re.findall(r"in_real\[\s*(\d+)\s*\]\s*=\s*\d+'h([0-9a-fA-F]+)", tb_text)}
    imag_vals = {int(m[0]): int(m[1], 16) for m in re.findall(r"in_imag\[\s*(\d+)\s*\]\s*=\s*\d+'h([0-9a-fA-F]+)", tb_text)}
    
    # Reconstruct input signals
    x = []
    for i in range(1024):
        r_hex = f"{real_vals.get(i, 0):x}"
        i_hex = f"{imag_vals.get(i, 0):x}"
        r_val = decode_fp(r_hex, N)
        i_val = decode_fp(i_hex, N)
        x.append(complex(r_val, i_val))
    
    # Compute double-precision FFT
    X_mat = np.fft.fft(x)
    matlab = [(X_mat[k].real, X_mat[k].imag) for k in range(1024)]
except Exception as e:
    print(f'Error parsing testbench inputs or running FFT: {e}')
    matlab = [(0.0, 0.0)] * 1024

# Read simulation log (autodetect UTF-16 or UTF-8)
if len(sys.argv) <= 1:
    log_path = f'sim/sim_1024_fp{N}.log'
try:
    with open(log_path, 'rb') as f:
        raw_bytes = f.read()
    if raw_bytes[:2] in (b'\xff\xfe', b'\xfe\xff'):
        raw = raw_bytes.decode('utf-16')
    else:
        raw = raw_bytes.decode('utf-8', errors='replace')
except Exception as e:
    print(f"Error reading log file: {e}")
    raw = ""

# Parse RTL outputs
pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
rtl = {}

for line in raw.splitlines():
    m = pattern.search(line)
    if m:
        idx = int(m.group(1))
        rtl[idx] = (decode_fp(m.group(2), N), decode_fp(m.group(3), N))

print(f"Parsed {len(rtl)} RTL output bins from '{log_path}'\n")

if len(rtl) == 0:
    print("No RTL output bins found! Please check if the simulation completed successfully.")
    exit(1)

# Compare and calculate metrics
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

    er = rr - mr
    ei = ri - mi
    em = math.sqrt(er*er + ei*ei)

    sq_err_r   += er * er
    sq_err_i   += ei * ei
    sq_err_mag += em * em

    if abs(er) > max_err_r:
        max_err_r = abs(er)
        max_err_idx_r = k
    if abs(ei) > max_err_i:
        max_err_i = abs(ei)
        max_err_idx_i = k
    if em > max_err_mag:
        max_err_mag = em

    # Print first 16 and last 4 for a quick look
    if k < 16 or k >= POINTS - 4:
        print(f"{k:>5}  {rr:>10.4f} {mr:>10.4f} {ri:>10.4f} {mi:>10.4f}  {er:>8.4f} {ei:>8.4f}")

print("\n" + "=" * 60)

# Aggregate error metrics
sq_signal = 0.0   # total signal power (MATLAB)
sq_err    = 0.0   # total error power (RTL - MATLAB)
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

signal_rms  = math.sqrt(sq_signal / POINTS)
error_rms   = math.sqrt(sq_err    / POINTS)

snr_db      = 10 * math.log10(sq_signal / sq_err) if sq_err > 0 else float('inf')
nrmse_pct   = (error_rms / signal_rms) * 100
accuracy    = 100.0 - nrmse_pct
mae         = abs_err / POINTS

print(f"ACCURACY REPORT  (Custom RTL FP16 vs MATLAB Double-Precision)")
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

# ── FMCW Radar Range Estimation Report ─────────────────────────────────────────
mat_mags = np.array([math.sqrt(m[0]**2 + m[1]**2) for m in matlab])
rtl_mags = np.zeros(POINTS)
for k in range(POINTS):
    r, i = rtl.get(k, (0.0, 0.0))
    rtl_mags[k] = math.sqrt(r*r + i*i)

# Find peak in bins 1 to POINTS//2 - 1 (avoid DC component)
mat_peak_idx = int(np.argmax(mat_mags[1:POINTS//2])) + 1
rtl_peak_idx = int(np.argmax(rtl_mags[1:POINTS//2])) + 1

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

mat_interp = interpolate_peak(mat_mags, mat_peak_idx)
rtl_interp = interpolate_peak(rtl_mags, rtl_peak_idx)

# Range resolution factor (assume 1.0 m/bin for FMCW scaling representation)
true_range = mat_interp
est_range = rtl_interp
range_error = abs(est_range - true_range)

print("\n" + "=" * 60)
print("FMCW RADAR RANGE ESTIMATION REPORT")
print("=" * 60)
print(f"  True Target Peak Bin (MATLAB) : {mat_peak_idx} (Interpolated: {mat_interp:.6f})")
print(f"  Est  Target Peak Bin (RTL)    : {rtl_peak_idx} (Interpolated: {rtl_interp:.6f})")
print(f"  True Range                    : {true_range:.6f} m")
print(f"  Estimated Range               : {est_range:.6f} m")
print(f"  Range Error                   : {range_error:.6f} m")
print("=" * 60)
