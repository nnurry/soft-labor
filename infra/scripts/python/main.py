import os

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

            cloud_init_config_instance = CloudInit(  # noqa: F821
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
    CONFIG_FILE = "vm_config.yaml"  # Make sure this file exists with your config

    # Dummy SSH Key for testing if ~/.ssh/shared-VM-ssh-key-id_ed25519.pub doesn't exist
    if not os.path.exists(
        os.path.expanduser("~/.ssh/shared-VM-ssh-key-id_ed25519.pub")
    ):
        print(
            "SSH public key not found. Creating a dummy vm_config.yaml and key for demonstration."
        )
        # Create a dummy config file
        dummy_config_content = """
base_vm_name: "your-base-vm-name" # Change this to an actual base VM name on your host
master_nodes:
  - name: "test-k8s-master-1"
    ip_address: "192.168.122.101"
    vcpu: 2
    memory_gb: 2
    disk_gb: 20
    mac_address: "52:54:00:00:00:01"
worker_nodes:
  - name: "test-k8s-worker-1"
    ip_address: "192.168.122.111"
    vcpu: 2
    memory_gb: 2
    disk_gb: 20
    mac_address: "52:54:00:00:00:11"
ssh_user: youruser
ssh_public_key_path: "~/.ssh/dummy_vm_ssh_key.pub"
ssh_private_key_path: "~/.ssh/dummy_vm_ssh_key"
cloud_init_global_config:
  nameservers:
    - "8.8.8.8"
  disable_root_pw: true
"""
        with open(CONFIG_FILE, "w") as f:
            f.write(dummy_config_content)

        # Generate dummy SSH key pair
        dummy_ssh_pub_path = os.path.expanduser("~/.ssh/dummy_vm_ssh_key.pub")
        dummy_ssh_priv_path = os.path.expanduser("~/.ssh/dummy_vm_ssh_key")
        if not os.path.exists(os.path.dirname(dummy_ssh_pub_path)):
            os.makedirs(os.path.dirname(dummy_ssh_pub_path))
        OSUtils.run_command(
            ["ssh-keygen", "-t", "ed25519", "-f", dummy_ssh_priv_path, "-N", ""],
            shell=False,
        )
        print(f"Dummy SSH key pair generated at {dummy_ssh_priv_path}")

    # --- Actual Usage ---
    try:
        parser = VMConfigParser(CONFIG_FILE)
        hub = CLI(parser)
        hub.list_available_commands()

    except Exception as e:
        print(f"An error occurred in the main execution block: {e}")
