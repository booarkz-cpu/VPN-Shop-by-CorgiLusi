import json
import logging
import os
import redis.asyncio as redis

r = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'), decode_responses=True)


async def publish(tid, payload):
    try:
        await r.publish(f'ticket:{tid}', json.dumps(payload, ensure_ascii=False))
    except Exception:
        logging.getLogger(__name__).warning('Realtime unavailable; committed changes remain in database')
