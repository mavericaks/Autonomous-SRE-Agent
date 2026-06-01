#!/bin/bash
curl -s -X POST http://localhost:9999/test \
  -H 'Content-Type: application/json' \
  -d '{"alert": "High CPU usage detected on openstack-compute1 (10.10.10.11). The node is running at 100% CPU utilization across all cores. OpenStack Nova compute service may be impacted. Investigate and remediate."}'
