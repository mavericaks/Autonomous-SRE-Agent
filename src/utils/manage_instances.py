import paramiko
import time
import sys

ip = '10.10.10.10'
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print(f"Connecting to {ip}...")
    ssh.connect(ip, username='kolla', password='123', timeout=10)
    
    def run_cmd(cmd):
        print(f"Executing: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        return out
        
    print("Checking OpenStack Instances...")
    out = run_cmd('source /etc/kolla/admin-openrc.sh && openstack server list -f value')
    
    lines = out.strip().split('\n')
    instances = []
    for line in lines:
        if not line.strip(): continue
        parts = line.strip().split()
        inst_id = parts[0]
        name = parts[1]
        status = parts[2]
        networks = line.split('Networks=')[-1] if 'Networks=' in line else line
        # just find the floating ip (192.168.137.x)
        fip = None
        for p in line.replace(',', ' ').split():
            if p.startswith('192.168.137.'):
                fip = p
                
        instances.append((inst_id, name, status, fip))
        print(f"Instance: {name} ({inst_id}) - Status: {status} - FIP: {fip}")
        
        if status == 'SHUTOFF':
            print(f"Starting instance {name}...")
            run_cmd(f'source /etc/kolla/admin-openrc.sh && openstack server start {inst_id}')
                
    time.sleep(15)
    print("Checking Status After Start...")
    print(run_cmd('source /etc/kolla/admin-openrc.sh && openstack server list'))

    print("\nChecking Internet Connectivity on Instances...")
    for inst_id, name, status, fip in instances:
        if fip:
            # wait a bit for ssh to be ready
            print(f"Pinging 8.8.8.8 from {name} ({fip})...")
            check_cmd = f"ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@{fip} 'ping -c 1 8.8.8.8'"
            out = run_cmd(check_cmd)
            if '1 received' in out or 'bytes from 8.8.8.8' in out:
                print(f"{name} internet OK")
            else:
                print(f"{name} internet FAILED")
                print("Output:", out)
        else:
            print(f"No floating IP for {name}")

    ssh.close()
except Exception as e:
    print(f"Failed to connect or run commands: {e}")

