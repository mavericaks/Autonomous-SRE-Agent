import paramiko
import time

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to 10.10.10.10...")
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD)

print("Executing fix...")
stdin, stdout, stderr = ssh.exec_command('sudo rm -f /etc/resolv.conf && echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf', get_pty=True)
stdin.write('<REDACTED>
')
stdin.flush()
time.sleep(2)

print("Output:")
print(stdout.read().decode())
print(stderr.read().decode())

print("Testing DNS...")
stdin, stdout, stderr = ssh.exec_command('curl -s -w "/nHTTP_STATUS:%{http_code}/n" --connect-timeout 5 https://api.cerebras.ai/v1/models')
print(stdout.read().decode())
ssh.close()
print("Done.")
