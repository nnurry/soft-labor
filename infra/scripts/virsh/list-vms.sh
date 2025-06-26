#!/bin/bash

# Always start with --all in the arguments array
VIRSH_LIST_ARGS=("--all")

# Check for flags
if [ "$#" -eq 0 ]; then
    VIRSH_LIST_ARGS+=("--table")
else
    if [ "$1" == "-n" ] || [ "$1" == "--name" ]; then
        VIRSH_LIST_ARGS+=("--name")
        shift
    else 
        echo "Error: Unrecognized argument: '$1'. Usage: $0 [-n | --name]"
        exit 1
    fi
fi

echo "Listing all VMs..."

# Execute virsh list with the determined arguments from the array
# "${VIRSH_LIST_ARGS[@]}" expands all elements of the array as separate arguments
VIRSH_OUTPUT=$(virsh list "${VIRSH_LIST_ARGS[@]}")
EXIT_STATUS=$? # Capture the exit status immediately after the command

# Check if the command was successful
if [ $EXIT_STATUS -eq 0 ]; then
    echo "$VIRSH_OUTPUT"
else
    echo "Error: Failed to list VMs."
    echo "Please ensure libvirt is running and you have appropriate permissions."
    exit 1
fi
