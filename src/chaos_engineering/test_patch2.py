import sys, base64, subprocess

def k8s_run(cmd):
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
    remote_sh = f"echo {b64_cmd} | base64 -d | bash"
    full = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 \"sudo ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74 '{remote_sh}'\""
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=20)
    return r.stdout.strip() + "\n" + r.stderr.strip()

patch_cmd = """kubectl patch deployment video-streaming-server -p '{"spec": {"strategy": {"type": "Recreate", "rollingUpdate": null}, "template": {"spec": {"containers": [{"name": "nginx-rtmp", "command": ["sh", "-c", "exit 1"]}]}}}}'"""
print("PATCH RESULT:")
print(k8s_run(patch_cmd))

# Also trigger undo immediately so it doesn't break the environment
print("UNDO:")
print(k8s_run("kubectl rollout undo deployment video-streaming-server"))
