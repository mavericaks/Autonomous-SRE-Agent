import base64, subprocess

cmd = """
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

sudo cp /var/lib/etcd/member/snap/db /tmp/db.bak
sudo rm -rf /var/lib/etcd/member
sudo mkdir -p /var/lib/etcd/member/snap
sudo cp /tmp/db.bak /var/lib/etcd/member/snap/db

sudo timeout 10 /tmp/etcd --data-dir /var/lib/etcd --force-new-cluster --listen-client-urls=http://127.0.0.1:23790 --advertise-client-urls=http://127.0.0.1:23790 --listen-peer-urls=http://127.0.0.1:23800 --initial-advertise-peer-urls=http://127.0.0.1:23800 --initial-cluster=default=http://127.0.0.1:23800

sudo chown -R root:root /var/lib/etcd
sudo systemctl start kubelet
"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True)
print(r.stdout.strip() + r.stderr.strip())
