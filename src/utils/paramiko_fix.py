import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to 10.10.10.10...")
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')

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
stdin, stdout, stderr = ssh.exec_command('curl -s -w "\\nHTTP_STATUS:%{http_code}\\n" --connect-timeout 5 https://api.cerebras.ai/v1/models')
print(stdout.read().decode())
ssh.close()
print("Done.")
