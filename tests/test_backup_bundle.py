"""Recovery encryption rejects corruption, truncation and frame substitution."""
import importlib.util
from io import BytesIO
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

spec=importlib.util.spec_from_file_location('backup_bundle',Path(__file__).parents[1]/'scripts/backup_bundle.py')
bundle=importlib.util.module_from_spec(spec);spec.loader.exec_module(bundle)
SECRET=b'a-long-recovery-password'


def encrypted(data):
    result=BytesIO();bundle.encrypt(BytesIO(data),result,SECRET);return result.getvalue()


@pytest.mark.parametrize('data',[b'',b'private settings',b'X'*(bundle.CHUNK+5)])
def test_streaming_roundtrip(data):
    result=BytesIO();bundle.decrypt(BytesIO(encrypted(data)),result,SECRET)
    assert result.getvalue()==data


@pytest.mark.parametrize('mutation',['wrong-password','header','ciphertext','missing-final','truncated','trailing','frame-size'])
def test_rejected_corrupt_bundles(mutation):
    data=bytearray(encrypted(b'private data'));secret=SECRET
    if mutation=='wrong-password':secret=b'wrong-long-password'
    elif mutation=='header':data[len(bundle.MAGIC)]^=1
    elif mutation=='ciphertext':data[-1]^=1
    elif mutation=='missing-final':data=data[:-20]
    elif mutation=='truncated':data=data[:-1]
    elif mutation=='trailing':data+=b'extra'
    elif mutation=='frame-size':data[len(bundle.MAGIC)+24:len(bundle.MAGIC)+28]=b'\xff'*4
    with pytest.raises((ValueError,InvalidTag)):bundle.decrypt(BytesIO(data),BytesIO(),secret)


def test_random_salt_and_nonce():
    assert encrypted(b'same')!=encrypted(b'same')
