import paramiko, base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='123')

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03"

print("Running etcdutl defrag on k8s master...")
script = """
set -e
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

# Restore the db if it was renamed by the previous script
if [ -f /var/lib/etcd/member/snap/db.corrupt ]; then
    sudo mv /var/lib/etcd/member/snap/db.corrupt /var/lib/etcd/member/snap/db
fi

# Defrag the database in-place
sudo /tmp/etcdutl defrag --data-dir /var/lib/etcd

sudo chown -R root:root /var/lib/etcd
sudo systemctl start kubelet
"""

b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 'echo {b64_script} | base64 -d | sudo bash'"

stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

ssh.close()
print("Done.")
