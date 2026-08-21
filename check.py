import urllib.request
import urllib.parse
import re
import socket
import base64
import json
import subprocess
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor

# Большой список источников (с исправленной ссылкой soroushmirzaei)
SOURCES = [
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/verified/configs.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/V2Ray-Config-By-EbraSha.txt",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt"
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
MAX_PER_COUNTRY = 10
TARGET_TOTAL_SERVERS = 100

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
    print(f"Всего источников в списке SOURCES: {len(SOURCES)}")
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
                print(f"  [+] Скачано {len(found)} узлов | {url}")
                for key in found:
                    raw_keys.add(clean_string(key))
        except Exception as e:
            print(f"  [-] Ошибка при скачивании ({e}) | {url}")
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

def auto_push():
    print("\n5. Публикация обновлений на GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update subscription list"], check=False)
        res = subprocess.run(["git", "push"], capture_output=True, text=True)
        if res.returncode == 0:
            print("   [+] Базы успешно выгружены на GitHub!")
        else:
            print(f"   [-] Ошибка при git push: {res.stderr.strip()}")
    except Exception as e:
        print(f"   [-] Ошибка выполнения git: {e}")

def main():
    print("1. Скачивание проверенных баз подписок...")
    candidates = fetch_candidates()
    print(f"\n   Итого уникальных кандидатов со всех источников: {len(candidates)}")

    print("\n2. Быстрый отбор по открытым портам...")
    passed_tcp = []
    with ThreadPoolExecutor(max_workers=120) as executor:
        for res in executor.map(check_port, candidates):
            if res:
                passed_tcp.append(res)
    print(f"   Открытые порты у {len(passed_tcp)} узлов.")

    # Перемешиваем кандидаты для равномерного распределения протоколов
    random.shuffle(passed_tcp)

    print("\n3. HTTP GET проверка с разбавлением по странам...")
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

    print(f"\n4. Сохранение {len(final_working)} серверов...")
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_working))

    b64_content = base64.b64encode("\n".join(final_working).encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

    auto_push()
    print("Готово!")

if __name__ == "__main__":
    main()
