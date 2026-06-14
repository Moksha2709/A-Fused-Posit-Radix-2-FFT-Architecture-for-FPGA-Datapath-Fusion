import math
import sys
import os

# Setup working directory to project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
POINTS = 1024          # FFT size (must be a power of 2)
LOG2_POINTS = int(math.log2(POINTS))
ADDR_BITS = LOG2_POINTS - 1   # address bus width for POINTS/2 twiddles
# ──────────────────────────────────────────────────────────────────────────────

def encode_posit_N_1(val, N=8):
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

# Generate POINTS/2 unique twiddle factors for W_POINTS^n, n = 0 .. POINTS/2-1
twiddles = []
for n in range(POINTS // 2):
    c =  math.cos(2 * math.pi * n / POINTS)
    s = -math.sin(2 * math.pi * n / POINTS)
    twiddles.append((c, s))

out = []
out.append(f"module twiddle_rom #(parameter N = 10)(")
out.append(f"    input  [{ADDR_BITS-1}:0] addr,")
out.append(f"    output reg [N-1:0] wr,")
out.append(f"    output reg [N-1:0] wi")
out.append(");")
out.append("")
out.append("always @(*) begin")

for N in range(16, 3, -1):
    hex_width = (N + 3) // 4
    if N == 16:
        out.append(f"    if (N == {N}) begin")
    else:
        out.append(f"    else if (N == {N}) begin")
    out.append(f"        case(addr)")
    for i, (r_val, i_val) in enumerate(twiddles):
        wr_enc = encode_posit_N_1(r_val, N)
        wi_enc = encode_posit_N_1(i_val, N)
        fmt_wr = f"{wr_enc:0{hex_width}X}"
        fmt_wi = f"{wi_enc:0{hex_width}X}"
        out.append(f"            {ADDR_BITS}'d{i}: begin wr = {N}'h{fmt_wr}; wi = {N}'h{fmt_wi}; end // W_{POINTS}^{i} = {r_val:8.5f} + j {i_val:8.5f}")
    out.append(f"            default: begin wr = 0; wi = 0; end")
    out.append(f"        endcase")
    out.append(f"    end")

out.append("    else begin")
out.append("        wr = 0;")
out.append("        wi = 0;")
out.append("    end")
out.append("end")
out.append("endmodule")

with open('hdl/twiddle_rom.v', 'w') as f:
    f.write('\n'.join(out) + '\n')

print(f"Generated twiddle_rom.v -> {POINTS}-point FFT, {POINTS//2} twiddle factors, addr bus [{ADDR_BITS-1}:0]")
