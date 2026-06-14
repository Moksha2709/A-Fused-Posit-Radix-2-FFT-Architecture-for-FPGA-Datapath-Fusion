# Non-Fused Posit RTL Source Files

This directory contains the synthesizable Verilog HDL source files and FPGA physical constraints (`.xdc`) for the baseline Non-Fused Posit FFT. It includes standard modular Posit arithmetic components, such as independent Posit adders, subtractors, and multipliers, alongside a standard complex multiplier. The top-level pipelined control logic, dual-port sample RAM, twiddle factor ROM, and standalone decode/encode modules are also located here.
