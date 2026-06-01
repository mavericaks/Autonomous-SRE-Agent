import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')

cmd = "ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 'sudo bash -c \"mv /var/lib/etcd/member/snap/*.snap /tmp/ || true\"'"
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

cmd = "ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 'sudo systemctl restart containerd kubelet'"
stdin, stdout, stderr = ssh.exec_command(cmd)

ssh.close()
