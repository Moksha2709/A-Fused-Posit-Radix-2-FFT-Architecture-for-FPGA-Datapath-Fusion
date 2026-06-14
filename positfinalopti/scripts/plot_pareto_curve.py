import numpy as np
import os

# Data definition (RMSE values from actual RTL simulations)
posit_bits = np.array([8, 9, 10, 11, 12, 13, 14, 15, 16])
posit_rmse = np.array([3.118395, 1.468418, 0.741050, 0.392094, 0.197891, 0.101179, 0.050361, 0.024832, 0.012423])

fp_bits = np.array([12, 13, 14, 15, 16])
fp_rmse = np.array([0.342071, 0.168553, 0.082727, 0.042054, 0.020780])

# System Power Model: P_total = P_mem(N) + P_arith(N)
# P_mem = beta * N (SRAM storage & Bus transfer power scales linearly with word width)
# P_arith = gamma * N^2 (Arithmetic complexity scales quadratically with word width)
BETA = 5.0        # 5.0 mW per word-width bit
GAMMA_FP = 0.05   # 0.05 mW per bit^2 (for standard fixed-mantissa FP multiplier)
GAMMA_POSIT = 0.075 # 0.075 mW per bit^2 (1.5x scaling for dynamic regime encoding/shifting)

posit_power = BETA * posit_bits + GAMMA_POSIT * (posit_bits ** 2)
fp_power = BETA * fp_bits + GAMMA_FP * (fp_bits ** 2)

# Normalization for Euclidean distance calculation
# To compute distance to origin (0,0) soundly, we scale both axes to [0, 1]
min_rmse = min(np.min(posit_rmse), np.min(fp_rmse))
max_rmse = max(np.max(posit_rmse), np.max(fp_rmse))
min_power = min(np.min(posit_power), np.min(fp_power))
max_power = max(np.max(posit_power), np.max(fp_power))

def normalize(val, min_val, max_val):
    return (val - min_val) / (max_val - min_val)

# Normalize all coordinates
norm_posit_rmse = normalize(posit_rmse, min_rmse, max_rmse)
norm_posit_power = normalize(posit_power, min_power, max_power)

norm_fp_rmse = normalize(fp_rmse, min_rmse, max_rmse)
norm_fp_power = normalize(fp_power, min_power, max_power)

# Calculate Euclidean distance from Normalized Origin (0,0)
posit_dist = np.sqrt(norm_posit_rmse**2 + norm_posit_power**2)
fp_dist = np.sqrt(norm_fp_rmse**2 + norm_fp_power**2)

# Print out results to console for verification
print("=== POSIT SYSTEM CONFIGURATIONS ===")
for i, N in enumerate(posit_bits):
    print(f"Posit({N},1) -> Power: {posit_power[i]:.2f} mW, RMSE: {posit_rmse[i]:.6f}, Norm Dist: {posit_dist[i]:.4f}")

print("\n=== FLOATING-POINT SYSTEM CONFIGURATIONS ===")
for i, N in enumerate(fp_bits):
    print(f"FP{N}       -> Power: {fp_power[i]:.2f} mW, RMSE: {fp_rmse[i]:.6f}, Norm Dist: {fp_dist[i]:.4f}")

# Find the global optimal design point (min distance)
opt_posit_idx = np.argmin(posit_dist)
opt_fp_idx = np.argmin(fp_dist)

print(f"\nOptimal Posit Design Point: Posit({posit_bits[opt_posit_idx]},1) with distance {posit_dist[opt_posit_idx]:.4f}")
print(f"Optimal FP Design Point: FP{fp_bits[opt_fp_idx]} with distance {fp_dist[opt_fp_idx]:.4f}")

