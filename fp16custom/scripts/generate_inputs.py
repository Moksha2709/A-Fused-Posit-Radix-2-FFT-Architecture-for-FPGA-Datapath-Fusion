import math

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
POINTS = 1024          # FFT size (must be a power of 2)
N      = 12            # Posit bit-width (N,1 format)
# ──────────────────────────────────────────────────────────────────────────────

def encode_posit_N_1(val, N=10):
    if val == 0: return 0
    if math.isnan(val) or math.isinf(val): return 1 << (N-1)

    sign = 1 if val < 0 else 0
    val_abs = abs(val)

    e_val = math.floor(math.log2(val_abs))
    k = e_val // 2
    e = e_val % 2

    fraction = val_abs / (4**k * 2**e)

    p = 0
    if k >= 0:
        run = k + 1
        regime_bit = 1
    else:
        run = -k
        regime_bit = 0

    idx = N - 2
    for _ in range(run):
        if idx >= 0:
            p |= (regime_bit << idx)
            idx -= 1

    if idx >= 0:
        p |= ((1 - regime_bit) << idx)
        idx -= 1

    if idx >= 0:
        p |= (e << idx)
        idx -= 1

    if idx >= 0:
        frac_val = fraction - 1.0
        scaled = round(frac_val * (2**(idx + 1)))
        if scaled >= (2**(idx + 1)):
            scaled = (2**(idx + 1)) - 1
        p |= scaled

    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)

    return p

def decode_posit_N_1(p, N=10):
    if p == 0: return 0.0
    if p == (1 << (N-1)): return float('nan')

    sign = (p >> (N-1)) & 1
    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)

    p_string = bin(p)[2:].zfill(N)

    regime_bit = int(p_string[1])
    idx = 2
    run = 1
    while idx < N and int(p_string[idx]) == regime_bit:
        run += 1
        idx += 1

    if regime_bit == 1:
        k = run - 1
    else:
        k = -run

    idx += 1

    if idx < N:
        e = int(p_string[idx])
        idx += 1
    else:
        e = 0

    frac = 1.0
    weight = 0.5
    while idx < N:
        if int(p_string[idx]) == 1:
            frac += weight
        weight /= 2
        idx += 1

    val = (4**k) * (2**e) * frac
    if sign:
        val = -val

    return val

# ─── GENERATE DYNAMIC TEST SIGNAL ─────────────────────────────────────────────
# Signal: x[n] = cos(2π·3·n/POINTS) + 0.5·cos(2π·7·n/POINTS)
# (two frequency components — the FFT should show peaks at bin 3, 7)
hex_width = (N + 3) // 4

print("Verilog Input Assignments:")
for i in range(POINTS):
    r_val = math.cos(2 * math.pi * 3 * i / POINTS) + \
            0.5 * math.cos(2 * math.pi * 7 * i / POINTS)
    i_val = 0.0

    bpr = encode_posit_N_1(r_val, N)
    bpi = encode_posit_N_1(i_val, N)
    fmt_bpr = f"{bpr:0{hex_width}X}"
    fmt_bpi = f"{bpi:0{hex_width}X}"
    print(f"    in_real[{i:4d}] = {N}'h{fmt_bpr}; in_imag[{i:4d}] = {N}'h{fmt_bpi};")
