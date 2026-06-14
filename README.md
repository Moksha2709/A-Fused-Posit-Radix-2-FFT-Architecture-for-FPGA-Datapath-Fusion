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

