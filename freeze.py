import json, time, zlib

NOWORK_FILE = '/home/dimon859/my-vpn-sub/.nowork_sources.json'
NOWORK_LIMIT = 5

def load_nowork():
    try:
        return json.load(open(NOWORK_FILE))
    except Exception:
        return {}

def is_frozen(st, url, now):
    return st.get(url, {}).get('frozen_until', 0) > now

def update_nowork(st, ss, home, frozen, dead, n_act):
    if len(home) < 50 or len(dead) > 0.8 * n_act:
        print('⚠️ Прогон не засчитан для заморозки')
        return
    wk = {x.split('#')[0] for x in home}
    now = time.time()
    for url, cfgs in ss.items():
        if url in frozen:
            continue
        e = st.setdefault(url, {'zero': 0, 'frozen_until': 0})
        if any(x.split('#')[0] in wk for x in cfgs):
            e['zero'] = 0
            e['frozen_until'] = 0
        else:
            e['zero'] += 1
            if e['zero'] >= NOWORK_LIMIT:
                d = 3 + zlib.crc32(url.encode()) % 5
                e['frozen_until'] = now + d * 86400
    json.dump(st, open(NOWORK_FILE, 'w'))
    n = sum(1 for e in st.values() if e.get('frozen_until', 0) > now)
    print(f'🧊 Заморожено источников: {n}')
