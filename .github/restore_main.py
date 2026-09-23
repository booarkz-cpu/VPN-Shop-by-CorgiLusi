import hashlib
import subprocess
from pathlib import Path

root = Path(".publish-restore")
chunks = []
for i in range(11):
    raw = root / f"part-{i:02d}"
    if not raw.is_file():
        raise SystemExit(f"missing part {i:02d}")
    chunks.append(raw.read_bytes())
data = b"".join(chunks)
data = data.replace(b"{{ARROW}}", chr(0x2192).encode())
data = data.replace(b"{{EMDASH}}", chr(0x2014).encode())
digest = hashlib.sha256(data).hexdigest()
print(len(data), digest)
if len(data) != 381229 or digest != "32b6f12649d21819844afb7b9fa4f8d7618560ff57bb7f00046a827e75eb7471":
    raise SystemExit("hash mismatch")
Path("backend/app/main.py").write_bytes(data)
subprocess.check_call(["git", "config", "user.name", "booarkz-cpu"])
subprocess.check_call(["git", "config", "user.email", "boo.ar.kz@gmail.com"])
subprocess.check_call(["git", "add", "backend/app/main.py"])
subprocess.check_call(["git", "rm", "-r", ".publish-restore"])
subprocess.check_call(["git", "commit", "-m", "Restore backend/app/main.py from the audited source."])
result = subprocess.run(["git", "push", "origin", "HEAD:main"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
if result.returncode != 0:
    raise SystemExit("push failed")
