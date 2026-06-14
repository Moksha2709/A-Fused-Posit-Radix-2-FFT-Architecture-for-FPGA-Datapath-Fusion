import math
import sys

def encode_posit_N_1(val, N=8):
    if val == 0: return 0
    if math.isnan(val) or math.isinf(val): return 1 << (N-1)
    
    sign = 1 if val < 0 else 0
    val_abs = abs(val)
    
    e_val = math.floor(math.log2(val_abs))
    # For es=1, useed = 2. So k = floor(e_val / 2^es) = floor(e_val / 2)
    k = e_val // 2
    e = e_val % 2
    
    fraction = val_abs / (4**k * 2**e)
    # fraction is in [1.0, 2.0)
    
    # Pack bits
    p = 0
    
    # Regime
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
            
    # Terminator
    if idx >= 0:
        p |= ((1 - regime_bit) << idx)
        idx -= 1
        
    # Exponent
    if idx >= 0:
        p |= (e << idx)
        idx -= 1
        
    # Fraction
    if idx >= 0:
        frac_val = fraction - 1.0
        # remaining bits = idx + 1
        scaled = round(frac_val * (2**(idx + 1)))
        # Handle rounding overflow
        if scaled >= (2**(idx + 1)):
            scaled = (2**(idx + 1)) - 1 # saturated (or we could propagate carry, but keep simple)
            
        p |= scaled
        
    # Two's complement for negatives
    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)
        
    return p

N = 10

if len(sys.argv) > 1:
    N = int(sys.argv[1])

print(f"// Twiddle factors W_16^n for POSIT({N},1)")

twiddles = []
for n in range(8):
    c = math.cos(2 * math.pi * n / 16)
    s = -math.sin(2 * math.pi * n / 16)
    twiddles.append((c, s))

for i, (r_val, i_val) in enumerate(twiddles):
    wr = encode_posit_N_1(r_val, N)
    wi = encode_posit_N_1(i_val, N)
    hex_width = (N + 3) // 4
    fmt_wr = f"{wr:0{hex_width}X}"
    fmt_wi = f"{wi:0{hex_width}X}"
    print(f"    3'd{i}: begin wr = {N}'h{fmt_wr}; wi = {N}'h{fmt_wi}; end // W_16^{i} = {r_val:7.4f} + j {i_val:7.4f}")

print(f"\n// TEST VECTOR ENCODING for N={N}:")
vals = [
    (  1.0000,   0.0000), (  0.5878,   0.8090), ( -0.3090,   0.9511), ( -0.9511,   0.3090),
    ( -0.8090,  -0.5878), ( -0.0000,  -1.0000), (  0.8090,  -0.5878), (  0.9511,   0.3090),
    (  0.3090,   0.9511), ( -0.5878,   0.8090), ( -1.0000,   0.0000), ( -0.5878,  -0.8090),
    (  0.3090,  -0.9511), (  0.9511,  -0.3090), (  0.8090,   0.5878), (  0.0000,   1.0000)
]

for i, (r_val, i_val) in enumerate(vals):
    bpr = encode_posit_N_1(r_val, N)
    bpi = encode_posit_N_1(i_val, N)
    fmt_bpr = f"{bpr:0{hex_width}X}"
    fmt_bpi = f"{bpi:0{hex_width}X}"
    print(f"    in_real[{i:2d}] = {N}'h{fmt_bpr}; in_imag[{i:2d}] = {N}'h{fmt_bpi};")
