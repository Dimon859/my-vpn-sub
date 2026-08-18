import urllib.request
import socket
import json
import time
from urllib.parse import urlparse, unquote, quote
from concurrent.futures import ThreadPoolExecutor
import base64

SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/GoldCaviar/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_SS%2BAll_RUS.txt",
    "https://cdn.jsdelivr.net/gh/igareck/vpn-configs-for-russia@main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/ru-sni/vless_ru.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/sub/vless",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/sub/hysteria2",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha-All-Type.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/vless_configs.txt",
    "https://raw.githubusercontent.com/AvenCores/goida-vpn-configs/main/githubmirror/26.txt",
    "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/main/ByeWhiteLists2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"
]

SUPPORTED_PROTOCOLS = ("vless://", "hysteria2://", "hy2://", "ss://", "trojan://")

def country_code_to_emoji(country_code):
    if not country_code or len(country_code) != 2:
        return "🌐"
    return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

def get_ip_location(host):
    try:
        url = f"http://ip-api.com/json/{host}?fields=status,countryCode,country"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as resp:
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

def check_and_ping_node(item):
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

def format_node_name(line, country_code, country_name, index):
    flag = country_code_to_emoji(country_code)
    base_key = line.split("#")[0]
    new_name = f"{flag} {country_name} #{index}"
    return f"{base_key}#{quote(new_name)}"

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
                        raw_keys.add(line)
        except Exception:
            continue

    print(f"Собрано уникальных ключей: {len(raw_keys)}")

    raw_keys_list = list(raw_keys)[:3000]
    print(f"Отправляем на проверку первые {len(raw_keys_list)} серверов...")

    candidates = []
    for key in raw_keys_list:
        host, port = parse_node(key)
        if host and port:
            candidates.append((key, host, port))

    valid_nodes = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_and_ping_node, candidates)
        for line, host, latency in results:
            if line and host:
                valid_nodes.append((line, host, latency))

    valid_nodes.sort(key=lambda x: x[2])

    unique_nodes = []
    seen_ips = set()
    for line, host, latency in valid_nodes:
        if host not in seen_ips:
            seen_ips.add(host)
            unique_nodes.append((line, host, latency))

    top_nodes = unique_nodes[:25]

    final_keys = []
    country_counters = {}
    
    for line, host, latency in top_nodes:
        cc, country_name = get_ip_location(host)
        country_counters[cc] = country_counters.get(cc, 0) + 1
        formatted_key = format_node_name(line, cc, country_name, country_counters[cc])
        final_keys.append(formatted_key)

    clean_content = "\n".join(final_keys)
    
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write(clean_content)

    with open("white_list.txt", "w", encoding="utf-8") as f:
        f.write(clean_content)

    base64_content = base64.b64encode(clean_content.encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(base64_content)

    print(f"Успешно сохранено {len(final_keys)} самых быстрых серверов с флагами!")

if __name__ == "__main__":
    main()
