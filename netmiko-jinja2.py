import os
from netmiko import ConnectHandler
from jinja2 import Environment, FileSystemLoader

# ==== Connection info ====
BASE = {
    "device_type": "cisco_ios",
    "username": "admin",
    "use_keys": True,
    "key_file": os.path.expanduser("~/.ssh/id_rsa"),
    "allow_agent": False,
}

R1_IP = "172.31.47.4"
R2_IP = "172.31.47.5"
S1_IP = "172.31.47.3"

env = Environment(loader=FileSystemLoader("templates"))


def render(template_name, **kwargs):
    template = env.get_template(template_name)
    rendered = template.render(**kwargs)
    # ตัดบรรทัดว่างที่ jinja2 อาจสร้างจาก {% for %} tags
    return [line for line in rendered.splitlines() if line.strip() != ""]


def send(device_ip, commands, label):
    device = {**BASE, "ip": device_ip}
    print(f"\n=== Connecting to {label} ({device_ip}) ===")
    conn = ConnectHandler(**device)
    output = conn.send_config_set(commands)
    print(output)
    conn.save_config()
    conn.disconnect()


# ---------- S1: VLAN101 ----------
s1_commands = render(
    "s1_config.j2",
    vlan_id=101,
    vlan_name="CONTROL-DATA",
    interfaces=["GigabitEthernet0/1", "GigabitEthernet0/2"],
)

# ---------- R1: OSPF ----------
r1_commands = render(
    "r1_config.j2",
    ospf_process=1,
    vrf_name="control-data",
    router_id="1.1.1.1",
    loopback_ip="1.1.1.1",
    networks=[
        {"ip": "192.168.10.0", "wildcard": "0.0.0.255", "area": 0},
        {"ip": "192.168.47.0", "wildcard": "0.0.0.3", "area": 0},
        {"ip": "1.1.1.1", "wildcard": "0.0.0.0", "area": 0},
    ],
)

# ---------- R2: OSPF + PAT + null route ----------
r2_commands = render(
    "r2_config.j2",
    ospf_process=1,
    vrf_name="control-data",
    router_id="2.2.2.2",
    loopback_ip="2.2.2.2",
    networks=[
        {"ip": "192.168.47.0", "wildcard": "0.0.0.3", "area": 0},
        {"ip": "192.168.20.0", "wildcard": "0.0.0.255", "area": 0},
        {"ip": "2.2.2.2", "wildcard": "0.0.0.0", "area": 0},
    ],
    mgmt_net="172.31.47.0",
    mgmt_mask="255.255.255.240",
    nat_acl_name="NAT_YELLOW",
    nat_networks=[
        {"ip": "192.168.10.0", "wildcard": "0.0.0.255"},
        {"ip": "192.168.20.0", "wildcard": "0.0.0.255"},
    ],
    nat_outside_intf="GigabitEthernet0/3",
    nat_inside_intfs=["GigabitEthernet0/1", "GigabitEthernet0/2"],
)

# ---------- VTY ACL: R1, R2, S1 ----------
vty_acl_commands = render(
    "vty_acl.j2",
    acl_name="VTY_ACCESS",
    permit_networks=[
        {"ip": "172.31.47.0", "wildcard": "0.0.0.15"},
        {"ip": "10.30.6.0", "wildcard": "0.0.0.255"},
        {"ip": "10.253.190.0", "wildcard": "0.0.0.255"},
        {"ip": "192.168.91.0", "wildcard": "0.0.0.255"},
    ],
)

if __name__ == "__main__":
    send(S1_IP, s1_commands, "S1")
    send(R1_IP, r1_commands, "R1")
    send(R2_IP, r2_commands, "R2")

    send(R1_IP, vty_acl_commands, "R1 (VTY ACL)")
    send(R2_IP, vty_acl_commands, "R2 (VTY ACL)")
    send(S1_IP, vty_acl_commands, "S1 (VTY ACL)")