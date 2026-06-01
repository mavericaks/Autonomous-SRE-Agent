import base64, subprocess

cmd = """printf 'GET / HTTP/1.0\\r\\nHost: 172.16.0.146\\r\\n\\r\\n' | nc -w 5 172.16.0.146 30080 | head -5"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 bash -c \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=15)
print(f"Exit: {r.returncode}")
print(f"Stdout: {r.stdout.strip()}")
print(f"Stderr: {r.stderr.strip()}")
