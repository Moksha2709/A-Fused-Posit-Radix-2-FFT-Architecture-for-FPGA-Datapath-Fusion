# =============================================================================
# vivado_run.tcl
# Full Vivado flow: Create project → Synthesis → Implementation → Reports
# Target: Posit(16,1) 1024-Point FFT  (fft16_top, N=16, POINTS=1024)
#
# USAGE (in Vivado Tcl Console):
#   source {c:/Users/ROHITH SAI/FIXED_POINT_FFT_RTL/.../vivado_run.tcl}
#
# OR from command line:
#   vivado -mode batch -source vivado_run.tcl
# =============================================================================

# --------------------------------------------------------------------------- #
# 0. USER SETTINGS — Edit these if your part or paths differ
# --------------------------------------------------------------------------- #
set PART      "xc7a35tcpg236-1"   ;# Artix-7 35T (Basys3). Change if needed.
set PROJ_NAME "posit_fft_N16"
set PROJ_DIR  "./vivado_proj"

set SRC_DIR [file normalize [file dirname [info script]]]

# --------------------------------------------------------------------------- #
# 1. Create Project
# --------------------------------------------------------------------------- #
create_project $PROJ_NAME $PROJ_DIR -part $PART -force

set_property target_language Verilog [current_project]

# --------------------------------------------------------------------------- #
# 2. Add Design Sources
# --------------------------------------------------------------------------- #
add_files [list \
    $SRC_DIR/fft16_top.v      \
    $SRC_DIR/sample_ram.v     \
    $SRC_DIR/twiddle_rom.v    \
    $SRC_DIR/butterfly.v      \
    $SRC_DIR/POSIT_Multiplier.v  \
    $SRC_DIR/POSIT_adder.v    \
    $SRC_DIR/POSIT_subtractor.v \
    $SRC_DIR/POSIT_decode.v   \
    $SRC_DIR/POSIT_encode.v   \
]

# --------------------------------------------------------------------------- #
# 3. Add Constraints
# --------------------------------------------------------------------------- #
add_files -fileset constrs_1 $SRC_DIR/fft16_constraints.xdc

# --------------------------------------------------------------------------- #
# 4. Set Top Module and Parameters (N=16, POINTS=1024)
# --------------------------------------------------------------------------- #
set_property top fft16_top [current_fileset]
set_property generic {N=16 POINTS=1024 LOG2_POINTS=10} [current_fileset]
update_compile_order -fileset sources_1

puts "=== Project created. Top = fft16_top, N=16, POINTS=1024 ==="

# --------------------------------------------------------------------------- #
# 5. Run Synthesis
# --------------------------------------------------------------------------- #
puts "=== Starting Synthesis... ==="
# Configure synthesis to use zero DSP blocks (force LUT/fabric logic implementation)
set_property STEPS.SYNTH_DESIGN.ARGS.MAX_DSP 0 [get_runs synth_1]
launch_runs synth_1 -jobs 4
wait_on_run synth_1

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    error "Synthesis FAILED. Check Messages tab."
}
puts "=== Synthesis COMPLETE ==="

open_run synth_1 -name synth_1

# --------------------------------------------------------------------------- #
# 6. Post-Synthesis Reports
# --------------------------------------------------------------------------- #
file mkdir $PROJ_DIR/reports

report_utilization \
    -file $PROJ_DIR/reports/util_synth.rpt \
    -hierarchical

puts "=== Post-Synthesis utilization report saved ==="

# --------------------------------------------------------------------------- #
# 7. Run Implementation
# --------------------------------------------------------------------------- #
puts "=== Starting Implementation... ==="
launch_runs impl_1 -jobs 4
wait_on_run impl_1

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    error "Implementation FAILED. Check Messages tab."
}
puts "=== Implementation COMPLETE ==="

open_run impl_1 -name impl_1

# --------------------------------------------------------------------------- #
# 8. Post-Implementation Reports
# --------------------------------------------------------------------------- #

# 8a. Utilization (final, post-route)
report_utilization \
    -file $PROJ_DIR/reports/util_impl.rpt \
    -hierarchical
puts "=== Utilization report: $PROJ_DIR/reports/util_impl.rpt ==="

# 8b. Timing Summary (WNS, TNS, Fmax)
report_timing_summary \
    -file $PROJ_DIR/reports/timing_summary.rpt \
    -warn_on_violation
puts "=== Timing summary: $PROJ_DIR/reports/timing_summary.rpt ==="

# 8c. Critical path (worst 5 paths)
report_timing \
    -max_paths 5 \
    -path_type full \
    -file $PROJ_DIR/reports/timing_paths.rpt
puts "=== Timing paths: $PROJ_DIR/reports/timing_paths.rpt ==="

# 8d. Power Report
report_power \
    -file $PROJ_DIR/reports/power.rpt
puts "=== Power report: $PROJ_DIR/reports/power.rpt ==="

# 8e. Design Analysis (logic levels, fanout)
report_design_analysis \
    -logic_level_distribution \
    -file $PROJ_DIR/reports/design_analysis.rpt
puts "=== Design analysis: $PROJ_DIR/reports/design_analysis.rpt ==="

# --------------------------------------------------------------------------- #
# 9. Print Quick Summary to Console
# --------------------------------------------------------------------------- #
puts ""
puts "============================================================"
puts " POSIT(16,1) FFT SYNTHESIS SUMMARY"
puts "============================================================"

# Timing
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set clk_period 10.0
set fmax [expr {1000.0 / ($clk_period - $wns)}]
puts [format "  WNS           : %.3f ns" $wns]
puts [format "  Fmax (achieved): %.1f MHz" $fmax]

# Utilization
set luts  [get_property LUT_AS_LOGIC  [get_cells -hierarchical -filter {REF_NAME =~ LUT*}]]
puts "  (See util_impl.rpt for LUT/FF/BRAM/DSP counts)"
puts "  Reports saved to: $PROJ_DIR/reports/"
puts "============================================================"
