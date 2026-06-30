#!/bin/bash
# Deploy AI SRE Agent to the OpenStack Controller node
# This script sets up the Python venv, installs dependencies, and starts the agent.
set -e

AGENT_DIR="/opt/ai-sre-agent"
echo "=== AI SRE Agent Deployment ==="

# Create directory
sudo mkdir -p $AGENT_DIR
sudo chown kolla:kolla $AGENT_DIR

# Copy agent files
cp -r /tmp/ai-agent/* $AGENT_DIR/

# Create Python virtual environment
echo "[1/4] Creating Python virtual environment..."
python3 -m venv $AGENT_DIR/venv
source $AGENT_DIR/venv/bin/activate

# Install dependencies
echo "[2/4] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r $AGENT_DIR/requirements.txt

# Create .env from example if not exists
if [ ! -f $AGENT_DIR/.env ]; then
    cp $AGENT_DIR/.env.example $AGENT_DIR/.env
    echo "[!] Created .env from template - you must set OPENAI_API_KEY!"
fi

# Create systemd service
echo "[3/4] Creating systemd service..."
sudo tee /etc/systemd/system/ai-sre-agent.service > /dev/null << 'SVCEOF'
[Unit]
Description=AI SRE Agent - Autonomous Degradation Detection
After=network.target docker.service

[Service]
Type=simple
User=kolla
Group=kolla
WorkingDirectory=/opt/ai-sre-agent
Environment=PATH=/opt/ai-sre-agent/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/ai-sre-agent/venv/bin/python /opt/ai-sre-agent/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

# Enable and start the service
echo "[4/4] Starting AI SRE Agent service..."
sudo systemctl daemon-reload
sudo systemctl enable ai-sre-agent
sudo systemctl restart ai-sre-agent

echo "=== Deployment complete! ==="
echo "Agent listening on port 9999"
echo "Health check: curl http://10.10.10.10:9999/health"
echo "Test endpoint: curl -X POST http://10.10.10.10:9999/test -H 'Content-Type: application/json' -d '{\"alert\": \"Test alert\"}'"
