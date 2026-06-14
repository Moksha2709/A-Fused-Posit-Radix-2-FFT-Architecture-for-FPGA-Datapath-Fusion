"""
posit_decoder.py
Decodes Posit(N, ES=1) hexadecimal values to floating-point.

Usage:
  Edit the CONFIG section and the hex_inputs list, then run:
      python posit_decoder.py
"""
import math

# ─── CONFIG ───────────────────────────────────────────────────────────────────
N  = 16   # Posit word width
ES = 1    # exponent bits (fixed at 1 for this design)
# ──────────────────────────────────────────────────────────────────────────────


def decode_posit(hex_str: str, N: int = 12) -> float:
    """
    Decode a Posit(N, 1) value given as a hex string.

    Steps
    -----
    1. Convert hex → N-bit integer p.
    2. Extract sign from MSB.
    3. If negative, take 2's complement to get the magnitude pattern.
    4. Parse regime  (run of identical bits + terminator).
    5. Parse exponent (1 bit).
    6. Parse fraction  (remaining bits).
    7. Compute  value = 4^k * 2^e * (1 + f).
    8. Apply sign.
    """
    # Step 1 — hex to integer
    p = int(hex_str, 16) & ((1 << N) - 1)          # mask to N bits

    # Special cases
    if p == 0:                    return 0.0
    if p == (1 << (N - 1)):       return float('nan')   # ±MaxComplex / NaR

    # Step 2 — sign
    sign = (p >> (N - 1)) & 1

    # Step 3 — 2's complement for negative values
    if sign:
        p = ((~p) + 1) & ((1 << N) - 1)

    # Step 4 — convert to bit string (N chars, MSB first)
    bits = bin(p)[2:].zfill(N)
    # bits[0]  = sign of magnitude (always 0 after step 3)
    # bits[1]  = first regime bit

    regime_bit = int(bits[1])
    idx = 2
    run = 1
    while idx < N and int(bits[idx]) == regime_bit:
        run += 1
        idx += 1
    # idx now points to the terminator (or past end)

    k = (run - 1) if regime_bit == 1 else -run

    idx += 1   # skip terminator

    # Step 5 — exponent (ES = 1 bit)
    if idx < N:
        e = int(bits[idx])
        idx += 1
    else:
        e = 0

    # Step 6 — fraction
    frac = 1.0
    weight = 0.5
    while idx < N:
        if int(bits[idx]) == 1:
            frac += weight
        weight *= 0.5
        idx += 1

    # Step 7 — real value
    value = (4.0 ** k) * (2.0 ** e) * frac

    # Step 8 — sign
    return -value if sign else value


def show_decode(hex_str: str, N: int = 12):
    """Decode and print a step-by-step breakdown."""
    p_orig = int(hex_str, 16) & ((1 << N) - 1)
    bits_orig = bin(p_orig)[2:].zfill(N)

    sign = (p_orig >> (N - 1)) & 1
    if sign:
        p_mag = ((~p_orig) + 1) & ((1 << N) - 1)
    else:
        p_mag = p_orig
    bits_mag = bin(p_mag)[2:].zfill(N)

    regime_bit = int(bits_mag[1])
    idx = 2; run = 1
    while idx < N and int(bits_mag[idx]) == regime_bit:
        run += 1; idx += 1
    k = (run - 1) if regime_bit == 1 else -run
    idx += 1
    e = int(bits_mag[idx]) if idx < N else 0
    if idx < N: idx += 1
    frac = 1.0; weight = 0.5
    while idx < N:
        if int(bits_mag[idx]): frac += weight
        weight *= 0.5; idx += 1

    value = (4.0 ** k) * (2.0 ** e) * frac
    if sign: value = -value

    print(f"  Hex input   : 0x{hex_str.upper()}")
    print(f"  N-bit binary: {bits_orig}  (N={N})")
    print(f"  Sign        : {sign}  ({'negative' if sign else 'positive'})")
    print(f"  Magnitude   : {bits_mag}")
    print(f"  Regime bits : {bits_mag[1:1+run]}  (regime_bit={regime_bit}, run={run}, k={k})")
    regime_end = 1 + run + 1  # start + run + terminator
    exp_str = bits_mag[regime_end:regime_end+1] if regime_end < N else '(none)'
    print(f"  Exponent    : {exp_str}  (e={e})")
    frac_start = regime_end + 1
    print(f"  Fraction    : {bits_mag[frac_start:]}  (f={frac:.8f})")
    print(f"  Formula     : 4^{k} × 2^{e} × {frac:.6f} = {abs(value):.8f}")
    print(f"  Result      : {value:.8f}")
    print()


# ─── TEST INPUTS ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    hex_inputs = [
        # From FFT simulation output (N=12)
        "700",   # X[0] real  → expect ≈ +16.49
        "E20",   # X[3] imag  → expect ≈ -0.2188  (close to MATLAB -0.218848)
        "702",   # X[3] real  → expect ≈ +17.35
        "000",   # zero
        "800",   # NaR (Not-a-Real)
        "400",   # +1.0
        "C00",   # -1.0
        "9F0",   # -4.5  (encoding of -4.5 in Posit(12,1))
    ]

    print(f"{'='*60}")
    print(f"  Posit({N},1) Hex Decoder")
    print(f"{'='*60}\n")

    for h in hex_inputs:
        result = decode_posit(h, N)
        print(f"  0x{h.upper():>4s}  ->  {result:12.6f}")

    print("\n" + "-"*60)
    print("  Detailed breakdown for 0xE20:")
    print("-"*60)
    show_decode("E20", N)

    print("-"*60)
    print("  Detailed breakdown for 0x9F0  (should give -4.5):")
    print("-"*60)
    show_decode("9F0", N)
