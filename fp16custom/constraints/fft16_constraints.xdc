# -------------------------------------------------------------------------
# XDC Timing Constraints for fft16_top
# Target Frequency: 100 MHz
# -------------------------------------------------------------------------

# Define the primary clock 'clk'
# Period is 10.000 ns (100 MHz), with a 50% duty cycle (high from 0ns to 5ns)
create_clock -period 10.000 -name sys_clk -waveform {0.000 5.000} [get_ports clk]

# The reset signal is typically asynchronous to the data path, 
# you can optionally set a false path to prevent Vivado from over-optimizing the reset net
set_false_path -from [get_ports rst]
