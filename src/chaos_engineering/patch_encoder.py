import paramiko, base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='123')

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74"

patch_cmd = """kubectl patch deployment video-encoder-worker -p '{"spec": {"template": {"spec": {"containers": [{"name": "worker", "image": "registry.k8s.io/pause:3.10.1", "command": []}]}}}}'"""
b64_cmd = base64.b64encode(patch_cmd.encode('utf-8')).decode('utf-8')

cmd = f"{ssh_inner} 'echo {b64_cmd} | base64 -d | bash'"

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
ssh.close()
