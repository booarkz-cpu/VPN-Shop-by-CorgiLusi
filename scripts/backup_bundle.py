#!/usr/bin/env python3
"""Authenticated streaming encryption for private recovery bundles.

Decryption must complete into a private temporary file before any restore starts.
"""
import argparse
import os
import struct
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b'VPNBACKUP1\n'
CHUNK = 1024 * 1024


def password():
    value = os.environ.get('BACKUP_BUNDLE_PASSWORD', '')
    if not 12 <= len(value) <= 1024:
        raise ValueError('BACKUP_BUNDLE_PASSWORD must contain 12–1024 characters')
    return value.encode('utf-8')


def read_exact(source, count):
    pieces = []
    while count:
        part = source.read(count)
        if not part:
            raise ValueError('Truncated encrypted backup')
        pieces.append(part)
        count -= len(part)
    return b''.join(pieces)


def cipher(secret, salt):
    return AESGCM(Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(secret))


def encrypt(source, target, secret):
    salt, prefix = os.urandom(16), os.urandom(8)
    header = MAGIC + salt + prefix
    aes = cipher(secret, salt)
    target.write(header)
    sequence = 0
    while True:
        data = source.read(CHUNK)
        index = struct.pack('>I', sequence)
        block = aes.encrypt(prefix + index, data, header + index)
        target.write(struct.pack('>I', len(block)))
        target.write(block)
        sequence += 1
        if not data:
            break  # An authenticated empty frame is mandatory; EOF is not success.


def decrypt(source, target, secret):
    header = read_exact(source, len(MAGIC) + 24)
    if not header.startswith(MAGIC):
        raise ValueError('Unsupported backup format')
    salt, prefix = header[len(MAGIC):len(MAGIC)+16], header[-8:]
    aes = cipher(secret, salt)
    sequence = 0
    while True:
        size = struct.unpack('>I', read_exact(source, 4))[0]
        if not 16 <= size <= CHUNK + 16:
            raise ValueError('Invalid backup frame size')
        index = struct.pack('>I', sequence)
        data = aes.decrypt(prefix + index, read_exact(source, size), header + index)
        sequence += 1
        if not data:
            if source.read(1):
                raise ValueError('Trailing backup data')
            break
        target.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('encrypt', 'decrypt'))
    action = parser.parse_args().action
    try:
        (encrypt if action == 'encrypt' else decrypt)(sys.stdin.buffer, sys.stdout.buffer, password())
    except Exception:
        print('Backup encryption/verification failed; discard incomplete output.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
