import re

pattern = re.compile(r'X\[(\d+)\]\s+r=([0-9a-fA-F]+)\s+i=([0-9a-fA-F]+)')
with open('sim_1024_N8.log', 'r') as f:
    for line in f:
        m = pattern.search(line)
        if m:
            idx = int(m.group(1))
            if idx < 20:
                print(f"X[{idx}] r={m.group(2)} i={m.group(3)}")
