import base64, subprocess

cmd = """
# Remove bad flag
sudo sed -i '/--experimental-bbolt-freelist-type/d' /etc/kubernetes/manifests/etcd.yaml

# Stop Kubelet to ensure no etcd is running
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

# Download etcd release to get etcdutl
wget -q https://github.com/etcd-io/etcd/releases/download/v3.5.16/etcd-v3.5.16-linux-amd64.tar.gz -O /tmp/etcd.tar.gz
tar -xzf /tmp/etcd.tar.gz -C /tmp/
sudo cp /tmp/etcd-v3.5.16-linux-amd64/etcdutl /usr/local/bin/

# Defrag the database to fix bbolt corruption
sudo etcdutl defrag --data-dir /var/lib/etcd

# Start kubelet again
sudo systemctl start kubelet
"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True)
print(r.stdout.strip() + r.stderr.strip())
