#!/bin/bash
echo "kolla" | sudo -S bash -c 'rm -f /etc/resolv.conf && echo "nameserver 8.8.8.8" > /etc/resolv.conf'
curl -s -w "\nHTTP_STATUS:%{http_code}\n" --connect-timeout 5 https://api.cerebras.ai/v1/models
