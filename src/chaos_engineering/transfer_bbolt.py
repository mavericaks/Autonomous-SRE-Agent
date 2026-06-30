import paramiko, urllib.request, os

print("Downloading bbolt on Windows host...")
url = "https://github.com/etcd-io/bbolt/releases/download/v1.3.11/bbolt-linux-amd64"
bbolt_path = "H:\\Kolla-Ansible\\src\\chaos_engineering\\bbolt"
urllib.request.urlretrieve(url, bbolt_path)

print("Connecting to Kolla controller...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='123')

print("Transferring bbolt to Kolla controller...")
sftp = ssh.open_sftp()
sftp.put(bbolt_path, '/tmp/bbolt')
sftp.chmod('/tmp/bbolt', 0o755)
sftp.close()

print("Copying bbolt to k8s master via scp...")
cmd_scp = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 scp -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa /tmp/bbolt ubuntu@172.16.0.74:/tmp/bbolt"
ssh.exec_command(cmd_scp)

ssh.close()
print("Transfer complete.")
