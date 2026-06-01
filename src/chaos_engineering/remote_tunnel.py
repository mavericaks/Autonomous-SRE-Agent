"""
Two-hop SSH tunnel to expose K8s video streaming.

Chain:
  Windows:8888 --SSH--> OpenStack:qrouter --nc--> K8s-Master --L forward--> K8s-Worker:30080

We use SSH ProxyCommand to go through the qrouter namespace,
then SSH into K8s master (using the key on OpenStack host)
and set up a port forward to the worker node.
"""
import subprocess
import sys
import time

# The approach: 
# 1. Copy k8s_rsa key from OpenStack host to local temp
# 2. SSH to K8s master via ProxyCommand (OpenStack -> qrouter -> nc to master)
# 3. -L forward localhost:8888 -> 172.16.0.146:30080

# Step 1: Grab the SSH key
print("[1] Fetching K8s SSH key from OpenStack host...")
r = subprocess.run(
    'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "cat /home/kolla/.ssh/k8s_rsa"',
    shell=True, capture_output=True, text=True
)
if r.returncode != 0:
    print(f"Failed: {r.stderr}")
    sys.exit(1)

key_path = r"H:\Kolla-Ansible\chaos_engineering\k8s_rsa_local"
with open(key_path, "w", newline="\n") as f:
    f.write(r.stdout)
print(f"  [OK] Key saved to {key_path}")

# Fix permissions (Windows)
subprocess.run(f'icacls "{key_path}" /inheritance:r /grant:r "%USERNAME%:R"', shell=True, capture_output=True)

# Step 2: SSH with ProxyCommand through qrouter namespace
print("[2] Starting SSH tunnel: localhost:8888 -> K8s-Worker:30080")
print("    Route: Windows -> OpenStack(qrouter ns) -> K8s-Master -> Worker:30080")

proxy_cmd = "ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 nc %h %p"

tunnel_cmd = (
    f'ssh -o StrictHostKeyChecking=no '
    f'-o "ProxyCommand={proxy_cmd}" '
    f'-i "{key_path}" '
    f'-N -L 8888:172.16.0.146:30080 '
    f'ubuntu@172.16.0.74'
)

print(f"  Command: {tunnel_cmd}")
proc = subprocess.Popen(tunnel_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)

if proc.poll() is not None:
    err = proc.stderr.read().decode()
    print(f"  [FAIL] Tunnel died: {err}")
    sys.exit(1)

print("  [OK] Tunnel is running!")

# Step 3: Test
print("[3] Testing connection...")
import urllib.request
try:
    resp = urllib.request.urlopen("http://localhost:8888/", timeout=10)
    print(f"  [OK] Video streaming accessible! Status: {resp.getcode()}")
except Exception as e:
    print(f"  [WARN] Test failed: {e}")
    print("  The tunnel may still be starting up...")

print()
print("=" * 60)
print("  VIDEO STREAMING IS NOW ACCESSIBLE AT:")
print("  http://localhost:8888")
print()
print("  To access from your phone on a different network,")
print("  run this in a SEPARATE terminal:")
print("  ssh -p 443 -R0:localhost:8888 a.pinggy.io")
print("=" * 60)
print()
print("Press Ctrl+C to stop the tunnel...")

try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()
    print("\n[*] Tunnel stopped.")
