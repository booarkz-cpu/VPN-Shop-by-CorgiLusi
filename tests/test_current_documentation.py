"""Current operator entrypoints must link to available guides."""
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ['README.md','DOCUMENTATION.md','DOCUMENTATION_RU.md','INSTALL.md','INSTALL_STEPS.md',
          'INSTRUCTION.md','FUNCTIONS.md','SECURITY.md','MOBILE.md','MODULES.md',
          'OPERATIONS_RUNBOOK_RU.md','API_REFERENCE_RU.md','docs/INDEX.md',
          'docs/ru/WORKSPACE_GIVEAWAYS.md','docs/ru/WORKSPACE_UPGRADE.md']


@pytest.mark.parametrize('filename',GUIDES)
def test_current_guide_links_exist(filename):
    path = ROOT / filename
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
        if re.match(r'^[a-zA-Z]+:',target) or target.startswith('#'):
            continue
        link = target.split('#',1)[0]
        assert (path.parent/link).is_file(), f'{filename}: missing link {target}'
