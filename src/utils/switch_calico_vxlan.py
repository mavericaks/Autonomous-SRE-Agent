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

def run_on_node(ip, cmd):
    router_id = run_on_controller("source /etc/kolla/admin-openrc.sh && openstack router show router1 -c id -f value").strip()
    full_cmd = f"sudo ip netns exec qrouter-{router_id} ssh -o StrictHostKeyChecking=no -i ~/.ssh/k8s_rsa ubuntu@{ip} \"{cmd}\""
    return run_on_controller(full_cmd)

print("Patching calico-config ConfigMap...")
run_on_node("172.16.0.74", "kubectl patch configmap calico-config -n kube-system -p '{\\\"data\\\":{\\\"calico_backend\\\":\\\"vxlan\\\"}}'")

print("Patching default-ipv4-ippool IPPool...")
run_on_node("172.16.0.74", "kubectl patch ippool default-ipv4-ippool --type=merge -p '{\\\"spec\\\":{\\\"ipipMode\\\":\\\"Never\\\",\\\"vxlanMode\\\":\\\"Always\\\"}}'")

print("Deleting Calico pods to force restart...")
run_on_node("172.16.0.74", "kubectl delete pod -n kube-system -l k8s-app=calico-node")
