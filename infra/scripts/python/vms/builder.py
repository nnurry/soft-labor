import os
import shutil
import uuid
from utils import OSUtils
import xml.etree.ElementTree as ET


class VMBuilder:
    def __init__(
        self,
        vm_config: dict,
        base_vm_name: str,
        cloud_init_iso_path: str,
    ):
        self.vm_config = vm_config
        self.base_vm_name = base_vm_name
        self.cloud_init_iso_path = cloud_init_iso_path
        self.vm_name = vm_config["name"]
        self.vcpu = vm_config["vcpu"]
        self.memory_gb = vm_config["memory_gb"]
        self.disk_gb = vm_config["disk_gb"]
        self.mac_address = vm_config["mac_address"]
        self.disk_dir = None  # To be determined from base VM XML
        self.is_cow_clone = vm_config.get("is_cow_clone", True)

    def _get_base_disk_path(self) -> str:
        base_xml = OSUtils.run_command(
            ["virsh", "dumpxml", self.base_vm_name], check_output=True
        )
        root = ET.fromstring(base_xml)
        for disk in root.findall(".//disk[@device='disk']/source"):
            if "file" in disk.attrib:
                return disk.attrib["file"]
        raise ValueError(f"Could not find base disk path for VM: {self.base_vm_name}")

    def _clone_disk(self, base_disk_path: str, is_cow: bool = True) -> str:
        self.disk_dir = os.path.dirname(base_disk_path)
        new_disk_path = os.path.join(self.disk_dir, f"{self.vm_name}.qcow2")

        if is_cow:
            qemu_img_cmd = [
                "qemu-img",
                "create",
                "-f",
                "qcow2",
                "-b",
                base_disk_path,
                "-F",
                "qcow2",
                new_disk_path,
                f"{self.disk_gb}G",
            ]
            OSUtils.run_command(qemu_img_cmd, sudo=True)

        else:
            shutil.copyfile(base_disk_path, new_disk_path)
        return new_disk_path

    def _generate_vm_xml(self, new_disk_path: str) -> str:
        base_xml = OSUtils.run_command(
            ["virsh", "dumpxml", self.base_vm_name], check_output=True
        )
        root = ET.fromstring(base_xml)

        name_elem = root.find("name")
        if name_elem is not None:
            name_elem.text = self.vm_name

        uuid_elem = root.find("uuid")
        if uuid_elem is not None:
            uuid_elem.text = str(uuid.uuid4())

        vcpu_elem = root.find("vcpu")
        if vcpu_elem is not None:
            vcpu_elem.text = str(self.vcpu)

        cpu_topology_elem = root.find("cpu/topology")
        if cpu_topology_elem is not None:
            cpu_topology_elem.set("cores", str(self.vcpu))

        memory_mb = int(self.memory_gb * 1024)
        memory_elem = root.find("memory")
        current_memory_elem = root.find("currentMemory")
        if memory_elem is not None:
            memory_elem.text = str(memory_mb * 1024)
            memory_elem.set("unit", "KiB")
        if current_memory_elem is not None:
            current_memory_elem.text = str(memory_mb * 1024)
            current_memory_elem.set("unit", "KiB")

        for disk in root.findall(".//disk[@device='disk']"):
            source = disk.find("source")
            if source is not None and "file" in source.attrib:
                source.set("file", new_disk_path)
                if "backing_file" in source.attrib:
                    del source.attrib["backing_file"]

        for interface in root.findall(".//interface[@type='bridge']"):
            source = interface.find("source")
            if source is not None and "br0" in source.get("bridge"):
                mac = interface.find("mac")
                if mac is not None:
                    mac.set("address", self.mac_address)
                break

        disks_parent = root.find(".//disk[@device='cdrom']..")
        for disk in disks_parent.findall(".//disk[@device='cdrom']"):
            disks_parent.remove(disk)

        disk_elem = ET.Element("disk", {"type": "file", "device": "cdrom"})
        ET.SubElement(disk_elem, "driver", {"name": "qemu", "type": "raw"})
        ET.SubElement(disk_elem, "source", {"file": self.cloud_init_iso_path})
        ET.SubElement(disk_elem, "target", {"dev": "hdc", "bus": "sata"})
        ET.SubElement(disk_elem, "readonly")
        ET.SubElement(disk_elem, "boot", {"order": "2"})

        disks_parent.append(disk_elem)

        os_boot_elem = root.find(".//os/boot")
        if os_boot_elem is not None:
            os_boot_elem.set("dev", "hd")

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def define_and_start_vm(self) -> None:
        base_disk_path = self._get_base_disk_path()
        new_disk_path = self._clone_disk(base_disk_path, self.is_cow_clone)

        vm_xml = self._generate_vm_xml(new_disk_path)
        xml_path = f"/tmp/vm-{uuid.uuid4()}.xml"
        with open(xml_path, "w") as file:
            file.write(vm_xml)

        try:
            OSUtils.run_command(["virsh", "define", "--file", xml_path], sudo=True)
            OSUtils.run_command(["virsh", "start", self.vm_name], sudo=True)
        except Exception as e:
            os.remove(xml_path)
            raise e
