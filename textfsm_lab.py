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
    "S1": "172.31.47.3",
}

# interface ที่ต่อ PC โดยตรง (ไม่มี cdp neighbor เพราะ PC ไม่รัน CDP)
PC_INTERFACES = {
    "R1": ["GigabitEthernet0/1"],
    "S1": ["GigabitEthernet0/2"],
}

# interface ที่เป็น WAN/DHCP (ต่อ NAT1 cloud)
WAN_INTERFACES = {
    "R2": ["GigabitEthernet0/3"],
}


def get_cdp_neighbors(conn):
    result = conn.send_command("show cdp neighbors detail", use_textfsm=True)
    mapping = {}
    for entry in result:
        local_intf = entry.get("local_interface")
        remote_intf = entry.get("neighbor_interface")
        remote_device = entry.get("neighbor_name")
        remote_device = remote_device.split(".")[0] if remote_device else remote_device
        if local_intf:
            mapping[local_intf] = (remote_device, remote_intf)
    return mapping


def build_description(device_name, interface, cdp_map):
    def shorten(intf_name):
        return intf_name.replace("GigabitEthernet", "Gi").replace("FastEthernet", "Fa")

    if interface in cdp_map:
        remote_device, remote_intf = cdp_map[interface]
        if remote_device and remote_intf:
            return f"Connect to {shorten(remote_intf)} of {remote_device}"
    if interface in PC_INTERFACES.get(device_name, []):
        return "Connect to PC"
    if interface in WAN_INTERFACES.get(device_name, []):
        return "Connect to WAN"
    return None


def configure_descriptions(device_name, ip):
    print(f"\n=== {device_name} ({ip}) ===")
    conn = ConnectHandler(**{**BASE, "ip": ip})

    cdp_map = get_cdp_neighbors(conn)
    print(f"CDP Map: {cdp_map}")   # <-- เพิ่มบรรทัดนี้ debug ดูก่อน

    int_brief = conn.send_command("show ip interface brief", use_textfsm=True)
    print(f"Interfaces: {int_brief}")   # <-- เพิ่มด้วย ดูว่า field ชื่ออะไร

    commands = []
    for entry in int_brief:
        intf = entry.get("interface") or entry.get("intf")
        if not intf or intf.lower().startswith("vlan") or intf.lower().startswith("nvi"):
            continue
        desc = build_description(device_name, intf, cdp_map)
        print(f"  {intf} -> {desc}")   # <-- เพิ่มด้วย ดูว่า mapping ตรงไหม
        if desc:
            commands.append(f"interface {intf}")
            commands.append(f" description {desc}")

    print(f"Commands to send: {commands}")   # <-- เพิ่มดูก่อนส่งจริง

    if commands:
        output = conn.send_config_set(commands)
        print(output)
        conn.save_config()
    else:
        print("No description commands generated.")

    conn.disconnect()


if __name__ == "__main__":
    for name, ip in devices.items():
        configure_descriptions(name, ip)