#!/usr/bin/env python3
"""Package tracked source files without local credentials or build products."""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path


def main() -> None:
    target = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for raw in sorted(filter(None, paths)):
            rel = Path(os.fsdecode(raw))
            path = root / rel
            if path.is_symlink() or not path.is_file():
                continue
            if rel.name.startswith(".env") and rel.name != ".env.example" and rel.name != ".env.test.example":
                continue
            if rel.suffix.lower() in {".apk", ".ipa", ".zip"}:
                continue
            archive.write(path, rel.as_posix())
        template = root / "release-manifest.template.json"
        if template.is_file() and b"release-manifest.template.json" not in paths:
            archive.write(template, template.name)


if __name__ == "__main__":
    main()
