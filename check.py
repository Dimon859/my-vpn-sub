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

SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2ray",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Esl3m/vpn/main/v2ray",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix"
]

TEST_URL = "https://www.youtube.com/generate_204"

def fetch_candidates():
    raw_keys = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read().decode('utf-8', errors='ignore').strip()
                text_to_search = content
                try:
                    padded = content + "=" * ((4 - len(content) % 4) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    if "://" in decoded:
                        text_to_search = decoded
                except Exception:
                    pass

                found = re.findall(r'(?:vless|vmess|hysteria2|hy2|trojan|ss)://[^\s\r\n\'"]+', text_to_search, re.IGNORECASE)
                for key in found:
                    raw_keys.add(key.strip())
        except Exception:
            continue
    return list(raw_keys)

def parse_host_port(link):
    try:
        m = re.search(r'@([^:/]+):(\d+)', link)
        if m:
            return m.group(1), int(m.group(2))
        m2 = re.search(r'://([^:/]+):(\d+)', link)
        if m2:
            return m2.group(1), int(m2.group(2))
    except Exception:
        pass
    return None, None

def check_port(link):
    host, port = parse_host_port(link)
    if not host or not port:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        res = sock.connect_ex((host, port))
        sock.close()
        if res == 0:
            return link
    except Exception:
        pass
    return None

def build_singbox_outbound(link):
    try:
        parsed = urllib.parse.urlparse(link)
        scheme = parsed.scheme.lower()
        
        if scheme == "vless":
            uuid = parsed.username
            host = parsed.hostname
            port = parsed.port
            params = urllib.parse.parse_qs(parsed.query)
            
            outbound = {
                "type": "vless",
                "tag": "proxy",
                "server": host,
                "server_port": port,
                "uuid": uuid
            }
            if params.get("security", [""])[0] in ["tls", "reality"]:
                tls_conf = {"enabled": True, "insecure": True}
                if "sni" in params:
                    tls_conf["server_name"] = params["sni"][0]
                if params.get("security", [""])[0] == "reality":
                    tls_conf["reality"] = {
                        "enabled": True,
                        "public_key": params.get("pbk", [""])[0],
                        "short_id": params.get("sid", [""])[0]
                    }
                outbound["tls"] = tls_conf
            if "type" in params and params["type"][0] == "ws":
                outbound["transport"] = {"type": "ws", "path": params.get("path", ["/"])[0]}
            return outbound

        elif scheme in ["hysteria2", "hy2"]:
            auth = parsed.username or parsed.password
            host = parsed.hostname
            port = parsed.port
            params = urllib.parse.parse_qs(parsed.query)
            outbound = {
                "type": "hysteria2",
                "tag": "proxy",
                "server": host,
                "server_port": port,
                "password": auth,
                "tls": {"enabled": True, "insecure": True}
            }
            if "sni" in params:
                outbound["tls"]["server_name"] = params["sni"][0]
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
        time.sleep(0.8)

        proxy_handler = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{port}', 'https': f'http://127.0.0.1:{port}'})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(TEST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        
        with opener.open(req, timeout=3.0) as resp:
            if resp.status in [200, 204]:
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

def main():
    print("1. Скачивание конфигураций...")
    candidates = fetch_candidates()
    print(f"   Загружено кандидатов: {len(candidates)}")

    print("2. Этап 1: Фильтр по TCP-порту...")
    passed_tcp = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        for res in executor.map(check_port, candidates):
            if res:
                passed_tcp.append(res)
                if len(passed_tcp) >= 150:
                    break
    print(f"   Открытые порты у {len(passed_tcp)} узлов.")

    print("3. Этап 2: Настоящая L7-проверка через sing-box...")
    final_working = []
    for link in passed_tcp:
        if verify_l7(link):
            final_working.append(link)
            print(f"   [+] Сервер #{len(final_working)} прошел честный HTTP-тест!")
            if len(final_working) >= 15:
                break

    if not final_working:
        print("   Ни один сервер не прошел L7-тест.")
        return

    print(f"4. Сохранение {len(final_working)} проверенных серверов...")
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_working))

    b64_content = base64.b64encode("\n".join(final_working).encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

    print("Готово!")

if __name__ == "__main__":
    main()
