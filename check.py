import urllib.request
import re
import socket
import base64
from concurrent.futures import ThreadPoolExecutor

# Актуальные источники подписок (как Base64, так и открытый текст)
SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2ray",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Esl3m/vpn/main/v2ray",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_FREE.txt"
]

def fetch_candidates():
    """Скачивание и извлечение конфигураций из всех источников"""
    raw_keys = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read().decode('utf-8', errors='ignore').strip()
                text_to_search = content
                
                # Автоматическая попытка разблокировать Base64
                try:
                    padded = content + "=" * ((4 - len(content) % 4) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    if "://" in decoded:
                        text_to_search = decoded
                except Exception:
                    pass

                # Поиск всех поддерживаемых протоколов
                found = re.findall(
                    r'(?:vless|vmess|hysteria2|hy2|trojan|ss)://[^\s\r\n\'"]+', 
                    text_to_search, 
                    re.IGNORECASE
                )
                for key in found:
                    raw_keys.add(key.strip())
        except Exception:
            continue
            
    return list(raw_keys)

def parse_node(link):
    """Извлечение хоста/IP и порта из URI ссылки"""
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
    """Проверка доступности TCP-порта узла"""
    host, port = parse_node(link)
    if not host or not port:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.5)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        if result == 0:
            return link
    except Exception:
        pass
    return None

def main():
    print("1. Скачивание подписок из источников...")
    candidates = fetch_candidates()
    print(f"   Загружено уникальных кандидатов: {len(candidates)}")

    if not candidates:
        print("   Ошибка: не удалось получить серверы из источников.")
        return

    print("2. Быстрая многопоточная проверка доступности портов...")
    passed_servers = []
    
    # Используем 50 параллельных потоков для моментальной проверки
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_port, candidates)
        for res in results:
            if res:
                passed_servers.append(res)
                if len(passed_servers) >= 150:  # Ограничение лучших серверов для базы
                    break

    print(f"   Успешно прошли проверку портов: {len(passed_servers)} серверов.")

    if not passed_servers:
        print("   Внимание: Ни один сервер не ответил. Файлы не перезаписаны.")
        return

    print("3. Сохранение рабочих конфигураций...")
    
    # Сохранение чистого списка в открытом текстовом формате
    with open("clean_sub.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(passed_servers))

    # Сохранение списка в формате Base64
    b64_content = base64.b64encode("\n".join(passed_servers).encode('utf-8')).decode('utf-8')
    with open("clean_sub_base64.txt", "w", encoding="utf-8") as f:
        f.write(b64_content)

    print("Готово! Подписка успешно обновлена.")

if __name__ == "__main__":
    main()
