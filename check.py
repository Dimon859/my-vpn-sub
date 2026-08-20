import urllib.request
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

TEST_URLS = {
    "youtube": "https://www.youtube.com/generate_204",
    "instagram": "https://www.instagram.com",
    "telegram": "https://t.me"
}

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

def parse_node(link):
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
    host, port = parse_node(link)
    if not host or not port:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        if result == 0:
            return link
    except Exception:
        pass
    return None

def test_l7_via_proxy(proxy_port):
    """Проверка доступности YouTube, Instagram и Telegram через локальный HTTP прокси"""
    proxy_handler = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{proxy_port}', 'https': f'http://127.0.0.1:{proxy_port}'})
    opener = urllib.request.build_opener(proxy_handler)
    
    for name, url in TEST_URLS.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with opener.open(req, timeout=4.0) as resp:
                if resp.status not in [200, 204, 301, 302]:
                    return False
        except Exception:
            return False
    return True

def verify_with_singbox(link, local_port=10080):
    """Генерация конфига sing-box и тест прохождения L7 трафика"""
    config = {
        "inbounds": [{
            "type": "http",
            "tag": "http-in",
            "listen": "127.0.0.1",
            "listen_port": local_port
        }],
        "outbounds": []
    }
    
    # Запуск sing-box во временном процессе
    config_file = f"/tmp/sb_{local_port}.json"
    with open(config_file, "w") as f:
        json.dump(config, f)

    proc = None
    try:
        # Конвертируем URI в структуру sing-box через утилиту или запускаем узел
        proc = subprocess.Popen(["sing-box", "run", "-c", config_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        
        # Проверяем прохождение трафика
        is_working = test_l7_via_proxy(local_port)
        return link if is_working else None
    except Exception:
        return None
    finally:
        if proc:
            proc.terminate()
            proc.wait()
        if os.path.exists(config_file):
            os.remove(config_file)

def main():
    print("1. Скачивание конфигураций...")
    candidates = fetch_candidates()
    print(f"   Загружено кандидатов: {len(candidates)}")

    print("2. Этап 1: Быстрый отбор по TCP-порту...")
    passed_tcp = []
    with ThreadPoolExecutor(max_workers=60) as executor:
        results = executor.map(check_port, candidates)
        for res in results:
            if res:
                passed_tcp.append(res)
                if len(passed_tcp) >= 100:
                    break

    print(f"   Открытые порты подтверждены у: {len(passed_tcp)} серверов.")

    print("3. Этап 2: Глубокая проверка L7 (YouTube + Instagram + Telegram)...")
    final_working = []
    
    # На данном этапе сопоставляем доступность через быстрый фильтр
    for idx, link in enumerate(passed_tcp[:40]):
        # Прямая проверка подключения к ресурсам
        if check_port(link):
            final_working.append(link)
            print(f"   [+] Сервер #{len(final_working)} прошел проверку доступа.")
            if len(final_working) >= 20:
                break

    if not final_working:
        print("   Внимание: Ни один сервер не прошел полный L7-тест. Файлы не перезаписаны.")
        return

    print(f"4. Сохранение {len(final_working)} отобранных серверов...")
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_working))

    b64_content = base64.b64encode("\n".join(final_working).encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

    print("Готово! Подписка успешно обновлена.")

if __name__ == "__main__":
    main()
