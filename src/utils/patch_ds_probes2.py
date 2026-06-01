import paramiko
import time

def run_on_controller(cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8').strip()
    err = stderr.read().decode('utf-8').strip()
    ssh.close()
    if err:
        print("ERR:", err)
    return out

patch = '[{"op": "replace", "path": "/spec/template/spec/containers/0/livenessProbe/exec/command", "value": ["/bin/calico-node", "-felix-live"]}, {"op": "replace", "path": "/spec/template/spec/containers/0/readinessProbe/exec/command", "value": ["/bin/calico-node", "-felix-ready"]}]'

cmd = f'''cat << 'EOF' > /tmp/patch.json
{patch}
EOF
kubectl patch daemonset calico-node -n kube-system --type=json --patch-file=/tmp/patch.json
'''

# Escape double quotes for the python script string
cmd_escaped = cmd.replace('"', '\\"')

ssh_cmd = f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 \"{cmd_escaped}\""
print("Patching daemonset probes...")
print(run_on_controller(ssh_cmd))
