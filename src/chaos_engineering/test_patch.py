import sys
import base64
import subprocess

def k8s_run(cmd):
    """Run a kubectl command on the K8s master node safely using base64 via double-hop SSH."""
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
    # Decode and execute the command on the target node
    remote_sh = f"echo {b64_cmd} | base64 -d | bash"
    full = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 \"sudo ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 '{remote_sh}'\""
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() + "\n" + r.stderr.strip()
    except Exception as e:
        return str(e)

patch_cmd = """kubectl patch deployment video-streaming-server -p '{"spec": {"template": {"spec": {"containers": [{"name": "nginx-rtmp", "command": ["sh", "-c", "exit 1"]}]}}}}'"""
print("RUNNING PATCH:")
print(k8s_run(patch_cmd))

print("\nCHECKING PODS:")
print(k8s_run("kubectl get pods"))
