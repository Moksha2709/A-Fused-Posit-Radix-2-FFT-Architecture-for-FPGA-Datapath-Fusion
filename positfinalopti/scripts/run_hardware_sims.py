import sys
import os
import subprocess
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(script_dir, '..'))
target_dir = workspace_root
fp_dir = os.path.abspath(os.path.join(workspace_root, '../floatingpoint'))

def run_posit_sim(N):
    print(f"\n--- RUNNING POSIT SIMULATION FOR N={N} ---")
    
    # 1. Update N in build_tb.py
    build_tb_path = os.path.join(target_dir, 'scripts', 'build_tb.py')
    with open(build_tb_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'N\s*=\s*\d+', f'N = {N}', text, count=1)
    with open(build_tb_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 2. Run build_tb.py
    subprocess.run([sys.executable, os.path.join("scripts", "build_tb.py")], cwd=target_dir, check=True)
    
    # 3. Update N in fft16_top.v
    top_path = os.path.join(target_dir, 'rtl', 'fft16_top.v')
    with open(top_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'parameter\s+N\s*=\s*\d+,', f'parameter N          = {N},', text)
    with open(top_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 4. Compile with iverilog
    vvp_file = f"test_posit_sim_{N}.vvp"
    compile_cmd = [
        "iverilog", "-o", os.path.join("sim", vvp_file),
        os.path.join("tb", "tb_fft16.v"),
        os.path.join("rtl", "fft16_top.v"),
        os.path.join("rtl", "sample_ram.v"),
        os.path.join("rtl", "twiddle_rom.v"),
        os.path.join("rtl", "butterfly.v"),
        os.path.join("rtl", "complex_mult.v"),
        os.path.join("rtl", "POSIT_Multiplier.v"),
        os.path.join("rtl", "POSIT_adder.v"),
        os.path.join("rtl", "POSIT_decode.v"),
        os.path.join("rtl", "POSIT_encode.v"),
        os.path.join("rtl", "POSIT_subtractor.v")
    ]
    subprocess.run(compile_cmd, cwd=target_dir, check=True)
    
    # 5. Run simulation
    log_file = f"sim_1024_N{N}.log"
    print(f"Running simulation to output '{log_file}'...")
    with open(os.path.join(target_dir, "sim", log_file), "w", encoding="utf-8") as out_f:
        subprocess.run(["vvp", os.path.join("sim", vvp_file)], cwd=target_dir, stdout=out_f, check=True)
        
    # 6. Run comparison
    compare_cmd = [sys.executable, os.path.join("scripts", "compare_fft.py"), os.path.join("sim", log_file), str(N)]
    res = subprocess.run(compare_cmd, cwd=target_dir, stdout=subprocess.PIPE, text=True, check=True)
    
    # Extract SNR and Range Error from compare_fft.py output
    snr = None
    range_error = None
    for line in res.stdout.splitlines():
        if "SNR" in line and "dB" in line:
            # e.g., "  SNR                   : 65.14 dB"
            m = re.search(r'SNR\s*:\s*([\d\.\-]+)\s*dB', line)
            if m: snr = float(m.group(1))
        if "Range Error" in line:
            # e.g., "  Range Error                   : 0.045236 m"
            m = re.search(r'Range Error\s*:\s*([\d\.\-]+)\s*m', line)
            if m: range_error = float(m.group(1)) * 100.0 # to cm
            
    print(f"RESULT POSIT {N}: SNR = {snr} dB, Range Error = {range_error} cm")
    return snr, range_error
 
def run_fp_sim(N):
    print(f"\n--- RUNNING FLOATING-POINT SIMULATION FOR N={N} ---")
    
    # 1. Update N in switch_fp_tb.py
    switch_fp_path = os.path.join(target_dir, 'scripts', 'switch_fp_tb.py')
    with open(switch_fp_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'N\s*=\s*\d+', f'N = {N}', text, count=1)
    with open(switch_fp_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 2. Run switch_fp_tb.py (this generates the tb_fft16.v in FP folder)
    subprocess.run([sys.executable, os.path.join("scripts", "switch_fp_tb.py")], cwd=target_dir, check=True)
    
    # 3. Update N in fp16_fft16_top.v
    top_path = os.path.join(fp_dir, 'fp16_fft16_top.v')
    with open(top_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'parameter\s+N\s*=\s*\d+,', f'parameter N          = {N},', text)
    with open(top_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 4. Compile with iverilog
    vvp_file = f"test_fp_sim_{N}.vvp"
    compile_cmd = [
        "iverilog", "-o", vvp_file,
        "tb_fft16.v", "fp16_fft16_top.v", "sample_ram.v", "fp16_twiddle_rom.v", 
        "fp16_butterfly.v", "fp16_add.v", "fp16_sub.v", "fp16_mul.v", "fp16_op_wrapper.v"
    ]
    subprocess.run(compile_cmd, cwd=fp_dir, check=True)
    
    # 5. Run simulation
    log_file = f"sim_1024_fp{N}.log"
    print(f"Running simulation to output '{log_file}'...")
    with open(os.path.join(fp_dir, log_file), "w", encoding="utf-8") as out_f:
        subprocess.run(["vvp", vvp_file], cwd=fp_dir, stdout=out_f, check=True)
        
    # 6. Run comparison
    compare_cmd = [sys.executable, "compare_fp16.py", log_file, str(N)]
    res = subprocess.run(compare_cmd, cwd=fp_dir, stdout=subprocess.PIPE, text=True, check=True)
    
    # Extract SNR and Range Error
    snr = None
    range_error = None
    for line in res.stdout.splitlines():
        if "SNR" in line and "dB" in line:
            m = re.search(r'SNR\s*:\s*([\d\.\-]+)\s*dB', line)
            if m: snr = float(m.group(1))
        if "Range Error" in line:
            m = re.search(r'Range Error\s*:\s*([\d\.\-]+)\s*m', line)
            if m: range_error = float(m.group(1)) * 100.0 # to cm
            
    print(f"RESULT FP {N}: SNR = {snr} dB, Range Error = {range_error} cm")
    return snr, range_error

results = {}

# Run sweeps
# results['FP12'] = run_fp_sim(12)
results['Posit12'] = run_posit_sim(12)
results['Posit15'] = run_posit_sim(15)
# results['FP16'] = run_fp_sim(16)
results['Posit16'] = run_posit_sim(16)

print("\n=========================================================")
print(" SWEEP RESULTS FROM HARDWARE (RTL) SIMULATIONS")
print("=========================================================")
print(f"{'Format':>12} | {'RTL SNR (dB)':>15} | {'RTL Range Error (cm)':>25}")
print("-" * 60)
for fmt in ['Posit12', 'Posit15', 'Posit16']:
    snr, r_err = results[fmt]
    print(f"{fmt:>12} | {snr:15.2f} dB | {r_err:23.5f} cm")
print("=========================================================")
