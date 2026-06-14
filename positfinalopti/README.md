# A Fused and Non-Fused Posit Radix-2 FFT Architecture for FPGA Datapath Fusion

This repository contains the synthesizable Verilog HDL implementations of a 1024-point pipelined Radix-2 Fast Fourier Transform (FFT) utilizing **Posit(N, 1)** arithmetic, optimized for FPGA deployments. It is designed to showcase the hardware resource savings and precision improvements achieved by fusing Posit arithmetic operations within the Radix-2 butterfly datapath.

---

## Directory Layout

The repository is organized into two completely isolated directories representing the two architectural variants:

* **[`fused/`](file:///c:/SRIP/positfinalopti/fused)**: Contains the highly optimized **Fused Posit FFT** design, scripts, testbench, and local simulation folder.
* **[`non_fused/`](file:///c:/SRIP/positfinalopti/non_fused)**: Contains the baseline **Non-Fused Posit FFT** design, scripts, testbench, and local simulation folder.

Each of these directories has a standard structure:
* `rtl/`: Synthesizable Verilog HDL source files and constraints (`.xdc`).
* `tb/`: Testbench files to load input vectors and capture outputs.
* `scripts/`: Python simulation and verification scripts, plus Vivado synthesis Tcl scripts.
* `sim/`: Real-world input vectors (`real_inputs_1024.txt`) and simulation log outputs.

---

## Architectural Comparison

### 1. Fused Posit Butterfly Architecture (`fused/`)
In a standard Posit butterfly implementation, every discrete arithmetic operator (multiplier, adder, subtractor) decodes its input Posits into sign-scale-mantissa formats and encodes the results back. This leads to **20 decoders and 10 encoders** per butterfly.

The **Fused** architecture eliminates this redundant decoding/encoding overhead:
* **Input Boundary Decoding**: Decodes only the **6 external inputs** (two complex inputs $A, B$ and one complex twiddle factor $W$) once at the input boundary.
* **Raw Intermediate Computation**: Conducts all complex multiplications, additions, and subtractions in a raw, unpacked representation (sign, scale, mantissa).
* **Output Boundary Encoding**: Encodes only the **4 final outputs** ($Y_0, Y_1$) back into the Posit format.
* **Benefits**: Saves **~50% LUT area** on FPGA, reduces power consumption, and eliminates intermediate rounding stages to significantly reduce quantization noise.

### 2. Non-Fused Posit Butterfly Architecture (`non_fused/`)
* Built using discrete, modular Posit operators (standard Posit adder, subtractor, and multiplier modules).
* Each arithmetic module operates independently, performing its own Posit decoding and encoding.
* Serves as the primary reference baseline to evaluate the hardware and numerical improvements of the fused design.

---

## Custom Floating-Point Baselines (FP16 & FP32)

To validate the precision advantages of Posit arithmetic, these designs were compared against custom **FP16** and **FP32** Floating-Point architectures:
* The floating-point baselines use the **identical pipelined control datapath and dual-port RAM structures** as the Posit architectures.
* However, the arithmetic butterfly blocks utilize standard IEEE 754 FP16/FP32 operations.
* Testing shows that the Posit designs achieve a significantly higher Signal-to-Noise Ratio (SNR) than floating-point baselines at lower word-widths due to the tapered precision of Posits.

---

## Why We Simulate & Verify

Simulations are conducted to:
1. **Functional Correctness**: Verify the pipeline control FSM, RAM loading, twiddle addressing, and RAM readback.
2. **Numerical Accuracy Verification**: Run simulations on a real-world unquantized radar signal (located in `real_inputs_1024.txt`) and compare the RTL outputs against a double-precision golden reference FFT computed in MATLAB/NumPy.
3. **SNR and RMSE Quantification**: Capture and analyze the outputs to compute the Signal-to-Noise Ratio (SNR) in dB, Root-Mean-Square Error (RMSE), and Max Absolute Error (MAE) without range tracking error interference.

---

## How to Simulate

Ensure you have `iverilog` (Icarus Verilog), `vvp`, and Python installed.

### A. Simulating the Fused Posit Design
1. Navigate to the `fused` directory.
2. Generate the testbench with Posit(16,1) inputs:
   ```bash
   py fused/scripts/build_tb.py 16
   ```
3. Compile the design:
   ```bash
   iverilog -o fused/sim/test_posit_sim_fused_16.vvp fused/tb/tb_fft16_fused.v fused/rtl/fft16_top_fused.v fused/rtl/sample_ram.v fused/rtl/twiddle_rom.v fused/rtl/posit_fused_butterfly.v fused/rtl/posit_addsub_raw.v fused/rtl/posit_mul_raw.v fused/rtl/POSIT_decode.v fused/rtl/POSIT_encode.v fused/rtl/posit_raw_to_enc.v
   ```
4. Run the simulation to produce a log:
   ```bash
   vvp fused/sim/test_posit_sim_fused_16.vvp > fused/sim/sim_1024_fused_N16.log
   ```
5. Evaluate SNR and accuracy:
   ```bash
   py fused/scripts/compare_fft.py fused/sim/sim_1024_fused_N16.log 16
   ```

### B. Simulating the Non-Fused Posit Design
1. Navigate to the `non_fused` directory.
2. Generate the testbench with Posit(16,1) inputs:
   ```bash
   py non_fused/scripts/build_tb.py 16
   ```
3. Compile the design:
   ```bash
   iverilog -o non_fused/sim/test_posit_sim_16.vvp non_fused/tb/tb_fft16.v non_fused/rtl/fft16_top.v non_fused/rtl/sample_ram.v non_fused/rtl/twiddle_rom.v non_fused/rtl/butterfly.v non_fused/rtl/complex_mult.v non_fused/rtl/POSIT_Multiplier.v non_fused/rtl/POSIT_adder.v non_fused/rtl/POSIT_subtractor.v non_fused/rtl/POSIT_decode.v non_fused/rtl/POSIT_encode.v
   ```
4. Run the simulation to produce a log:
   ```bash
   vvp non_fused/sim/test_posit_sim_16.vvp > non_fused/sim/sim_1024_N16.log
   ```
5. Evaluate SNR and accuracy:
   ```bash
   py non_fused/scripts/compare_fft.py non_fused/sim/sim_1024_N16.log 16
   ```