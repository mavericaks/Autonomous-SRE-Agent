import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')

cmd = "ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 'cat /home/ubuntu/video-app.yaml'"
stdin, stdout, stderr = ssh.exec_command(cmd)

print(stdout.read().decode('utf-8', 'ignore'))

ssh.close()
