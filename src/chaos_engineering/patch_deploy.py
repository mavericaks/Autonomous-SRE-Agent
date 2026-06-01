import base64, subprocess

patch_cmd = """kubectl patch deployment video-streaming-server -p '{"spec":{"template":{"spec":{"volumes":[{"name":"html-vol","configMap":{"name":"video-streaming-html"}}],"containers":[{"name":"nginx-rtmp","volumeMounts":[{"name":"html-vol","mountPath":"/usr/share/nginx/html"}]}]}}}}'"""

b64 = base64.b64encode(patch_cmd.encode()).decode()
remote_sh = f"echo {b64} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
print(f"stdout: {r.stdout.strip()}")
print(f"stderr: {r.stderr.strip()}")
print(f"exit: {r.returncode}")
