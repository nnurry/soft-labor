#!/bin/bash
export LIBVIRT_DEFAULT_URI=${LIBVIRT_DEFAULT_URI:-qemu:///system}
BASE_DISK_DIR="/var/lib/libvirt/images"

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <BASE_VM_NAME> <NEW_VM_NAME> [NEW_DISK_PATH]"
    echo "  If NEW_DISK_PATH is not provided, it defaults to ${BASE_DISK_DIR}/<NEW_VM_NAME>.qcow2"
    exit 1
fi

BASE_VM_NAME="$1"
NEW_VM_NAME="$2"

if [ -z "$3" ]; then
    NEW_DISK_PATH="${BASE_DISK_DIR}/${NEW_VM_NAME}.qcow2"
    echo "NEW_DISK_PATH not provided. Defaulting to: $NEW_DISK_PATH"
else
    NEW_DISK_PATH="$3"
    echo "Using provided NEW_DISK_PATH: $NEW_DISK_PATH"
fi

echo "Cloning VM..."
echo "  Original VM: $BASE_VM_NAME"
echo "  New VM Name: $NEW_VM_NAME"
echo "  New Disk Path: $NEW_DISK_PATH"
echo ""

virt-clone \
    --original "$BASE_VM_NAME" \
    --name "$NEW_VM_NAME" \
    --file "$NEW_DISK_PATH"

if [ $? -eq 0 ]; then
    echo "Successfully cloned VM: $NEW_VM_NAME"
else
    echo "Error: Failed to clone VM '$BASE_VM_NAME' to '$NEW_VM_NAME'."
    echo "Please check the error messages above for details."
    exit 1
fi

echo "VM cloning script finished."
