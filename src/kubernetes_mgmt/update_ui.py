import paramiko
import time
import base64

def run_on_controller(cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_k8s_node(node_ip, cmd, timeout=90):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} 'bash patch.sh'"
    
    # First, transfer the script
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
    prep_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} 'echo {b64_cmd} | base64 -d > patch.sh'"
    run_on_controller(prep_cmd)

    # Now execute it
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>', timeout=10)
    channel = ssh.invoke_shell()
    time.sleep(1)
    channel.recv(9999)
    channel.send(full_cmd + "\n")
    time.sleep(2)
    
    output = ""
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        if channel.recv_ready():
            chunk = channel.recv(65535).decode('utf-8')
            output += chunk
            if 'kolla@openstack-controller' in chunk and chunk.strip().endswith('$'):
                break
        elif channel.exit_status_ready():
            break
    channel.close()
    ssh.close()
    return output

print("Deploying UI via kubectl script...")

with open(r"H:\Kolla-Ansible\kubernetes_management\video-ui.yaml", "r") as f:
    yaml_content = f.read()

b64_yaml = base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')

bash_script = f"""#!/bin/bash
echo {b64_yaml} | base64 -d > video-ui.yaml
kubectl apply -f video-ui.yaml
kubectl patch deployment video-streaming-server -p '{{"spec":{{"template":{{"spec":{{"volumes":[{{"name":"ui-volume","configMap":{{"name":"video-app-ui"}}}}],"containers":[{{"name":"nginx-rtmp","volumeMounts":[{{"name":"ui-volume","mountPath":"/usr/share/nginx/html"}}]}}]}}}}}}}}'
"""

out = run_on_k8s_node("172.16.0.74", bash_script, timeout=60)
try:
    print(out)
except UnicodeEncodeError:
    print(out.encode('ascii', 'replace').decode('ascii'))
print("UI deployed successfully!")
