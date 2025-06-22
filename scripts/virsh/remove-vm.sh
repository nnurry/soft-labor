#!/bin/bash

# --- Input Validation ---
VM_NAME="$1"

if [ -z "$VM_NAME" ]; then
    echo "Usage: $0 <VM_NAME>"
    echo "  <VM_NAME> is the name of the virtual machine to undefine."
    exit 1
fi

echo "--- Processing VM: $VM_NAME ---"

# --- Step 1: Pre-check VM existence and Identify Associated Disk Images ---
echo "Checking VM existence and identifying associated disk images for '$VM_NAME' (before undefining)..."

# Check if the VM exists and is defined
virsh dominfo "$VM_NAME" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Error: VM '$VM_NAME' does not exist or is not defined in libvirt. Cannot proceed."
    exit 1
fi

DISK_LIST_RAW=$(
    virsh domblklist "$VM_NAME" --details 2>/dev/null | \
    grep -E '(v|s|h|x)d[a-z]' | \
    awk '{print $4}'
)

QCOW2_DISKS=()
OTHER_DISKS=()

if [ -n "$DISK_LIST_RAW" ]; then
    # Read the raw newline-separated paths into a temporary array
    local_temp_paths_array=()
    IFS=$'\n' read -r -d '' -a local_temp_paths_array <<< "$DISK_LIST_RAW"

    for disk_path in "${local_temp_paths_array[@]}"; do
        if [[ "$disk_path" == "-" ]]; then
            continue
        fi
        if [[ "$disk_path" == *.qcow2 ]]; then
            QCOW2_DISKS+=("$disk_path")
        else
            OTHER_DISKS+=("$disk_path")
        fi
    done
fi

if [ ${#QCOW2_DISKS[@]} -eq 0 ] && [ ${#OTHER_DISKS[@]} -eq 0 ]; then
    echo "No file-backed disk images found associated with '$VM_NAME' that this script can identify."
else
    echo ""
    echo "--- IMPORTANT: The following disk images are associated with '$VM_NAME': ---"
    echo "--- They WILL NOT be deleted by this script. You must remove them manually if desired. ---"
    if [ ${#QCOW2_DISKS[@]} -gt 0 ]; then
        echo "  QCOW2 Disks:"
        for disk in "${QCOW2_DISKS[@]}"; do
            echo "    - $disk"
        done
    fi
    if [ ${#OTHER_DISKS[@]} -gt 0 ]; then
        echo "  Other Disk Types (e.g., raw, iso, nbd):"
        for disk in "${OTHER_DISKS[@]}"; 
        do
            echo "    - $disk"
        done
        echo "Remember to 'sudo rm' these files if you no longer need them."
    fi
    echo "--------------------------------------------------------------------------------"
    echo ""
fi


echo "Attempting to undefine VM: $VM_NAME"
virsh undefine --domain "$VM_NAME"
EXIT_STATUS=$?

if [ $EXIT_STATUS -eq 0 ]; then
    echo "Successfully undefined VM: $VM_NAME"
else
    echo "Error: Failed to undefine VM: $VM_NAME (Exit Code: $EXIT_STATUS)"
    echo "Please ensure the VM is shut off before attempting to undefine it."
    exit 1
fi

echo "--- VM undefine process finished for: $VM_NAME ---"
