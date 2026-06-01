import paramiko
import time

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
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ~/.ssh/k8s_rsa ubuntu@{node_ip} '{cmd}'"
    
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

print("Deploying Video Streaming App to K8s...")

yaml_content = """cat << 'EOF' > video-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: video-streaming-server
  labels:
    app: video-stream
spec:
  replicas: 2
  selector:
    matchLabels:
      app: video-stream
  template:
    metadata:
      labels:
        app: video-stream
    spec:
      containers:
      - name: nginx-rtmp
        image: nginx
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 1935
          name: rtmp
        - containerPort: 80
          name: http
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 800m
            memory: 1024Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: video-encoder-worker
  labels:
    app: video-encoder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: video-encoder
  template:
    metadata:
      labels:
        app: video-encoder
    spec:
      containers:
      - name: cpu-stress
        image: polinux/stress
        imagePullPolicy: IfNotPresent
        args: ["stress", "--cpu", "1", "--vm", "1", "--vm-bytes", "128M"]
        resources:
          requests:
            cpu: 500m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: video-streaming-svc
spec:
  type: NodePort
  selector:
    app: video-stream
  ports:
    - port: 80
      name: http
      targetPort: 80
      nodePort: 30080
    - port: 1935
      name: rtmp
      targetPort: 1935
      nodePort: 31935
EOF
kubectl apply -f video-app.yaml
"""

out = run_on_k8s_node("172.16.0.74", yaml_content, timeout=120)
print(out)

print("Checking deployment status...")
time.sleep(5)
status = run_on_k8s_node("172.16.0.74", "kubectl get pods,svc", timeout=30)
print(status)
