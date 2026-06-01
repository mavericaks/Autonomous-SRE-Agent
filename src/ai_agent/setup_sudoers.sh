#!/bin/bash
echo 'kolla ALL=(ALL) NOPASSWD: /usr/sbin/ip' > /etc/sudoers.d/ai-sre-agent
chmod 440 /etc/sudoers.d/ai-sre-agent
echo "Sudoers configured"
