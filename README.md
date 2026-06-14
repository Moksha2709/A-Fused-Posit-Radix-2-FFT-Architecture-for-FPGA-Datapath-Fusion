# A Fused-Posit Radix-2 FFT Architecture for FPGA Datapath Fusion

This repository contains a high-performance, custom hardware implementation of a **1024-Point Radix-2 Decimation-in-Time (DIT) Fast Fourier Transform (FFT)** architecture targeting FPGAs. 

The project evaluates and compares a **Re-Engineered Posit(N, 1) arithmetic datapath** against custom behavioral **IEEE-754 Half-Precision (FP16)** and **Single-Precision (FP32)** floating-point baselines. All designs are implemented in pure behavioral Verilog, eliminating any dependency on vendor-specific IP cores (e.g., Xilinx Floating-Point IP) to guarantee a completely fair comparison in area, timing, power, and numerical accuracy.

---

## 🚀 Key Architectural Novelty: Datapath Fusion

### 1. Fused Decode-Compute-Encode Butterfly
In a conventional Posit-based butterfly unit, every arithmetic operator (multipliers, adders, subtractors) performs a full decode of its inputs and a full encode of its outputs. For a complex radix-2 butterfly (requiring 4 multiplications, 3 additions, and 3 subtractions), a standard modular implementation requires:
* **20 Posit Decoders**
* **10 Posit Encoders**

Our optimized **Fused Butterfly Architecture** ([posit_fused_butterfly.v](file:///c:/SRIP/positfinalopti/rtl/posit_fused_butterfly.v)) fuses the entire datapath:
* **Stage 1 (Decode):** Decodes the 6 complex inputs (A, B, and Twiddle W) only *once* using **6 decoders**.
* **Stage 2-4 (Compute):** Executes all multiplications, additions, and subtractions in a **raw decoded format** (carrying sign, scale/exponent, and mantissa).
* **Stage 5 (Encode):** Encodes the 4 final butterfly outputs back to the Posit format using **4 encoders**.

This reduces hardware resource requirements from **20 decoders + 10 encoders** down to only **6 decoders + 4 encoders**, significantly saving FPGA logic cells, reducing propagation delay, and easing routing congestion.

```
       Conventional Butterfly                      Fused Butterfly (This Work)
      +------------------------+                   +------------------------+
      |  20 Decoders / Encoders|                   |  6 Decoders / Encoders |
      +------------------------+                   +------------------------+
```

### 2. High-Precision Guard Bits & RNE Rounding
To prevent the compound truncation noise across the 10 stages of the 1024-point FFT, the internal operators ([POSIT_adder.v](file:///c:/SRIP/positfinalopti/rtl/POSIT_adder.v) and [POSIT_Multiplier.v](file:///c:/SRIP/positfinalopti/rtl/POSIT_Multiplier.v)) maintain **6 intermediate fraction guard bits** during addition and multiplication. 
* Exact **Round-to-Nearest-Even (RNE)** rounding is performed only once at the final encoding stage ([posit_raw_to_enc.v](file:///c:/SRIP/positfinalopti/rtl/posit_raw_to_enc.v)).
* This prevents small, high-frequency signal peaks from being prematurely truncated to zero, maintaining a significantly lower noise floor compared to standard software models that truncate at each intermediate stage.

---

## 📂 Directory Structure

The project is structured into four main folders:

1. **[positfinalopti](file:///c:/SRIP/positfinalopti/)**: The core optimized Posit FFT implementation.
   * **[rtl/](file:///c:/SRIP/positfinalopti/rtl/)**: Hardware description files for the fused Posit FFT, including [posit_fused_butterfly.v](file:///c:/SRIP/positfinalopti/rtl/posit_fused_butterfly.v), the top-level FSM controller [fft16_top_fused.v](file:///c:/SRIP/positfinalopti/rtl/fft16_top_fused.v), and basic memory wrappers.
   * **[scripts/](file:///c:/SRIP/positfinalopti/scripts/)**: Automated sweeps to compile, simulate, and parse accuracy statistics.
   * **[sim/](file:///c:/SRIP/positfinalopti/sim/)**: Raw input radar data vectors and simulation outputs.
   * **[tb/](file:///c:/SRIP/positfinalopti/tb/)**: Testbenches for verification.
   * **[docs/](file:///c:/SRIP/positfinalopti/docs/)**: Detailed reports on Scenario A & Scenario B radar simulations.

2. **[fp16custom](file:///c:/SRIP/fp16custom/)**: Custom IEEE-754 Half-Precision (16-bit) baseline.
   * Matches the control FSM, pipelining, and memory layout of the Posit design exactly.
   * Built using custom combinational FP16 RTL operators ([fp16_add.v](file:///c:/SRIP/fp16custom/rtl/fp16_add.v), [fp16_mul.v](file:///c:/SRIP/fp16custom/rtl/fp16_mul.v)) without using vendor IP.

3. **[fp32custom](file:///c:/SRIP/fp32custom/)**: Custom IEEE-754 Single-Precision (32-bit) baseline.
   * Provides the custom FP32 arithmetic unit implementations ([fp32_add.v](file:///c:/SRIP/fp32custom/hdl/fp32_add.v), [fp32_mul.v](file:///c:/SRIP/fp32custom/hdl/fp32_mul.v)) alongside FP16 and Posit components for comparative debugging.

4. **[reports2](file:///c:/SRIP/reports2/)**: Vivado synthesis and implementation reports.
   * Categorized by bitwidth config (e.g., `P12E1` for 12-bit Posit, `FloatingPoint16`, `FPCustom32`).
   * Contains reports for **utilization**, **power**, **timing**, and **critical path analyses** mapped directly from Vivado runs.

---

## 📊 Performance & Accuracy Benchmarks

The designs were verified using real-world FMCW radar input signals compared against a double-precision MATLAB/NumPy FFT reference.

### Scenario A: Distorted Single-Target Radar Input
Input signal contains a fundamental peak with realistic receiver odd-harmonic distortion peaks.

| Bitwidth (N) | Posit RTL SNR (dB) | FP RTL SNR (dB) | SNR Advantage | Posit Range Error (cm) | FP Range Error (cm) | Accuracy Boost |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **12** | **41.16 dB** | 36.41 dB (FP12) | **+4.75 dB** | **14.18 cm** | 66.79 cm | **4.7x lower range error** |
| **13** | **46.99 dB** | 42.56 dB (FP13) | **+4.43 dB** | **14.58 cm** | 49.31 cm | **3.4x lower range error** |
| **14** | **53.05 dB** | 48.74 dB (FP14) | **+4.31 dB** | **11.47 cm** | 22.61 cm | **2.0x lower range error** |
| **15** | **59.19 dB** | 54.62 dB (FP15) | **+4.57 dB** | **1.45 cm** | 5.88 cm | **4.1x lower range error** |
| **16** | **65.21 dB** | 60.74 dB (FP16) | **+4.47 dB** | **4.61 cm** | 7.58 cm | **1.6x lower range error** |

### Scenario B: Dual-Target FMCW Radar (Strong + Weak Target at -46 dB)
A highly challenging scenario tracking a weak target peak located close to a strong target. Under standard floating-point truncation, the weak peak is completely drowned in arithmetic noise.

| Format | Word-width | Hardware SNR (dB) | Weak Peak Bin | Target Range Error (cm) | Improvement |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FP12 (e5m6) RTL** | 12-bit | 0.00 dB | 25.000000 | 547.6262 cm | *baseline (Failed)* |
| **Posit(12, 1) RTL** | 12-bit | **41.90 dB** | **30.428777** | **4.7491 cm** | **115.31x range error reduction** |
| **FP15 (e5m9) RTL** | 15-bit | 56.98 dB | 30.432650 | 4.3618 cm | *baseline* |
| **Posit(15, 1) RTL** | 15-bit | **57.31 dB** | **30.470954** | **0.5314 cm** | **8.21x range error reduction** |

---

## 🛠️ Simulation & Verification Instructions

### Prerequisites
* **Icarus Verilog** (`iverilog` & `vvp`)
* **Python 3.x** (with `numpy`, `matplotlib` packages)

### Running Posit FFT Simulation (N=16 Example)
To compile and simulate the fused Posit FFT using Icarus Verilog:

```bash
# Navigate to the Posit directory
cd positfinalopti

# Compile RTL and Testbench
iverilog -o sim/test_posit_sim_16.vvp tb/tb_fft16_fused.v rtl/fft16_top_fused.v rtl/sample_ram.v rtl/twiddle_rom.v rtl/posit_fused_butterfly.v rtl/POSIT_decode.v rtl/posit_mul_raw.v rtl/posit_addsub_raw.v rtl/posit_raw_to_enc.v

# Run the simulation (outputs log of FFT bins)
vvp sim/test_posit_sim_16.vvp > sim/sim_1024_N16.log
```

### Running Accuracy Comparisons
To calculate the accuracy metrics (SNR, RMSE, MAE, Range Error) dynamically against double-precision NumPy FFT reference vectors:

```bash
# Run the Python verification script
python scripts/verify_sw_vs_rtl.py
```

### Running Custom FP16 Simulation
To compile and simulate the custom FP16 baseline:

```bash
# Navigate to the FP16 directory
cd fp16custom

# Compile RTL and Testbench
iverilog -o sim/test_sim.vvp sim/tb_fft16.v rtl/fp16_fft16_top.v rtl/sample_ram.v rtl/fp16_twiddle_rom.v rtl/fp16_butterfly.v rtl/fp16_add.v rtl/fp16_sub.v rtl/fp16_mul.v

# Run simulation
vvp sim/test_sim.vvp > sim/sim_1024_fp16.log

# Evaluate metrics
python scripts/compare_fp16.py
```