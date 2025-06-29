import os
import argparse

from cloud_init.config import CloudInit
from cloud_init.iso_builder import CloudInitISOBuilder
from utils import OSUtils
from vms.builder import VMBuilder
from vms.parser import VMConfigParser


class CLI:
    def __init__(
        self,
        config_parser: VMConfigParser,
        cloud_init_base_dir: str = "cloud-init-data",
    ):
        self.config_parser = config_parser
        self.cloud_init_base_dir = cloud_init_base_dir
        self.ssh_public_key_content = self._load_ssh_public_key()
        self.all_nodes_config = (
            self.config_parser.master_nodes + self.config_parser.worker_nodes
        )

    def _load_ssh_public_key(self) -> str:
        public_key_path = self.config_parser.ssh_public_key_path
        if not os.path.exists(public_key_path):
            raise FileNotFoundError(f"SSH public key not found: {public_key_path}")
        with open(public_key_path, "r") as f:
            return f.read().strip()

    def list_vms(self):
        try:
            output = OSUtils.run_command(
                ["virsh", "list", "--all", "--name"], check_output=True
            )
            print("Existing VMs:")
            print(output)
        except Exception as e:
            print(f"Error listing VMs: {e}")

    def create_vm(self, node_config: dict):
        vm_name = node_config["name"]

        try:
            existing_vms = OSUtils.run_command(
                ["virsh", "list", "--all", "--name"], check_output=True
            ).splitlines()
            if vm_name in existing_vms:
                print(f"VM {vm_name} already exists. Skipping creation.")
                return

            cloud_init_config_instance = CloudInit(
                hostname=vm_name,
                ip_address=node_config["ip_address"],
                ssh_user=self.config_parser.ssh_user,
                ssh_public_keys_content=[self.ssh_public_key_content],
                nameservers=self.config_parser.cloud_init_global_config.get(
                    "nameservers"
                ),
                timezone=self.config_parser.cloud_init_global_config.get("timezone"),
                package_update=self.config_parser.cloud_init_global_config.get(
                    "package_update"
                ),
                packages=self.config_parser.cloud_init_global_config.get("packages"),
                runcmd=self.config_parser.cloud_init_global_config.get("runcmd"),
                gateway="192.168.122.1",  # Assuming default virbr0 gateway
            )

            iso_builder = CloudInitISOBuilder(
                cloud_init_config_instance, self.cloud_init_base_dir
            )
            cloud_init_iso_path = iso_builder.build_iso()

            vm_builder = VMBuilder(
                node_config, self.config_parser.base_vm_name, cloud_init_iso_path
            )
            vm_builder.define_and_start_vm()
            print(f"VM {vm_name} created and started successfully.")

        except Exception as e:
            print(f"Error creating VM {vm_name}: {e}")

    def delete_vm(self, vm_name: str):
        try:
            OSUtils.run_command(["virsh", "destroy", vm_name], sudo=True)
            OSUtils.run_command(["virsh", "undefine", vm_name], sudo=True)
            # Optional: Delete associated disk image and cloud-init directory
            # For this, you would need to store/retrieve disk path and cloud-init path
            # from your records or VM XML. Let's skip for now to keep it simpler.
            print(f"VM {vm_name} destroyed and undefined.")
        except Exception as e:
            print(f"Error deleting VM {vm_name}: {e}")

    def list_available_commands(self):
        print("Available Commands:")
        print("  list_vms()")
        print("  create_vm(node_config_dict)")
        print("  delete_vm(vm_name)")
        print("  list_available_commands()")


if __name__ == "__main__":
    CONFIG_FILE = "vm_config.yaml"

    parser = argparse.ArgumentParser(
        description="A CLI tool for managing virtual machines.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--config",
        default=CONFIG_FILE,
        help=f"Path to the VM configuration YAML file (default: {CONFIG_FILE})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    list_parser = subparsers.add_parser(
        "list", help="List all existing virtual machines."
    )

    create_parser = subparsers.add_parser(
        "create", help="Create a virtual machine based on the configuration."
    )
    create_parser.add_argument(
        "node_name",
        nargs="?",
        help="Specify a single node to create by name (e.g., 'test-k8s-master-1').\n"
        "If omitted, all nodes defined in the config file will be created.",
    )

    delete_parser = subparsers.add_parser("delete", help="Delete a virtual machine.")
    delete_parser.add_argument(
        "vm_name",
        help="The name of the VM to delete (e.g., 'test-k8s-master-1').",
    )

    args = parser.parse_args()

    try:
        if not os.path.exists(args.config):
            raise FileNotFoundError(
                f"Configuration file '{args.config}' not found. Please provide a valid configuration file."
            )

        vm_config_parser = VMConfigParser(args.config)
        cli_app = CLI(vm_config_parser)

        if args.command == "list":
            cli_app.list_vms()
        elif args.command == "create":
            if args.node_name:
                found_node = None
                for node in cli_app.all_nodes_config:
                    if node["name"] == args.node_name:
                        found_node = node
                        break
                if found_node:
                    cli_app.create_vm(found_node)
                else:
                    print(f"Error: Node '{args.node_name}' not found in configuration.")
            else:
                for node_config in cli_app.all_nodes_config:
                    cli_app.create_vm(node_config)
        elif args.command == "delete":
            cli_app.delete_vm(args.vm_name)
        else:
            parser.print_help()  # If no command is given, print general help

    except FileNotFoundError as fnfe:
        print(f"Error: {fnfe}")
        # Exit with a non-zero status code to indicate an error
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)
