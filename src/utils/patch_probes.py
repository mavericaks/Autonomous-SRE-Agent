import json
import paramiko

with open('h:\\Kolla-Ansible\\ds.json', 'r') as f:
    ds = json.load(f)

for container in ds['spec']['template']['spec']['containers']:
    if container['name'] == 'calico-node':
        # Remove bird-live and bird-ready from probes
        if 'livenessProbe' in container:
            cmd = container['livenessProbe']['exec']['command']
            if '-bird-live' in cmd:
                cmd.remove('-bird-live')
        if 'readinessProbe' in container:
            cmd = container['readinessProbe']['exec']['command']
            if '-bird-ready' in cmd:
                cmd.remove('-bird-ready')

with open('h:\\Kolla-Ansible\\ds_modified.json', 'w') as f:
    json.dump(ds, f)

def run_on_controller():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')
    
    sftp = ssh.open_sftp()
    sftp.put('h:\\Kolla-Ansible\\ds_modified.json', '/tmp/ds_modified.json')
    sftp.close()
    
    cmd = "ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 \"cat > /tmp/ds_modified.json\" < /tmp/ds_modified.json"
    ssh.exec_command(cmd)
    
    time.sleep(2)
    cmd2 = "ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@192.168.137.229 \"kubectl apply -f /tmp/ds_modified.json\""
    stdin, stdout, stderr = ssh.exec_command(cmd2)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

import time
run_on_controller()
