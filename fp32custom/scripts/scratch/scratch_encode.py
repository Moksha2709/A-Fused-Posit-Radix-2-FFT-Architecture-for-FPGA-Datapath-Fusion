def decode_posit8_1(p):
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
        idx = idx - 1
        if idx >= 0:
            e = (mag >> idx) & 1
            idx -= 1
        else:
            e = 0
            
        frac_val = 0
        for i in range(4):
            if idx >= 0:
                frac_val |= (((mag >> idx) & 1) << (3 - i))
                idx -= 1
                
    fraction = 1.0 + frac_val / 16.0
    val = (4 ** k) * (2 ** e) * fraction
    if sign:
        val = -val
    return val

vals = [
    ( 1.0000,   0.0000), ( 0.5878,   0.8090), (-0.3090,   0.9511), (-0.9511,   0.3090),
    (-0.8090,  -0.5878), (-0.0000,  -1.0000), ( 0.8090,  -0.5878), ( 0.9511,   0.3090),
    ( 0.3090,   0.9511), (-0.5878,   0.8090), (-1.0000,   0.0000), (-0.5878,  -0.8090),
    ( 0.3090,  -0.9511), ( 0.9511,  -0.3090), ( 0.8090,   0.5878), ( 0.0000,   1.0000)
]

print("initial begin")
for i, (r_val, i_val) in enumerate(vals):
    best_p_r = 0
    best_diff_r = float('inf')
    for p in range(256):
        if p == 0x80: continue
        dec = decode_posit8_1(p)
        diff = abs(dec - r_val)
        if diff < best_diff_r: best_diff_r = diff; best_p_r = p
        
    best_p_i = 0
    best_diff_i = float('inf')
    for p in range(256):
        if p == 0x80: continue
        dec = decode_posit8_1(p)
        diff = abs(dec - i_val)
        if diff < best_diff_i: best_diff_i = diff; best_p_i = p
        
    print(f"    in_real[{i:2d}]  = 8'h{best_p_r:02X}; in_imag[{i:2d}]  = 8'h{best_p_i:02X};")
print("end")
