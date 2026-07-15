from netmiko import ConnectHandler

# ==== Connection info (ใช้ SSH key auth ที่ตั้งไว้จาก lab paramiko) ====
BASE = {
    "device_type": "cisco_ios",
    "username": "admin",
    "use_keys": True,
    "key_file": r"C:\Users\HP\.ssh\id_rsa",   # แก้ตาม path จริงของเครื่องคุณ
    "allow_agent": False,
}

R1_IP = "172.31.47.4"
R2_IP = "172.31.47.5"
S1_IP = "172.31.47.3"

MGMT_NET = "172.31.47.0 0.0.0.15"
LAB306_NET = "10.30.6.0 0.0.0.255"
VPN_NET = "10.253.190.0 0.0.0.255"
LOCAL_TEST_NET = "192.168.91.0 0.0.0.255"


def send(device_ip, commands, label):
    device = {**BASE, "ip": device_ip}
    print(f"\n=== Connecting to {label} ({device_ip}) ===")
    conn = ConnectHandler(**device)
    output = conn.send_config_set(commands)
    print(output)
    conn.save_config()
    conn.disconnect()


# ---------- S1: VLAN101 for control/data plane ----------
s1_commands = [
    "vlan 101",
    " name CONTROL-DATA",
    "exit",
    "interface GigabitEthernet0/1",
    " switchport mode access",
    " switchport access vlan 101",
    "interface GigabitEthernet0/2",
    " switchport mode access",
    " switchport access vlan 101",
    "exit",
]

# ---------- R1: OSPF ----------
r1_commands = [
    "router ospf 1 vrf control-data",
    " router-id 1.1.1.1",
    " network 192.168.10.0 0.0.0.255 area 0",
    " network 192.168.47.0 0.0.0.3 area 0",
    " network 1.1.1.1 0.0.0.0 area 0",
    "exit",
    "interface loopback0",
    " vrf forwarding control-data",
    " ip address 1.1.1.1 255.255.255.255",
    "exit",
]

# ---------- R2: OSPF + default route + PAT ----------
r2_commands = [
    "router ospf 1 vrf control-data",
    " router-id 2.2.2.2",
    " network 192.168.47.0 0.0.0.3 area 0",
    " network 192.168.20.0 0.0.0.255 area 0",
    " network 2.2.2.2 0.0.0.0 area 0",
    " default-information originate",
    "exit",
    "interface loopback0",
    " vrf forwarding control-data",
    " ip address 2.2.2.2 255.255.255.255",
    "exit",
    "ip route vrf control-data 172.31.47.0 255.255.255.240 Null0",
    "ip route vrf control-data 0.0.0.0 0.0.0.0 dhcp",
    "ip access-list standard NAT_YELLOW",
    " permit 192.168.10.0 0.0.0.255",
    " permit 192.168.20.0 0.0.0.255",
    "exit",
    "interface GigabitEthernet0/3",
    " ip nat outside",
    "exit",
    "interface GigabitEthernet0/1",
    " ip nat inside",
    "exit",
    "interface GigabitEthernet0/2",
    " ip nat inside",
    "exit",
    "ip nat inside source list NAT_YELLOW interface GigabitEthernet0/3 overload",
]

# ---------- ACL จำกัด VTY: R1, R2, S1 ----------
vty_acl_commands = [
    "no ip access-list standard VTY_ACCESS",
    "ip access-list standard VTY_ACCESS",
    f" permit {MGMT_NET}",
    f" permit {LAB306_NET}",
    f" permit {VPN_NET}",
    f" permit {LOCAL_TEST_NET}",
    " deny any log",
    "exit",
    "line vty 0 4",
    " access-class VTY_ACCESS in",
    "exit",
]

if __name__ == "__main__":
    send(S1_IP, s1_commands, "S1")
    send(R1_IP, r1_commands, "R1")
    send(R2_IP, r2_commands, "R2")

    send(R1_IP, vty_acl_commands, "R1 (VTY ACL)")
    send(R2_IP, vty_acl_commands, "R2 (VTY ACL)")
    send(S1_IP, vty_acl_commands, "S1 (VTY ACL)")