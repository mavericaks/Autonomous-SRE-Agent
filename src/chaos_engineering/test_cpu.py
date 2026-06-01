import base64, subprocess, time

def k8s_run(cmd):
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
    remote_sh = f"echo {b64_cmd} | base64 -d | bash"
    full = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
    r = subprocess.run(full, shell=True, capture_output=True, text=True)
    return r.stdout.strip() + r.stderr.strip()

print("Waiting for K8s API...")
for _ in range(30):
    out = k8s_run("kubectl get nodes")
    if "NAME" in out and "master" in out:
        print("API is UP!")
        print(out)
        print("Checking pods...")
        print(k8s_run("kubectl get pods -A"))
        break
    else:
        print("Still waiting... Output:", out)
    time.sleep(10)
