import subprocess, base64, paramiko

app_yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: video-streaming-html
data:
  index.html: "<html><body>Placeholder</body></html>"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: video-streaming-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: video-streaming
  template:
    metadata:
      labels:
        app: video-streaming
    spec:
      volumes:
      - name: html-vol
        configMap:
          name: video-streaming-html
      containers:
      - name: nginx-rtmp
        image: nginx
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
        volumeMounts:
        - name: html-vol
          mountPath: /usr/share/nginx/html

---
apiVersion: v1
kind: Service
metadata:
  name: video-streaming-svc
spec:
  type: NodePort
  selector:
    app: video-streaming
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: video-encoder-worker
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
      - name: worker
        image: busybox
        imagePullPolicy: IfNotPresent
        command: ["sleep", "3600"]
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='123')

ssh_inner = "echo '123' | sudo -S ip netns exec qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03 ssh -o StrictHostKeyChecking=no -i /home/kolla/.ssh/k8s_rsa ubuntu@172.16.0.74"

b64_yaml = base64.b64encode(app_yaml.encode('utf-8')).decode('utf-8')
cmd_deploy = f"{ssh_inner} 'echo {b64_yaml} | base64 -d > /tmp/app.yaml && kubectl apply -f /tmp/app.yaml'"

print("Deploying dummy workload resources...")
stdin, stdout, stderr = ssh.exec_command(cmd_deploy)
print(stdout.read().decode('utf-8'))

ssh.close()
print("Done recreating resources.")
