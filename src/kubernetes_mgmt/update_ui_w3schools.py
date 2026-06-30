import paramiko
import time
import base64

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



def run_on_controller(cmd, timeout=30):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8').strip()
    ssh.close()
    return out

def run_on_k8s_node(node_ip, cmd, timeout=90):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} 'bash patch.sh'"
    
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode('utf-8')
    prep_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} 'echo {b64_cmd} | base64 -d > patch.sh'"
    run_on_controller(prep_cmd)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)
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

yaml_content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: video-app-ui
data:
  index.html: |
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI-SRE Live Video Stream</title>
        <style>
            body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
            .header { text-align: center; margin-bottom: 20px; }
            .header h1 { margin: 0; color: #38bdf8; font-size: 2.5rem; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5); }
            .header p { margin: 5px 0 0; color: #94a3b8; font-size: 1.1rem; }
            .video-container { width: 90%; max-width: 900px; aspect-ratio: 16/9; background-color: #000; border: 1px solid #334155; border-radius: 12px; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
            .live-badge { position: absolute; top: 20px; left: 20px; background: #ef4444; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; letter-spacing: 1px; animation: pulse 2s infinite; z-index: 10; }
            @keyframes pulse { 0% { opacity: 1; box-shadow: 0 0 10px #ef4444; } 50% { opacity: 0.5; box-shadow: none; } 100% { opacity: 1; box-shadow: 0 0 10px #ef4444; } }
            .controls { width: 90%; max-width: 900px; display: flex; justify-content: space-between; margin-top: 20px; padding: 20px; background: #1e293b; border-radius: 12px; box-sizing: border-box; }
            .stat { color: #cbd5e1; font-size: 1rem; }
            .stat span { font-weight: bold; color: #10b981; margin-left: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>AI-SRE Demonstration Platform</h1>
            <p>Live Kubernetes Video Streaming Target</p>
        </div>
        <div class="video-container">
            <div class="live-badge">LIVE</div>
            <video controls autoplay loop muted style="width: 100%; height: 100%; object-fit: cover;">
                <source src="https://www.w3schools.com/html/mov_bbb.mp4" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        <div class="controls">
            <div class="stat">Status: <span>Optimal</span></div>
            <div class="stat">Resolution: <span>1080p60</span></div>
            <div class="stat">Latency: <span>2.4 ms</span></div>
            <div class="stat">Backend: <span>Kubernetes</span></div>
        </div>
    </body>
    </html>
"""

print("Deploying updated UI and forcing pod restart...")

b64_yaml = base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')

bash_script = f"""#!/bin/bash
echo {b64_yaml} | base64 -d > video-ui.yaml
kubectl apply -f video-ui.yaml
kubectl rollout restart deployment video-streaming-server
"""

out = run_on_k8s_node("172.16.0.74", bash_script, timeout=60)
try:
    print(out)
except UnicodeEncodeError:
    print(out.encode('ascii', 'replace').decode('ascii'))
print("UI deployed successfully!")
