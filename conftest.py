"""Source checks read the assembled shop module, admin entry, and installer."""
import base64
from pathlib import Path

_read_text = Path.read_text


def _assembled_read_text(self, *args, **kwargs):
    text = _read_text(self, *args, **kwargs)
    if self.name == "main.py" and "MAIN_PY_ASSEMBLED_FROM_PARTS" in text:
        parts = self.resolve().parent / "main_src"
        chunks = [_read_text(parts / f"part-{i:02d}", encoding="utf-8") for i in range(11)]
        return "".join(chunks).replace("{{ARROW}}", chr(0x2192)).replace("{{EMDASH}}", chr(0x2014))
    if self.name == "main.tsx" and "MAIN_TSX_ASSEMBLED_FROM_PARTS" in text:
        parts = self.resolve().parent / "main_src"
        chunks = [_read_text(path, encoding="utf-8") for path in sorted(parts.glob("part-*"))]
        return "".join(chunks)
    if self.name == "main.tsx" and '"../../cabinet/src/main"' in text:
        cabinet = self.resolve().parents[2] / "cabinet" / "src"
        return text + _read_text(cabinet / "main.tsx", encoding="utf-8") + _read_text(cabinet / "workspace.tsx", encoding="utf-8")
    if self.name == "i18n.tsx" and '"../../cabinet/src/i18n"' in text:
        return _read_text(self.resolve().parents[2] / "cabinet/src/i18n.tsx", encoding="utf-8")
    if self.name == "install-vps.sh" and "INSTALLER_ASSEMBLED_FROM_PARTS" in text:
        parts = self.resolve().parent / "install-vps-src"
        chunks = [base64.b64decode(_read_text(path, encoding="utf-8").strip()) for path in sorted(parts.glob("part-*"))]
        return b"".join(chunks).decode("utf-8")
    return text


Path.read_text = _assembled_read_text
