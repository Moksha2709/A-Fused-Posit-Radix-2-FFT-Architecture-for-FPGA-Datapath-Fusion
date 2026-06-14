# Fused Posit FFT Testbench

This directory contains the Verilog HDL testbench file (`tb_fft16_fused.v`) used to verify the functional correctness and numerical precision of the Fused Posit FFT design. The testbench handles loading test inputs from file vectors, feeding them into the top-level FFT architecture under test, and capturing simulation outputs. This enables post-simulation performance evaluations, such as root-mean-square error (RMSE) and signal-to-noise ratio (SNR) verification.
