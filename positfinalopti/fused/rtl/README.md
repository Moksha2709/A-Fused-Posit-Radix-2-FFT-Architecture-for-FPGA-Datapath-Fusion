# Fused Posit RTL Source Files

This directory contains the synthesizable Verilog HDL source files and FPGA physical constraints (`.xdc`) for the Fused Posit FFT architecture. Key modules include the top-level pipelined FFT processor, dual-port RAM for samples, twiddle factor ROM, and custom raw arithmetic units (multipliers and adders) designed for fused datapath execution. It also includes the basic Posit decode/encode blocks that operate exclusively at the butterfly boundaries.
