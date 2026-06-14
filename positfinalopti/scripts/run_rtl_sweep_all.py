import os
import subprocess
import re
import sys

target_dir = r"c:\Users\ROHITH SAI\FIXED_POINT_FFT_RTL\posit_16pointfft\POSIT_N_1_Corrected_1024\POSIT_N_1_Corrected\Design-and-Implementation-of-a-16-Point-Fixed-Point-FFT-Using-VHDL"

def run_posit_sim(N):
    print(f"Running RTL simulation for N={N}...")
    
    # 1. Update N in build_tb.py
    build_tb_path = os.path.join(target_dir, 'build_tb.py')
    with open(build_tb_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'N\s*=\s*\d+', f'N = {N}', text, count=1)
    with open(build_tb_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 2. Run build_tb.py to generate testbench inputs
    subprocess.run([sys.executable, "build_tb.py"], cwd=target_dir, stdout=subprocess.DEVNULL, check=True)
    
    # 3. Update N in fft16_top.v
    top_path = os.path.join(target_dir, 'fft16_top.v')
    with open(top_path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'parameter\s+N\s*=\s*\d+,', f'parameter N          = {N},', text)
    with open(top_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # 4. Compile with iverilog
    vvp_file = f"test_posit_sim_{N}.vvp"
    compile_cmd = [
        "iverilog", "-o", vvp_file,
        "tb_fft16.v", "fft16_top.v", "sample_ram.v", "twiddle_rom.v", 
        "butterfly.v", "complex_mult.v", "POSIT_Multiplier.v", 
        "POSIT_adder.v", "POSIT_decode.v", "POSIT_encode.v", "POSIT_subtractor.v"
    ]
    subprocess.run(compile_cmd, cwd=target_dir, stdout=subprocess.DEVNULL, check=True)
    
    # 5. Run simulation
    log_file = f"sim_1024_N{N}.log"
    with open(os.path.join(target_dir, log_file), "w", encoding="utf-8") as out_f:
        subprocess.run(["vvp", vvp_file], cwd=target_dir, stdout=out_f, check=True)
        
    # 6. Run comparison parser
    compare_cmd = [sys.executable, "compare_fft.py", log_file, str(N)]
    res = subprocess.run(compare_cmd, cwd=target_dir, stdout=subprocess.PIPE, text=True, check=True)
    
    # Extract metrics
    snr = None
    rmse = None
    mae = None
    nrmse = None
    accuracy = None
    range_error = None
    for line in res.stdout.splitlines():
        if "SNR" in line and "dB" in line:
            m = re.search(r'SNR\s*:\s*([\d\.\-]+)\s*dB', line)
            if m: snr = float(m.group(1))
        if "RMSE (magnitude)" in line:
            m = re.search(r'RMSE \(magnitude\)\s*:\s*([\d\.\-]+)', line)
            if m: rmse = float(m.group(1))
        if "Mean Absolute Error" in line:
            m = re.search(r'Mean Absolute Error\s*:\s*([\d\.\-]+)', line)
            if m: mae = float(m.group(1))
        if "Normalized RMSE" in line:
            m = re.search(r'Normalized RMSE\s*:\s*([\d\.\-]+)\s*%', line)
            if m: nrmse = float(m.group(1))
        if "Overall Accuracy" in line:
            m = re.search(r'Overall Accuracy\s*:\s*([\d\.\-]+)\s*%', line)
            if m: accuracy = float(m.group(1))
        if "Range Error" in line:
            m = re.search(r'Range Error\s*:\s*([\d\.\-]+)\s*m', line)
            if m: range_error = float(m.group(1)) * 100.0 # to cm
            
    # Clean up compilation files
    try:
        os.remove(os.path.join(target_dir, vvp_file))
    except:
        pass
        
    return snr, rmse, mae, nrmse, accuracy, range_error

results = []
for N in range(4, 17):
    try:
        snr, rmse, mae, nrmse, acc, r_err = run_posit_sim(N)
        results.append((N, snr, rmse, mae, nrmse, acc, r_err))
        print(f"N={N} Done: SNR={snr} dB, Range Error={r_err} cm")
    except Exception as e:
        print(f"Error on N={N}: {e}")

print("\n=========================================================================================================")
print(" ACTUAL HARDWARE (RTL) SIMULATION SWEEP RESULTS (N=4 to 16)")
print("=========================================================================================================")
print(f"{'N':>2} | {'RTL SNR (dB)':>13} | {'RTL RMSE':>12} | {'RTL MAE':>12} | {'NRMSE (%)':>10} | {'Accuracy (%)':>12} | {'RTL Range Error (cm)':>22}")
print("-" * 105)
for N, snr, rmse, mae, nrmse, acc, r_err in results:
    snr_str = f"{snr:.2f} dB" if snr is not None else "N/A"
    rmse_str = f"{rmse:.6f}" if rmse is not None else "N/A"
    mae_str = f"{mae:.6f}" if mae is not None else "N/A"
    nrmse_str = f"{nrmse:.4f}%" if nrmse is not None else "N/A"
    acc_str = f"{acc:.4f}%" if acc is not None else "N/A"
    r_err_str = f"{r_err:.5f} cm" if r_err is not None else "N/A"
    print(f"{N:>2} | {snr_str:>13} | {rmse_str:>12} | {mae_str:>12} | {nrmse_str:>10} | {acc_str:>12} | {r_err_str:>22}")
print("=========================================================================================================")
