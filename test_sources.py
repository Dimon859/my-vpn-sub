import urllib.request
import urllib.parse
import re
import base64
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    # Основные гигантские подписки
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
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/reality/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vmess/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vless/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/trojan/mix",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/shadowsocks/mix",
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

def check_single_source(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            text_to_search = content
            try:
                padded = content.strip() + "=" * ((4 - len(content.strip()) % 4) % 4)
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                if "://" in decoded:
                    text_to_search = decoded
            except Exception:
                pass

            found = re.findall(r'(?:vless|vmess|ss|trojan|hysteria2|hy2)://[^\s\r\n\'"]+', text_to_search, re.IGNORECASE)
            return url, len(found), "OK"
    except Exception as e:
        return url, 0, f"Error: {e}"

print("=== Проверка каждого источника по отдельности ===")
all_keys = set()
with ThreadPoolExecutor(max_workers=20) as executor:
    results = list(executor.map(check_single_source, SOURCES))

valid_sources = []
empty_sources = []

for url, count, status in results:
    if count > 0:
        print(f"[+] {count} серверов | {url}")
        valid_sources.append(url)
    else:
        print(f"[-] 0 серверов ({status}) | {url}")
        empty_sources.append(url)

print("\n-------------------------------------------")
print(f"Всего источников в списке: {len(SOURCES)}")
print(f"Рабочих источников: {len(valid_sources)}")
print(f"Пустых/недоступных: {len(empty_sources)}")
