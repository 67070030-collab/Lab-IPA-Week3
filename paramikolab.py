import os
import paramiko

# Map ของอุปกรณ์ทั้งหมดที่ต้อง SSH เข้าไป (Management VRF)
devices = {
    "R0": "172.31.47.1",
    "R1": "172.31.47.4",
    "R2": "172.31.47.5",
    "S0": "172.31.47.2",
    "S1": "172.31.47.3",
}

USERNAME = "admin"

# ใช้ os.path.expanduser แทน hardcode path
# ทำงานได้ทั้ง Windows / Linux / Mac โดยไม่ต้องแก้ path เอง
private_key_path = os.path.expanduser("~/.ssh/id_rsa")

try:
    private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
except FileNotFoundError:
    print(f"ไม่พบ private key ที่ {private_key_path}")
    raise
except paramiko.SSHException as e:
    print(f"อ่าน private key ไม่ได้ (key format ผิด หรือมี passphrase): {e}")
    raise

for name, ip in devices.items():
    print(f"\n=== Connecting to {name} ({ip}) ===")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=ip,
            username=USERNAME,
            pkey=private_key,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        stdin, stdout, stderr = client.exec_command("show ip int brief")
        output = stdout.read().decode()
        error = stderr.read().decode()

        if output:
            print(output)
        if error:
            print(f"[stderr] {error}")

    except paramiko.AuthenticationException:
        print(f"[{name}] Authentication ล้มเหลว — เช็ค public key ที่ config บน router ว่าตรงกับ private key ไหม")
    except paramiko.SSHException as e:
        print(f"[{name}] SSH error: {e}")
    except TimeoutError:
        print(f"[{name}] Timeout — เช็คว่า ping ผ่าน VRF management ไป {ip} ได้ไหม")
    except Exception as e:
        print(f"[{name}] Failed to connect: {e}")
    finally:
        client.close()

# --- ดึง running-config ของ R0 เก็บลงไฟล์ ---
print("\n=== Fetching R0 running-config ===")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(
        hostname=devices["R0"],
        username=USERNAME,
        pkey=private_key,
        look_for_keys=False,
        allow_agent=False,
        timeout=10,
    )
    stdin, stdout, stderr = client.exec_command("show running-config")
    config_output = stdout.read().decode()

    with open("R0_running_config.txt", "w") as f:
        f.write(config_output)

    print("Saved R0 running-config to R0_running_config.txt")
except Exception as e:
    print(f"Failed to fetch R0 config: {e}")
finally:
    client.close()