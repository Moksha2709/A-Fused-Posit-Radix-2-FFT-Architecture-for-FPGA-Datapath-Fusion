import sys

def decode_posit8_1(p):
    if p == 0:
        return 0.0
    if p == 0x80:
        return float('nan')
    
    sign = (p >> 7) & 1
    
    if sign == 1:
        # Two's complement for negative
        p = ((-p) & 0xFF)
        
    # extract regime
    regime_bits = (p >> 6) & 1
    k = 0
    shifted = p << 2
    for i in range(7):
        bit = (shifted >> 7) & 1
        if bit == regime_bits:
            k += 1
        else:
            break
        shifted = (shifted << 1) & 0xFF
        
    if regime_bits == 1:
        regime = k
    else:
        regime = -k - 1
        
    bits_consumed = 1  # sign
    bits_consumed += k + (1 if k < 6 else 0)  # regime bits (including terminating bit if not dropped)
    
    # Exponent is 1 bit (es=1)
    if bits_consumed < 8:
        e = (p >> (7 - bits_consumed)) & 1
        bits_consumed += 1
    else:
        e = 0
        
    # Fraction is the rest
    if bits_consumed < 8:
        fracbits = 8 - bits_consumed
        f_val = p & ((1 << fracbits) - 1)
        fraction = 1.0 + f_val / (1 << fracbits)
    else:
        fraction = 1.0
        
    val = (4 ** regime) * (2 ** e) * fraction
    if sign == 1:
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
    vr = decode_posit8_1(r)
    vi = decode_posit8_1(im)
    print(f"X[{i}] = {vr:.6f} + j{vi:.6f}")
