"""Release parity must detect missing assets and stale servers, without model calls."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import zipfile
import pytest

from skillnet.distribution import build_identity
from skillnet.model_assets import restore_bundled_model
from tools.verify_delivery import digest, verify, safe_path

ROOT = Path(__file__).resolve().parents[1]


def fixture_delivery(tmp_path):
    (tmp_path/'config').mkdir();(tmp_path/'data').mkdir()
    (tmp_path/'server.py').write_bytes(b'current backend\n')
    (tmp_path/'data/library.json').write_bytes(b'{}\n')
    rows = [{'path':n, 'bytes':len((tmp_path/n).read_bytes()),
             'sha256':hashlib.sha256((tmp_path/n).read_bytes()).hexdigest(), 'mutable':False}
            for n in ['server.py','data/library.json']]
    raw=json.dumps({'files':rows}).encode()
    (tmp_path/'config/delivery-manifest.json').write_bytes(raw)
    (tmp_path/'config/delivery.json').write_text(json.dumps({'release':'test',
        'source_tree_sha256':digest(rows),'manifest_sha256':hashlib.sha256(raw).hexdigest()}))


def test_delivery_detects_stale_backend_and_missing_assets(tmp_path):
    fixture_delivery(tmp_path)
    assert verify(tmp_path,True)['ok']
    (tmp_path/'server.py').write_bytes(b'old backend\n')
    assert verify(tmp_path)['differences']==[{'path':'server.py','reason':'changed'}]
    (tmp_path/'server.py').unlink()
    assert verify(tmp_path)['differences']==[{'path':'server.py','reason':'missing'}]


def test_runtime_only_changes_do_not_hide_product_changes(tmp_path):
    fixture_delivery(tmp_path)
    (tmp_path/'data/library.json').write_bytes(b'{"new_task":1}')
    assert verify(tmp_path)['ok']
    assert not verify(tmp_path,True)['ok']
    manifest=tmp_path/'config/delivery-manifest.json'
    manifest.write_bytes(manifest.read_bytes()+b' ')
    with pytest.raises(ValueError,match='manifest SHA'):verify(tmp_path)


@pytest.mark.parametrize('name',['../secret','/etc/passwd','C:/secret','a\\b','.env','.env.local','x.key','.git/config','.e_run1/Local State'])
def test_manifest_cannot_package_secrets_or_escape_root(tmp_path,name):
    with pytest.raises(ValueError):safe_path(tmp_path,name)


def test_zip_identity_does_not_require_git_or_expose_credentials(tmp_path):
    fixture_delivery(tmp_path)
    (tmp_path/'.env').write_text('DEEPSEEK_API_KEY=private-key')
    identity=build_identity(tmp_path)
    assert identity['release']=='test' and identity['git_commit'] is None
    assert 'private-key' not in json.dumps(identity)


def test_occupied_port_exits_before_starting_a_second_server(tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen()
        port=listener.getsockname()[1]
        result=subprocess.run([sys.executable,str(ROOT/'run.py'),'--port',str(port),'--no-browser'],
            cwd=tmp_path,capture_output=True,encoding='utf-8',errors='replace',timeout=15)
    assert result.returncode==2 and str(port) in result.stderr


@pytest.mark.parametrize('failure',[None,'changed_bytes','unexpected_path'])
def test_offline_encoder_rejects_corrupt_or_extra_assets(tmp_path,failure):
    (tmp_path/'config').mkdir();(tmp_path/'assets/semantic').mkdir(parents=True)
    data=b'fixed public weights'
    manifest={'repository':'fixture','revision':'fixed','files':{
        'onnx/model_quantized.onnx':{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}}
    pinned=json.dumps(manifest).encode()
    (tmp_path/'config/semantic_model.json').write_bytes(pinned)
    with zipfile.ZipFile(tmp_path/'assets/semantic/multilingual-e5-small.zip','w') as archive:
        archive.writestr('onnx/model_quantized.onnx',data if failure!='changed_bytes' else b'x'*len(data))
        if failure=='unexpected_path':archive.writestr('../escaped',b'bad')
    target=tmp_path/'cache'
    if failure:
        with pytest.raises(ValueError):restore_bundled_model(target,tmp_path)
        assert not (target/'manifest.json').exists()
        assert not (tmp_path/'escaped').exists()
    else:
        restore_bundled_model(target,tmp_path)
        assert (target/'onnx/model_quantized.onnx').read_bytes()==data
        assert (target/'manifest.json').read_bytes()==pinned
    assert (tmp_path/'config/semantic_model.json').read_bytes()==pinned
