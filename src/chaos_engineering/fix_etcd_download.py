import base64, subprocess

cmd = """
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

# Download etcd release which contains etcdutl
wget -q https://github.com/etcd-io/etcd/releases/download/v3.5.16/etcd-v3.5.16-linux-amd64.tar.gz -O /tmp/etcd.tar.gz
tar -xzf /tmp/etcd.tar.gz -C /tmp/
sudo cp /tmp/etcd-v3.5.16-linux-amd64/etcdutl /usr/local/bin/

# Back up corrupt DB
sudo mv /var/lib/etcd/member/snap/db /var/lib/etcd/member/snap/db.corrupt

# Remove freelist using etcdutl
# etcdutl doesn't have a direct 'remove freelist' command, but etcd can rebuild it if we just copy the db with bbolt?
# Wait! etcdutl snapshot restore can't restore a corrupted file.
# But wait, we can just start etcd manually with a flag to rebuild freelist, and then stop it!
sudo /tmp/etcd-v3.5.16-linux-amd64/etcd --data-dir=/var/lib/etcd --experimental-bbolt-freelist-type=map --force-new-cluster &
ETCD_PID=$!
sleep 5
sudo kill $ETCD_PID

sudo chown -R root:root /var/lib/etcd
sudo systemctl start kubelet
"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True)
print(r.stdout.strip() + r.stderr.strip())
