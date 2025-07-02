import yaml
import json
import uuid
import os


class UserData:
    def __init__(
        self,
        hostname: str,
        ssh_user: str,
        ssh_public_keys_content: list[str],
        timezone: str = None,
        package_update: bool = False,
        packages: list[str] = None,
        runcmd: list[str] = None,
    ):
        self.hostname = hostname
        self.ssh_user = ssh_user
        self.ssh_public_keys_content = ssh_public_keys_content
        self.timezone = timezone
        self.package_update = package_update
        self.packages = packages if packages is not None else []
        self.runcmd = runcmd if runcmd is not None else []

    def to_yaml(self) -> str:
        user_data_content = {
            "hostname": self.hostname,
            "manage_etc_hosts": True,
            "disable_root_pw": True,
            "users": [
                {
                    "name": self.ssh_user,
                    "sudo": "ALL=(ALL) NOPASSWD:ALL",
                    "ssh_authorized_keys": self.ssh_public_keys_content,
                }
            ],
        }

        if self.timezone:
            user_data_content["timezone"] = self.timezone
        if self.package_update:
            user_data_content["package_update"] = self.package_update
        if self.packages:
            user_data_content["packages"] = self.packages
        if self.runcmd:
            user_data_content["runcmd"] = self.runcmd

        return (
            "#cloud-config"
            + "\n"
            + yaml.dump(
                user_data_content, indent=2, default_flow_style=False, sort_keys=False
            )
        )


class NetworkConfig:
    def __init__(
        self,
        ip_address: str,
        nameservers: list[str],
        gateway: str,
    ):
        self.ip_address = ip_address
        self.nameservers = nameservers
        self.gateway = gateway

    def to_yaml(self) -> str:
        network_config = {
            "network": {
                "version": 2,
                "ethernets": {
                    "eth0": {
                        "dhcp4": False,
                        "addresses": [f"{self.ip_address}/24"],
                        "gateway4": self.gateway,
                        "nameservers": {
                            "addresses": self.nameservers,
                        },
                    }
                },
            },
        }

        return yaml.dump(
            network_config, indent=2, default_flow_style=False, sort_keys=False
        )


class MetaData:
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.instance_id = f"k8s-{self.hostname}-{uuid.uuid4().hex[:8]}"

    def to_json(self) -> str:
        meta_data = {
            "instance-id": self.instance_id,
            "local-hostname": self.hostname,
        }
        return json.dumps(meta_data, indent=2)


class CloudInit:
    def __init__(
        self,
        hostname: str,
        ip_address: str,
        ssh_user: str,
        ssh_public_keys_content: list[str],
        nameservers: list[str],
        gateway: str,
        timezone: str = None,
        package_update: bool = False,
        packages: list[str] = None,
        runcmd: list[str] = None,
    ):
        self.user_data_config = UserData(
            hostname=hostname,
            ssh_user=ssh_user,
            ssh_public_keys_content=ssh_public_keys_content,
            timezone=timezone,
            package_update=package_update,
            packages=packages,
            runcmd=runcmd,
        )
        self.network_config = NetworkConfig(
            ip_address=ip_address,
            nameservers=nameservers,
            gateway=gateway,
        )
        self.meta_data_config = MetaData(hostname=hostname)

    def generate_user_data(self) -> str:
        return self.user_data_config.to_yaml()

    def generate_meta_data(self) -> str:
        return self.meta_data_config.to_json()

    def generate_network_config(self) -> str:
        return self.network_config.to_yaml()

    def save_configs(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)

        user_data_path = os.path.join(output_dir, "user-data")
        meta_data_path = os.path.join(output_dir, "meta-data")
        network_config_path = os.path.join(output_dir, "network-config")

        with open(user_data_path, "w") as f:
            f.write(self.generate_user_data())

        with open(meta_data_path, "w") as f:
            f.write(self.generate_meta_data())

        with open(network_config_path, "w") as f:
            f.write(self.generate_network_config())
