import subprocess
import threading
import time
import re
import sys
import urllib.request

import os

key_path = r"H:\Kolla-Ansible\src\chaos_engineering\k8s_rsa_local"

if not os.path.exists(key_path):
    print("[1] Fetching K8s SSH key from OpenStack host...")
    r = subprocess.run(
        'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "cat /home/kolla/.ssh/k8s_rsa"',
        shell=True, capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"Failed: {r.stderr}")
        sys.exit(1)

    with open(key_path, "w", newline="\n") as f:
        f.write(r.stdout)
    print(f"  [OK] Key saved to {key_path}")

    # Fix permissions (Windows)
    subprocess.run(f'icacls "{key_path}" /inheritance:r /grant:r "%USERNAME%:R"', shell=True, capture_output=True)
else:
    print(f"[1] Key already exists at {key_path}")

# Step 2: SSH with ProxyCommand through qrouter namespace
print("[2] Starting SSH tunnel: localhost:8888 -> K8s-Worker:30080")
proxy_cmd = "ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 nc %h %p"

tunnel_cmd = (
    f'ssh -o StrictHostKeyChecking=no '
    f'-o "ProxyCommand={proxy_cmd}" '
    f'-i "{key_path}" '
    f'-N -L 8888:172.16.0.146:30080 '
    f'ubuntu@172.16.0.74'
)

proc_tunnel = subprocess.Popen(tunnel_cmd, shell=True)
time.sleep(3)

if proc_tunnel.poll() is not None:
    print(f"  [FAIL] Tunnel died")
    sys.exit(1)

print("  [OK] Tunnel is running!")

# Test connection
try:
    urllib.request.urlopen("http://localhost:8888/", timeout=10)
    print("  [OK] Local video streaming accessible!")
except Exception as e:
    print(f"  [WARN] Local video streaming inaccessible: {e}")

# Step 3: Start Pinggy
print("[3] Starting Pinggy internet tunnel (forwarding to localhost:8888)...")
proc_pinggy = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-p", "443", "-R0:localhost:8888", "a.pinggy.io"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True
)

def read_pinggy():
    for line in iter(proc_pinggy.stdout.readline, ''):
        if "pinggy.link" in line:
            url_match = re.search(r"http[s]?://[a-zA-Z0-9-]+\.pinggy\.link", line)
            if url_match:
                url = url_match.group(0)
                print("\n=========================================================", flush=True)
                print(f"  INTERNET URL FOR MOBILE DEMO:", flush=True)
                print(f"  {url}", flush=True)
                print("=========================================================\n", flush=True)
                with open(r"H:\Kolla-Ansible\src\chaos_engineering\pinggy_url.txt", "w") as f:
                    f.write(url)
        
t = threading.Thread(target=read_pinggy, daemon=True)
t.start()

print("Press Ctrl+C to stop everything...", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    proc_tunnel.terminate()
    proc_pinggy.terminate()
    print("\n[*] Stopped.")
