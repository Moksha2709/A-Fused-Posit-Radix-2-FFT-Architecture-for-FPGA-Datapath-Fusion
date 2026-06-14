def decode_posit8_2(p):
    if p == 0: return 0.0
    if p == 0x80: return float('nan')
    sign = (p >> 7) & 1
    p_abs = p
    if sign:
        p_abs = ((~p) + 1) & 0xFF
    mag = p_abs & 0x7F
    
    regime_bit = (mag >> 6) & 1
    run = 0
    for i in range(6, -1, -1):
        if ((mag >> i) & 1) == regime_bit:
            run += 1
        else:
            break
            
    if regime_bit == 1:
        k = run - 1
    else:
        k = -run
        
    if run == 7:
        e = 0
        frac_val = 0
    else:
        idx = 6 - run
        idx = idx - 1 # skip terminating bit
        # Extract up to 2 bits of exponent
        e = 0
        for i in range(2):
            if idx >= 0:
                e = (e << 1) | ((mag >> idx) & 1)
                idx -= 1
            else:
                e = (e << 1)
                
        frac_val = 0
        frac_bits = 0
        # Remaining bits are fraction (max 3 bits can be remaining since 1 sign + 2 min regime + 2 exp = 5. 8-5=3)
        # But let's just dynamically read whatever is left.
        while idx >= 0:
            frac_val = (frac_val << 1) | ((mag >> idx) & 1)
            frac_bits += 1
            idx -= 1
        
        # Scale frac_val
        if frac_bits > 0:
            fraction = 1.0 + frac_val / (2.0 ** frac_bits)
        else:
            fraction = 1.0
            
    # Unpack fraction if run==7? Wait, earlier I did:
    if run == 7:
        fraction = 1.0

    val = (16 ** k) * (2 ** e) * fraction
    if sign:
        val = -val
    return val

# Twiddle factors W_16^n = cos(2pi*n/16) - j * sin(2pi*n/16)
import math
twiddles = []
for n in range(8):
    c = math.cos(2 * math.pi * n / 16)
    s = -math.sin(2 * math.pi * n / 16)
    twiddles.append((c, s))

print("TWIDDLES W_16^n (Posit 8,2)")
for i, (r_val, i_val) in enumerate(twiddles):
    best_p_r = 0; best_diff_r = float('inf')
    best_p_i = 0; best_diff_i = float('inf')
    for p in range(256):
        if p == 0x80: continue
        dec = decode_posit8_2(p)
        diff_r = abs(dec - r_val)
        diff_i = abs(dec - i_val)
        if diff_r < best_diff_r: best_diff_r = diff_r; best_p_r = p
        if diff_i < best_diff_i: best_diff_i = diff_i; best_p_i = p
    print(f"3'd{i}: begin wr = 8'h{best_p_r:02X}; wi = 8'h{best_p_i:02X}; end // W_16^{i} = {r_val:7.4f} + j {i_val:7.4f} (Posit approx: {decode_posit8_2(best_p_r):7.4f} + j {decode_posit8_2(best_p_i):7.4f})")
    
# User requested test vectors
vals = [
    (  1.0000,   0.0000), (  0.5878,   0.8090), ( -0.3090,   0.9511), ( -0.9511,   0.3090),
    ( -0.8090,  -0.5878), ( -0.0000,  -1.0000), (  0.8090,  -0.5878), (  0.9511,   0.3090),
    (  0.3090,   0.9511), ( -0.5878,   0.8090), ( -1.0000,   0.0000), ( -0.5878,  -0.8090),
    (  0.3090,  -0.9511), (  0.9511,  -0.3090), (  0.8090,   0.5878), (  0.0000,   1.0000)
]

print("TEST VECTOR ENCODING:")
for i, (r_val, i_val) in enumerate(vals):
    best_p_r = 0; best_diff_r = float('inf')
    best_p_i = 0; best_diff_i = float('inf')
    for p in range(256):
        if p == 0x80: continue
        dec = decode_posit8_2(p)
        diff_r = abs(dec - r_val)
        diff_i = abs(dec - i_val)
        if diff_r < best_diff_r: best_diff_r = diff_r; best_p_r = p
        if diff_i < best_diff_i: best_diff_i = diff_i; best_p_i = p
    print(f"    in_real[{i:2d}] = 8'h{best_p_r:02X}; in_imag[{i:2d}] = 8'h{best_p_i:02X};")
