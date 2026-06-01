import base64, subprocess

cmd = """
sudo chmod +x /tmp/etcdutl
sudo systemctl stop kubelet
sudo crictl stop $(sudo crictl ps -a --name etcd -q) || true

sudo mv /var/lib/etcd/member/snap/db /var/lib/etcd/member/snap/db.corrupt
sudo /tmp/etcdutl defrag --data-dir /var/lib/etcd

sudo chown -R root:root /var/lib/etcd
sudo systemctl start kubelet
"""

b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
remote_sh = f"echo {b64_cmd} | base64 -d | bash"
full = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 kolla@10.10.10.10 "sudo -n ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74 \'{remote_sh}\'"'
r = subprocess.run(full, shell=True, capture_output=True, text=True)
print(r.stdout.strip() + r.stderr.strip())
