import sys
sys.path.insert(0, '/opt/ai-sre-agent')
import main
import traceback

print("Testing Mist Integration...")
try:
    print(main.smart_invoke("Test Mist: run get_mist_device_inventory and get_mist_alarms"))
except Exception as e:
    traceback.print_exc()
