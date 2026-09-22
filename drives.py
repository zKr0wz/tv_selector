import platform
from dataclasses import dataclass

import psutil


IGNORED_FILESYSTEMS = {
    "squashfs",
    "tmpfs",
    "devtmpfs",
    "proc",
    "sysfs",
    "overlay",
}

@dataclass
class Drive:
    device: str
    mountpoint: str
    filesystem: str
    operating_system: str

def should_ignore_drive(device: str, filesystem: str) -> bool:
    if device.startswith("/dev/loop"):
        return True

    if filesystem.lower() in IGNORED_FILESYSTEMS:
        return True

    return False

def discover_drives() -> list[Drive]:
    drives = []
    system = platform.system()

    for partition in psutil.disk_partitions(all=False):
        if should_ignore_drive(
            partition.device,
            partition.fstype,
        ):
            continue

        drive = Drive(
            device=partition.device,
            mountpoint=partition.mountpoint,
            filesystem=partition.fstype,
            operating_system=system
        )

        drives.append(drive)

    return drives

def print_drives(drives: list[Drive]) -> None:
    print("\nDetected Storage")
    print("-" * 60)

    for number, drive in enumerate(drives, start=1):
        print(f"[{number}] {drive.device}")
        print(f"   Mount:        {drive.mountpoint}")
        print(f"   Filesystem:   {drive.filesystem}")
        print(f"   OS:           {drive.operating_system}")
        print()

def main():
    drives = discover_drives()

    if not drives:
        print("No drives detected.")
        return

    print_drives(drives)

if __name__ == "__main__":
    main()
