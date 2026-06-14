# FP16 FFT Implementation Walkthrough (Option B: Custom RTL)

This directory contains the **Option B** IEEE-754 Half-Precision (FP16) 1024-Point FFT design. 
This architecture matches the combinational datapath and control flow of the Posit design, eliminating all Xilinx proprietary IP cores to ensure a completely fair comparison in area, timing, and power.

## 1. Files to Import into Vivado
Add the following custom behavioral RTL files (located in the `rtl/` directory) into your Vivado project as design sources:
- `rtl/fp16_fft16_top.v` (Top-level FFT controller module)
- `rtl/fp16_butterfly.v` (Combinational butterfly calculating unit)
- `rtl/fp16_add.v` (Custom FP16 adder)
- `rtl/fp16_sub.v` (Custom FP16 subtractor)
- `rtl/fp16_mul.v` (Custom FP16 multiplier)
- `rtl/fp16_twiddle_rom.v` (Pre-computed FP16 Twiddle factors)
- `rtl/sample_ram.v` (Standard double-port RAM)

> [!IMPORTANT]
> **No Vivado Floating-Point IP cores are required.** All calculations are performed using the custom combinational FP16 RTL operators.

## 2. Setting Up Vivado Project Parameters
1. Create a project in Vivado targeting your FPGA (e.g., Zynq UltraScale+ `xczu5ev-sfvc784-3-e`).
2. Add the Verilog files from `rtl/` and the constraints file `constraints/fft16_constraints.xdc`.
3. Set `fp16_fft16_top` as the top module.
4. Verify/configure the module parameters (generics) in the hierarchy settings:
   - `N = 16`
   - `POINTS = 1024`
   - `LOG2_POINTS = 10`

## 3. Simulation & Verification
The RTL simulation can be compiled and run locally using Icarus Verilog:
```bash
# Compile with iverilog
iverilog -o sim/test_sim.vvp sim/tb_fft16.v rtl/fp16_fft16_top.v rtl/sample_ram.v rtl/fp16_twiddle_rom.v rtl/fp16_butterfly.v rtl/fp16_add.v rtl/fp16_sub.v rtl/fp16_mul.v

# Run simulation using vvp to generate sim/sim_1024_fp16.log
vvp sim/test_sim.vvp > sim/sim_1024_fp16.log
```

To calculate the accuracy metrics (RMSE, SNR, MAE) dynamically against a double-precision NumPy FFT reference, run:
```bash
python scripts/compare_fp16.py
```

## 4. Expected Baseline Performance
The custom combinational FP16 RTL simulation yields:
* **RMSE (Magnitude):** `0.020334`
* **Signal-to-Noise Ratio (SNR):** `60.93 dB`
* **Normalized RMSE:** `0.0899 %`
* **Overall Accuracy:** `99.9101 %`
