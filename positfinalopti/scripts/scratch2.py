import sys

def dec_p8(p):
    if p == 0: return 0.0
    if p == 0x80: return float('nan')
    sign = (p >> 7) & 1
    
    if sign:
        p_abs = (~p & 0xFF) + 1
    else:
        p_abs = p
    
    mag = p_abs & 0x7F
    
    reg_bit = (mag >> 6) & 1
    run = 0
    for i in range(6, -1, -1):
        if ((mag >> i) & 1) == reg_bit:
            run += 1
        else:
            break
            
    if reg_bit == 1:
        k = run - 1
    else:
        k = -run
        
    if run == 7:
        exp = 0
        frac = 0
    else:
        idx = 6 - run   # skip regime bits
        idx -= 1        # skip term bit
        
        if idx >= 0:
            exp = (mag >> idx) & 1
            idx -= 1
        else:
            exp = 0
            
        frac = 0
        for i in range(4):
            if idx >= 0:
                bit = (mag >> idx) & 1
                frac |= (bit << (3 - i))
                idx -= 1
                
    f_val = 1.0 + frac / 16.0
    val = (4 ** k) * (2 ** exp) * f_val
    if sign:
        val = -val
    return val

hex_outputs = [
    (0x96, 0x98),
    (0xde, 0xbe),
    (0xd0, 0xd0),
    (0x34, 0x00),
    (0x00, 0xaf),
    (0xcc, 0x54),
    (0x30, 0x48),
    (0x1f, 0xaf),
    (0xd0, 0x00),
    (0x22, 0xc4),
    (0x30, 0x30),
    (0xcc, 0x50),
    (0x00, 0xca),
    (0x34, 0xd0),
    (0xd0, 0xb8),
    (0xe1, 0x18),
]

for i, (r, im) in enumerate(hex_outputs):
    vr = dec_p8(r)
    vi = dec_p8(im)
    print(f"X[{i:2d}] = {vr:9.6f} + j {vi:9.6f}")
