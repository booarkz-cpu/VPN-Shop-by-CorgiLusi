import secrets,pyotp
from argon2 import PasswordHasher
ph=PasswordHasher()
def csrf(session):
 session.setdefault("csrf",secrets.token_urlsafe(32));return session["csrf"]
def valid_csrf(session,token):return bool(token and secrets.compare_digest(session.get("csrf",""),token))
def new_totp():return pyotp.random_base32()
