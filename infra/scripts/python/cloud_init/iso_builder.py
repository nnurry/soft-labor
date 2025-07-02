import os
from cloud_init.config import CloudInit
from utils import OSUtils


class CloudInitISOBuilder:
    def __init__(self, config: CloudInit, base_output_dir: str = "cloud-init-data"):
        self.config = config
        self.vm_output_dir = os.path.join(
            base_output_dir, config.user_data_config.hostname
        )
        self.iso_path = os.path.join(
            self.vm_output_dir, f"{config.user_data_config.hostname}-cidata.iso"
        )
        self.vm_output_dir = os.path.abspath(self.vm_output_dir)
        self.iso_path = os.path.abspath(self.iso_path)

    def build_iso(self) -> str:
        self.config.save_configs(self.vm_output_dir)

        try:
            mkisofs_cmd = [
                "mkisofs",
                "-output",
                self.iso_path,
                "-volid",
                "cidata",
                "-joliet",
                "-r",
                os.path.join(self.vm_output_dir, "user-data"),
                os.path.join(self.vm_output_dir, "meta-data"),
                os.path.join(self.vm_output_dir, "network-config"),
            ]
            
            OSUtils.run_command(mkisofs_cmd)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Required command utility not found: {e}. Please ensure 'mkisofs' or 'cloud-localds' is installed."
            )

        return self.iso_path
