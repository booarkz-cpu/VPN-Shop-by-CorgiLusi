#!/usr/bin/env python3
"""Reject unsafe rollback snapshots before stopping or replacing an installation."""

import sys
import tarfile
from pathlib import PurePosixPath


def validate(path: str) -> None:
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = member.name
            if name in (".", "./") and member.isdir():
                continue
            parts = PurePosixPath(name).parts
            if (name.startswith("/") or ".." in parts or not parts
                    or not (member.isfile() or member.isdir())):
                raise ValueError(f"Unsafe archive entry: {name}")
            if any(part == ".git" or part == ".rollback" or part.startswith(".env")
                   for part in parts):
                raise ValueError(f"Protected archive entry: {name}")


if __name__ == "__main__":
    try:
        validate(sys.argv[1])
    except (OSError, tarfile.TarError, ValueError, IndexError) as error:
        print(f"Rollback archive rejected: {error}", file=sys.stderr)
        sys.exit(2)
