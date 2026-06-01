import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')

stdin, stdout, stderr = ssh.exec_command('sudo -S docker restart horizon', get_pty=True)
stdin.write('<REDACTED>
')
stdin.flush()
time.sleep(3)
out = stdout.read().decode('utf-8', 'ignore')
print("HORIZON RESTART:")
print(out)

ssh.close()
