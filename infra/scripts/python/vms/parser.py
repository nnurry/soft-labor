import os

import yaml


class VMConfigParser:
    def __init__(self, config_file_path: str):
        self.config_file_path = os.path.expanduser(config_file_path)
        self.config_data = self._load_config()

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(
                f"Config file not found at: {self.config_file_path}"
            )
        with open(self.config_file_path, "r") as f:
            return yaml.safe_load(f)

    @property
    def base_vm_name(self) -> str:
        return self.config_data["base_vm_name"]

    @property
    def master_nodes(self) -> list[dict]:
        return self.config_data.get("master_nodes", [])

    @property
    def worker_nodes(self) -> list[dict]:
        return self.config_data.get("worker_nodes", [])

    @property
    def ssh_user(self) -> str:
        return self.config_data["ssh_user"]

    @property
    def ssh_public_key_path(self) -> str:
        return os.path.expanduser(self.config_data["ssh_public_key_path"])

    @property
    def ssh_private_key_path(self) -> str:
        return os.path.expanduser(self.config_data["ssh_private_key_path"])

    @property
    def cloud_init_global_config(self) -> dict:
        return self.config_data.get("cloud_init_global_config", {})
