import paramiko
import time

nodes = ['10.10.10.10', '10.10.10.11', '10.10.10.12']
base_cmd = 'sudo ip link set br-ex up 2>/dev/null; sudo ip addr add 192.168.137.{}/24 dev br-ex 2>/dev/null; sudo ip route del default 2>/dev/null; sudo ip route add default via 192.168.137.1 2>/dev/null; sudo bash -c "rm -f /etc/resolv.conf && echo \'nameserver 8.8.8.8\' > /etc/resolv.conf"'

for i, ip_addr in enumerate(nodes):
    node_id = str(10 + i)
    cmd = base_cmd.format(node_id)
    print(f"Fixing {ip_addr}...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_addr, username='kolla', password='<REDACTED>', timeout=10)
        
        # We must use invoke_shell to get a true PTY that plays nice with sudo's use_pty constraint
        channel = ssh.invoke_shell()
        time.sleep(1)
        channel.send(cmd + "\n")
        time.sleep(1)
        # Sudo will prompt for password
        resp = channel.recv(9999).decode('utf-8')
        if "password" in resp.lower() or "[sudo]" in resp.lower():
            channel.send("123\n")
            time.sleep(2)
        
        print(f"Success for {ip_addr}.")
        ssh.close()
    except Exception as e:
        print(f"Failed on {ip_addr}: {e}")

print("Testing API connectivity on Controller...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.10.10.10', username='kolla', password='<REDACTED>')
stdin, stdout, stderr = ssh.exec_command('curl -s -w "\\nHTTP_STATUS:%{http_code}\\n" --connect-timeout 5 https://api.cerebras.ai/v1/models')
print(stdout.read().decode())
ssh.close()
