import pytest
from netmiko import ConnectHandler
import os

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

EXPECTED_DESCRIPTIONS = {
    "R1": {
        "Gi0/0": "Connect to Gi0/1 of S0",
        "Gi0/1": "Connect to PC",
        "Gi0/2": "Connect to Gi0/1 of R2",
    },
    "R2": {
        "Gi0/0": "Connect to Gi0/2 of S0",
        "Gi0/1": "Connect to Gi0/2 of R1",
        "Gi0/2": "Connect to Gi0/1 of S1",
        "Gi0/3": "Connect to WAN",
    },
    "S1": {
        "Gi0/1": "Connect to Gi0/2 of R2",
        "Gi0/2": "Connect to PC",
        "Gi0/3": "Connect to Gi0/3 of S0",
    },
}


@pytest.fixture(scope="module")
def connections():
    conns = {}
    for name, ip in devices.items():
        conns[name] = ConnectHandler(**{**BASE, "ip": ip})
    yield conns
    for conn in conns.values():
        conn.disconnect()


@pytest.mark.parametrize("device_name", ["R1", "R2", "S1"])
def test_interface_descriptions(connections, device_name):
    conn = connections[device_name]
    output = conn.send_command("show interfaces description", use_textfsm=True)
    print(f"\nRAW OUTPUT for {device_name}: {output}")

    actual = {}
    for entry in output:
        actual[entry["port"]] = entry.get("description", "").strip()
    expected = EXPECTED_DESCRIPTIONS[device_name]
    for interface, expected_desc in expected.items():
        assert interface in actual, f"{interface} not found on {device_name}"
        assert actual[interface] == expected_desc