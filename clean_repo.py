import os
import re

TARGET_DIR = r"h:\Kolla-Ansible"

# Secrets to scrub
SECRETS = {
    # Mist Token
    r"<REDACTED_MIST_TOKEN>": "<REDACTED_MIST_TOKEN>",
    # OpenStack Password
    r"<REDACTED_OS_PASSWORD>": "<REDACTED_OS_PASSWORD>",
    # Hardcoded plain passwords
    r"password='<REDACTED>'": "password='<REDACTED>'",
    r"password='<REDACTED>'": "password='<REDACTED>'",
    r"password=\"123\"": "password=\"<REDACTED>\"",
    r"password=\"kolla\"": "password=\"<REDACTED>\"",
    r"stdin.write\('123\\n'\)": "stdin.write('<REDACTED>\\n')",
    r"stdin.write\(\"123\\n\"\)": "stdin.write(\"<REDACTED>\\n\")",
    r"stdin.write\('kolla\\n'\)": "stdin.write('<REDACTED>\\n')",
    r"stdin.write\(\"kolla\\n\"\)": "stdin.write(\"<REDACTED>\\n\")",
    # Specific command lines with passwords
    r"sudo -S.*?\n.*?123": "sudo -S ... <REDACTED>",
    # API key from Groq
    r"gsk_[a-zA-Z0-9]{40,}": "<REDACTED_GROQ_API_KEY>"
}

def scrub_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return # Skip binary or unreadable files

    original = content
    for pattern, replacement in SECRETS.items():
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Scrubbed secrets in {filepath}")

def main():
    for root, dirs, files in os.walk(TARGET_DIR):
        if '.git' in root or '__pycache__' in root or 'etcd-v3.5.16' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.sh', '.yml', '.yaml', '.ps1', '.json', '.md', '.txt', '.env', '.example')):
                scrub_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
