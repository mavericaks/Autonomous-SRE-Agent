#!/bin/bash
set -ex
# Format /dev/sdb for Swift with label KOLLA_SWIFT_DATA
# Run on ALL nodes that will participate in Swift

DISK="/dev/sdb"

# Check if disk already has partitions
if lsblk -n "$DISK" | grep -q part; then
    echo "Disk already partitioned, skipping parted"
else
    sudo parted "$DISK" --script mklabel gpt
    sudo parted "$DISK" --script mkpart primary 0% 100%
fi

sleep 1

# Format partition as XFS with Swift label
PART="${DISK}1"
sudo mkfs.xfs -f -L KOLLA_SWIFT_DATA "$PART"
echo "Swift disk prepared: $(lsblk -f "$PART")"
