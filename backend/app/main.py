"""Shop HTTP entrypoint.

MAIN_PY_ASSEMBLED_FROM_PARTS
The module body is stored in main_src/part-00 through part-10.
{{ARROW}} is expanded to the unicode arrow and {{EMDASH}} to the em dash.
"""
from pathlib import Path

_parts = Path(__file__).resolve().parent / "main_src"
_chunks = [(_parts / f"part-{i:02d}").read_text(encoding="utf-8") for i in range(11)]
_source = "".join(_chunks).replace("{{ARROW}}", chr(0x2192)).replace("{{EMDASH}}", chr(0x2014))
exec(compile(_source, __file__, "exec"), globals())
del _parts, _chunks, _source
