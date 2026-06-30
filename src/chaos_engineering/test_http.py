import base64, subprocess

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



cmd = """printf 'GET / HTTP/1.0/r/nHost: 172.16.0.146/r/n/r/n' | nc -w 5 172.16.0.146 30080 | head -5"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 bash -c \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=15)
print(f"Exit: {r.returncode}")
print(f"Stdout: {r.stdout.strip()}")
print(f"Stderr: {r.stderr.strip()}")
