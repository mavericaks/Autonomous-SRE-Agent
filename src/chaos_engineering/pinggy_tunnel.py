import subprocess
import re
import threading
import time

def run_pinggy():
    print("Starting Pinggy tunnel...")
    process = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-p", "443", "-R0:localhost:30080", "a.pinggy.io"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    def print_output():
        for line in process.stdout:
            print(line, end="")
            if "pinggy.link" in line:
                url_match = re.search(r"https://[a-zA-Z0-9-]+\.pinggy\.link", line)
                if url_match:
                    print(f"\n[PINGGY URL FOUND]: {url_match.group(0)}")
                    
    t = threading.Thread(target=print_output, daemon=True)
    t.start()
    
    while True:
        time.sleep(1)
        if process.poll() is not None:
            print("Pinggy process exited unexpectedly.")
            break

if __name__ == "__main__":
    run_pinggy()
