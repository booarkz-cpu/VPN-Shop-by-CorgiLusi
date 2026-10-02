#!/usr/bin/env python3
"""Configure both sides without printing credentials or replacing unrelated settings."""
import argparse
import os
from pathlib import Path
import re
import secrets
import tempfile
from urllib.parse import urlsplit

def read_values(path):
    values={}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key,value=line.split('=',1);values[key.strip()]=value.strip().strip('"').strip("'")
    return values

def updated(text,values):
    lines=text.splitlines();seen=set();out=[]
    for line in lines:
        key=line.split('=',1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else None
        if key in values:
            if key not in seen:out.append(key+'='+values[key]);seen.add(key)
        else:out.append(line)
    for key,value in values.items():
        if key not in seen:out.append(key+'='+value)
    return '\n'.join(out)+'\n'

def write_private(path,text):
    fd,temp=tempfile.mkstemp(prefix='.bridge-config-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as file:file.write(text)
        os.chmod(temp,0o600);os.replace(temp,path)
    finally:Path(temp).unlink(missing_ok=True)

def configure(root,origin,instance,dry_run=False):
    u=urlsplit(origin)
    if u.scheme!='https' or not u.hostname or u.path not in ('','/') or u.query or u.fragment or u.username or u.password:
        raise ValueError('Нужен HTTPS origin магазина без пути, параметров и credentials')
    origin=origin.rstrip('/')
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,40}',instance):raise ValueError('Instance: 8–40 латинских букв, цифр, _ или -')
    first=root/'.env';second=root/'support-pro/.env'
    if not first.is_file() or not second.is_file():raise ValueError('Сначала создайте .env магазина и support-pro/.env действующей установки')
    a,b=read_values(first),read_values(second)
    token=a.get('SUPPORT_BRIDGE_TOKEN') or b.get('SHOP_BRIDGE_TOKEN') or secrets.token_hex(32)
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}',token):raise ValueError('Существующий ключ интеграции некорректен; настройка не изменена')
    if a.get('SUPPORT_BRIDGE_TOKEN') and b.get('SHOP_BRIDGE_TOKEN') and a['SUPPORT_BRIDGE_TOKEN']!=b['SHOP_BRIDGE_TOKEN']:
        raise ValueError('Ключи двух сервисов различаются; настройка не изменена')
    if b.get('SHOP_BRIDGE_URL') and b['SHOP_BRIDGE_URL'].rstrip('/')!=origin:raise ValueError('Изменение магазина требует переноса существующих связей')
    if b.get('SHOP_BRIDGE_INSTANCE') and b['SHOP_BRIDGE_INSTANCE']!=instance:raise ValueError('Нельзя менять namespace уже настроенной интеграции')
    original=[p.read_text() for p in (first,second)]
    contents=[updated(original[0],{'SUPPORT_BRIDGE_TOKEN':token}),updated(original[1],{'SHOP_BRIDGE_URL':origin,'SHOP_BRIDGE_TOKEN':token,'SHOP_BRIDGE_INSTANCE':instance})]
    if dry_run:return
    try:
        for path,data in zip((first,second),contents):write_private(path,data)
    except BaseException:
        for path,data in zip((first,second),original):write_private(path,data)
        raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin',required=True);parser.add_argument('--instance',default='support-main')
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:configure(args.project_dir,args.origin,args.instance,args.dry_run)
    except (ValueError,OSError) as exc:parser.exit(1,str(exc)+'\n')
    print('Проверка пройдена; изменений нет' if args.dry_run else 'Настройки обоих сервисов сохранены. Секреты не выводятся. Пересоздайте backend и Support Pro.')
if __name__=='__main__':main()
