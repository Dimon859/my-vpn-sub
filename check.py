import urllib.request
import socket
import json
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import base64

# Сфокусированные свежие источники
SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TVC/main/subscriptions/xray/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/mft01/Free-V2ray-Config/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber/main/vless.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/ru-sni/vless_ru.txt",
    "https://raw.githubusercontent.com/GoldCaviar/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/main/ByeWhiteLists2.txt"
]

SUPPORTED_PROTOCOLS = ("vless://", "hysteria2://", "hy2://", "trojan://")

def country_code_to_emoji(country_code):
    if not country_code or len(country_code) != 2 or country_code == "XX":
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

def is_anti_block_config(line):
    """Оставляем только Hysteria2, Trojan и VLESS с Reality / TLS / RU-маскировкой"""
    line_lower = line.lower()
    
    if line_lower.startswith(("hysteria2://", "hy2://", "trojan://")):
        return True
        
    if line_lower.startswith("vless://"):
        if "security=reality" in line_lower or "security=tls" in line_lower:
            return True
        if any(ru_host in line_lower for ru_host in ['.ru', 'vk', 'mail', 'yandex', 'ozon', 'sber']):
            return True

    return False

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

def filter_by_country_limit(nodes, limit_per_country=2, max_total=20):
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
                    if line.startswith(SUPPORTED_PROTOCOLS) and is_anti_block_config(line):
                        raw_keys.add(line)
        except Exception:
            continue

    print(f"Собрано уникальных свежих ключей: {len(raw_keys)}")

    raw_keys_list = list(raw_keys)[:2500]

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

    # 1. WHITE LIST (В приоритете VLESS-Reality)
    white_candidates = [
        node for node in valid_nodes 
        if "security=reality" in node[0].lower() or "sni=" in node[0].lower()
    ]
    white_top = filter_by_country_limit(white_candidates, limit_per_country=2, max_total=20)
    
    final_white_keys = [
        format_node_name(line, cc, country_name, idx)
        for idx, (line, host, latency, cc, country_name) in enumerate(white_top, 1)
    ]

    # 2. CLEAN SUB (Общая свежая подборка)
    clean_top = filter_by_country_limit(valid_nodes, limit_per_country=2, max_total=20)
    
    final_clean_keys = [
        format_node_name(line, cc, country_name, idx)
        for idx, (line, host, latency, cc, country_name) in enumerate(clean_top, 1)
    ]

    # Запись
    clean_content = "\n".join(final_clean_keys)
    white_content = "\n".join(final_white_keys)

    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write(clean_content)

    with open("white_list.txt", "w", encoding="utf-8") as f:
        f.write(white_content)

    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(clean_content.encode('utf-8')).decode('utf-8'))

    with open("white_list_base64.txt", "w", encoding="utf-8") as f:
        f.write(base64.b64encode(white_content.encode('utf-8')).decode('utf-8'))

    print("Подписки успешно обновлены новыми базами!")

if __name__ == "__main__":
    main()
