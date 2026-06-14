# Dual-Target RTL Simulation Results (Scenario B)
This report summarizes the hardware results obtained by compiling and simulating the RTL VHDL/Verilog blocks in Icarus Verilog.

## Summary Table: RTL Range Error and SNR Comparison
| Format | Word-width | Hardware SNR (dB) | Weak Peak Bin | Target Range Error (cm) | Improvement |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FP12 (e5m6) RTL** | 12-bit | 0.00 dB | 25.000000 | 547.6262 cm | baseline |
| **Posit(12,1) RTL** | 12-bit | 41.90 dB | 30.428777 | 4.7491 cm | **115.31x reduction** |
| **FP15 (e5m9) RTL** | 15-bit | 56.98 dB | 30.432650 | 4.3618 cm | baseline |
| **Posit(15,1) RTL** | 15-bit | 57.31 dB | 30.470954 | 0.5314 cm | **8.21x reduction** |
