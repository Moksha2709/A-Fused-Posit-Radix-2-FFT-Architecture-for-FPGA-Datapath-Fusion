import os
import math
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

# FP15 Encoder/Decoder
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

# Quantize inputs to FP15
quantized_inputs = [decode_fp15(encode_fp15(x)) for x in unquantized_inputs]

# Compute software FFT on quantized inputs (represent quantized software model)
X_quant_sw = np.fft.fft(quantized_inputs)

# Parse RTL outputs from simulation log
log_file = "sim/sim_1024_fp15.log"
pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
rtl = {}
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        m = pattern.search(line)
        if m:
            idx = int(m.group(1))
            rtl[idx] = (decode_fp15(int(m.group(2), 16)), decode_fp15(int(m.group(3), 16)))

# Compute Arithmetic SNR (RTL vs Quantized SW FFT)
sq_quant_sw = 0.0
sq_arith_err = 0.0

for k in range(1024):
    qsr, qsi = X_quant_sw[k].real, X_quant_sw[k].imag
    rr, ri = rtl.get(k, (0.0, 0.0))
    sq_quant_sw += qsr*qsr + qsi*qsi
    sq_arith_err += (rr-qsr)**2 + (ri-qsi)**2

arith_snr = 10 * math.log10(sq_quant_sw / sq_arith_err)
print(f"Arithmetic SNR (RTL vs Quantized SW) = {arith_snr:.2f} dB")
