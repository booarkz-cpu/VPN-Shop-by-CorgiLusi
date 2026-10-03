"""Current operator entrypoints must link to available guides."""
import re
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = json.loads((ROOT/'docs/current-guides.json').read_text())['guides']


@pytest.mark.parametrize('filename',GUIDES)
def test_current_guide_links_exist(filename):
    path = ROOT / filename
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
        if re.match(r'^[a-zA-Z]+:',target) or target.startswith('#'):
            continue
        link = target.split('#',1)[0]
        assert (path.parent/link).exists(), f'{filename}: missing link {target}'


def test_generated_api_catalogue_matches_application():
    import importlib.util
    spec=importlib.util.spec_from_file_location('api_docs', ROOT/'scripts/generate-api-docs.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert (ROOT/'docs/API_ENDPOINTS.md').read_text()==module.render()


@pytest.mark.parametrize('filename',GUIDES)
def test_current_guides_do_not_reference_invented_prerelease_tags(filename):
    manifest=json.loads((ROOT/'release-manifest.template.json').read_text())
    version=re.escape(manifest['version'])
    assert not re.search(r'v?'+version+r'-(?:alpha|beta|rc)\.\d+', (ROOT/filename).read_text()), filename
