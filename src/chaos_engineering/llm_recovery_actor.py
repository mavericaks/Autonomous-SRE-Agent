import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CONTROLLER_IP, username='kolla', password=SSH_PASSWORD, timeout=10)

sftp = ssh.open_sftp()
sftp.get('/opt/ai-sre-agent/main.py', 'main_tmp.py')

with open('main_tmp.py', 'r') as f:
    content = f.read()

# The prompt replacement text
rca_prompt = '''f"""The following alert has fired: {alert_text}

You are an Application-Centric Autonomous SRE Agent.
You MUST use your tools to perform a deep Root Cause Analysis across all 3 layers (Kubernetes App, OpenStack Infrastructure, Mist Network) to find the exact reason for this alert and execute remediation.

Format your FINAL response EXACTLY as follows (Do not deviate):
[AI-RCA] Symptom Detected: <Briefly state what the alert is>
[AI-RCA] Layer 1 (App/K8s): <What you found in K8s API>
[AI-RCA] Layer 2 (IaaS/OS): <What you found in OpenStack Hypervisor/Network>
[AI-RCA] Root Cause Isolated: <The mathematical/logical link between the layers causing the fault>
[AI-RCA] Recovery Strategy: <What remediation script/action you executed>
"""'''

# We need to replace all instances of:
# prompt = (
#    f"The following ... alert ... fired. Investigate the root cause "
#    f"and take autonomous remediation action.\n\n{alert_text}"
# )
# Or similar in the code.

import re

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



# Find the prompt block in k8s_alert_poller
content = re.sub(
    r'prompt\s*=\s*\(\s*f"The following Kubernetes alert.*?\{alert_text\}"\s*\)',
    f'prompt = {rca_prompt}',
    content,
    flags=re.DOTALL
)

# Find the prompt block in mist_alarm_poller
content = re.sub(
    r'prompt\s*=\s*\(\s*f"The following Juniper Mist network alarm.*?\{alert_text\}"\s*\)',
    f'prompt = {rca_prompt}',
    content,
    flags=re.DOTALL
)

# Find the prompt block in receive_alert
content = re.sub(
    r'prompt\s*=\s*\(\s*f"The following Prometheus alert.*?\{alert_text\}"\s*\)',
    f'prompt = {rca_prompt}',
    content,
    flags=re.DOTALL
)

with open('main_tmp.py', 'w') as f:
    f.write(content)

sftp.put('main_tmp.py', '/tmp/main.py')
ssh.exec_command('sudo mv /tmp/main.py /opt/ai-sre-agent/main.py && sudo chown kolla:kolla /opt/ai-sre-agent/main.py')
ssh.exec_command('sudo systemctl restart ai-sre-agent')

sftp.close()
ssh.close()
print("AI Agent successfully updated with Strict RCA Prompts and restarted.")
