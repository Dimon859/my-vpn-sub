import urllib.request
import socket
import json
import time
import subprocess
import os
import tempfile
from urllib.parse import quote, parse_qs, urlparse
from concurrent.futures import ThreadPoolExecutor
import base64

SOURCES = [
    "https://raw.githubusercontent.com/GoldCaviar/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/ru-sni/vless_ru.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
    "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/main/ByeWhiteLists2.txt",
    "https://raw.githubusercontent.com/AvenCores/goida-vpn-configs/main/githubmirror/26.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/mft01/Free-V2ray-Config/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber/main/vless.txt"
]

SUPPORTED_PROTOCOLS = ("vless://", "hysteria2://", "hy2://", "trojan://")
TEST_URLS = [
    "https://www.youtube.com",
    "https://www.instagram.com",
    "https://api.telegram.org"
]

def country_code_to_emoji(country_code):
    if not country_code or len(country_code) != 2 or country_code == "XX":
        return "🌐"
    return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

def get_ip_location(host):
    try:
        url = f"http://ip-api.com/json/{host}?fields=status,countryCode,country"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 'success':
                return data.get('countryCode', 'XX'), data.get('country', 'Unknown')
    except Exception:
        pass
    return "XX", "Unknown"

def decode_base64_if_needed(content):
    try:
        decoded = base64.b64decode(content.strip()).decode('utf-8', errors='ignore')
        if any(decoded.startswith(p) for p in SUPPORTED_PROTOCOLS):
            return decoded
    except Exception:
        pass
    return content

def parse_node(line):
    try:
        raw = line.split("://", 1)[1]
        raw = raw.split("#")[0].split("?")[0]
        if "@" in raw:
            raw = raw.split("@")[-1]
        
        if raw.startswith("["):
            host = raw.split("]")[0] + "]"
            port = raw.split("]:")[-1]
        else:
            host, port = raw.split(":")
            
        return host.strip(), int(port.strip())
    except Exception:
        return None, None

def check_tcp_port(item):
    line, host, port = item
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        res = sock.connect_ex((host, port))
        latency = (time.time() - start_time) * 1000
        sock.close()
        if res == 0:
            return line, host, round(latency, 1)
    except Exception:
        pass
    return None, None, None

def build_singbox_outbound(line):
    try:
        parsed = urlparse(line)
        protocol = parsed.scheme
        user_info = parsed.username or parsed.netloc.split("@")[0]
        host = parsed.hostname
        port = parsed.port
        params = parse_qs(parsed.query)

        if protocol == "vless":
            outbound = {
                "type": "vless",
                "tag": "proxy",
                "server": host,
                "server_port": port,
                "uuid": user_info,
                "flow": params.get("flow", [""])[0]
            }
            security = params.get("security", ["none"])[0]
            if security in ["tls", "reality"]:
                tls_conf = {
                    "enabled": True,
                    "server_name": params.get("sni", [params.get("servername", [""])[0]])[0],
                    "insecure": True
                }
                if security == "reality":
                    tls_conf["reality"] = {
                        "enabled": True,
                        "public_key": params.get("pbk", [""])[0],
                        "short_id": params.get("sid", [""])[0]
                    }
                outbound["tls"] = tls_conf
            return outbound

        elif protocol in ["hysteria2", "hy2"]:
            return {
                "type": "hysteria2",
                "tag": "proxy",
                "server": host,
                "server_port": port,
                "password": user_info,
                "tls": {
                    "enabled": True,
                    "server_name": params.get("sni", [""])[0],
                    "insecure": True
                }
            }
    except Exception:
        pass
    return None

def verify_services_via_singbox(line, port_index):
    outbound = build_singbox_outbound(line)
    if not outbound:
        return False

    socks_port = 20000 + (port_index % 500)
    config = {
        "log": {"level": "panic"},
        "inbounds": [{
            "type": "socks",
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "listen_port": socks_port
        }],
        "outbounds": [outbound]
    }

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(config, f)
        config_path = f.name

    proc = None
    try:
        proc = subprocess.Popen(
            ["sing-box", "run", "-c", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.4)

        proxy_url = f"socks5h://127.0.0.1:{socks_port}"
        success_count = 0

        for target_url in TEST_URLS:
            try:
                cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "3.5", "--proxy", proxy_url, target_url]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.stdout.strip() in ["200", "301", "302", "404"]:
                    success_count += 1
            except Exception:
                pass

        return success_count == len(TEST_URLS)

    except Exception:
        return False
    finally:
        if proc:
            proc.kill()
            proc.wait()
        if os.path.exists(config_path):
            os.remove(config_path)

def format_node_name(line, country_code, country_name, index):
    flag = country_code_to_emoji(country_code)
    base_key = line.split("#")[0]
    new_name = f"{flag} {country_name} #{index}"
    return f"{base_key}#{quote(new_name)}"

def filter_by_country_limit(nodes, limit_per_country=5, max_total=50):
    selected = []
    country_counts = {}
    seen_ips = set()

    for line, host, latency in nodes:
        if host in seen_ips:
            continue
            
        cc, country_name = get_ip_location(host)
        current_count = country_counts.get(cc, 0)
        
        if current_count < limit_per_country:
            country_counts[cc] = current_count + 1
            seen_ips.add(host)
            selected.append((line, host, latency, cc, country_name))
            
        if len(selected) >= max_total:
            break
            
    return selected

def main():
    raw_keys = set()
    
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
                content = decode_base64_if_needed(content)
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith(SUPPORTED_PROTOCOLS):
                        if line.startswith("vless://") and not ("security=reality" in line.lower() or "security=tls" in line.lower()):
                            continue
                        raw_keys.add(line)
        except Exception:
            continue

    print(f"Загружено уникальных кандидатов: {len(raw_keys)}")

    candidates = []
    for key in list(raw_keys)[:2500]:
        host, port = parse_node(key)
        if host and port:
            candidates.append((key, host, port))

    print("Этап 1: Быстрая проверка портов через провайдера...")
    stage1_passed = []
    with ThreadPoolExecutor(max_workers=60) as executor:
        results = executor.map(check_tcp_port, candidates)
        for line, host, latency in results:
            if line and host:
                stage1_passed.append((line, host, latency))

    print(f"Прошли первичную проверку: {len(stage1_passed)} серверов.")
    print("Этап 2: Глубокая проверка сервисов (YouTube, Instagram, Telegram) через sing-box...")

    fully_working_nodes = []
    
    def worker(idx_item):
        idx, (line, host, latency) = idx_item
        if verify_services_via_singbox(line, idx):
            return line, host, latency
        return None, None, None

    indexed_candidates = list(enumerate(stage1_passed[:150]))
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(worker, indexed_candidates)
        for line, host, latency in results:
            if line and host:
                fully_working_nodes.append((line, host, latency))

    fully_working_nodes.sort(key=lambda x: x[2])
    print(f"Итого проверенных 100% рабочих серверов: {len(fully_working_nodes)}")

    top_nodes = filter_by_country_limit(fully_working_nodes, limit_per_country=5, max_total=50)
    
    final_keys = [
        format_node_name(line, cc, country_name, idx)
        for idx, (line, host, latency, cc, country_name) in enumerate(top_nodes, 1)
    ]

    clean_content = "\n".join(final_keys)

    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write(clean_content)

    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(clean_content.encode('utf-8')).decode('utf-8'))

    print("Подписка с проверенными ресурсами сформирована!")

if __name__ == "__main__":
    main()
