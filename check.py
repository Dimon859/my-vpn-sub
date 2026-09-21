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
    "https://raw.githubusercontent.com/gooseteam-hackers/GooseVPN/refs/heads/main/configs/plus.txt"
]

def is_supported(s):
    return (s.startswith('vless://') or 
            s.startswith('trojan://') or
            s.startswith('hysteria2://') or s.startswith('hy2://'))

def is_priority(s):
    if 'reality' in s.lower():
        return True
    if 'grpc' in s.lower():
        return True
    if 'xtls-rprx-vision' in s.lower():
        return True
    if 'xhttp' in s.lower():
        return True
    if 'hysteria2://' in s.lower() or 'hy2://' in s.lower():
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
    try:
        r = subprocess.run(['curl', '-4', '-sL', '--max-time', '10', url],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        content = r.stdout.strip()
        if not content or len(content) < 10:
            return set()
        configs = set()
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if is_supported(line):
                configs.add(line)
                continue
            try:
                decoded_line = base64.b64decode(line).decode('utf-8', errors='ignore')
                if is_supported(decoded_line.strip()):
                    configs.add(decoded_line.strip())
            except:
                pass
        return configs
    except:
        return set()

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
    seen = set()
    result = []
    for c in configs:
        key = f"{get_host(c)}:{get_port(c)}"
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

def test_sites(socks_port):
    sites = ['https://www.google.com', 'https://www.instagram.com', 'https://t.me',
            'https://www.youtube.com', 'https://www.facebook.com', 'https://twitter.com',
            'https://www.whatsapp.com', 'https://openai.com']
    ok = 0
    for site in sites:
        try:
            cmd = ['curl', '-s', '--max-time', '8', '--socks5-hostname', f'127.0.0.1:{socks_port}', site]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and len(r.stdout) > 100:
                ok += 1
        except:
            pass
    return ok

def create_xray_outbound(c):
    try:
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
                stream["tlsSettings"] = {"allowInsecure": True, "serverName": params.get('sni', p.hostname)}
            
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
                stream["tlsSettings"] = {"allowInsecure": True, "serverName": data.get('sni', data.get('add', ''))}
            if network == 'ws':
                stream["wsSettings"] = {"path": data.get('path', '/'), "headers": {"Host": data.get('host', data.get('add', ''))}}
            elif network == 'grpc':
                stream["grpcSettings"] = {"serviceName": data.get('serviceName', '')}
            elif network == 'xhttp':
                stream["xhttpSettings"] = {"path": data.get('path', '/'), "host": data.get('host', ''), "mode": data.get('mode', 'packet-up')}
            return {"protocol": "vmess", "settings": {"vnext": [{"address": data.get('add', ''),
                "port": int(data.get('port', 443)), "users": [{"id": data.get('id', ''),
                "alterId": int(data.get('aid', 0)), "security": "auto"}]}]}, "streamSettings": stream}
        elif c.startswith('trojan://'):
            p = urllib.parse.urlparse(c.split('#')[0])
            params = dict(urllib.parse.parse_qsl(p.query))
            return {"protocol": "trojan", "settings": {"servers": [{"address": p.hostname,
                "port": p.port or 443, "password": p.username}]}, "streamSettings": {"network": "tcp",
                "security": "tls", "tlsSettings": {"allowInsecure": True, "serverName": params.get('sni', p.hostname)}}}
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

def test_with_xray(c):
    try:
        if c.startswith('vless://') and not check_reality_params(c):
            return False, 0
        outbound = create_xray_outbound(c)
        if not outbound:
            return False, 0
        port = random.randint(20000, 60000)
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
        socks_port = random.randint(20000, 60000)
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
        return (ok >= 5 and speed_ok), speed_val
    except:
        return False, 0
    finally:
        try:
            os.unlink(cf)
        except:
            pass

def test_config(c):
    host = get_host(c)
    port = get_port(c)
    protocol = get_protocol(c)
    
    tcp_ok, ping_ms = test_tcp(host, port)
    
    if not tcp_ok:
        recent_checks.append({'host': host, 'port': port, 'protocol': protocol, 'status': False, 'ping_ms': 0, 'speed': 0})
        return False
    
    if c.startswith('hysteria2://') or c.startswith('hy2://'):
        result, speed = test_hysteria2_singbox(c)
    else:
        result, speed = test_with_xray(c)
    
    recent_checks.append({'host': host, 'port': port, 'protocol': protocol, 'status': result, 'ping_ms': ping_ms, 'speed': speed})
    
    return result

def get_country(host):
    global geo_cache
    if host in geo_cache:
        return geo_cache[host]
    
    try:
        ip = host if re.match(r'^\d+\.\d+\.\d+\.\d+$', host) else socket.gethostbyname(host)
        r = subprocess.run(['curl', '-s', '--max-time', '5', 
                          f'http://ip-api.com/json/{ip}?fields=country,countryCode,city'],
                         capture_output=True, text=True, timeout=8)
        data = json.loads(r.stdout)
        if data.get('status') == 'success':
            country = data.get('country', 'Unknown')
            city = data.get('city', '')
            cc = data.get('countryCode', 'XX')
            flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 else '🌍'
            info = {'country': country, 'code': cc, 'city': city, 'flag': flag}
            geo_cache[host] = info
            return info
    except:
        pass
    
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

def format_configs(configs):
    counters = {}
    result = []
    print('\n🌍 Определение стран...')
    for i, c in enumerate(configs, 1):
        proto = get_protocol(c)
        geo = get_country(get_host(c))
        label = f"{geo['flag']} {geo['country']}" + (f" - {geo['city']}" if geo['city'] else '')
        counters[proto] = counters.get(proto, 0) + 1
        result.append(update_name(c, f"{proto} | {label} [{counters[proto]}]"))
        if i % 10 == 0:
            sys.stdout.write(f'\r  {i}/{len(configs)}')
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
        subprocess.run(['git', 'add', 'clean_sub.txt', 'clean_sub_base64.txt'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'Auto-update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'], check=True, capture_output=True)
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], capture_output=True)
        r = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
        if r.returncode == 0:
            print('✅ Выгружено!')
        else:
            r = subprocess.run(['git', 'push', '--force', 'origin', 'main'], capture_output=True, text=True)
            print('✅ Выгружено (force)!' if r.returncode == 0 else '❌ Ошибка push')
    except Exception as e:
        print(f'❌ Git: {e}')

def main():
    start = datetime.now()
    print('=' * 70)
    print(f'🚀 {SUBSCRIPTION_NAME} - ПРОВЕРКА СЕРВЕРОВ')
    print('=' * 70)
    print('\n📥 Загрузка...')
    raw = set()
    working_sources = 0
    for url in SOURCES:
        try:
            configs = download_source(url)
            if configs:
                raw.update(configs)
                working_sources += 1
                print(f'✅ {len(configs)} - {url[:60]}')
        except:
            pass
    configs = remove_dups(list(raw))
    print(f'\n✅ Источников: {working_sources}/{len(SOURCES)}')
    print(f'✅ Загружено: {len(configs)}')
    
    priority_configs = [c for c in configs if is_priority(c)]
    other_configs = [c for c in configs if not is_priority(c)]
    configs = priority_configs + other_configs
    print(f'✅ Приоритетных (Reality/gRPC/XHTTP/Hysteria2): {len(priority_configs)}')
    
    if not configs:
        print('❌ Нет конфигураций!')
        return
    
    print('\n🏠 Проверка (TCP + Xray + 5 сайтов + 1 Mbit/s)...')
    home = []
    checked = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(test_config, c): c for c in configs}
        for f in as_completed(futures):
            c = futures[f]
            try:
                if f.result(timeout=30):
                    home.append(c)
            except:
                pass
            checked += 1
            if checked % 10 == 0 or checked == len(configs):
                progress_detail(checked, len(configs), len(home))
    
    print(f'\n\n✅ Рабочих: {len(home)}')
    if not home:
        print('❌ Нет рабочих!')
        return
    clean = format_configs(home)
    header = f"# {SUBSCRIPTION_NAME}\n# {'=' * 50}\n"
    out_raw = header + '\n'.join(clean)
    out_b64 = base64.b64encode(out_raw.encode('utf-8')).decode('utf-8')
    with open('clean_sub.txt', 'w', encoding='utf-8') as f:
        f.write(out_raw)
    with open('clean_sub_base64.txt', 'w', encoding='utf-8') as f:
        f.write(out_b64)
    print(f'\n✅ Сохранено: {len(clean)} серверов')
    print('\n📤 GITHUB...')
    git_push()
    print(f'\n✅ Завершено за {datetime.now() - start}')

if __name__ == '__main__':
    main()
