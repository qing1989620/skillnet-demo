"""Read a complete scientific community package via the actual service SDK."""
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet import config
from skillnet.integration import ClientConfig, SkillNetClient


def main():
    name='gh-scientific-13c-metabolic-flux-d6d252'
    with SkillNetClient(ClientConfig(token=os.environ.get('SKILLNET_TOKEN',''))) as client:
        manifest=client.call_tool('list_skill_resources',{'name':name})
        files=[]
        for item in manifest['files']:
            raw=client.read_skill_resource(name,item['path'],expected_sha256=item['sha256'])
            files.append(dict(path=item['path'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        script=next(r for r in files if r['path'].endswith('.py') and r['bytes']<=65536)
        text=client.call_tool('read_skill_resource',{'name':name,'path':script['path']})
        assert text['executed'] is False and text['kind']=='untrusted_reference_data'
    snapshots=json.loads((ROOT/'seed/community/packages.json').read_text(encoding='utf-8'))
    report=dict(kind='real-http-readonly-community-resources',packages=len(snapshots),
        registered_files=sum(len(r['files']) for r in snapshots.values()),sample=name,
        package_sha256=manifest['package_sha256'],repository=manifest['repository'],commit=manifest['commit'],
        license=manifest['license'],downloaded_files=files,all_digests_matched=True,executed=False,
        optional_tool='read_skill_resource',tool_resource=script['path'],production_connection_verified=False)
    (ROOT/'out/skill-resources-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(dict(packages=report['packages'],registered_files=report['registered_files'],
        sample_files=len(files),all_digests_matched=True,executed=False)))


if __name__=='__main__':main()
