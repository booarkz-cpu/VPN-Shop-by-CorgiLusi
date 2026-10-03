"""Bounded SQLite import and previewed, atomic customer administration."""
import asyncio
import hashlib
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import CustomerOperation, UserImportIdentity, User
from .security import require_permission

router = APIRouter(prefix='/api/admin/customer-operations', tags=['customer-operations'])
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def read_sqlite(data, table=None, telegram_column=None, username_column=None):
    if len(data) > MAX_BYTES or not data.startswith(b'SQLite format 3\x00'):
        raise HTTPException(422, 'Нужна автономная SQLite-база размером до 8 МиБ')
    connection = sqlite3.connect(':memory:')
    try:
        connection.deserialize(data)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1024 * 1024)
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA query_only=ON')
        steps = 0
        def budget():
            nonlocal steps
            steps += 1
            return int(steps > 1000)
        connection.set_progress_handler(budget, 1000)
        tables = connection.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' AND upper(sql) NOT LIKE '%VIRTUAL%' ORDER BY name LIMIT 51").fetchall()
        if len(tables) > 50:
            raise HTTPException(422, 'В базе больше 50 таблиц')
        schema = {name: [r[1] for r in connection.execute('PRAGMA table_info(' + identifier(name) + ')')] for (name,) in tables}
        if table is None:
            return {'tables': schema, 'max_rows': MAX_ROWS}
        if table not in schema or telegram_column not in schema[table] or (username_column and username_column not in schema[table]):
            raise HTTPException(422, 'Проверьте таблицу и сопоставление колонок')
        columns = identifier(telegram_column) + (',' + identifier(username_column) if username_column else '')
        rows = connection.execute('SELECT ' + columns + ' FROM ' + identifier(table) + ' LIMIT ?', (MAX_ROWS + 1,)).fetchall()
        if not rows or len(rows) > MAX_ROWS:
            raise HTTPException(422, 'Нужно от 1 до 5000 строк; разделите большую базу на части')
        normalized, seen = [], set()
        for index, row in enumerate(rows, 1):
            raw = row[0]
            if not isinstance(raw, (str, int)) or not re.fullmatch(r'[1-9][0-9]{0,15}', str(raw)) or int(raw) > 2**52 - 1:
                raise HTTPException(422, f'Строка {index}: неверный Telegram ID')
            telegram_id = int(raw)
            if telegram_id in seen:
                raise HTTPException(422, f'Строка {index}: повтор Telegram ID; исправьте исходную базу')
            seen.add(telegram_id)
            username = row[1] if username_column else None
            if username is not None and (not isinstance(username, str) or len(username) > 255 or any(ord(c) < 32 for c in username)):
                raise HTTPException(422, f'Строка {index}: неверное имя (до 255 символов)')
            normalized.append({'telegram_id': telegram_id, 'username': username or None})
        return sorted(normalized, key=lambda r: r['telegram_id'])
    except (sqlite3.Error, ValueError, OverflowError):
        raise HTTPException(422, 'База повреждена, содержит неподдерживаемую схему или превышает лимит обработки')
    finally:
        connection.close()


async def upload_bytes(request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, 'Максимальный размер базы — 8 МиБ')
        chunks.append(chunk)
    return b''.join(chunks)


@router.post('/import/inspect')
async def inspect_import(request: Request, admin=Depends(require_permission('users.write'))):
    return await asyncio.to_thread(read_sqlite, await upload_bytes(request))


def user_state(user):
    return {'id': user.id, 'telegram_id': user.telegram_id, 'username': user.username,
            'deleted_at': str(user.deleted_at), 'restricted_at': str(user.restricted_at)}


async def import_snapshot(db, rows):
    ids = [r['telegram_id'] for r in rows]
    users, imported = {}, {}
    # Keep bind counts below SQLite's defaults as well as PostgreSQL's limit.
    for offset in range(0, len(ids), 500):
        batch = ids[offset:offset + 500]
        users.update({u.telegram_id: u for u in (await db.scalars(select(User).where(User.telegram_id.in_(batch)).execution_options(populate_existing=True))).all()})
        imported.update({u.telegram_id: u.user_id for u in (await db.scalars(select(UserImportIdentity).where(UserImportIdentity.telegram_id.in_(batch)))).all()})
    decisions = []
    for row in rows:
        user = users.get(row['telegram_id'])
        decisions.append({**row, 'action': 'skip' if user or row['telegram_id'] in imported else 'create',
                          'user_id': user.id if user else imported.get(row['telegram_id']),
                          'existing': user_state(user) if user else None})
    return decisions


async def save_preview(db, admin, kind, payload, snapshot, reason):
    now = datetime.utcnow()
    # Retain journal metadata, but remove expired imported personal data.
    await db.execute(update(CustomerOperation).where(CustomerOperation.status == 'preview', CustomerOperation.expires_at <= now).values(status='expired', payload={}))
    operation = CustomerOperation(id=secrets.token_urlsafe(24), actor=admin.email, kind=kind,
        reason=reason, status='preview', payload=payload, fingerprint=digest(snapshot),
        result={}, expires_at=now + timedelta(minutes=15))
    db.add(operation)
    await db.commit()
    return {'id': operation.id, 'kind': kind, 'expires_at': operation.expires_at,
            'rows': snapshot, 'total': len(snapshot)}


@router.post('/import/preview')
async def preview_import(request: Request, source: str = Query(min_length=1, max_length=100),
        table: str = Query(min_length=1, max_length=255), telegram_column: str = Query(min_length=1, max_length=255),
        username_column: str | None = Query(default=None, max_length=255),
        db: AsyncSession = Depends(get_db), admin=Depends(require_permission('users.write'))):
    if not source.strip():
        raise HTTPException(422, 'Укажите название источника')
    data = await upload_bytes(request)
    rows = await asyncio.to_thread(read_sqlite, data, table, telegram_column, username_column)
    snapshot = await import_snapshot(db, rows)
    return await save_preview(db, admin, 'import', {'rows': rows, 'source': source.strip(),
        'file_sha256': hashlib.sha256(data).hexdigest(), 'mapping': {'table': table, 'telegram_id': telegram_column, 'username': username_column}}, snapshot, source.strip())


class BulkIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str = Field(pattern='^(restrict|unrestrict)$')
    user_ids: list[int] = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=3, max_length=500)


async def bulk_snapshot(db, payload, lock=False):
    ids = payload['user_ids']
    statement = select(User).where(User.id.in_(ids)).order_by(User.id).execution_options(populate_existing=True)
    if lock:
        statement = statement.with_for_update()
    users = (await db.scalars(statement)).all()
    if len(users) != len(ids) or any(u.deleted_at for u in users):
        raise HTTPException(409, 'Есть удалённые или отсутствующие клиенты; обновите выбор')
    snapshot = [{**user_state(u), 'action': payload['action'],
        'changed': bool(u.restricted_at) != (payload['action'] == 'restrict')} for u in users]
    return users, snapshot


@router.post('/bulk/preview')
async def preview_bulk(payload: BulkIn, db: AsyncSession = Depends(get_db), admin=Depends(require_permission('users.write'))):
    if len(set(payload.user_ids)) != len(payload.user_ids) or any(i <= 0 or i > 2147483647 for i in payload.user_ids) or len(payload.reason.strip()) < 3:
        raise HTTPException(422, 'Нужны разные положительные ID и причина действия')
    data = payload.model_dump()
    data['user_ids'] = sorted(data['user_ids'])
    _, snapshot = await bulk_snapshot(db, data)
    return await save_preview(db, admin, 'bulk', data, snapshot, payload.reason.strip())


@router.post('/{operation_id}/apply')
async def apply_operation(operation_id: str, db: AsyncSession = Depends(get_db), admin=Depends(require_permission('users.write'))):
    from .main import audit
    from .account_actions import revoke_access
    operation = await db.scalar(select(CustomerOperation).where(CustomerOperation.id == operation_id).with_for_update().execution_options(populate_existing=True))
    if not operation or operation.actor != admin.email:
        raise HTTPException(404, 'Предпросмотр не найден')
    if operation.status == 'applied':
        return operation.result
    if operation.status != 'preview' or operation.expires_at <= datetime.utcnow():
        raise HTTPException(409, 'Предпросмотр истёк; создайте новый')
    try:
        if operation.kind == 'import':
            snapshot = await import_snapshot(db, operation.payload['rows'])
            users = []
        else:
            users, snapshot = await bulk_snapshot(db, operation.payload, lock=True)
        if digest(snapshot) != operation.fingerprint:
            raise HTTPException(409, 'Данные изменились; создайте новый предпросмотр')
        results = []
        if operation.kind == 'import':
            for row in snapshot:
                if row['action'] == 'create':
                    user = User(telegram_id=row['telegram_id'], username=row['username'])
                    db.add(user)
                    await db.flush()
                    db.add(UserImportIdentity(telegram_id=row['telegram_id'], user_id=user.id, operation_id=operation.id))
                    results.append({'user_id': user.id, 'action': 'created'})
                else:
                    results.append({'user_id': row['user_id'], 'action': 'skipped'})
        else:
            for user, row in zip(users, snapshot):
                if row['changed']:
                    user.restricted_at = datetime.utcnow() if operation.payload['action'] == 'restrict' else None
                    if user.restricted_at:
                        await revoke_access(db, user)
                results.append({'user_id': user.id, 'action': row['action'], 'changed': row['changed']})
        result = {'id': operation.id, 'kind': operation.kind, 'total': len(results), 'rows': results}
        operation.result = result
        operation.status = 'applied'
        operation.applied_at = datetime.utcnow()
        # Keep import mapping and file checksum, not the uploaded names or database.
        operation.payload = {k: v for k, v in operation.payload.items() if k != 'rows'}
        await audit(db, 'customers.' + operation.kind, admin.email, operation.id,
            {'reason': operation.reason, 'total': len(results)})
        await db.commit()
        return result
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, 'Конфликт с параллельным изменением; создайте новый предпросмотр')


@router.get('/journal')
async def journal(db: AsyncSession = Depends(get_db), admin=Depends(require_permission('users.write'))):
    rows = (await db.scalars(select(CustomerOperation).where(CustomerOperation.actor == admin.email).order_by(CustomerOperation.created_at.desc()).limit(50))).all()
    now = datetime.utcnow()
    return [{'id': r.id, 'kind': r.kind, 'status': 'expired' if r.status == 'preview' and r.expires_at <= now else r.status,
             'reason': r.reason, 'created_at': r.created_at, 'applied_at': r.applied_at,
             'total': r.result.get('total'), 'result': r.result} for r in rows]
