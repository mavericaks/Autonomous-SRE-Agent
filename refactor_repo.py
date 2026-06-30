import os
import re

import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', '10.10.10.10')
COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', '10.10.10.11')
COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', '10.10.10.12')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')



TARGET_DIR = os.path.join(BASE_DIR, "-Refactored")

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original_content = content
    
    # Needs dotenv import?
    needs_dotenv = False

    # Replace H:\Kolla-Ansible with a dynamic path using BASE_DIR from env or relative
    # A lot of scripts are in src/utils or src/chaos_engineering
    if os.path.join(BASE_DIR, "") in content or os.path.join(BASE_DIR, "") in content or CONTROLLER_IP in content or "123" in content or "<REDACTED>" in content:
        # We will use dotenv
        needs_dotenv = True
        
        # Replace paths
        content = re.sub(r'r?"H://Kolla-Ansible([^"]*)"', r'os.path.join(BASE_DIR, "\1")', content)
        content = re.sub(r'r?os.path.join(BASE_DIR, "([^")]*)"', r'os.path.join(BASE_DIR, "\1")', content)
        content = re.sub(r"r?'H://Kolla-Ansible([^']*)'", r"os.path.join(BASE_DIR, '\1')", content)
        content = re.sub(r"r?os.path.join(BASE_DIR, '([^')]*)'", r"os.path.join(BASE_DIR, '\1')", content)
        
        # Clean up some double slashes from the regex replacement if they exist
        content = content.replace('//', '/')
        
        # Replace IPs
        content = re.sub(r"'10\.10\.10\.10'", "CONTROLLER_IP", content)
        content = re.sub(r'"10\.10\.10\.10"', "CONTROLLER_IP", content)
        content = re.sub(r"'10\.10\.10\.11'", "COMPUTE1_IP", content)
        content = re.sub(r'"10\.10\.10\.11"', "COMPUTE1_IP", content)
        content = re.sub(r"'10\.10\.10\.12'", "COMPUTE2_IP", content)
        content = re.sub(r'"10\.10\.10\.12"', "COMPUTE2_IP", content)
        
        # Replace Passwords
        content = re.sub(r"password=SSH_PASSWORD", "password=SSH_PASSWORD", content)
        content = re.sub(r'password=SSH_PASSWORD', "password=SSH_PASSWORD", content)
        content = re.sub(r"password=SSH_PASSWORD", "password=SSH_PASSWORD", content)
        content = re.sub(r'password=SSH_PASSWORD', "password=SSH_PASSWORD", content)

    if needs_dotenv and filepath.endswith('.py') and content != original_content:
        # Add imports if they don't exist
        imports = (
            "import os\n"
            "from dotenv import load_dotenv\n"
            "load_dotenv()\n\n"
            "BASE_DIR = os.getenv('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))\n"
            "CONTROLLER_IP = os.getenv('OPENSTACK_CONTROLLER_IP', CONTROLLER_IP)\n"
            "COMPUTE1_IP = os.getenv('OPENSTACK_COMPUTE1_IP', COMPUTE1_IP)\n"
            "COMPUTE2_IP = os.getenv('OPENSTACK_COMPUTE2_IP', COMPUTE2_IP)\n"
            "SSH_PASSWORD = os.getenv('SSH_PASSWORD', '123')\n\n"
        )
        
        # Find where to inject (after imports)
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i + 1
        
        if insert_idx == 0:
            lines.insert(0, imports)
        else:
            lines.insert(insert_idx, "\n" + imports)
            
        content = '\n'.join(lines)
        
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Refactored: {filepath}")

for root, _, files in os.walk(TARGET_DIR):
    if '.git' in root or 'venv' in root or '__pycache__' in root: continue
    for file in files:
        if file.endswith('.py'):
            refactor_file(os.path.join(root, file))

# Create .env.example
env_example = """# Autonomous SRE Agent Configuration
BASE_DIR=/path/to/repo/root
OPENSTACK_CONTROLLER_IP=10.10.10.10
OPENSTACK_COMPUTE1_IP=10.10.10.11
OPENSTACK_COMPUTE2_IP=10.10.10.12
SSH_USER=kolla
SSH_PASSWORD=your_secure_password
OPENAI_API_KEY=sk-your-openai-key
MIST_API_TOKEN=your-mist-token
"""
with open(os.path.join(TARGET_DIR, '.env.example'), 'w') as f:
    f.write(env_example)
print("Created .env.example")
