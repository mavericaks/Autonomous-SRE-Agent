import base64, subprocess, sys

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



# Read HTML
with open(os.path.join(BASE_DIR, "\src\chaos_engineering\streaming_index.html"), "r", encoding="utf-8") as f:
    html = f.read()

b64 = base64.b64encode(html.encode()).decode()
CHUNK = 4000
chunks = [b64[i:i+CHUNK] for i in range(0, len(b64), CHUNK)]
print(f"HTML: {len(html)} bytes, {len(chunks)} chunks")

def k8s_run(cmd):
    full = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{cmd}\'"'
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

# Transfer file
print("[1] Transferring HTML...")
k8s_run("rm -f /tmp/index.html.b64")
for i, chunk in enumerate(chunks):
    _, e, c = k8s_run(f"echo -n {chunk} >> /tmp/index.html.b64")
    if c != 0: print(f"  FAIL chunk {i}: {e}"); sys.exit(1)
    print(f"  Chunk {i+1}/{len(chunks)} OK")

k8s_run("base64 -d /tmp/index.html.b64 > /tmp/index.html")

# Update ConfigMap
print("[2] Updating ConfigMap...")
k8s_run("kubectl delete configmap video-streaming-html --ignore-not-found")
out, err, _ = k8s_run("kubectl create configmap video-streaming-html --from-file=index.html=/tmp/index.html")
print(f"  {out} {err}")

# Restart pods to pick up new ConfigMap
print("[3] Restarting pods...")
b64cmd = base64.b64encode(b"kubectl rollout restart deployment/video-streaming-server").decode()
remote = f"echo {b64cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
print(f"  {r.stdout.strip()} {r.stderr.strip()}")

print("\n[DONE] Live video feed deployed! Refresh your browser.")
