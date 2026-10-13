"""Pinned resources travel as data through service and SDK, never as modules."""
import copy
import hashlib
import json
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

import server
from skillnet import resources
from skillnet.catalog import SkillLibrary
from skillnet.evidence import digest
from skillnet.integration import ClientConfig, IntegrationError, SkillNetClient, skill_tools
from skillnet.schema import Skill


@pytest.fixture
def package(tmp_path,monkeypatch):
    directory=tmp_path/'seed/community/skills/test-package'
    directory.mkdir(parents=True)
    body=b'---\nname: example\ndescription: example\n---\n# Example\n'
    (directory/'SKILL.md').write_bytes(body)
    (directory/'scripts').mkdir()
    (directory/'scripts/danger.py').write_bytes(b'raise RuntimeError("THIS MUST NEVER EXECUTE")\n')
    (directory/'LICENSE').write_bytes(b'MIT\n')
    skill=Skill('example','example','test',source='github',metadata={
        'package_path':'seed/community/skills/test-package','repository':'test/example',
        'commit':'a'*40,'source_url':'https://github.com/test/example',
        'content_sha256':hashlib.sha256(body).hexdigest()})
    (tmp_path/'seed/community/catalog.json').write_text(json.dumps([skill.to_dict()]),encoding='utf-8')
    records=resources.build_snapshots(tmp_path)
    (tmp_path/'seed/community/packages.json').write_text(json.dumps(records),encoding='utf-8')
    monkeypatch.setattr(resources,'ROOT',tmp_path)
    resources._snapshots.cache_clear()
    yield skill,directory
    resources._snapshots.cache_clear()


def test_resource_transfer_verifies_all_bytes_without_executing_script(package):
    skill,directory=package
    record=resources.package_manifest(skill)
    assert len(record['files'])==3 and record['execution_verified'] is False
    assert record['package_sha256']==digest({k:v for k,v in record.items() if k!='package_sha256'})
    assert resources.read_resource(skill,'scripts/danger.py').startswith(b'raise RuntimeError')
    record['files'].clear()
    assert len(resources.package_manifest(skill)['files'])==3
    (directory/'scripts/danger.py').write_bytes(b'changed')
    with pytest.raises(resources.ResourceIntegrityError):resources.read_resource(skill,'scripts/danger.py')


def test_resource_snapshot_excludes_local_caches_and_hidden_files(package):
    _,directory=package
    (directory/'scripts/__pycache__').mkdir()
    (directory/'scripts/__pycache__/danger.pyc').write_bytes(b'local cache')
    (directory/'.pytest_cache').mkdir()
    (directory/'.pytest_cache/state').write_bytes(b'local state')
    (directory/'scripts/loose.pyc').write_bytes(b'local bytecode')
    record=resources.build_snapshots(directory.parents[3])['example']
    assert {r['path'] for r in record['files']}=={'SKILL.md','scripts/danger.py','LICENSE'}


@pytest.mark.parametrize('path',['../LICENSE','/LICENSE','scripts/../LICENSE','scripts\\danger.py',
    'scripts//danger.py','.env','C:/secret','scripts/\x00danger.py','scripts/.hidden'])
def test_resources_reject_traversal_hidden_files_and_windows_paths(package,path):
    skill,_=package
    with pytest.raises(ValueError):resources.read_resource(skill,path)


def test_resources_reject_unregistered_files_wrong_package_and_broken_pin(package):
    skill,directory=package
    (directory/'new.txt').write_text('unregistered',encoding='utf-8')
    with pytest.raises(FileNotFoundError):resources.read_resource(skill,'new.txt')
    wrong=copy.deepcopy(skill)
    wrong.metadata['package_path']='seed/community/skills/other'
    with pytest.raises(resources.ResourceIntegrityError):resources.package_manifest(wrong)
    (directory/'SKILL.md').write_text('changed',encoding='utf-8')
    with pytest.raises(ValueError):resources.build_snapshots(directory.parents[3])


def test_resource_http_contract_requires_token_and_fails_closed_on_tamper(package,monkeypatch):
    skill,directory=package
    monkeypatch.setattr(server,'STATE',{'lib':SkillLibrary([skill])})
    monkeypatch.setattr(server,'ACCESS_TOKEN','test-token')
    client=TestClient(server.app)
    try:
        assert client.get('/api/skill/example/package').status_code==401
        headers={'X-SkillNet-Token':'test-token'}
        manifest=client.get('/api/skill/example/package',headers=headers).json()
        assert manifest['name']=='example'
        response=client.get('/api/skill/example/resource',params={'path':'scripts/danger.py'},headers=headers)
        assert response.status_code==200 and b'MUST NEVER EXECUTE' in response.content
        assert response.headers['content-type']=='application/octet-stream'
        assert 'sandbox' in response.headers['content-security-policy']
        assert client.get('/api/skill/example/resource',params={'path':'../LICENSE'},headers=headers).status_code==422
        assert client.get('/api/skill/example/resource',params={'path':'new.txt'},headers=headers).status_code==404
        (directory/'scripts/danger.py').write_bytes(b'changed')
        assert client.get('/api/skill/example/resource',params={'path':'scripts/danger.py'},headers=headers).status_code==409
    finally:client.close()


def test_optional_resource_tools_are_progressive_readonly_and_digest_checked(package):
    skill,directory=package
    record=resources.package_manifest(skill)
    def handler(request):
        if request.url.path.endswith('/package'):return httpx.Response(200,json=record)
        assert request.url.params['path']=='scripts/danger.py'
        return httpx.Response(200,content=(directory/'scripts/danger.py').read_bytes())
    assert len(skill_tools())==2 and len(skill_tools(include_resources=True))==4
    with SkillNetClient(ClientConfig(),transport=httpx.MockTransport(handler)) as client:
        assert client.call_tool('list_skill_resources',{'name':'example'})['name']=='example'
        data=client.call_tool('read_skill_resource',{'name':'example','path':'scripts/danger.py'})
        assert data['executed'] is False and data['kind']=='untrusted_reference_data'
        assert 'MUST NEVER EXECUTE' in data['text']
        with pytest.raises(ValueError):client.call_tool('read_skill_resource',{'name':'example','path':'../LICENSE'})
        (directory/'scripts/danger.py').write_bytes(b'changed')
        with pytest.raises(IntegrationError) as error:client.call_tool('read_skill_resource',{'name':'example','path':'scripts/danger.py'})
        assert error.value.code=='digest_mismatch'
        record['license']='changed'
        with pytest.raises(IntegrationError) as error:client.get_skill_package('example')
        assert error.value.code=='digest_mismatch'


def test_all_delivered_packages_match_recorded_resource_snapshot():
    snapshots=resources._snapshots()
    assert len(snapshots)==1769
    tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=resources.ROOT).decode('utf-8').split('\0'))
    total=0
    for record in snapshots.values():
        assert record['package_sha256']==digest({k:v for k,v in record.items() if k!='package_sha256'})
        root=resources.ROOT/record['package_path']
        for item in record['files']:
            assert record['package_path']+'/'+item['path'] in tracked
            raw=(root/item['path']).read_bytes()
            assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
            total+=1
    assert total==10898
