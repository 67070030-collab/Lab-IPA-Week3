import os
import re
from netmiko import ConnectHandler

BASE = {
    "device_type": "cisco_ios",
    "username": "admin",
    "use_keys": True,
    "key_file": os.path.expanduser("~/.ssh/id_rsa"),
    "allow_agent": False,
}

devices = {
    "R1": "172.31.47.4",
    "R2": "172.31.47.5",
}

# ---------- Regex patterns ----------
# ตัวอย่างบรรทัดที่ต้อง match จาก "show ip interface brief":
# GigabitEthernet0/0   172.31.47.4   YES manual up   up
INTERFACE_PATTERN = re.compile(
    r"^(?P<interface>\S+)\s+"
    r"(?P<ip>\S+)\s+"
    r"(?P<ok>YES|NO)\s+"
    r"(?P<method>\S+)\s+"
    r"(?P<status>up|down|administratively down)\s+"
    r"(?P<protocol>up|down)$",
    re.MULTILINE,
)

# ตัวอย่างบรรทัดจาก "show version":
# R1 uptime is 2 weeks, 3 days, 4 hours, 12 minutes
UPTIME_PATTERN = re.compile(
    r"^(?P<hostname>\S+)\s+uptime\s+is\s+(?P<uptime>.+)$",
    re.MULTILINE,
)


def get_active_interfaces(output):
    """คืนค่า list ของ interface ที่ status=up และ protocol=up (active จริง)"""
    active = []
    for match in INTERFACE_PATTERN.finditer(output):
        data = match.groupdict()
        if data["status"] == "up" and data["protocol"] == "up":
            active.append(data["interface"])
    return active


def get_uptime(output):
    match = UPTIME_PATTERN.search(output)
    if match:
        return match.group("uptime").strip()
    return "Unknown"


def main():
    for name, ip in devices.items():
        print(f"\n=== {name} ({ip}) ===")
        device = {**BASE, "ip": ip}
        conn = ConnectHandler(**device)

        # ---- Active interfaces ----
        int_output = conn.send_command("show ip interface brief")
        active_interfaces = get_active_interfaces(int_output)

        print("Active Interfaces:")
        if active_interfaces:
            for intf in active_interfaces:
                print(f"  - {intf}")
        else:
            print("  (none found)")

        # ---- Uptime ----
        version_output = conn.send_command("show version")
        uptime = get_uptime(version_output)
        print(f"Uptime: {uptime}")

        conn.disconnect()


if __name__ == "__main__":
    main()