# A Fused-Posit Radix-2 FFT Architecture for FPGA Datapath Fusion

This repository contains a high-performance, synthesizable hardware implementation of a **1024-Point Radix-2 Decimation-in-Time (DIT) Fast Fourier Transform (FFT)** architecture targeting FPGAs. 

The project evaluates and compares a **fused Posit(N, 1) arithmetic datapath** against standard non-fused Posit architectures and custom **IEEE-754 FP16/FP32** floating-point baselines. All designs are implemented in pure behavioral Verilog to guarantee a completely fair comparison in area, timing, power, and numerical accuracy.

---

## 📂 Repository Organization

All development code and test workflows are situated under the [`positfinalopti/`](file:///c:/SRIP/positfinalopti) directory, divided into two self-contained folders:

* **[`positfinalopti/fused/`](file:///c:/SRIP/positfinalopti/fused)**: Contains the synthesizable source files, constraints, testbench, and simulation scripts for the **Fused Posit FFT** design.
* **[`positfinalopti/non_fused/`](file:///c:/SRIP/positfinalopti/non_fused)**: Contains the synthesizable source files, constraints, testbench, and simulation scripts for the standard **Non-Fused Posit FFT** design.

---

## 🚀 Key Architectural Novelty: Datapath Fusion

### 1. Fused Decode-Compute-Encode Butterfly
In a conventional Posit-based butterfly unit, every individual arithmetic operator (multipliers, adders, subtractors) performs a full decode of its inputs and a full encode of its outputs. For a complex radix-2 butterfly (requiring 4 multiplications, 3 additions, and 3 subtractions), a standard implementation requires:
* **20 Posit Decoders**
* **10 Posit Encoders**

Our optimized **Fused Butterfly Architecture** ([posit_fused_butterfly.v](file:///c:/SRIP/positfinalopti/fused/rtl/posit_fused_butterfly.v)) fuses the entire butterfly datapath:
* **Stage 1 (Decode):** Decodes the 6 complex inputs (two complex inputs $A, B$ and one complex twiddle factor $W$) only *once* using **6 decoders**.
* **Stage 2-4 (Compute):** Executes all complex multiplications, additions, and subtractions in a **raw decoded format** (carrying sign, scale/exponent, and mantissa).
* **Stage 5 (Encode):** Encodes the 4 final butterfly outputs back to the Posit format using **4 encoders**.

This reduces hardware resource requirements from **20 decoders + 10 encoders** down to only **6 decoders + 4 encoders**, saving ~50% FPGA logic cells and reducing propagation delay.

```
       Conventional Butterfly                      Fused Butterfly (This Work)
      +------------------------+                   +------------------------+
      |  20 Decoders / Encoders|                   |  6 Decoders / Encoders |
      +------------------------+                   +------------------------+
```

### 2. High-Precision Guard Bits & RNE Rounding
To prevent the compound truncation noise across the 10 stages of the 1024-point FFT:
* The raw internal operators maintain **6 intermediate fraction guard bits** during addition and multiplication.
* Exact **Round-to-Nearest-Even (RNE)** rounding is performed only once at the final encoding stage ([posit_raw_to_enc.v](file:///c:/SRIP/positfinalopti/fused/rtl/posit_raw_to_enc.v)).
* This prevents small, high-frequency signal peaks from being prematurely truncated to zero, maintaining a significantly lower noise floor compared to standard software models that truncate at each intermediate stage.

---

## 📊 Custom Floating-Point Baselines (FP16 & FP32)

To evaluate the precision advantages of the Posit design:
* We compared the Posit architectures against custom **FP16** and **FP32** Floating-Point architectures.
* The floating-point baselines use the **identical pipelined control datapath and dual-port RAM structures** as the Posit architectures, but utilize standard IEEE 754 float operators.
* Testing shows that the Posit designs achieve a significantly higher Signal-to-Noise Ratio (SNR) than floating-point baselines at lower word-widths.

