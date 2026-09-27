#!/usr/bin/env python3
"""Idempotent 20.0.14 environment migration. Never print secret values."""
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit, unquote


def migrate(text):
    lines = text.splitlines()
    values = {}
    for line in lines:
        match = re.match(r'^([A-Z][A-Z0-9_]*)=(.*)$', line)
        if match:
            raw = match[2].strip()
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                raw = raw[1:-1]
            values[match[1]] = raw
    updates = {}
    embedded = unquote(urlsplit(values.get('REDIS_URL', '')).password or '')
    for name in ('REDIS_PASSWORD', 'SUPPORT_REDIS_PASSWORD'):
        current = values.get(name, '')
        if not current or current.startswith('change-me'):
            updates[name] = embedded if name == 'REDIS_PASSWORD' and embedded else secrets.token_hex(32)
    updates['MOBILE_CLIENT_KEY'] = ''
    updates['MOBILE_REQUIRE_PROOF'] = 'false'
    # Preserve custom origins for manual validation; migrate the old installer's
    # combined, exact frontend-domain list to separate privilege boundaries.
    admin = values.get('ADMIN_DOMAIN', '')
    cabinet_hosts = {values.get(k, '') for k in ('CABINET_DOMAIN', 'APP_DOMAIN', 'MINIAPP_DOMAIN')}
    old = [x.strip() for x in values.get('ADMIN_CORS_ORIGINS', '').split(',') if x.strip()]
    if old and all(x == 'https://' + admin or x in {'https://' + h for h in cabinet_hosts if h} for x in old):
        updates['ADMIN_CORS_ORIGINS'] = ','.join(x for x in old if x == 'https://' + admin)
        if not values.get('CABINET_CORS_ORIGINS'):
            updates['CABINET_CORS_ORIGINS'] = ','.join(x for x in old if x != 'https://' + admin)
    if 'TRUSTED_PROXY_CIDRS' not in values:
        updates['TRUSTED_PROXY_CIDRS'] = values.get('CADDY_INGRESS_IP', '172.30.84.2') + '/32'
    seen = set()
    out = []
    for line in lines:
        key = line.split('=', 1)[0]
        if key in updates:
            if key in seen:
                continue
            line = key + "='" + updates[key].replace("'", "\\'") + "'"
            seen.add(key)
        out.append(line)
    for key in updates.keys() - seen:
        out.append(key + "='" + updates[key].replace("'", "\\'") + "'")
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    path = Path('.env')
    text = migrate(path.read_text())
    tmp = path.with_name('.env.security-tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    print('Security environment migration complete. No secrets were printed.')
