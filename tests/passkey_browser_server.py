"""Loopback-only, ephemeral browser fixture. Never deploy this test server."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import uvicorn
from app import main as shop
from app.db import get_db
from app.models import Base, AdminUser, FeatureFlag
from app.security import hash_password

engine=create_async_engine('sqlite+aiosqlite:///:memory:')


@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine,expire_on_commit=False) as db:
        db.add(AdminUser(email='browser@example.test',password_hash=hash_password('browser-only-password'),role='admin'))
        db.add(FeatureFlag(key='passkeys',enabled=True))
        await db.commit()
    yield
    await engine.dispose()


async def database():
    async with AsyncSession(engine,expire_on_commit=False) as db:yield db


app=FastAPI(lifespan=lifespan)
app.router.routes.extend(shop.app.router.routes)
app.dependency_overrides[get_db]=database
shop.app.dependency_overrides[get_db]=database
app.add_middleware(shop.SecurityHeadersMiddleware)
app.mount('/',StaticFiles(directory=str(Path(__file__).resolve().parents[1]/'admin/dist'),html=True))

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=8777,log_level='warning')
