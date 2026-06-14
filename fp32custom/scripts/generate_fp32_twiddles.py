import os
import math
import numpy as np

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
POINTS = 1024          # FFT size (must be a power of 2)
LOG2_POINTS = int(math.log2(POINTS))
ADDR_BITS = LOG2_POINTS - 1   # address bus width for POINTS/2 twiddles
# ──────────────────────────────────────────────────────────────────────────────

def encode_fp32(val):
    fp32_val = np.float32(val)
    hex_val = fp32_val.view('uint32')
    return hex_val

# Generate POINTS/2 unique twiddle factors for W_POINTS^n, n = 0 .. POINTS/2-1
twiddles = []
for n in range(POINTS // 2):
    c =  math.cos(2 * math.pi * n / POINTS)
    s = -math.sin(2 * math.pi * n / POINTS)
    twiddles.append((c, s))

out = []
out.append(f"module fp32_twiddle_rom (")
out.append(f"    input  [{ADDR_BITS-1}:0] addr,")
out.append(f"    output reg [31:0] wr,")
out.append(f"    output reg [31:0] wi")
out.append(");")
out.append("")
out.append("always @(*) begin")
out.append(f"    case(addr)")

for i, (r_val, i_val) in enumerate(twiddles):
    wr_enc = encode_fp32(r_val)
    wi_enc = encode_fp32(i_val)
    fmt_wr = f"{wr_enc:08X}"
    fmt_wi = f"{wi_enc:08X}"
    out.append(f"        {ADDR_BITS}'d{i}: begin wr = 32'h{fmt_wr}; wi = 32'h{fmt_wi}; end // W_{POINTS}^{i} = {r_val:8.5f} + j {i_val:8.5f}")

out.append(f"        default: begin wr = 0; wi = 0; end")
out.append(f"    endcase")
out.append("end")
out.append("endmodule")

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
out_path = os.path.join(project_root, 'hdl', 'fp32_twiddle_rom.v')

with open(out_path, 'w') as f:
    f.write('\n'.join(out) + '\n')

print(f"Generated fp32_twiddle_rom.v -> {out_path}")
