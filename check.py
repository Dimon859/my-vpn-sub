import urllib.request
import urllib.parse
import re
import socket
import base64
import json
import subprocess
import time
import os
from concurrent.futures import ThreadPoolExecutor

# Расширенный список источников (60+ агрегаторов и подписок)
SOURCES = [
    # GitHub Aggregators & Auto-collectors
    "https://raw.githubusercontent.com/freefq/free/master/v2ray",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Esl3m/vpn/main/v2ray",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/Loperamido/v2ray-subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/mft0/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs/main/happy",
    "https://raw.githubusercontent.com/aamilf/v2ray-collector/main/sub/all.txt",
    "https://raw.githubusercontent.com/vless-collector/vless-sub/main/vless.txt",
    "https://raw.githubusercontent.com/ts-indexer/sub-collector/main/sub/mix.txt",
    "https://raw.githubusercontent.com/Awesome-V2Ray/V2Ray-Config/main/sub.txt",
    "https://raw.githubusercontent.com/peassfull/v2ray-collector/main/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/mosec-sub/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/alien-vpn/free-vpn/main/sub.txt",
    "https://raw.githubusercontent.com/v2ray-free/free-v2ray-config/main/sub.txt",
    "https://raw.githubusercontent.com/vpn-collector/free-sub/main/sub.txt",
    "https://raw.githubusercontent.com/roosterkiev/optimus/main/sub.txt",
    "https://raw.githubusercontent.com/shafinet/v2ray-configs/main/all.txt",
    "https://raw.githubusercontent.com/coldbird-sub/v2ray/main/sub.txt",
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber/main/sub.txt",
    "https://raw.githubusercontent.com/v2rayk/v2ray-free/master/v2ray",
    "https://raw.githubusercontent.com/Pillar-v2ray/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/x2ray/v2ray-configs/main/sub.txt",
    "https://raw.githubusercontent.com/Leon4rdo-V2ray/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/crackas/v2ray-collector/main/sub.txt",
    "https://raw.githubusercontent.com/V2ray-Central/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/BtechVpn/V2ray-Collector/main/sub.txt",
    "https://raw.githubusercontent.com/erik-sub/v2ray-collector/main/sub.txt",
    # Telegram-based categories
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/reality/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vmess/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vless/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/trojan/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/shadowsocks/mix",
    # Additional large nodes feeds
    "https://raw.githubusercontent.com/aungthurha/v2ray-collector/main/sub.txt",
    "https://raw.githubusercontent.com/K3R3M-K/v2ray-collector/main/sub.txt",
    "https://raw.githubusercontent.com/mhayas/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/darknessv2ray/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/Snape-v2ray/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/404p/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/Mo-V2ray/V2ray-Configs/main/sub.txt",
    "https://raw.githubusercontent.com/Bayan-V2ray/V2ray-Configs/main/sub.txt",
    "https://raw.githubusercontent.com/vless-nodes/vless/main/sub.txt",
    "https://raw.githubusercontent.com/free-v2ray/v2ray-node/master/sub.txt",
    "https://raw.githubusercontent.com/Sora-V2ray/V2ray-Configs/main/sub.txt",
    "https://raw.githubusercontent.com/OpenV2Ray/V2Ray-Config/main/sub.txt",
    "https://raw.githubusercontent.com/ShadowSocks-Nodes/ShadowSocks/main/sub.txt",
    "https://raw.githubusercontent.com/Xray-Nodes/Xray-Configs/main/sub.txt",
    "https://raw.githubusercontent.com/FreeV2RayNodes/V2Ray/main/sub.txt",
    "https://raw.githubusercontent.com/V2ray-Free-Nodes/V2Ray/main/sub.txt",
    "https://raw.githubusercontent.com/v2ray-sub-pool/v2ray/main/sub.txt",
    "https://raw.githubusercontent.com/VPN-Collector/V2Ray-Collector/main/sub.txt",
    "https://raw.githubusercontent.com/Fast-V2Ray/V2Ray-Configs/main/sub.txt",
    "https://raw.githubusercontent.com/Pro-V2Ray/V2Ray-Configs/main/sub.txt"
]

TEST_URLS = [
    "https://www.youtube.com/generate_204",
    "https://www.instagram.com",
    "https://api.telegram.org"
]

COUNTRY_FLAGS = {
    "US": "🇺🇸", "DE": "🇩🇪", "NL": "🇳🇱", "FR": "🇫🇷", "GB": "🇬🇧",
    "FI": "🇫🇮", "PL": "🇵🇱", "SE": "🇸🇪", "JP": "🇯🇵", "SG": "🇸🇬",
    "KR": "🇰🇷", "TR": "🇹🇷", "CA": "🇨🇦", "AU": "🇦🇺", "CH": "🇨🇭",
    "IE": "🇮🇪", "IT": "🇮🇹", "ES": "🇪🇸", "CZ": "🇨🇿", "AT": "🇦🇹"
}

IP_CACHE = {}
MAX_PER_COUNTRY = 3  # Максимум 3 сервера от одной страны для разнообразия
TARGET_TOTAL_SERVERS = 40  # Всего рабочих серверов в готовой подписке

def get_country_info(host):
    if host in IP_CACHE:
        return IP_CACHE[host]
    try:
        req = urllib.request.Request(f"http://ip-api.com/json/{host}?fields=status,countryCode", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("status") == "success":
                code = data.get("countryCode", "UN")
                flag = COUNTRY_FLAGS.get(code, "🌐")
                result = (code, flag)
                IP_CACHE[host] = result
                return result
    except Exception:
        pass
    return "UN", "🌐"

def clean_string(s):
    return s.strip().replace('\r', '').replace('\n', '')

def fetch_candidates():
    raw_keys = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read().decode('utf-8', errors='ignore')
                text_to_search = content
                try:
                    padded = content.strip() + "=" * ((4 - len(content.strip()) % 4) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    if "://" in decoded:
                        text_to_search = decoded
                except Exception:
                    pass

                found = re.findall(r'(?:vless|vmess|ss|trojan|hysteria2|hy2)://[^\s\r\n\'"]+', text_to_search, re.IGNORECASE)
                for key in found:
                    raw_keys.add(clean_string(key))
        except Exception:
            continue
    return list(raw_keys)

def parse_host_port(link):
    try:
        m = re.search(r'@([^:/]+):(\d+)', link)
        if m: return m.group(1), int(m.group(2))
        m2 = re.search(r'://([^:/]+):(\d+)', link)
        if m2: return m2.group(1), int(m2.group(2))
    except Exception:
        pass
    return None, None

def check_port(link):
    host, port = parse_host_port(link)
    if not host or not port:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.2)
        res = sock.connect_ex((host, port))
        sock.close()
        if res == 0:
            return link
    except Exception:
        pass
    return None

def build_singbox_outbound(link):
    try:
        clean_link = clean_string(link)
        parsed = urllib.parse.urlparse(clean_link)
        scheme = parsed.scheme.lower()
        
        if scheme == "vless":
            uuid = parsed.username
            host = parsed.hostname
            port = parsed.port
            params = urllib.parse.parse_qs(parsed.query)
            if not host or not port or not uuid: return None
            outbound = {"type": "vless", "tag": "proxy", "server": host, "server_port": port, "uuid": uuid}
            sec = params.get("security", [""])[0]
            if sec in ["tls", "reality"]:
                tls_conf = {"enabled": True, "insecure": True}
                if "sni" in params: tls_conf["server_name"] = params["sni"][0]
                if sec == "reality":
                    tls_conf["reality"] = {"enabled": True, "public_key": params.get("pbk", [""])[0], "short_id": params.get("sid", [""])[0]}
                outbound["tls"] = tls_conf
            if params.get("type", [""])[0] == "ws":
                outbound["transport"] = {"type": "ws", "path": params.get("path", ["/"])[0]}
            return outbound

        elif scheme in ["hysteria2", "hy2"]:
            auth = parsed.username or parsed.password
            host = parsed.hostname
            port = parsed.port
            params = urllib.parse.parse_qs(parsed.query)
            if not host or not port or not auth: return None
            outbound = {"type": "hysteria2", "tag": "proxy", "server": host, "server_port": port, "password": auth, "tls": {"enabled": True, "insecure": True}}
            if "sni" in params: outbound["tls"]["server_name"] = params["sni"][0]
            return outbound

        elif scheme == "trojan":
            password = parsed.username
            host = parsed.hostname
            port = parsed.port
            params = urllib.parse.parse_qs(parsed.query)
            if not host or not port or not password: return None
            outbound = {"type": "trojan", "tag": "proxy", "server": host, "server_port": port, "password": password, "tls": {"enabled": True, "insecure": True}}
            if "sni" in params: outbound["tls"]["server_name"] = params["sni"][0]
            return outbound
    except Exception:
        pass
    return None

def verify_l7(link, port=10080):
    outbound = build_singbox_outbound(link)
    if not outbound:
        return False

    config = {
        "inbounds": [{"type": "http", "tag": "http-in", "listen": "127.0.0.1", "listen_port": port}],
        "outbounds": [outbound]
    }

    cfg_path = f"/tmp/sb_{port}.json"
    with open(cfg_path, "w") as f:
        json.dump(config, f)

    proc = None
    try:
        proc = subprocess.Popen(["sing-box", "run", "-c", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.7)

        proxy_handler = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{port}', 'https': f'http://127.0.0.1:{port}'})
        opener = urllib.request.build_opener(proxy_handler)
        
        for url in TEST_URLS:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with opener.open(req, timeout=3.5) as resp:
                if resp.status not in [200, 204]:
                    return False
        return True
    except Exception:
        return False
    finally:
        if proc:
            proc.terminate()
            proc.wait()
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
    return False

def rename_link(link, index, code, flag):
    scheme = link.split("://")[0].upper()
    if scheme == "HY2": scheme = "Hysteria2"

    clean_label = f"{flag} {code} | {scheme}-{index}"
    base_part = link.split("#")[0]
    return f"{base_part}#{urllib.parse.quote(clean_label)}"

def main():
    print("1. Скачивание расширенных баз подписок...")
    candidates = fetch_candidates()
    print(f"   Загружено кандидатов: {len(candidates)}")

    print("2. Быстрый отбор по открытым портам...")
    passed_tcp = []
    with ThreadPoolExecutor(max_workers=120) as executor:
        for res in executor.map(check_port, candidates):
            if res:
                passed_tcp.append(res)
    print(f"   Открытые порты у {len(passed_tcp)} узлов.")

    print("3. HTTP GET проверка с распределением по странам...")
    final_working = []
    country_counts = {}

    for link in passed_tcp:
        host, _ = parse_host_port(link)
        code, flag = get_country_info(host) if host else ("UN", "🌐")

        if country_counts.get(code, 0) >= MAX_PER_COUNTRY:
            continue

        if verify_l7(link):
            country_counts[code] = country_counts.get(code, 0) + 1
            renamed = rename_link(link, country_counts[code], code, flag)
            final_working.append(renamed)
            print(f"   [+] Найден сервер #{len(final_working)} ({code}): {urllib.parse.unquote(renamed.split('#')[-1])}")
            
            if len(final_working) >= TARGET_TOTAL_SERVERS:
                break

    if not final_working:
        print("   Рабочих серверов не найдено.")
        return

    print(f"4. Сохранение {len(final_working)} разноплановых серверов...")
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_working))

    b64_content = base64.b64encode("\n".join(final_working).encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

    print("Готово!")

if __name__ == "__main__":
    main()
