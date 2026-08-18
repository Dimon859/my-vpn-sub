import urllib.request
import socket
from urllib.parse import urlparse

# 1. Вставьте сюда ссылки на источники (RAW-тексты подписок)
SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-configs-for-russia/main/githubmirror/ru-sni/vless_ru.txt"
]

def check_host(host, port, timeout=2):
    """ Проверка доступности сокета по IP/Порту """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except Exception:
        return False

clean_keys = []

for url in SOURCES:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            lines = response.read().decode('utf-8', errors='ignore').splitlines()
            for line in lines:
                line = line.strip()
                if line.startswith("vless://"):
                    try:
                        # Извлекаем IP и порт из vless://
                        parsed = urlparse(line)
                        netloc = parsed.netloc.split('@')[-1]
                        host, port = netloc.split(':')
                        
                        # Если сервер откликается — добавляем в чистый список
                        if check_host(host, port):
                            clean_keys.append(line)
                    except Exception:
                        continue
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# Ограничиваем список максимум 30 лучшими нодами, чтобы не лагал телефон
clean_keys = list(set(clean_keys))[:30]

with open("clean_sub.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(clean_keys))

print(f"Done! Clean nodes saved: {len(clean_keys)}")
