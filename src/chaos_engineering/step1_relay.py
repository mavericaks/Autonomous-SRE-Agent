import base64, subprocess, time

relay_code = r"""
import socket, threading, subprocess, sys
def handle(c):
    try:
        p = subprocess.Popen(['sudo','-n','ip','netns','exec','qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03','nc','172.16.0.146','30080'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def c2r():
            try:
                while True:
                    d = c.recv(4096)
                    if not d: break
                    p.stdin.write(d); p.stdin.flush()
            except: pass
            finally:
                try: p.stdin.close()
                except: pass
        def r2c():
            try:
                while True:
                    d = p.stdout.read(4096)
                    if not d: break
                    c.sendall(d)
            except: pass
            finally: c.close()
        t1=threading.Thread(target=c2r,daemon=True);t1.start()
        t2=threading.Thread(target=r2c,daemon=True);t2.start()
        t2.join()
    except: pass
    finally:
        c.close()
        try: p.terminate()
        except: pass
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
s.bind(('0.0.0.0',8888)); s.listen(10)
print('RELAY_READY'); sys.stdout.flush()
while True:
    c,a=s.accept()
    threading.Thread(target=handle,args=(c,),daemon=True).start()
"""

b64 = base64.b64encode(relay_code.encode()).decode()

# Deploy the relay script
cmd1 = f'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "echo {b64} | base64 -d > /tmp/tcp_relay.py"'
r1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, timeout=15)
print(f"Deploy script: exit={r1.returncode}")

# Kill old instances
cmd2 = 'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "pkill -f tcp_relay 2>/dev/null; sleep 1"'
subprocess.run(cmd2, shell=True, capture_output=True, timeout=15)

# Start as background process
cmd3 = 'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "nohup python3 /tmp/tcp_relay.py > /tmp/tcp_relay.log 2>&1 &"'
r3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True, timeout=15)
print(f"Start relay: exit={r3.returncode}")

time.sleep(3)

# Check if running
cmd4 = 'ssh -o StrictHostKeyChecking=no kolla@10.10.10.10 "cat /tmp/tcp_relay.log && ps aux | grep tcp_relay | grep -v grep"'
r4 = subprocess.run(cmd4, shell=True, capture_output=True, text=True, timeout=15)
print(f"Status: {r4.stdout.strip()}")
print(f"Errors: {r4.stderr.strip()}")
