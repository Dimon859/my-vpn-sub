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

MODEM_IP = "192.168.8.100"
MODEM_GATEWAY = "192.168.8.1"
SUBSCRIPTION_NAME = "MyVPN"
geo_cache = {}

SOURCES = [
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/all.txt",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/base64",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/hiddify",
    "https://raw.githubusercontent.com/sashalsk/V2Ray/main/V2Config",
    "https://raw.githubusercontent.com/ts-sf/fly/main/vless",
    "https://raw.githubusercontent.com/ts-sf/fly/main/hysteria2",
    "https://raw.githubusercontent.com/alidc/v2ray/main/vless.txt",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge_base64.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_RAW.txt",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription1",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription2",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription3",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription4",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription5",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription6",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription7",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription8",
    "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.txt",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/free",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Vless_Sub.txt",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/Leon406/v2ray-sub/main/sub/v2ray",
    "https://raw.githubusercontent.com/v2rayfree/v2ray-free/main/sub.txt",
    "https://raw.githubusercontent.com/AmazingDM/sub/main/sub.txt",
    "https://raw.githubusercontent.com/hwanz/v2ray-sub/main/sub.txt",
    "https://raw.githubusercontent.com/AmirhoseinArsalanii/free-v2ray/main/Vless.txt",
    "https://raw.githubusercontent.com/lagzian/SS-Collector/master/V2Ray.txt"
]

def is_supported(s):
    return s.startswith('vless://') or s.startswith('hysteria2://') or s.startswith('hy2://')

def download_source(url):
    try:
        r = subprocess.run(['curl', '-4', '-sL', '--max-time', '10', url],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        content = r.stdout.strip()
        if not content or len(content) < 10:
            return set()
        configs = set()
        try:
            lines = base64.b64decode(content).decode('utf-8', errors='ignore').splitlines()
        except:
            lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if is_supported(line):
                configs.add(line)
        return configs
    except:
        return set()

def get_host(c):
    try:
        return urllib.parse.urlparse(c.split('#')[0]).hostname or ''
    except:
        return ''

def get_port(c):
    try:
        return urllib.parse.urlparse(c.split('#')[0]).port or 443
    except:
        return 443

def is_reality(c):
    return 'reality' in c.lower()

def remove_dups(configs):
    seen = set()
    result = []
    for c in configs:
        key = f"{get_host(c)}:{get_port(c)}"
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result

def create_xray_config(c):
    try:
        if not c.startswith('vless://'):
            return None
        p = urllib.parse.urlparse(c.split('#')[0])
        params = dict(urllib.parse.parse_qsl(p.query))
        security = params.get('security', 'none')
        stream = {"network": params.get('type', 'tcp'), "security": security}
        if security == 'reality':
            stream["realitySettings"] = {"show": False, "fingerprint": params.get('fp', 'chrome'),
                "serverName": params.get('sni', ''), "publicKey": params.get('pbk', ''), "shortId": params.get('sid', '')}
        elif security == 'tls':
            stream["tlsSettings"] = {"allowInsecure": True, "serverName": params.get('sni', p.hostname)}
        if stream["network"] == 'ws':
            stream["wsSettings"] = {"path": params.get('path', '/'), "headers": {"Host": params.get('host', p.hostname)}}
        return {"protocol": "vless", "settings": {"vnext": [{"address": p.hostname, "port": p.port or 443,
            "users": [{"id": p.username, "encryption": "none", "flow": params.get('flow', '')}]}]}, "streamSettings": stream}
    except:
        return None

def test_vless(c, via_modem=False):
    try:
        outbound = create_xray_config(c)
        if not outbound:
            return False
        port = random.randint(20000, 60000)
        config = {"log": {"loglevel": "none"}, "inbounds": [{"port": port, "listen": "127.0.0.1",
            "protocol": "socks", "settings": {"udp": True}}], "outbounds": [outbound]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            cf = f.name
        proc = subprocess.Popen(['xray', '-c', cf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        time.sleep(2)
        sites = ['https://www.google.com', 'https://www.instagram.com', 'https://t.me', 'https://www.youtube.com']
        ok = 0
        for site in sites:
            try:
                cmd = ['curl', '-s', '--max-time', '5', '--socks5-hostname', f'127.0.0.1:{port}', site]
                if via_modem:
                    cmd = ['curl', '-s', '--max-time', '5', '--interface', MODEM_IP, '--socks5-hostname', f'127.0.0.1:{port}', site]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                if r.returncode == 0 and len(r.stdout) > 100:
                    ok += 1
            except:
                pass
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            proc.kill()
        return ok >= 3
    except:
        return False
    finally:
        try:
            os.unlink(cf)
        except:
            pass

def get_country(host):
    global geo_cache
    if host in geo_cache:
        return geo_cache[host]
    try:
        ip = host if re.match(r'^\d+\.\d+\.\d+\.\d+$', host) else socket.gethostbyname(host)
        r = subprocess.run(['curl', '-s', '--max-time', '5', f'http://ip-api.com/json/{ip}?fields=country,countryCode,city'],
                         capture_output=True, text=True, timeout=8)
        data = json.loads(r.stdout)
        if data.get('status') == 'success':
            cc = data.get('countryCode', 'XX')
            flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 else '🌍'
            info = {'country': data.get('country', 'Unknown'), 'code': cc, 'city': data.get('city', ''), 'flag': flag}
            geo_cache[host] = info
            return info
    except:
        pass
    info = {'country': 'Unknown', 'code': 'XX', 'city': '', 'flag': '🌍'}
    geo_cache[host] = info
    return info

def update_name(c, name):
    try:
        return c.split('#')[0] + '#' + urllib.parse.quote(name)
    except:
        return c

def format_configs(configs):
    counters = {}
    result = []
    print('\n🌍 Определение стран...')
    for i, c in enumerate(configs, 1):
        proto = 'HYSTERIA2' if c.startswith('hysteria2://') or c.startswith('hy2://') else ('REALITY' if is_reality(c) else 'VLESS')
        geo = get_country(get_host(c))
        label = f"{geo['flag']} {geo['country']}" + (f" - {geo['city']}" if geo['city'] else '')
        counters[proto] = counters.get(proto, 0) + 1
        result.append(update_name(c, f"{proto} | {label} [{counters[proto]}]"))
        if i % 10 == 0:
            sys.stdout.write(f'\r  {i}/{len(configs)}')
            sys.stdout.flush()
    print('\n✅ Готово!')
    return result

def progress(cur, total, work, t):
    pct = (cur / total * 100) if total else 0
    bar = '█' * int(30 * cur // total) + '░' * (30 - int(30 * cur // total))
    icon = '🏠' if t == 'home' else '📱'
    sys.stdout.write(f'\r[{bar}] {pct:.1f}% ({cur}/{total}) | {icon} {work}')
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
    print(f'🚀 {SUBSCRIPTION_NAME} - ПОЛНАЯ ПРОВЕРКА')
    print('=' * 70)
    print('\n📥 Загрузка...')
    raw = set()
    for url in SOURCES:
        try:
            configs = download_source(url)
            if configs:
                raw.update(configs)
                print(f'✅ {len(configs)} - {url[:50]}')
        except:
            pass
    configs = remove_dups(list(raw))
    print(f'\n✅ Загружено: {len(configs)}')
    if not configs:
        print('❌ Нет конфигураций!')
        return
    print('\n🏠 Проверка домашнего...')
    home = []
    checked = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(test_vless, c, False): c for c in configs}
        for f in as_completed(futures):
            c = futures[f]
            try:
                if f.result(timeout=20):
                    home.append(c)
            except:
                pass
            checked += 1
            progress(checked, len(configs), len(home), 'home')
    print(f'\n✅ Домашний: {len(home)}')
    print('\n📱 Проверка мобильного...')
    modem = []
    checked = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(test_vless, c, True): c for c in configs}
        for f in as_completed(futures):
            c = futures[f]
            try:
                if f.result(timeout=20):
                    modem.append(c)
            except:
                pass
            checked += 1
            progress(checked, len(configs), len(modem), 'modem')
    print(f'\n✅ Мобильный: {len(modem)}')
    working = list(set(home) & set(modem))
    print('\n' + '=' * 70)
    print(f'🏠 Домашний: {len(home)}')
    print(f'📱 Мобильный: {len(modem)}')
    print(f'✅ Универсальные: {len(working)}')
    print('=' * 70)
    if not working:
        print('❌ Нет универсальных!')
        return
    clean = format_configs(working)
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
