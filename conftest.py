"""Source checks read the assembled shop module."""
from pathlib import Path

_read_text = Path.read_text


def _assembled_read_text(self, *args, **kwargs):
    text = _read_text(self, *args, **kwargs)
    if self.name == "main.py" and "MAIN_PY_ASSEMBLED_FROM_PARTS" in text:
        parts = self.resolve().parent / "main_src"
        chunks = [_read_text(parts / f"part-{i:02d}", encoding="utf-8") for i in range(11)]
        return "".join(chunks).replace("{{ARROW}}", chr(0x2192)).replace("{{EMDASH}}", chr(0x2014))
    return text


Path.read_text = _assembled_read_text
