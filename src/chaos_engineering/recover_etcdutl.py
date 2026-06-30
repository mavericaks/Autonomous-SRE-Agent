import paramiko, base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='123')

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@172.16.0.74"

script = """
set -e
systemctl stop kubelet
crictl stop $(crictl ps -a --name etcd -q) || true

# Restore using etcdutl
ctr -n k8s.io run --rm \
    --mount type=bind,src=/var/lib/etcd,dst=/var/lib/etcd,options=rbind:rw \
    registry.k8s.io/etcd:3.5.16-0 etcd-restore \
    etcdutl snapshot restore /tmp/db.bak --data-dir /var/lib/etcd/new-member

rm -rf /var/lib/etcd/member
mv /var/lib/etcd/new-member /var/lib/etcd/member
chown -R root:root /var/lib/etcd/member

systemctl start kubelet
"""

b64_script = base64.b64encode(script.encode('utf-8')).decode('utf-8')
cmd = f"{ssh_inner} 'echo {b64_script} | base64 -d | sudo bash'"

print("Running etcdutl snapshot restore...")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
print(stdout.read().decode('utf-8', 'ignore'))
print("STDERR:")
print(stderr.read().decode('utf-8', 'ignore'))

ssh.close()
print("Done.")
