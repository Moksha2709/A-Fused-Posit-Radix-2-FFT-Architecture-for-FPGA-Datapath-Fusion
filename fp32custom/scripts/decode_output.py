from generate_inputs import decode_posit_N_1
import math

outputs = [
    (190, 0),
    (190, 0),
    (292, 756),
    (346, 747),
    (743, 117),
    (287, 0),
    (743, 907),
    (346, 277),
    (292, 268),
    (190, 0),
    (292, 756),
    (346, 747),
    (743, 117),
    (287, 0),
    (743, 907),
    (346, 277)
]

print("Decoded RTL Output:")
for i, (r, img) in enumerate(outputs):
    r_dec = decode_posit_N_1(r, 10)
    img_dec = decode_posit_N_1(img, 10)
    print(f"X[{i:2d}] = {r_dec:10.4f} + j {img_dec:10.4f}")
