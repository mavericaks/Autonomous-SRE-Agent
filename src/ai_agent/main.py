"""
AI SRE Agent - Autonomous Performance Degradation Detection & Resolution
=========================================================================
Smart Multi-Provider Architecture:
  PRIMARY (Cerebras)  → Fast Llama 3.3 70B for routine alerts
  REASONING (Gemini)  → Deep analysis for complex cross-layer issues
  FALLBACK (OpenRouter)→ Meta-router if above providers hit limits
  BACKUP (Groq)       → Last resort safety net

  Prometheus Alertmanager --webhook--> FastAPI /alert --> Smart Router --> ReAct Agent --> Tools
"""

import os
import json
import logging
import subprocess
import datetime
import asyncio
import threading
from typing import Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

import httpx
import requests

from stgnn_mathematical_critic import STGNNCritic

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai-sre-agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
K8S_MASTER_IP = os.getenv("K8S_MASTER_IP", "172.16.0.74")
K8S_SSH_KEY = os.getenv("K8S_SSH_KEY", "/home/kolla/.ssh/k8s_rsa")
K8S_SSH_USER = os.getenv("K8S_SSH_USER", "ubuntu")
OPENSTACK_PROMETHEUS_URL = os.getenv("OPENSTACK_PROMETHEUS_URL", "http://10.10.10.200:9091")
K8S_PROMETHEUS_URL = os.getenv("K8S_PROMETHEUS_URL", "http://10.0.0.195:30090")
K8S_QROUTER_NS = os.getenv("K8S_QROUTER_NS", "qrouter-1166407d-006b-4231-8187-3ad4ac6fbb03")
K8S_ALERT_POLL_INTERVAL = int(os.getenv("K8S_ALERT_POLL_INTERVAL", "60"))

# Juniper Mist AI Configuration
MIST_API_HOST = os.getenv("MIST_API_HOST", "https://api.gc4.mist.com")
MIST_API_TOKEN = os.getenv("MIST_API_TOKEN", "")
MIST_ORG_ID = os.getenv("MIST_ORG_ID", "")
MIST_SITE_ID = os.getenv("MIST_SITE_ID", "")
MIST_POLL_INTERVAL = int(os.getenv("MIST_POLL_INTERVAL", "60"))

def mist_api(method: str, path: str, json_data: dict = None) -> dict:
    """Helper to call the Mist REST API."""
    url = f"{MIST_API_HOST}{path}"
    headers = {
        "Authorization": f"Token {MIST_API_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.request(method, url, headers=headers, json=json_data, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    except Exception as e:
        return {"error": str(e)}

# Smart routing: keywords that trigger escalation to Gemini
ESCALATION_KEYWORDS = [
    "unclear", "uncertain", "unable to determine", "complex",
    "cascading", "cross-layer", "multiple failures", "not sure",
    "needs further", "inconclusive", "could not identify",
]

# ---------------------------------------------------------------------------
# Incident Journal (in-memory, persisted to disk)
# ---------------------------------------------------------------------------
INCIDENT_LOG_FILE = "/opt/ai-sre-agent/incidents.jsonl"
incident_journal: list[dict] = []


def log_incident(alert: dict, analysis: str, actions: str):
    """Persist an incident record to disk and memory."""
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "alert": alert,
        "analysis": analysis,
        "actions_taken": actions,
    }
    incident_journal.append(record)
    try:
        os.makedirs(os.path.dirname(INCIDENT_LOG_FILE), exist_ok=True)
        with open(INCIDENT_LOG_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.warning(f"Could not persist incident: {e}")


# ---------------------------------------------------------------------------
# TOOLS — These are the "hands" the AI uses to interact with infrastructure
# ---------------------------------------------------------------------------

@tool
def run_openstack_command(command: str) -> str:
    """Execute an OpenStack CLI command on the controller node.
    The admin credentials are already sourced.
    Example: run_openstack_command("openstack server list")
    Only pass the command without 'source /etc/kolla/admin-openrc.sh'.
    """
    full_cmd = f"source /etc/kolla/admin-openrc.sh && {command}"
    logger.info(f"[TOOL] OpenStack CLI: {command}")
    try:
        result = subprocess.run(
            ["bash", "-c", full_cmd],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout + result.stderr
        logger.info(f"[TOOL] OpenStack result: {output[:500]}")
        return output[:3000]  # Cap output to fit context window
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 60 seconds."
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def run_kubectl_command(command: str) -> str:
    """Execute a kubectl command on the Kubernetes master node via SSH.
    The SSH connection goes through the Neutron router namespace.
    Example: run_kubectl_command("kubectl get pods -A")
    Only pass the kubectl command itself.
    """
    ssh_cmd = (
        f"sudo ip netns exec {K8S_QROUTER_NS} "
        f"ssh -i {K8S_SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=15 "
        f"{K8S_SSH_USER}@{K8S_MASTER_IP} '{command}'"
    )
    logger.info(f"[TOOL] kubectl: {command}")
    try:
        result = subprocess.run(
            ["bash", "-c", ssh_cmd],
            capture_output=True, text=True, timeout=45
        )
        output = result.stdout + result.stderr
        logger.info(f"[TOOL] kubectl result: {output[:500]}")
        return output[:3000]
    except subprocess.TimeoutExpired:
        return "ERROR: SSH/kubectl command timed out after 45 seconds."
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def run_shell_command(command: str) -> str:
    """Execute a shell command directly on the controller node.
    Use for diagnostic commands like checking processes, disk usage, etc.
    Example: run_shell_command("top -bn1 | head -20")
    NEVER use this for destructive operations without careful reasoning.
    """
    logger.info(f"[TOOL] Shell: {command}")
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        logger.info(f"[TOOL] Shell result: {output[:500]}")
        return output[:3000]
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 30 seconds."
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def query_prometheus(input_str: str) -> str:
    """Query a Prometheus instance for metrics data.
    Input format: 'target|promql_query'
    Where target is one of:
      - 'openstack' (queries http://10.10.10.200:9091)
      - 'k8s' (queries K8s Prometheus via qrouter namespace)
    Examples:
      - 'openstack|up'
      - 'openstack|node_cpu_seconds_total{mode="idle"}[5m]'
      - 'openstack|100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    """
    parts = input_str.split("|", 1)
    if len(parts) != 2:
        return "ERROR: Input must be 'target|promql_query'. Example: 'openstack|up'"
    target, query = parts[0].strip(), parts[1].strip()

    if target == "openstack":
        prometheus_url = OPENSTACK_PROMETHEUS_URL
    elif target == "k8s":
        # K8s Prometheus is only reachable via qrouter namespace
        cmd = (
            f"sudo ip netns exec {K8S_QROUTER_NS} "
            f"curl -s 'http://{K8S_MASTER_IP}:30090/api/v1/query?query={query}'"
        )
        logger.info(f"[TOOL] K8s Prometheus query: {query}")
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=15
            )
            return result.stdout[:3000] if result.stdout else f"ERROR: {result.stderr[:500]}"
        except Exception as e:
            return f"ERROR: {str(e)}"
    else:
        return f"ERROR: Unknown target '{target}'. Use 'openstack' or 'k8s'."

    logger.info(f"[TOOL] Prometheus query: {query} @ {prometheus_url}")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": query}
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if len(results) > 20:
                results = results[:20]
                data["data"]["result"] = results
                data["_truncated"] = True
            return json.dumps(data, indent=2)[:3000]
    except Exception as e:
        return f"ERROR querying Prometheus: {str(e)}"


# ---------------------------------------------------------------------------
# MIST AI TOOLS — Network/Device layer (Juniper Mist Cloud)
# ---------------------------------------------------------------------------

@tool
def get_mist_device_inventory(filter_type: str = "all") -> str:
    """Get the inventory and health status of all Juniper Mist-managed devices.
    Shows device name, type, model, IP, status (connected/disconnected), CPU, memory, uptime.
    filter_type can be: 'all', 'ap', 'switch', 'gateway'
    Example: get_mist_device_inventory("all")
    Example: get_mist_device_inventory("switch")
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist device inventory (filter={filter_type})")
    data = mist_api("GET", f"/api/v1/sites/{MIST_SITE_ID}/stats/devices")
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    devices = data if isinstance(data, list) else []
    if filter_type != "all":
        devices = [d for d in devices if d.get("type", "") == filter_type]
    summary = []
    for d in devices:
        status = d.get("status", "unknown")
        name = d.get("name", d.get("mac", "unnamed"))
        dtype = d.get("type", "unknown")
        model = d.get("model", "unknown")
        ip = d.get("ip", "N/A")
        cpu = d.get("cpu_stat", {}).get("cpus", {}) if isinstance(d.get("cpu_stat"), dict) else {}
        mem = d.get("memory_stat", {}) if isinstance(d.get("memory_stat"), dict) else {}
        uptime = d.get("uptime", 0)
        summary.append(
            f"  {name} | type={dtype} | model={model} | ip={ip} | status={status} "
            f"| uptime={uptime}s | mem_usage={mem.get('usage', 'N/A')}%"
        )
    header = f"Mist Devices ({len(devices)} total, filter={filter_type}):\n"
    return (header + "\n".join(summary))[:3000]


@tool
def get_mist_alarms(count: int = 20) -> str:
    """Get active (unacknowledged) alarms from Juniper Mist.
    Shows alarm type, severity, device, timestamp, and details.
    Example: get_mist_alarms(10)
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist alarms (count={count})")
    data = mist_api("GET", f"/api/v1/sites/{MIST_SITE_ID}/alarms?ack=false&limit={count}")
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    alarms = data if isinstance(data, list) else data.get("results", [])
    if not alarms:
        return "No active alarms in Mist."
    summary = []
    for a in alarms[:count]:
        summary.append(
            f"  [{a.get('severity', 'unknown')}] {a.get('type', 'unknown')} "
            f"| device={a.get('hostnames', a.get('aps', ['N/A']))} "
            f"| count={a.get('count', 1)} | timestamp={a.get('timestamp', 'N/A')}"
        )
    header = f"Mist Alarms ({len(alarms)} active):\n"
    return (header + "\n".join(summary))[:3000]


@tool
def get_mist_sle_metrics(scope: str, metric: str) -> str:
    """Get Juniper Mist Service Level Experience (SLE) metrics.
    Scope can be: 'wifi', 'wired', 'wan'
    Metric depends on scope:
      wifi: 'time-to-connect', 'coverage', 'capacity', 'throughput', 'roaming', 'ap-availability'
      wired: 'switch-throughput', 'switch-health', 'successful-connects'
      wan: 'wan-link-health', 'application-health'
    Example: get_mist_sle_metrics("wifi", "coverage")
    Example: get_mist_sle_metrics("wan", "wan-link-health")
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist SLE: scope={scope}, metric={metric}")
    path = f"/api/v1/sites/{MIST_SITE_ID}/sle/{scope}/metric/{metric}?duration=1h"
    data = mist_api("GET", path)
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    return json.dumps(data, indent=2)[:3000]


@tool
def restart_mist_device(device_id: str) -> str:
    """Restart a Juniper Mist-managed device (AP, switch, or gateway).
    You MUST first get the device_id from get_mist_device_inventory.
    WARNING: This will cause a brief service interruption for clients on this device.
    Example: restart_mist_device("00000000-0000-0000-1000-5c5b35abc123")
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist restart device: {device_id}")
    data = mist_api("POST", f"/api/v1/sites/{MIST_SITE_ID}/devices/{device_id}/restart")
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    return f"Device {device_id} restart command sent successfully."


@tool
def bounce_mist_port(device_id: str, port: str) -> str:
    """Bounce (disable then re-enable) a port on a Juniper Mist-managed switch.
    This is useful for fixing client connectivity issues or clearing stuck PoE.
    You MUST first get the device_id from get_mist_device_inventory.
    Example: bounce_mist_port("00000000-0000-0000-1000-5c5b35abc123", "ge-0/0/0")
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist bounce port: device={device_id}, port={port}")
    data = mist_api(
        "POST",
        f"/api/v1/sites/{MIST_SITE_ID}/devices/{device_id}/bounce_port",
        json_data={"ports": [port]}
    )
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    return f"Port {port} on device {device_id} bounced successfully."


@tool
def get_mist_marvis_actions(limit: int = 10) -> str:
    """Get Marvis AI-generated action recommendations from Juniper Mist.
    Marvis is Juniper's built-in AI assistant that identifies and classifies
    network issues. This returns its latest recommended actions.
    Example: get_mist_marvis_actions(5)
    """
    if not MIST_API_TOKEN:
        return "ERROR: Mist API not configured."
    logger.info(f"[TOOL] Mist Marvis actions (limit={limit})")
    data = mist_api("GET", f"/api/v1/sites/{MIST_SITE_ID}/insights/marvis?limit={limit}")
    if isinstance(data, dict) and "error" in data:
        return f"ERROR: {data['error']}"
    return json.dumps(data, indent=2)[:3000]


# ---------------------------------------------------------------------------
# LLM AGENT SETUP
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) AI agent responsible for
autonomously detecting, diagnosing, and resolving performance degradation across a
full-stack environment spanning Cloud, Edge, and Network layers.

## Environment Layout
- **Cloud Layer — OpenStack (Physical VMs):**
  - Controller: 10.10.10.10 (runs Nova scheduler, Cinder, Neutron, Prometheus, Grafana)
  - Compute1: 10.10.10.11 (runs Nova compute, VMs)
  - Compute2: 10.10.10.12 (runs Nova compute, VMs)
  - VIP: 10.10.10.200 (HAProxy for all OpenStack APIs)
  - OpenStack Prometheus: http://10.10.10.200:9091

- **Edge Layer — Kubernetes (Inside OpenStack VMs):**
  - k8s-master: 10.0.0.195 (floating IP: 192.168.137.229)
  - k8s-worker-1: 10.0.0.146 (floating IP: 192.168.137.248)
  - k8s-worker-2: 10.0.0.130 (floating IP: 192.168.137.211)
  - K8s Prometheus: http://10.0.0.195:30090

- **Network Layer — Juniper Mist AI (Physical Devices):**
  - SRX300 Firewall/Gateway
  - EX2300-C and EX4100 PoE+ Switches
  - Indoor (AP32) and Outdoor (AP64) Access Points
  - Managed via Mist Cloud API (api.gc4.mist.com)
  - Mist provides SLE (Service Level Experience) metrics for Wi-Fi, Wired, and WAN

## Your Workflow
When you receive an alert:
1. **INVESTIGATE**: Gather context using the appropriate tools for the affected layer.
   - Cloud issues → query_prometheus, run_openstack_command, run_shell_command
   - Edge issues → run_kubectl_command, query_prometheus (k8s)
   - Network issues → get_mist_alarms, get_mist_device_inventory, get_mist_sle_metrics
   - Cross-layer issues → investigate ALL relevant layers
2. **DIAGNOSE**: Reason about the root cause. Consider cross-layer cascading:
   - A Mist switch going offline can cause K8s worker node failure
   - An OpenStack network issue can degrade Mist gateway connectivity
3. **PLAN**: Formulate a specific remediation plan with exact commands.
4. **EXECUTE**: Run remediation using appropriate tools.
   - Network remediation: restart_mist_device, bounce_mist_port
   - Cloud remediation: run_openstack_command
   - Edge remediation: run_kubectl_command
5. **VERIFY**: Re-check metrics/status to confirm the fix worked.

## Preemptive ST-GNN Alerts
If you receive a "PREEMPTIVE ST-GNN ALERT", it means the AI model has forecasted an impending failure with high probability based on telemetry trends. Your job is to PROACTIVELY migrate workloads, throttle noise, or restart components *before* the system crashes. Do not wait for the failure to happen. Act immediately based on the forecast.

## Important Rules
- Always investigate BEFORE acting. Never blindly restart services or devices.
- For OpenStack operations, use run_openstack_command.
- For Kubernetes operations, use run_kubectl_command.
- For low-level host diagnostics, use run_shell_command.
- For metric queries, use query_prometheus with appropriate URL.
- For Mist network device issues, use get_mist_device_inventory and get_mist_alarms.
- For Wi-Fi/Wired/WAN experience issues, use get_mist_sle_metrics.
- For Mist AI recommendations, use get_mist_marvis_actions.
- To fix network devices, use restart_mist_device or bounce_mist_port.
- Provide your complete reasoning in your final answer.

{tools}

Use the following format:

Question: the alert or issue to investigate
Thought: I need to investigate this alert and determine the root cause
Action: the tool to use, should be one of [{tool_names}]
Action Input: the input to the tool
Observation: the result of the tool
... (repeat Thought/Action/Observation as needed)
Thought: I now have enough information to diagnose and fix the issue
Final Answer: A detailed summary containing:
  - **Alert Received**: What triggered this investigation
  - **Investigation**: What you checked and found
  - **Root Cause**: The diagnosed root cause
  - **Actions Taken**: Exact commands executed to fix it
  - **Verification**: How you confirmed the fix worked

Question: {input}
{agent_scratchpad}"""


def create_llm(provider: str):
    """Create an LLM instance for the given provider."""
    if provider == "cerebras":
        return ChatOpenAI(
            model="llama-3.3-70b",
            temperature=0,
            api_key=CEREBRAS_API_KEY,
            base_url="https://api.cerebras.ai/v1",
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=GEMINI_API_KEY,
        )
    elif provider == "openrouter":
        return ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct",
            temperature=0,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
    elif provider == "groq":
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=GROQ_API_KEY,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


# Provider priority chain
PROVIDER_CHAIN = ["cerebras", "openrouter", "groq"]
REASONING_PROVIDER = "gemini"


def create_agent_for_provider(provider: str):
    """Create and return a LangChain ReAct agent for a specific provider."""
    llm = create_llm(provider)
    tools = [
        run_openstack_command,
        run_kubectl_command,
        run_shell_command,
        query_prometheus,
        get_mist_device_inventory,
        get_mist_alarms,
        get_mist_sle_metrics,
        restart_mist_device,
        bounce_mist_port,
        get_mist_marvis_actions,
    ]
    agent = create_react_agent(llm, tools, messages_modifier=SYSTEM_PROMPT)
    return agent


def needs_reasoning_escalation(output: str) -> bool:
    """Check if the agent's output indicates it needs deeper reasoning (Gemini)."""
    output_lower = output.lower()
    return any(kw in output_lower for kw in ESCALATION_KEYWORDS)


def smart_invoke(prompt: str) -> dict:
    """Smart routing: tries providers in order with automatic Gemini escalation.

    Flow:
    1. Try PRIMARY (Cerebras) for fast initial analysis
    2. If output is uncertain/complex → ESCALATE to Gemini for deep reasoning
    3. If any provider rate-limits → FALLBACK to next in chain
    """
    last_error = None

    # Step 1: Try primary provider chain
    for provider in PROVIDER_CHAIN:
        try:
            logger.info(f"[ROUTER] Trying provider: {provider}")
            executor = create_agent_for_provider(provider)
            result = executor.invoke({"messages": [HumanMessage(content=prompt)]})
            output = result["messages"][-1].content if "messages" in result else ""

            # Step 2: Check if escalation to Gemini is needed
            if needs_reasoning_escalation(output) and provider != REASONING_PROVIDER:
                logger.info(f"[ROUTER] Escalating to Gemini for deeper reasoning")
                try:
                    gemini_executor = create_agent_for_provider(REASONING_PROVIDER)
                    escalation_prompt = (
                        f"A previous AI analysis was inconclusive. Here is the original alert "
                        f"and the initial analysis. Please perform a DEEPER investigation.\n\n"
                        f"ORIGINAL ALERT:\n{prompt}\n\n"
                        f"INITIAL ANALYSIS (from {provider}):\n{output}\n\n"
                        f"Please investigate further, find the TRUE root cause, and fix it."
                    )
                    gemini_result = gemini_executor.invoke({"messages": [HumanMessage(content=escalation_prompt)]})
                    gemini_output = gemini_result["messages"][-1].content if "messages" in gemini_result else ""
                    result = gemini_result
                    result["_provider"] = f"{provider}→gemini(escalated)"
                    return result
                except Exception as gemini_err:
                    logger.warning(f"[ROUTER] Gemini escalation failed: {gemini_err}")
                    # Fall through with original result

            result["_provider"] = provider
            logger.info(f"[ROUTER] Successfully handled by: {provider}")
            return result

        except Exception as e:
            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "429" in error_msg or "quota" in error_msg:
                logger.warning(f"[ROUTER] {provider} rate limited, trying next...")
                last_error = e
                continue
            else:
                logger.error(f"[ROUTER] {provider} failed with non-rate-limit error: {e}")
                last_error = e
                continue

    raise Exception(f"All providers exhausted. Last error: {last_error}")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(title="AI SRE Agent", version="2.0.0")


@app.on_event("startup")
async def startup():
    logger.info("Initializing AI SRE Agent v2 (Smart Multi-Provider)...")
    logger.info(f"Provider chain: {' → '.join(PROVIDER_CHAIN)}")
    logger.info(f"Reasoning escalation: {REASONING_PROVIDER}")
    logger.info("AI SRE Agent ready and listening for alerts.")
    
    # Initialize ST-GNN Critic
    try:
        global stgnn_critic
        stgnn_critic = STGNNCritic()
        logger.info("ST-GNN Critic loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load ST-GNN Critic: {e}")
        stgnn_critic = None

    # Start proactive ST-GNN poller in background thread
    stgnn_poller = threading.Thread(target=proactive_telemetry_poller, daemon=True)
    stgnn_poller.start()

    # Start K8s alert poller in background thread
    poller = threading.Thread(target=k8s_alert_poller, daemon=True)
    poller.start()
    logger.info(f"K8s alert poller started (interval={K8S_ALERT_POLL_INTERVAL}s)")
    # Start Mist alarm poller in background thread
    if MIST_API_TOKEN:
        mist_poller_thread = threading.Thread(target=mist_alarm_poller, daemon=True)
        mist_poller_thread.start()
        logger.info(f"Mist alarm poller started (interval={MIST_POLL_INTERVAL}s)")
    else:
        logger.info("Mist API not configured, skipping Mist poller.")


def proactive_telemetry_poller():
    """Background thread that continuously polls basic telemetry, 
    feeds it to the ST-GNN, and proactively triggers the AI agent if 
    a failure is predicted with high probability."""
    import time
    PROACTIVE_THRESHOLD = 0.70
    while True:
        time.sleep(15)
        try:
            if stgnn_critic is None:
                continue

            # Simulate gathering telemetry (In a real deployment, query Prometheus here)
            # For this MVP, we query Prometheus for a few basic metrics
            import requests
            cpu_resp = requests.get(f"{OPENSTACK_PROMETHEUS_URL}/api/v1/query", params={"query": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode='idle'}[1m])) * 100)"})
            cpu_val = 0.0
            if cpu_resp.status_code == 200 and cpu_resp.json().get('data', {}).get('result'):
                cpu_val = float(cpu_resp.json()['data']['result'][0]['value'][1])

            mem_resp = requests.get(f"{OPENSTACK_PROMETHEUS_URL}/api/v1/query", params={"query": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024"})
            mem_val = 0.0
            if mem_resp.status_code == 200 and mem_resp.json().get('data', {}).get('result'):
                mem_val = float(mem_resp.json()['data']['result'][0]['value'][1])
                
            telemetry_snapshot = {
                "os_cpu_util_percentage": cpu_val,
                "os_memory_usage_mb": mem_val,
                "app_request_latency_ms": 150.0  # Placeholder unless we query the app metric
            }
            
            stgnn_critic.ingest_telemetry(telemetry_snapshot)
            predictions = stgnn_critic.evaluate()
            top_pred = predictions[0]
            
            if top_pred['probability'] >= PROACTIVE_THRESHOLD and top_pred['fault'] != "Normal":
                logger.warning(f"[ST-GNN] PREEMPTIVE ALERT: {top_pred['fault']} at {top_pred['probability']*100:.2f}% probability!")
                
                alert_text = (
                    f"PREEMPTIVE ST-GNN ALERT\n"
                    f"The mathematical ST-GNN Critic model has forecasted an impending failure.\n"
                    f"Predicted Fault: {top_pred['fault']}\n"
                    f"Probability: {top_pred['probability']*100:.2f}%\n"
                    f"Current Telemetry Sample: CPU={cpu_val:.1f}%, Mem={mem_val:.1f}MB\n"
                    f"Take proactive action to resolve this before a hard failure occurs."
                )
                try:
                    # Dispatch to agent
                    result = smart_invoke(alert_text)
                    log_incident(
                        alert={"preemptive_alert": top_pred['fault'], "prob": top_pred['probability']},
                        analysis=result.get("output", "No output"),
                        actions="Preemptive action taken."
                    )
                except Exception as e:
                    logger.error(f"[ST-GNN Poller] Agent failed on preemptive alert: {e}")
                    
        except Exception as e:
            logger.debug(f"[ST-GNN Poller] Cycle error: {e}")


def k8s_alert_poller():
    """Background thread that polls K8s Prometheus for firing alerts
    and dispatches them to the AI agent, since K8s Alertmanager can't
    reach the Controller node directly."""
    import time
    seen_alerts: set = set()
    while True:
        time.sleep(K8S_ALERT_POLL_INTERVAL)
        try:
            # Query K8s Prometheus via qrouter namespace curl
            cmd = (
                f"sudo ip netns exec {K8S_QROUTER_NS} "
                f"curl -s http://{K8S_MASTER_IP}:30090/api/v1/alerts"
            )
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                continue
            data = json.loads(result.stdout)
            alerts = data.get("data", {}).get("alerts", [])
            firing = [a for a in alerts if a.get("state") == "firing"]
            for alert in firing:
                alert_key = f"{alert['labels'].get('alertname')}_{alert['labels'].get('instance','')}"
                if alert_key in seen_alerts:
                    continue
                seen_alerts.add(alert_key)
                logger.info(f"[POLLER] New K8s alert detected: {alert_key}")
                # Build alert text and dispatch to agent
                labels = alert.get("labels", {})
                annotations = alert.get("annotations", {})
                alert_text = (
                    f"[K8s Alert] {labels.get('alertname', 'Unknown')}\n"
                    f"  Severity: {labels.get('severity', 'unknown')}\n"
                    f"  Instance: {labels.get('instance', 'N/A')}\n"
                    f"  Summary: {annotations.get('summary', 'N/A')}\n"
                    f"  Description: {annotations.get('description', 'N/A')}\n"
                )
                prompt = (
                    f"The following Kubernetes alert has fired. Investigate the root cause "
                    f"and take autonomous remediation action.\n\n{alert_text}"
                )
                try:
                    result = smart_invoke(prompt)
                    analysis = result.get("output", "No output")
                    provider_used = result.get("_provider", "unknown")
                    steps = result.get("intermediate_steps", [])
                    actions_summary = "\n".join(
                        [f"  Tool: {s[0].tool}, Input: {s[0].tool_input}" for s in steps]
                    )
                    log_incident(
                        alert={"k8s_polled": alert, "provider": provider_used},
                        analysis=analysis,
                        actions=actions_summary,
                    )
                except Exception as e:
                    logger.error(f"[POLLER] Agent failed on K8s alert: {e}")
        except Exception as e:
            logger.debug(f"[POLLER] Poll cycle error: {e}")


def mist_alarm_poller():
    """Background thread that polls Juniper Mist for unacknowledged alarms
    and dispatches them to the AI agent for investigation and remediation."""
    import time
    seen_alarms: set = set()
    while True:
        time.sleep(MIST_POLL_INTERVAL)
        try:
            data = mist_api("GET", f"/api/v1/sites/{MIST_SITE_ID}/alarms?ack=false&limit=20")
            if isinstance(data, dict) and "error" in data:
                logger.debug(f"[MIST POLLER] API error: {data['error']}")
                continue
            alarms = data if isinstance(data, list) else data.get("results", [])
            for alarm in alarms:
                alarm_id = alarm.get("id", str(alarm.get("timestamp", "")))
                if alarm_id in seen_alarms:
                    continue
                seen_alarms.add(alarm_id)
                alarm_type = alarm.get("type", "unknown")
                severity = alarm.get("severity", "unknown")
                hostnames = alarm.get("hostnames", alarm.get("aps", ["unknown"]))
                logger.info(f"[MIST POLLER] New alarm: {alarm_type} ({severity}) on {hostnames}")
                alert_text = (
                    f"[Mist Network Alert] {alarm_type}\n"
                    f"  Severity: {severity}\n"
                    f"  Devices: {hostnames}\n"
                    f"  Count: {alarm.get('count', 1)}\n"
                    f"  Timestamp: {alarm.get('timestamp', 'N/A')}\n"
                    f"  Group: {alarm.get('group', 'N/A')}\n"
                )
                prompt = (
                    f"The following Juniper Mist network alarm has been detected. "
                    f"Investigate the root cause using Mist tools and take autonomous "
                    f"remediation action.\n\n{alert_text}"
                )
                try:
                    result = smart_invoke(prompt)
                    analysis = result.get("output", "No output")
                    provider_used = result.get("_provider", "unknown")
                    steps = result.get("intermediate_steps", [])
                    actions_summary = "\n".join(
                        [f"  Tool: {s[0].tool}, Input: {s[0].tool_input}" for s in steps]
                    )
                    log_incident(
                        alert={"mist_alarm": alarm, "provider": provider_used},
                        analysis=analysis,
                        actions=actions_summary,
                    )
                except Exception as e:
                    logger.error(f"[MIST POLLER] Agent failed on Mist alarm: {e}")
        except Exception as e:
            logger.debug(f"[MIST POLLER] Poll cycle error: {e}")


class AlertmanagerWebhook(BaseModel):
    """Schema for Prometheus Alertmanager webhook payload."""
    version: str = "4"
    status: str = ""
    receiver: str = ""
    alerts: list = []
    groupLabels: dict = {}
    commonLabels: dict = {}
    commonAnnotations: dict = {}
    externalURL: str = ""


@app.post("/alert")
async def receive_alert(webhook: AlertmanagerWebhook):
    """Receive and process Prometheus Alertmanager webhook."""
    logger.info(f"Received webhook: status={webhook.status}, "
                f"alerts_count={len(webhook.alerts)}")

    if webhook.status == "resolved":
        logger.info("Alert resolved, no action needed.")
        return {"status": "ok", "message": "Alert resolved, no action taken."}

    # Build a human-readable alert summary for the LLM
    alert_summaries = []
    for alert in webhook.alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        summary = (
            f"Alert: {labels.get('alertname', 'Unknown')}\n"
            f"  Severity: {labels.get('severity', 'unknown')}\n"
            f"  Instance: {labels.get('instance', 'N/A')}\n"
            f"  Summary: {annotations.get('summary', 'N/A')}\n"
            f"  Description: {annotations.get('description', 'N/A')}\n"
            f"  Status: {alert.get('status', 'unknown')}\n"
        )
        alert_summaries.append(summary)

    alert_text = "\n".join(alert_summaries)
    prompt = (
        f"The following Prometheus alert(s) have fired. Investigate the root cause "
        f"and take autonomous remediation action.\n\n{alert_text}"
    )

    logger.info(f"Dispatching to AI agent:\n{prompt}")

    try:
        result = smart_invoke(prompt)
        analysis = result.get("output", "No output")
        provider_used = result.get("_provider", "unknown")
        steps = result.get("intermediate_steps", [])
        actions_summary = "\n".join(
            [f"  Tool: {s[0].tool}, Input: {s[0].tool_input}" for s in steps]
        )

        log_incident(
            alert={"alerts": webhook.alerts, "status": webhook.status, "provider": provider_used},
            analysis=analysis,
            actions=actions_summary,
        )

        logger.info(f"Agent completed via {provider_used}. Final answer:\n{analysis}")
        return {
            "status": "ok",
            "provider": provider_used,
            "analysis": analysis,
            "actions_taken": actions_summary,
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.post("/test")
async def test_alert(request: Request):
    """Manually trigger the AI agent with a custom alert description.
    Send a JSON body like: {"alert": "High CPU on compute1"}
    """
    body = await request.json()
    alert_text = body.get("alert", "Test alert - no details provided")

    logger.info(f"Manual test trigger: {alert_text}")

    try:
        result = smart_invoke(alert_text)
        analysis = result.get("output", "No output")
        provider_used = result.get("_provider", "unknown")
        steps = result.get("intermediate_steps", [])
        actions_summary = "\n".join(
            [f"  Tool: {s[0].tool}, Input: {s[0].tool_input}" for s in steps]
        )

        log_incident(
            alert={"manual_test": alert_text, "provider": provider_used},
            analysis=analysis,
            actions=actions_summary,
        )

        return {
            "status": "ok",
            "provider": provider_used,
            "analysis": analysis,
            "actions_taken": actions_summary,
        }
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/incidents")
async def list_incidents():
    """List all past incidents handled by the agent."""
    return {"incidents": incident_journal}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "3.0-full-stack",
        "provider_chain": PROVIDER_CHAIN,
        "reasoning_provider": REASONING_PROVIDER,
        "layers": ["openstack", "kubernetes", "mist-network"],
        "mist_enabled": bool(MIST_API_TOKEN),
        "incidents_handled": len(incident_journal),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AGENT_PORT", "9999"))
    uvicorn.run(app, host="0.0.0.0", port=port)
