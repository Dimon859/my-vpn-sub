import os
import re
import json
import base64
import subprocess
import urllib.parse
import socket
import time
import logging
import tempfile
import sys
import random
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# === ЛОКАЛЬНАЯ GEOIP БАЗА ===
GEOIP_DB_PATH = '/home/dimon859/my-vpn-sub/geoip/dbip-city-lite.mmdb'
_geoip_reader = None
try:
    import geoip2.database
    _geoip_reader = geoip2.database.Reader(GEOIP_DB_PATH)
    print(f'✅ GeoIP база загружена: {GEOIP_DB_PATH}')
except Exception as e:
    print(f'⚠️  GeoIP база не загружена: {e}')
# === /ЛОКАЛЬНАЯ GEOIP БАЗА ===


# === NTFY УВЕДОМЛЕНИЯ ===
def notify(message, title=None, priority=None):
    """Отправляет уведомление в ntfy.sh + Telegram"""
    # 1. ntfy
    try:
        topic_path = '/home/dimon859/my-vpn-sub/.ntfy_topic'
        if os.path.exists(topic_path):
            with open(topic_path) as f:
                topic = f.read().strip()
            if topic:
                cmd = ['curl', '-s', '--max-time', '10', '-d', message]
                if title:
                    cmd.extend(['-H', f'Title: {title}'])
                if priority:
                    cmd.extend(['-H', f'Priority: {priority}'])
                cmd.append(f'https://ntfy.sh/{topic}')
                subprocess.run(cmd, capture_output=True, timeout=15)
    except:
        pass

    # 2. Telegram
    try:
        import sys
        sys.path.insert(0, '/home/dimon859/my-vpn-sub')
        from tg_notify import send_telegram
        send_telegram(message, title=title)
    except:
        pass
# === /NTFY УВЕДОМЛЕНИЯ ===



SUBSCRIPTION_NAME = "MyVPN"
geo_cache = {}
recent_checks = []

SOURCES = [
    # Проверенные рабочие
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_RAW.txt",
    "https://solovyov-jenya2004.vercel.app/final_sorted/",
    "https://solovyov-jenya2004.vercel.app/final_sorted_base64/",
    "https://solovyov-jenya2004.vercel.app/random/",
    
    # hiztin VLESS-PO-GRIBI
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/1.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/2.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/3.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/4.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/5.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/6.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/8.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/9.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/10.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/11.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/12.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/13.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/14.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/15.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/16.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/17.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/18.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/19.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/20.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/21.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/22.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/23.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/24.txt",
    "https://raw.githubusercontent.com/hiztin/VLESS-PO-GRIBI/main/deploy/subscriptions/25.txt",
    
    # igareck
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_SS+All_RUS.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_SS%2BAll_RUS.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/BLACK_VLESS_RUS_mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt",
    "https://gitlab.com/igareck/vpn-configs-for-russia/-/raw/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/GoldCaviar/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
    
    # Новые для белых списков
    "https://raw.githubusercontent.com/prominbro/sub/refs/heads/main/212.txt",
    "https://raw.githubusercontent.com/prominbro/kfwlsub/refs/heads/main/sub",
    "https://raw.githubusercontent.com/RKPchannel/RKP_bypass_configs/refs/heads/main/whitelist.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Whitelist.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vrema.txt",
    "https://raw.githubusercontent.com/Ilyacom4ik/free-v2ray-2026/refs/heads/main/subscriptions/FreeCFGHub1.txt",
    "https://raw.githubusercontent.com/Ilyacom4ik/vpn-keys/refs/heads/main/allkeysFreeCFGHub.txt",
    "https://raw.githubusercontent.com/LimeHi/LimeVPN/refs/heads/main/LimeVPN.txt",
    "https://raw.githubusercontent.com/Alex999ooo/VPN-for-Russia-/refs/heads/main/VPN%20by%20Alex999ooo",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://xolirx-vpn.vercel.app/white",
    "https://sub.pfvpn.cfd/free/sub",
    "https://raw.githubusercontent.com/kama55726/KomaryServers/refs/heads/main/KomaryServ",
    "https://gitverse.ru/api/repos/qwerti2228/crypt_based/raw/branch/master/FreeCFGHub_subscription_lite",
    "https://raw.githubusercontent.com/uretkavpn/Uretkavpn/refs/heads/main/UretkaVpn.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vip.txt",
    "https://subrostunnel.vercel.app/lte.txt",
    "https://raw.githubusercontent.com/xolirx/list-check/refs/heads/main/white.txt",
    "https://raw.githubusercontent.com/s0ulcoil/nloVPN/refs/heads/main/nloVPN",
    "https://raw.githubusercontent.com/s0ulcoil/AstroVpn/refs/heads/main/AstroVpn",
    "https://raw.githubusercontent.com/s0ulcoil/K13vpn/refs/heads/main/K13vpn",
    "https://raw.githubusercontent.com/s0ulcoil/SerenaVPN/refs/heads/main/SerenaVPN",
    "https://raw.githubusercontent.com/s0ulcoil/elixVPN/refs/heads/main/elixVPN",
    "https://raw.githubusercontent.com/s0ulcoil/WSVPN/refs/heads/main/1WSVPN",
    "https://raw.githubusercontent.com/s0ulcoil/LumixVPN/refs/heads/main/LumixVPN",
    "https://raw.githubusercontent.com/s0ulcoil/FastConVPN/refs/heads/main/FastConVPN",
    "https://sub.savvka.fun/whitelist",
    "https://vpn.akres.fun/bwl",
    "https://raw.githubusercontent.com/likzil/vless1/refs/heads/main/Treetcpvpn",
    "https://raw.githubusercontent.com/stanislavPLS/AuraChannel/refs/heads/main/Autoconf.ru",
    "https://raw.githubusercontent.com/Ilyacom4ik/vpn-keys/refs/heads/main/FreeCFGHubSUB",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/Ghost-LInk-star/GhostL/refs/heads/main/dizzga.txt",
    "https://raw.githubusercontent.com/Ghost-LInk-star/bambuk/refs/heads/main/vpn.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vpn.txt",
    "https://raw.githubusercontent.com/Temnuk/naabuzil/refs/heads/main/whitelist_full",
    "https://raw.githubusercontent.com/Temnuk/naabuzil/refs/heads/main/whitelist",
    "https://raw.githubusercontent.com/stanislavPLS/AuraChannel/refs/heads/main/Q",
    "https://raw.githubusercontent.com/stanislavPLS/AuraChannel/refs/heads/main/GoodMixyVPN.txt",
    "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/refs/heads/main/ByeWhiteLists2.txt",
    "https://raw.githubusercontent.com/55prosek-lgtm/vpn_config_for_russia/refs/heads/main/whitelist.txt",
    "https://raw.githubusercontent.com/LowiKLive/BypassWhitelistRu/refs/heads/main/WhiteList-Bypass_Ru.txt",
    "https://raw.githubusercontent.com/vsevjik/OBSpiskov/refs/heads/main/wwh",
    "https://raw.githubusercontent.com/RYZgames31/UWB/refs/heads/main/wcfg",
    "https://raw.githubusercontent.com/twinkalex1470-crypto/CatWhiteVPN/refs/heads/main/CaTWhiteVPN.txt",
    "https://raw.githubusercontent.com/DarkFirexs/Whitelist-bypass_VPN/refs/heads/main/Whitelist%20%7C%20VPN",
    "https://raw.githubusercontent.com/stanislavPLS/AuraChannel/refs/heads/main/ID%3D1%2Cdata%3D280427",
    "https://raw.githubusercontent.com/stanislavPLS/GMVPN-users/refs/heads/main/id%3D1%2Cdata%3D120527",
    "https://raw.githubusercontent.com/zxcDeadinsulte/scalavpn-configs/refs/heads/main/test.txt",
    "https://sub.obbhod.online/premium",
    "https://raw.githubusercontent.com/Ilyacom4ik/free-v2ray-2026/refs/heads/main/subscriptions/whitelist-keys.txt",
    "https://subrostunnel.vercel.app/gen.txt",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN/refs/heads/main/AetrisVPN.txt",
    "https://raw.githubusercontent.com/zieng2/wl/refs/heads/main/vless_lite.txt",
    "https://raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyakbeta6.txt",
    "https://raw.githubusercontent.com/flaafix/AetrisVPN-white-list-lite/refs/heads/main/AetrisVPN.txt",
    "https://raw.githubusercontent.com/zieng2/wl/refs/heads/main/vless_universal.txt",
    "https://raw.githubusercontent.com/AirLinkVPN1/AirLinkVPN/refs/heads/main/rkn_white_list",
    "https://raw.githubusercontent.com/gooseteam-hackers/GooseVPN/refs/heads/main/configs/balanced.txt",
    "https://raw.githubusercontent.com/dequar/deqwl/refs/heads/main/deray.txt",
    "https://raw.githubusercontent.com/LimeHi/LimeVPN/refs/heads/main/whitelist.txt",
    "https://raw.githubusercontent.com/OceaniaVPN/StekloVPN/main/configs/whitelist.txt",
    "https://etoneya.su/whitelist",
    "https://gitverse.ru/api/repos/272/wl/raw/branch/master/whitelist",
    "https://gitverse.ru/api/repos/Akres/VPN/raw/branch/master/bwl",
    "https://raw.githubusercontent.com/gooseteam-hackers/GooseVPN/refs/heads/main/configs/plus.txt",
    # === НОВЫЕ ИСТОЧНИКИ ДЛЯ БЕЛЫХ СПИСКОВ ===
    "https://raw.githubusercontent.com/FLAT447/v2ray-lists/main/WHITE_FULL.txt",
    "https://raw.githubusercontent.com/FLAT447/v2ray-lists/main/WHITE_LITE.txt",
    "https://raw.githubusercontent.com/nikita29a/FreeProxyList/main/mirror/1.txt",
]

# === АВТОИСТОЧНИКИ ОТ HUNTER.PY ===
AUTO_SOURCES_FILE = '/home/dimon859/my-vpn-sub/.auto_sources.txt'
_auto_loaded = 0
try:
    if os.path.exists(AUTO_SOURCES_FILE):
        _existing = set(SOURCES)
        with open(AUTO_SOURCES_FILE) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith('#'):
                    continue
                # Формат: "count\turl" или "tcp\ttotal\turl" — берём ПОСЛЕДНЮЮ часть
                _parts = _line.split('\t')
                if len(_parts) >= 2:
                    _url = _parts[-1].strip()
                    if _url and _url.startswith('http') and _url not in _existing:
                        SOURCES.append(_url)
                        _existing.add(_url)
                        _auto_loaded += 1
        print(f'🎯 Автоисточников от hunter: +{_auto_loaded} (всего: {len(SOURCES)})')
except Exception as _e:
    print(f'⚠️  Автоисточники не загружены: {_e}')
# === /АВТОИСТОЧНИКИ ===

def is_supported(s):
    return (s.startswith('vless://') or 
            s.startswith('hysteria2://') or s.startswith('hy2://'))

def is_priority(s):
    sl = s.lower()
    # Reality — самый приоритетный
    if 'reality' in sl:
        return True
    # Hysteria2
    if 'hysteria2://' in sl or 'hy2://' in sl:
        return True
    # Транспорты с маскировкой
    if 'grpc' in sl:
        return True
    if 'xhttp' in sl or 'splithttp' in sl:
        return True
    if 'httpupgrade' in sl:
        return True
    # websocket заблокирован — не приоритет
    # Flow — XTLS Vision
    if 'xtls-rprx-vision' in sl:
        return True
    return False

def get_protocol(c):
    if c.startswith('vless://'):
        return 'REALITY' if is_reality(c) else 'VLESS'
    elif c.startswith('vmess://'):
        return 'VMESS'
    elif c.startswith('trojan://'):
        return 'TROJAN'
    elif c.startswith('ss://'):
        return 'SHADOWSOCKS'
    elif c.startswith('hysteria2://') or c.startswith('hy2://'):
        return 'HYSTERIA2'
    return 'PROXY'

def download_source(url):
    """Возвращает (configs, elapsed_sec) — elapsed это время скачивания"""
    start_t = time.time()
    try:
        r = subprocess.run(['curl', '-4', '-sL', '--max-time', '10', url],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        content = r.stdout.strip()
        elapsed = time.time() - start_t
        if not content or len(content) < 10:
            return set(), elapsed
        configs = set()
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if is_supported(line):
                configs.add(line)
                continue
            try:
                # Нормализуем padding для base64
                b64 = line.strip()
                padding = 4 - len(b64) % 4
                if padding != 4:
                    b64 += '=' * padding
                decoded = base64.b64decode(b64, validate=False).decode('utf-8', errors='ignore')
                # Разбиваем декодированный текст ПО СТРОКАМ
                for dl in decoded.splitlines():
                    dl = dl.strip()
                    if is_supported(dl):
                        configs.add(dl)
            except:
                pass
        return configs, elapsed
    except:
        return set(), time.time() - start_t

def get_host(c):
    try:
        if c.startswith('vmess://'):
            b64 = c[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            data = json.loads(base64.b64decode(b64).decode('utf-8', errors='ignore'))
            return str(data.get('add', '')).strip('[]').strip()
        return urllib.parse.urlparse(c.split('#')[0]).hostname or ''
    except:
        return ''

def get_port(c):
    try:
        if c.startswith('vmess://'):
            b64 = c[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            data = json.loads(base64.b64decode(b64).decode('utf-8', errors='ignore'))
            return int(data.get('port', 443))
        return urllib.parse.urlparse(c.split('#')[0]).port or 443
    except:
        return 443

def is_reality(c):
    return 'reality' in c.lower() or 'public_key' in c.lower() or 'short_id' in c.lower()

def check_reality_params(c):
    if not is_reality(c):
        return True
    url_params = ['pbk=', 'sid=', 'fp=', 'sni=']
    json_params = ['public_key', 'short_id', 'fingerprint', 'server_name']
    url_ok = all(param in c for param in url_params)
    if url_ok:
        return True
    json_ok = all(param in c for param in json_params)
    if json_ok:
        return True
    return False

def remove_dups(configs):
    """Дедуп по полному отпечатку: host:port:uuid:security:sni:pbk:sid:fp:flow:type:serviceName:path"""
    seen = set()
    result = []
    for c in configs:
        try:
            if c.startswith('vless://'):
                p = urllib.parse.urlparse(c.split('#')[0])
                params = dict(urllib.parse.parse_qsl(p.query))
                key = (f"{p.hostname}:{p.port or 443}:{p.username}:"
                       f"{params.get('security','')}:"
                       f"{params.get('sni','')}:"
                       f"{params.get('pbk','')}:"
                       f"{params.get('sid','')}:"
                       f"{params.get('fp','')}:"
                       f"{params.get('flow','')}:"
                       f"{params.get('type','tcp')}:"
                       f"{params.get('serviceName','')}:"
                       f"{params.get('path','')}:{params.get('host','')}:{params.get('mode','')}:{params.get('alpn','')}")
            elif c.startswith('hysteria2://') or c.startswith('hy2://'):
                p = urllib.parse.urlparse(c.split('#')[0])
                params = dict(urllib.parse.parse_qsl(p.query))
                key = (f"{p.hostname}:{p.port or 443}:{p.username}:"
                       f"{params.get('sni','')}:"
                       f"{params.get('insecure','')}:{params.get('obfs','')}:{params.get('obfs-password','')}:{params.get('pinSHA256','')}")
            else:
                # Для всего остального — просто без #name
                key = c.split('#')[0]
        except:
            key = c.split('#')[0]

        if key not in seen:
            seen.add(key)
            result.append(c)
    return result

def test_tcp(host, port, timeout=3):
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        ping_ms = (time.time() - start) * 1000
        return result == 0, ping_ms
    except:
        return False, 0

def test_speed(socks_port):
    try:
        start_time = time.time()
        cmd = ['curl', '-s', '--max-time', '15', '--socks5-hostname', f'127.0.0.1:{socks_port}',
               'https://speed.cloudflare.com/__down?bytes=5000000']
        r = subprocess.run(cmd, capture_output=True, timeout=20)
        end_time = time.time()
        elapsed = end_time - start_time
        if r.returncode == 0 and elapsed > 0:
            size = len(r.stdout)
            speed_mbits = (size * 8) / (elapsed * 1000000)
            return speed_mbits >= 1, speed_mbits
        return False, 0
    except:
        return False, 0

def test_sites(socks_port, max_fails=2):
    """Проверка сайтов через SOCKS. Fail-fast: после max_fails неудач — выход."""
    sites = ['https://www.google.com', 'https://www.instagram.com', 'https://t.me',
            'https://www.youtube.com', 'https://www.facebook.com', 'https://twitter.com',
            'https://www.whatsapp.com', 'https://openai.com']
    ok = 0
    fails = 0
    for site in sites:
        try:
            cmd = ['curl', '-s', '--max-time', '5', '--socks5-hostname', f'127.0.0.1:{socks_port}', site]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=7)
            if r.returncode == 0 and len(r.stdout) > 100:
                ok += 1
                fails = 0  # сброс при успехе
            else:
                fails += 1
                if fails >= max_fails:
                    return ok  # ❌ Fail-fast: сервер мёртв
        except:
            fails += 1
            if fails >= max_fails:
                return ok
    return ok

def create_xray_outbound(c):
    try:
        # Убираем WS (заблокирован)
        if 'type=ws' in c or 'type=websocket' in c:
            return None
        if c.startswith('vless://'):
            p = urllib.parse.urlparse(c.split('#')[0])
            params = dict(urllib.parse.parse_qsl(p.query))
            security = params.get('security', 'none')
            flow = params.get('flow', '')
            network = params.get('type', 'tcp')
            stream = {"network": network, "security": security}
            
            if security == 'reality':
                pbk = params.get('pbk', '')
                sid = params.get('sid', '')
                fp = params.get('fp', 'chrome')
                sni = params.get('sni', '')
                if not pbk:
                    pbk = params.get('public_key', '')
                if not sid:
                    sid = params.get('short_id', '')
                if fp == 'chrome':
                    fp = params.get('fingerprint', 'chrome')
                if not sni:
                    sni = params.get('server_name', '')
                stream["realitySettings"] = {"show": False, "fingerprint": fp,
                    "serverName": sni, "publicKey": pbk, "shortId": sid}
            elif security == 'tls':
                stream["tlsSettings"] = {"serverName": params.get('sni', p.hostname)}
            
            if network == 'ws':
                stream["wsSettings"] = {"path": params.get('path', '/'), "headers": {"Host": params.get('host', p.hostname)}}
            elif network == 'grpc':
                stream["grpcSettings"] = {"serviceName": params.get('serviceName', '')}
            elif network == 'xhttp':
                stream["xhttpSettings"] = {
                    "path": params.get('path', '/'),
                    "host": params.get('host', ''),
                    "mode": params.get('mode', 'packet-up')
                }
            elif network == 'httpupgrade':
                stream["httpupgradeSettings"] = {
                    "path": params.get('path', '/'),
                    "host": params.get('host', p.hostname)
                }
            
            return {"protocol": "vless", "settings": {"vnext": [{"address": p.hostname, "port": p.port or 443,
                "users": [{"id": p.username, "encryption": "none", "flow": flow}]}]}, "streamSettings": stream}
        elif c.startswith('vmess://'):
            b64 = c[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            data = json.loads(base64.b64decode(b64).decode('utf-8', errors='ignore'))
            network = data.get('net', 'tcp')
            stream = {"network": network, "security": data.get('tls', 'none')}
            if stream["security"] == 'tls':
                stream["tlsSettings"] = {"serverName": data.get('sni', data.get('add', ''))}
            if network == 'ws':
                stream["wsSettings"] = {"path": data.get('path', '/'), "headers": {"Host": data.get('host', data.get('add', ''))}}
            elif network == 'grpc':
                stream["grpcSettings"] = {"serviceName": data.get('serviceName', '')}
            elif network == 'xhttp':
                stream["xhttpSettings"] = {"path": data.get('path', '/'), "host": data.get('host', ''), "mode": data.get('mode', 'packet-up')}
            elif network == 'httpupgrade':
                stream["httpupgradeSettings"] = {"path": data.get('path', '/'), "host": data.get('host', data.get('add', ''))}
            return {"protocol": "vmess", "settings": {"vnext": [{"address": data.get('add', ''),
                "port": int(data.get('port', 443)), "users": [{"id": data.get('id', ''),
                "alterId": int(data.get('aid', 0)), "security": "auto"}]}]}, "streamSettings": stream}
        elif c.startswith('trojan://'):
            p = urllib.parse.urlparse(c.split('#')[0])
            params = dict(urllib.parse.parse_qsl(p.query))
            return {"protocol": "trojan", "settings": {"servers": [{"address": p.hostname,
                "port": p.port or 443, "password": p.username}]}, "streamSettings": {"network": "tcp",
                "security": "tls", "tlsSettings": {"serverName": params.get('sni', p.hostname)}}}
        elif c.startswith('ss://'):
            p = urllib.parse.urlparse(c.split('#')[0])
            if '@' in p.netloc:
                user_info = base64.b64decode(p.username).decode('utf-8')
                method, password = user_info.split(':', 1)
                host = p.hostname
                port = p.port
            else:
                b64 = c[5:].split('#')[0]
                padding = 4 - len(b64) % 4
                if padding != 4:
                    b64 += '=' * padding
                decoded = base64.b64decode(b64).decode('utf-8')
                method, rest = decoded.split(':', 1)
                password, host_port = rest.rsplit('@', 1)
                host, port = host_port.split(':')
                port = int(port)
            return {"protocol": "shadowsocks", "settings": {"servers": [{"address": host,
                "port": port, "method": method, "password": password}]}}
    except:
        return None
    return None

def get_free_port():
    """Возвращает свободный порт, выделенный ОС"""
    import socket as _socket
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def test_with_xray(c):
    try:
        if c.startswith('vless://') and not check_reality_params(c):
            return False, 0
        outbound = create_xray_outbound(c)
        if not outbound:
            return False, 0
        port = get_free_port()
        config = {"log": {"loglevel": "none"}, "inbounds": [{"port": port, "listen": "127.0.0.1",
            "protocol": "socks", "settings": {"udp": True}}], "outbounds": [outbound]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            cf = f.name
        proc = subprocess.Popen(['xray', '-c', cf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        time.sleep(2)
        ok = test_sites(port)
        speed_ok, speed_val = test_speed(port) if ok >= 5 else (False, 0)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            proc.kill()
        try:
            proc.wait(timeout=3)
        except:
            pass
        return (ok >= 5 and speed_ok), speed_val
    except:
        return False, 0
    finally:
        try:
            os.unlink(cf)
        except:
            pass

def test_hysteria2_singbox(c):
    try:
        p = urllib.parse.urlparse(c.split('#')[0])
        host = p.hostname
        port = p.port or 443
        password = p.username
        params = dict(urllib.parse.parse_qsl(p.query))
        socks_port = get_free_port()
        config = {
            "log": {"level": "error"},
            "inbounds": [{"type": "socks", "listen": "127.0.0.1", "listen_port": socks_port}],
            "outbounds": [{
                "type": "hysteria2",
                "server": host,
                "server_port": port,
                "password": password,
                "tls": {"enabled": True, "insecure": True, "server_name": params.get('sni', host)}
            }]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            cf = f.name
        proc = subprocess.Popen(['sing-box', 'run', '-c', cf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        time.sleep(2)
        ok = test_sites(socks_port)
        speed_ok, speed_val = test_speed(socks_port) if ok >= 5 else (False, 0)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            proc.kill()
        try:
            proc.wait(timeout=3)
        except:
            pass
        return (ok >= 5 and speed_ok), speed_val
    except:
        return False, 0
    finally:
        try:
            os.unlink(cf)
        except:
            pass

def test_config(c):
    """Возвращает (result, speed, was_xray)"""
    host = get_host(c)
    port = get_port(c)
    protocol = get_protocol(c)
    
    # Hysteria2 работает по UDP — TCP-проверка не подходит
    is_hy2 = c.startswith('hysteria2://') or c.startswith('hy2://')
    
    if is_hy2:
        # Для HY2 пропускаем TCP-проверку
        ping_ms = 0
        result, speed = test_hysteria2_singbox(c)
        recent_checks.append({'host': host, 'port': port, 'protocol': protocol, 'status': result, 'ping_ms': ping_ms, 'speed': speed})
        return result, speed, True  # был sing-box
    else:
        tcp_ok, ping_ms = test_tcp(host, port)
        if not tcp_ok:
            recent_checks.append({'host': host, 'port': port, 'protocol': protocol, 'status': False, 'ping_ms': 0, 'speed': 0})
            return False, 0, False  # Xray не запускался
        result, speed = test_with_xray(c)
        recent_checks.append({'host': host, 'port': port, 'protocol': protocol, 'status': result, 'ping_ms': ping_ms, 'speed': speed})
        return result, speed, True  # Xray был запущен

def get_country(host):
    global geo_cache
    if host in geo_cache:
        return geo_cache[host]
    
    ip = None
    try:
        ip = host if re.match(r'^\d+\.\d+\.\d+\.\d+$', host) else socket.gethostbyname(host)
    except:
        pass
    
    info = None
    
    # 1. ЛОКАЛЬНАЯ БАЗА (мгновенно, без лимитов)
    if ip and _geoip_reader:
        try:
            rec = _geoip_reader.city(ip)
            cc = rec.country.iso_code or 'XX'
            country = rec.country.name or 'Unknown'
            city = rec.city.name or ''
            flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 and cc != 'XX' else '🌍'
            if cc != 'XX':
                info = {'country': country, 'code': cc, 'city': city, 'flag': flag}
        except:
            pass
    
    # 2. ip-api.com (если локально не нашлось)
    if ip and not info:
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '5',
                f'http://ip-api.com/json/{ip}?fields=status,country,countryCode,city'],
                capture_output=True, text=True, timeout=8)
            data = json.loads(r.stdout)
            if data.get('status') == 'success':
                country = data.get('country', 'Unknown')
                cc = data.get('countryCode', 'XX')
                city = data.get('city', '')
                flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 else '🌍'
                if cc != 'XX':
                    info = {'country': country, 'code': cc, 'city': city, 'flag': flag}
        except:
            pass
    
    # 3. ipwho.is (второй запасной)
    if ip and not info:
        try:
            r = subprocess.run(['curl', '-s', '--max-time', '5',
                f'https://ipwho.is/{ip}'],
                capture_output=True, text=True, timeout=8)
            data = json.loads(r.stdout)
            if data.get('success'):
                country = data.get('country', 'Unknown')
                cc = data.get('country_code', 'XX')
                city = data.get('city', '')
                flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 else '🌍'
                if cc != 'XX':
                    info = {'country': country, 'code': cc, 'city': city, 'flag': flag}
        except:
            pass
    
    # 4. Ничего не сработало
    if not info:
        info = {'country': 'Unknown', 'code': 'XX', 'city': '', 'flag': '🌍'}
    
    geo_cache[host] = info
    return info

def update_name(c, name):
    try:
        if c.startswith('vmess://'):
            b64 = c[8:]
            padding = 4 - len(b64) % 4
            if padding != 4:
                b64 += '=' * padding
            data = json.loads(base64.b64decode(b64).decode('utf-8', errors='ignore'))
            data['ps'] = name
            new_b64 = base64.b64encode(json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).decode('utf-8')
            return 'vmess://' + new_b64
        return c.split('#')[0] + '#' + urllib.parse.quote(name)
    except:
        return c

def save_source_stats(source_servers, working_set):
    """Сохраняет статистику по источникам"""
    stats = {}
    for url, servers in source_servers.items():
        working_count = sum(1 for s in servers if s in working_set)
        total_count = len(servers)
        stats[url] = (working_count, total_count)
    
    # Сортировка по рабочим
    sorted_stats = sorted(stats.items(), key=lambda x: -x[1][0])
    
    with open('source_stats.txt', 'w', encoding='utf-8') as f:
        f.write(f'# Статистика источников ({datetime.now().strftime("%Y-%m-%d %H:%M")})\n')
        f.write('=' * 100 + '\n\n')
        for url, (working, total) in sorted_stats:
            percent = (working / total * 100) if total > 0 else 0
            f.write(f'{working:4d}/{total:4d} ({percent:5.1f}%) - {url}\n')
    
    logger.info(f'Статистика источников сохранена: source_stats.txt')
    print(f'✅ Статистика источников: source_stats.txt')

def format_configs(configs, speeds=None):
    """Форматирует с сортировкой по скорости"""
    if speeds is None:
        speeds = {}
    
    # Сортировка по скорости (убывание)
    sorted_configs = sorted(configs, key=lambda x: speeds.get(x, 0), reverse=True)
    
    result = []
    print('\n🌍 Форматирование...')
    
    for i, c in enumerate(sorted_configs, 1):
        speed = speeds.get(c, 0)
        
        # Гео
        geo = get_country(get_host(c))
        flag = geo['flag']
        code = geo['code']
        city = geo['city']
        
        # Формат
        prefix = f"{flag} {code}"
        
        if city:
            name = f"{prefix} | {city} [{i}]"
        else:
            name = f"{prefix} [{i}]"
        
        result.append(update_name(c, name))
        
        if i % 10 == 0:
            sys.stdout.write(f'\r  {i}/{len(sorted_configs)}')
            sys.stdout.flush()
    
    print('\n✅ Готово!')
    return result

def progress_detail(cur, total, work):
    pct = (cur / total * 100) if total else 0
    bar = '█' * int(30 * cur // total) + '░' * (30 - int(30 * cur // total))
    
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.write(f'[{bar}] {pct:.1f}% ({cur}/{total}) | Рабочих: {work}\n')
    sys.stdout.write('=' * 70 + '\n')
    
    if recent_checks:
        last = recent_checks[-1]
        status = '✅' if last['status'] else '❌'
        sys.stdout.write(f'📡 Текущий: {last["host"]}:{last["port"]} [{last["protocol"]}]\n')
        sys.stdout.write(f'   Пинг: {last["ping_ms"]:.0f}ms | Статус: {status}\n')
        if last['speed'] > 0:
            sys.stdout.write(f'   Скорость: {last["speed"]:.1f} Mbit/s\n')
        sys.stdout.write('-' * 70 + '\n')
        sys.stdout.write('Последние проверенные:\n')
        for item in recent_checks[-10:]:
            status = '✅' if item['status'] else '❌'
            sys.stdout.write(f'   {status} {item["host"]}:{item["port"]} [{item["protocol"]}] - {item["ping_ms"]:.0f}ms\n')
    
    sys.stdout.flush()

def git_push():
    try:
        # 1. Добавляем файлы
        subprocess.run(['git', 'add', 'clean_sub.txt', 'clean_sub_base64.txt', 'clean_sub.ru.txt', 'clean_sub.ru_base64.txt'], capture_output=True)
        
        # 2. Проверяем, есть ли что коммитить
        diff = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
        if diff.returncode != 0:
            # Есть изменения — коммитим
            subprocess.run(['git', 'commit', '-m', f'Auto-update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'], capture_output=True)
            print('✅ Закоммичено')
        else:
            print('ℹ️ Нечего коммитить')
        
        # 3. Pull --rebase (если есть что)
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], capture_output=True)
        
        # 4. Push без force
        r = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
        if r.returncode == 0:
            print('✅ Выгружено!')
        else:
            # Только если реально конфликт — force
            print(f'⚠️ Push не удался: {r.stderr[:200]}')
            r2 = subprocess.run(['git', 'push', '--force', 'origin', 'main'], capture_output=True, text=True)
            print('✅ Выгружено (force)!' if r2.returncode == 0 else '❌ Ошибка push')
    except Exception as e:
        print(f'❌ Git: {e}')

def main():
    import json as _json  # для всего main()
    start = datetime.now()
    notify(f'🚀 Проверка запущена\nВремя: {start.strftime("%Y-%m-%d %H:%M:%S")}', title='MyVPN', priority='low')
    print('=' * 70)
    print(f'🚀 {SUBSCRIPTION_NAME} - ПРОВЕРКА СЕРВЕРОВ')
    print('=' * 70)
    print('\n📥 Загрузка...')
    _t_load_start = time.time()

    # Загружаем историю мёртвых источников ЗАРАНЕЕ
    dead_file = '/home/dimon859/my-vpn-sub/.dead_sources.json'
    dead_history = {}
    if os.path.exists(dead_file):
        try:
            with open(dead_file) as _f:
                dead_history = json.load(_f)
        except:
            dead_history = {}

    # Порог автоотключения: если источник пуст N+ прогонов подряд — пропускаем
    AUTODISABLE_THRESHOLD = 3
    skipped_sources = []
    active_sources = []
    for _url in SOURCES:
        if dead_history.get(_url, 0) >= AUTODISABLE_THRESHOLD:
            skipped_sources.append(_url)
        else:
            active_sources.append(_url)

    if skipped_sources:
        print(f'🔕 Автоотключено (пусто {AUTODISABLE_THRESHOLD}+ прогонов): {len(skipped_sources)}')

    import freeze as _fz
    nw = _fz.load_nowork()
    frozen = {u for u in active_sources if _fz.is_frozen(nw, u, time.time())}
    active_sources = [u for u in active_sources if u not in frozen]
    if frozen:
        print(f'🧊 Заморожено: {len(frozen)}')
    raw = set()
    working_sources = 0
    source_servers = {}
    dead_sources = []
    source_times = {}
    for url in active_sources:
        try:
            configs, dl_time = download_source(url)
            source_times[url] = dl_time
            if configs:
                raw.update(configs)
                source_servers[url] = list(configs)
                working_sources += 1
                print(f'✅ {len(configs)} - {url[:60]}')
            else:
                dead_sources.append(url)
        except:
            dead_sources.append(url)
            source_times[url] = 0.0

    # Обновляем счётчики
    for url in active_sources:
        if url in dead_sources:
            dead_history[url] = dead_history.get(url, 0) + 1
        else:
            dead_history[url] = 0

    # Сохраняем
    try:
        with open(dead_file, 'w') as _f:
            json.dump(dead_history, _f)
    except:
        pass

    # Уведомление о мёртвых источниках (3+ раза подряд)
    dead_3plus = [(u, c) for u, c in dead_history.items() if c >= 3]
    if dead_3plus:
        lines = '\n'.join(f'• {u.split("/")[-1]} ({c} раз)' for u, c in sorted(dead_3plus, key=lambda x: -x[1])[:10])
        notify(
            f'📡 МЁРТВЫЕ ИСТОЧНИКИ ({len(dead_3plus)})\n'
            f'3+ прогона подряд пусто:\n'
            f'{lines}',
            title='MyVPN 📡',
            priority='default'
        )
    # Загружаем существующие рабочие серверы из clean_sub.txt + clean_sub.ru.txt
    existing = []
    for _fname in ["clean_sub.txt", "clean_sub.ru.txt"]:
        if os.path.exists(_fname):
            with open(_fname, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "://" in line:
                        existing.append(line)
    print(f"\n✅ Загружено старых рабочих: {len(existing)}")
    raw.update(existing)
    
    configs = remove_dups(list(raw))
    print(f"\n✅ Загружено всего: {len(configs)}")
    
    priority_configs = [c for c in configs if is_priority(c)]
    other_configs = [c for c in configs if not is_priority(c)]
    configs = priority_configs + other_configs
    print(f'✅ Приоритетных (Reality/gRPC/XHTTP/Hysteria2): {len(priority_configs)}')
    
    if not configs:
        print('❌ Нет конфигураций!')
        return
    
    _t_load_end = time.time()
    _load_sec = _t_load_end - _t_load_start

    print('\n🏠 Проверка (TCP + Xray + 5 сайтов + 1 Mbit/s)...')
    _t_check_start = time.time()
    home = []
    speeds = {}
    checked = 0
    xray_launched = 0
    xray_failed = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(test_config, c): c for c in configs}
        for f in as_completed(futures):
            c = futures[f]
            try:
                result, speed, was_xray = f.result()
                if was_xray:
                    xray_launched += 1
                    if not result:
                        xray_failed += 1
                if result:
                    home.append(c)
                    speeds[c] = speed
            except:
                xray_failed += 1
            checked += 1
            if checked % 10 == 0 or checked == len(configs):
                progress_detail(checked, len(configs), len(home))
    
    print(f'\n\n✅ Рабочих: {len(home)}')
    if not home:
        print('❌ Нет рабочих!')
        notify(
            f'💀 РАБОЧИХ НЕТ\n'
            f'📊 Проверено: {len(configs)}\n'
            f'❌ Подписка НЕ обновится\n'
            f'🔍 Проверь источники / интернет',
            title='MyVPN 💀',
            priority='high'
        )
        return
    clean = format_configs(home, speeds)

    # === РАЗДЕЛЕНИЕ ПО СТРАНАМ ===
    # RU-сервера → отдельная подписка
    # Остальные → основная подписка
    clean_ru = []
    clean_other = []
    for cfg in clean:
        try:
            _cc = get_country(get_host(cfg))['code']
            if _cc == 'RU':
                clean_ru.append(cfg)
            else:
                clean_other.append(cfg)
        except:
            clean_other.append(cfg)

    print(f'\n📊 Разделение:')
    print(f'   🇷🇺 RU: {len(clean_ru)}')
    print(f'   🌍 Остальные: {len(clean_other)}')

    # Основная подписка (без RU)
    header = f"# {SUBSCRIPTION_NAME}\n# {'=' * 50}\n"
    out_raw = header + '\n'.join(clean_other)
    out_b64 = base64.b64encode(out_raw.encode('utf-8')).decode('utf-8')
    with open('clean_sub.txt', 'w', encoding='utf-8') as f:
        f.write(out_raw)
    with open('clean_sub_base64.txt', 'w', encoding='utf-8') as f:
        f.write(out_b64)

    # Вторая подписка (только RU)
    header_ru = f"# {SUBSCRIPTION_NAME}(RU)\n# {'=' * 50}\n"
    out_raw_ru = header_ru + '\n'.join(clean_ru)
    out_b64_ru = base64.b64encode(out_raw_ru.encode('utf-8')).decode('utf-8')
    with open('clean_sub.ru.txt', 'w', encoding='utf-8') as f:
        f.write(out_raw_ru)
    with open('clean_sub.ru_base64.txt', 'w', encoding='utf-8') as f:
        f.write(out_b64_ru)

    # Сохраняем карту IP → страна (для dist-бота)
    try:
        ip_countries = {}
        for cfg in (clean_other + clean_ru):
            try:
                host = get_host(cfg)
                geo = get_country(host)
                ip_countries[host] = geo['code']
            except:
                pass
        with open('.ip_countries.json', 'w', encoding='utf-8') as f:
            json.dump(ip_countries, f, ensure_ascii=False, indent=0)
        print(f'✅ Карта IP→страна: {len(ip_countries)} записей')
    except Exception as e:
        print(f'⚠️  Не сохранил .ip_countries.json: {e}')

    _t_check_end = time.time()
    _check_sec = _t_check_end - _t_check_start
    _t_save_start = time.time()

    print(f'\n✅ Сохранено: {len(clean)} серверов')
    
    # Тревога: серверов стало мало
    if len(clean) < 50:
        notify(
            f'🚨 СЕРВЕРОВ СТАЛО МАЛО\n'
            f'Рабочих: {len(clean)}\n'
            f'Проверено: {len(configs)}\n'
            f'Обычно больше 100\n'
            f'🔍 Проверь SOURCES',
            title='MyVPN 🚨',
            priority='high'
        )
    
    # Рекорд по количеству серверов
    record_file = '/home/dimon859/my-vpn-sub/.record_count'
    prev_record = 0
    if os.path.exists(record_file):
        try:
            with open(record_file) as _f:
                prev_record = int(_f.read().strip())
        except:
            prev_record = 0

    if len(clean) > prev_record:
        # Новый рекорд
        notify(
            f'🏆 НОВЫЙ РЕКОРД!\n'
            f'Серверов: {len(clean)}\n'
            f'Было: {prev_record}\n'
            f'Прирост: +{len(clean) - prev_record}\n'
            f'🎉 Самый урожайный прогон!',
            title='MyVPN 🏆',
            priority='default'
        )
        try:
            with open(record_file, 'w') as _f:
                _f.write(str(len(clean)))
        except:
            pass

    # Сохраняем статистику источников
    try:
        save_source_stats(source_servers, set(home))
    except Exception as e:
        print(f'⚠️ Ошибка статистики: {e}')
    try:
        _fz.update_nowork(nw, source_servers, home, frozen, dead_sources, len(active_sources))
    except Exception as e:
        print(f'⚠️ Ошибка заморозки: {e}')
    
    _t_save_end = time.time()
    _save_sec = _t_save_end - _t_save_start
    _t_push_start = time.time()

    print('\n📤 GITHUB...')
    git_push()
    _push_sec = time.time() - _t_push_start

    # Итоговое уведомление
    elapsed = datetime.now() - start
    hours = elapsed.seconds // 3600
    minutes = (elapsed.seconds % 3600) // 60
    duration = f'{hours}ч {minutes}м' if hours else f'{minutes}м'

    try:
        import urllib.parse as _up
        from collections import Counter as _Counter

        # Статистика стран
        countries = _Counter()
        for cfg in clean:
            if '#' in cfg:
                name = _up.unquote(cfg.split('#', 1)[1])
                m = re.search(r'\b([A-Z]{2})\b', name)
                if m:
                    countries[m.group(1)] += 1
        top_countries = ', '.join(f'{cc}:{n}' for cc, n in countries.most_common(5))

        # Топ-10 стран с процентами
        total_named = sum(countries.values()) or 1
        top10_str = ', '.join(f'{cc}:{n}({n*100//total_named}%)' for cc, n in countries.most_common(10))

        # Протоколы
        proto_counter = _Counter()
        for cfg in clean:
            if cfg.startswith('vless://'):
                proto_counter['VLESS'] += 1
            elif cfg.startswith('vmess://'):
                proto_counter['VMESS'] += 1
            elif cfg.startswith('trojan://'):
                proto_counter['TROJAN'] += 1
            elif cfg.startswith('ss://'):
                proto_counter['SS'] += 1
            elif cfg.startswith('hysteria2://') or cfg.startswith('hy2://'):
                proto_counter['HY2'] += 1
        proto_str = ', '.join(f'{p}:{n}' for p, n in proto_counter.most_common())

        # Уникальные IP
        unique_ips = set()
        for cfg in clean:
            h = get_host(cfg)
            if h:
                unique_ips.add(h)
        unique_ip_str = f'🌐 Уникальных IP: {len(unique_ips)} (дублей: {len(clean) - len(unique_ips)})'

        # ===== ВОЛНА 2 =====
        # Континенты
        continent_map = {
            'RU': '🇷🇺 RU/Евразия', 'DE': '🇪🇺 Европа', 'FR': '🇪🇺 Европа', 'GB': '🇪🇺 Европа',
            'NL': '🇪🇺 Европа', 'FI': '🇪🇺 Европа', 'SE': '🇪🇺 Европа', 'NO': '🇪🇺 Европа',
            'PL': '🇪🇺 Европа', 'LT': '🇪🇺 Европа', 'LV': '🇪🇺 Европа', 'EE': '🇪🇺 Европа',
            'BG': '🇪🇺 Европа', 'RS': '🇪🇺 Европа', 'MD': '🇪🇺 Европа', 'UA': '🇪🇺 Европа',
            'IT': '🇪🇺 Европа', 'ES': '🇪🇺 Европа', 'AT': '🇪🇺 Европа', 'CH': '🇪🇺 Европа',
            'CZ': '🇪🇺 Европа', 'SK': '🇪🇺 Европа', 'HU': '🇪🇺 Европа', 'RO': '🇪🇺 Европа',
            'US': '🇺🇸 Америка', 'CA': '🇺🇸 Америка', 'BR': '🇺🇸 Америка', 'AR': '🇺🇸 Америка',
            'JP': '🇯🇵 Азия', 'KR': '🇯🇵 Азия', 'SG': '🇯🇵 Азия', 'HK': '🇯🇵 Азия',
            'IN': '🇯🇵 Азия', 'CN': '🇯🇵 Азия', 'TR': '🇯🇵 Азия', 'AE': '🇯🇵 Азия',
            'IL': '🇯🇵 Азия', 'TH': '🇯🇵 Азия', 'VN': '🇯🇵 Азия', 'ID': '🇯🇵 Азия',
            'AU': '🇦🇺 Океания', 'NZ': '🇦🇺 Океания',
            'ZA': '🌍 Африка', 'EG': '🌍 Африка', 'NG': '🌍 Африка',
        }
        cont_counter = _Counter()
        for cc, n in countries.items():
            cont = continent_map.get(cc, '🌍 Прочее')
            cont_counter[cont] += n
        continents_str = ', '.join(f'{c}:{n}' for c, n in cont_counter.most_common())

        # Самый старый / самый новый сервер (по истории clean_sub)
        old_servers_file = '/home/dimon859/my-vpn-sub/.server_first_seen.json'
        first_seen = {}
        if os.path.exists(old_servers_file):
            try:
                with open(old_servers_file) as _f:
                    first_seen = _json.load(_f)
            except:
                first_seen = {}

        import time as _time
        now_ts = int(_time.time())
        cur_keys = set()
        for cfg in clean:
            key = f'{get_host(cfg)}:{get_port(cfg)}'
            cur_keys.add(key)
            if key not in first_seen:
                first_seen[key] = now_ts

        # Чистим старые
        first_seen = {k: v for k, v in first_seen.items() if k in cur_keys}

        # Самый старый
        oldest_key = min(first_seen, key=first_seen.get) if first_seen else None
        oldest_days = 0
        if oldest_key:
            oldest_days = (now_ts - first_seen[oldest_key]) // 86400

        # Самый новый
        newest_key = max(first_seen, key=first_seen.get) if first_seen else None
        newest_min = 0
        if newest_key:
            newest_min = (now_ts - first_seen[newest_key]) // 60

        try:
            with open(old_servers_file, 'w') as _f:
                _json.dump(first_seen, _f)
        except:
            pass

        old_str = f'🏆 Старейший: {oldest_days} дн.' if oldest_days > 0 else ''
        new_str = f'🆕 Новейший: {newest_min} мин' if newest_min < 60 else ''

        # Смена IP (по сравнению с прошлым прогоном)
        prev_ips_file = '/home/dimon859/my-vpn-sub/.prev_ips.json'
        prev_ips = {}
        if os.path.exists(prev_ips_file):
            try:
                with open(prev_ips_file) as _f:
                    prev_ips = _json.load(_f)
            except:
                prev_ips = {}

        cur_ips = {}
        for cfg in clean:
            h = get_host(cfg)
            if h:
                cur_ips[h] = countries.get('XX', '')

        # Просто считаем: сколько host'ов исчезло/появилось
        added_ips = set(cur_ips) - set(prev_ips)
        removed_ips = set(prev_ips) - set(cur_ips)
        ip_changes = len(added_ips) + len(removed_ips)

        try:
            with open(prev_ips_file, 'w') as _f:
                _json.dump(cur_ips, _f)
        except:
            pass

        ip_change_str = f'🔄 Смена IP: +{len(added_ips)} / -{len(removed_ips)}' if ip_changes > 0 else ''
        # ===== /ВОЛНА 2 =====

        # ===== ВОЛНА 3: ИСТОЧНИКИ =====
        home_set = set(home)
        source_working = {}
        for _url, _cfgs in source_servers.items():
            _wc = sum(1 for _c in _cfgs if _c in home_set)
            source_working[_url] = _wc

        top_sources = sorted(source_working.items(), key=lambda x: -x[1])[:5]
        top_sources_str = ', '.join(f'{u.split("/")[-1]}({n})' for u, n in top_sources if n > 0)

        empty_sources_str = ''
        if dead_sources:
            _short = ', '.join(u.split('/')[-1][:20] for u in dead_sources[:5])
            empty_sources_str = f'❌ Пустых: {len(dead_sources)} ({_short})'

        speed_str = ''
        if source_times:
            _valid = {k: v for k, v in source_times.items() if v > 0}
            if _valid:
                _fast = min(_valid.items(), key=lambda x: x[1])
                _slow = max(_valid.items(), key=lambda x: x[1])
                speed_str = f'⚡ Быстр: {_fast[1]:.1f}с | 🐌 Медл: {_slow[1]:.1f}с'
        # ===== /ВОЛНА 3 =====

        # ===== ВОЛНА 5: САМЫЙ ДОЛГИЙ ПРОГОН ЗА НЕДЕЛЮ =====
        longest_str = ''
        try:
            import json as _json2
            from datetime import datetime as _dt, timedelta as _td
            _hist_file = '/home/dimon859/my-vpn-sub/history.jsonl'
            if os.path.exists(_hist_file):
                _entries = []
                with open(_hist_file) as _hf:
                    for _line in _hf:
                        try:
                            _entries.append(_json2.loads(_line))
                        except:
                            pass
                _cutoff = _dt.now() - _td(days=7)
                _recent = [_e for _e in _entries if _dt.strptime(_e['date'], '%Y-%m-%d %H:%M') >= _cutoff]
                if _recent:
                    _longest = max(_recent, key=lambda x: x['duration_min'])
                    _cur_min = elapsed.seconds // 60
                    longest_str = f'🐌 Самый долгий за неделю: {_longest["duration_min"]}м ({_longest["date"]})'
                    if _cur_min > _longest['duration_min']:
                        longest_str += ' — ⚠️ сейчас дольше!'
        except:
            pass
        # ===== /ВОЛНА 5 =====

        # ===== ВОЛНА 6: ИСТОЧНИКИ ТОРМОЗЯТ =====
        avg_src_time = 0
        if source_times:
            _valid_times = [v for v in source_times.values() if v > 0]
            if _valid_times:
                avg_src_time = sum(_valid_times) / len(_valid_times)
                if avg_src_time > 5.0:
                    notify(
                        f'⚠️ ИСТОЧНИКИ ТОРМОЗЯТ\n'
                        f'Среднее скачивание: {avg_src_time:.1f}с\n'
                        f'Обычно: 1-2с\n'
                        f'Возможно, проблемы с сетью',
                        title='MyVPN ⚠️',
                        priority='default'
                    )
        # ===== /ВОЛНА 6 =====

        # Запись в историю
        try:
            history_entry = {
                'date': start.strftime('%Y-%m-%d %H:%M'),
                'total': len(configs),
                'working': len(home),
                'clean': len(clean),
                'duration_min': elapsed.seconds // 60,
                'sources_ok': working_sources,
                'sources_total': len(SOURCES),
                'countries': dict(countries),
            }
            with open('/home/dimon859/my-vpn-sub/history.jsonl', 'a', encoding='utf-8') as _h:
                _h.write(_json.dumps(history_entry, ensure_ascii=False) + '\n')
        except:
            pass

        # Было в прошлый раз
        prev_count = 0
        prev_file = '/home/dimon859/my-vpn-sub/.prev_count'
        if os.path.exists(prev_file):
            try:
                with open(prev_file) as _f:
                    prev_count = int(_f.read().strip())
            except:
                pass
        diff_str = ''
        if prev_count:
            delta = len(clean) - prev_count
            arrow = '📈' if delta >= 0 else '📉'
            diff_str = f'{arrow} Было/стало: {prev_count} → {len(clean)} ({delta:+d})\n'

        # Топ-3 быстрых стран (по количеству серверов с молниями не считаем, просто первые 3 страны)
        fast3 = ', '.join(cc for cc, _ in countries.most_common(3))

        # Источники — считаем через source_stats
        sources_str = ''
        try:
            total_src = len(SOURCES)
            ok_src = working_sources
            sources_str = f'📡 Источников: {ok_src}/{total_src}\n'
        except:
            pass

        # Размер файла подписки
        size_str = ''
        try:
            sz = os.path.getsize('/home/dimon859/my-vpn-sub/clean_sub.txt')
            size_kb = sz / 1024
            size_str = f'📦 Размер: {size_kb:.1f} КБ\n'
        except:
            pass

        # Ссылка на GitHub
        link_str = ''
        try:
            r = subprocess.run(['git', 'config', '--get', 'remote.origin.url'],
                             capture_output=True, text=True, timeout=5)
            remote = r.stdout.strip()
            if remote:
                if remote.startswith('git@github.com:'):
                    remote = remote.replace('git@github.com:', 'https://github.com/').replace('.git', '')
                elif remote.endswith('.git'):
                    remote = remote[:-4]
                # Убираем токен из URL (если он там есть)
                remote = re.sub(r'://[^@]+@', '://', remote)
                link_str = f'🔗 {remote}/blob/main/clean_sub.txt\n'
        except:
            pass

        # Отсеяно мёртвых
        dead = len(configs) - len(home)
        dead_str = f'💀 Отсеяно: {dead}\n'

        # Новые страны (которых не было в прошлом прогоне)
        new_countries_str = ''
        prev_cc_file = '/home/dimon859/my-vpn-sub/.prev_countries'
        if os.path.exists(prev_cc_file):
            try:
                with open(prev_cc_file) as _f:
                    prev_cc = set(_f.read().strip().split(','))
                current_cc = set(countries.keys())
                new_cc = current_cc - prev_cc
                if new_cc:
                    new_countries_str = f'🆕 Новые страны: {", ".join(sorted(new_cc))}\n'
            except:
                pass

        # Сохраняем текущее состояние для следующего раза
        try:
            with open(prev_file, 'w') as _f:
                _f.write(str(len(clean)))
            with open(prev_cc_file, 'w') as _f:
                _f.write(','.join(countries.keys()))
        except:
            pass

        # Финальное сообщение
        msg = (
            f'✅ Проверка завершена\n'
            f'🕐 Старт: {start.strftime("%H:%M:%S")} | Финиш: {datetime.now().strftime("%H:%M:%S")}\n'
            f'⏱ Заняло: {duration}\n'
            f'⏳ Фазы: 📥{_load_sec:.0f}с | 🔍{_check_sec:.0f}с | 💾{_save_sec:.0f}с | 📤{_push_sec:.0f}с\n'
            f'📥 Воронка: {len(configs)} → TCP-OK → Xray-OK {len(home)}\n'
            f'⚙️ Xray: запущено {xray_launched}, упало {xray_failed}\n'
            f'📊 Проверено: {len(configs)}\n'
            f'🟢 Рабочих: {len(home)}\n'
            f'{dead_str}'
            f'📤 Выгружено: {len(clean)} серверов\n'
            f'{unique_ip_str}\n'
            f'{diff_str}'
            f'{size_str}'
            f'{sources_str}'
            f'📋 Протоколы: {proto_str}\n'
            f'🌍 Топ-10: {top10_str}\n'
            f'🌎 Континенты: {continents_str}\n'
            f'{old_str}'
            f'{new_str}'
            f'{ip_change_str}\n'
            f'{top_sources_str}\n'
            f'{empty_sources_str}\n'
            f'{speed_str}\n'
            f'{longest_str}\n'
            f'{new_countries_str}'
            f'{link_str}'
        )
        notify(msg, title='MyVPN ✅', priority='default')
    except Exception as _e:
        notify(f'⚠️ Уведомление с ошибкой: {_e}', title='MyVPN', priority='low')
    print(f'\n✅ Завершено за {elapsed}')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()[-500:]
        notify(f'❌ Проверка упала\n{e}\n\n{tb}', title='MyVPN ❌', priority='high')
        raise
