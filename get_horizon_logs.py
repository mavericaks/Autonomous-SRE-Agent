import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')

stdin, stdout, stderr = ssh.exec_command('sudo docker logs --tail 100 horizon', get_pty=True)
stdin.write('<REDACTED>
')
stdin.flush()
time.sleep(2)
out = stdout.read().decode()
print(out)
ssh.close()
