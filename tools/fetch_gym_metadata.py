"""Download bounded text entries from the official public Gym ZIP, verify ZIP CRC and SHA."""
from pathlib import Path,PurePosixPath
import urllib.request,json,struct,zlib,binascii,hashlib,time,concurrent.futures
import argparse
_parser=argparse.ArgumentParser();_parser.add_argument('--output',type=Path,required=True);_args=_parser.parse_args()
ROOT=_args.output.resolve();ROOT.mkdir(parents=True,exist_ok=True);S=ROOT/'sources';OUT=ROOT/'datasets/gym';OUT.mkdir(parents=True,exist_ok=True)
index=json.loads((S/'Gym-archive-index.json').read_text(encoding='utf-8'));url=(S/'Gym-range-url.local.txt').read_text();SIZE=index['bytes']
entries=[e for e in index['entries'] if e['bytes'] and e['bytes']<2*1024*1024 and (e['name'].endswith(('/instruction.md','/task.toml','/SKILL.md','/.skill_id','/dag_task.json','/LICENSE','/LICENSE.md','/LICENSE.txt')))]
print('Selected metadata:',len(entries),'entries,',sum(e['bytes'] for e in entries),'uncompressed bytes',flush=True)
def fetch(start,end):
    for retry in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'}),timeout=60) as s:
                assert s.status==206 and int(s.headers['Content-Range'].split('/')[-1])==SIZE
                b=s.read(end-start+2);assert len(b)==end-start+1;return b
        except Exception:
            if retry==3:raise
            time.sleep(.4*2**retry)
def one(e):
    rel=PurePosixPath(e['name']);assert not rel.is_absolute() and '..' not in rel.parts
    assert '\\' not in e['name'] and ':' not in e['name'],'Nonportable archive path'
    p=OUT.joinpath(*rel.parts).resolve();assert p.is_relative_to(OUT.resolve()),'Archive path escapes output'
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and len(p.read_bytes())==e['bytes'] and binascii.crc32(p.read_bytes())&0xffffffff==e['crc32']:b=p.read_bytes()
    else:
        header=fetch(e['offset'],e['offset']+29);assert header[:4]==b'PK\x03\x04'
        nl,xl=struct.unpack_from('<HH',header,26);start=e['offset']+30+nl+xl
        assert 0<e['compressed']<4*1024*1024,'Oversized compressed metadata entry'
        compressed=fetch(start,start+e['compressed']-1)
        if e['compression']==8:
            decompressor=zlib.decompressobj(-15);b=decompressor.decompress(compressed,e['bytes']+1)
            assert decompressor.eof and not decompressor.unconsumed_tail and not decompressor.unused_data,'Invalid bounded deflate stream'
        else:b=compressed if e['compression']==0 else None
        assert b is not None and len(b)==e['bytes'] and binascii.crc32(b)&0xffffffff==e['crc32'],e['name']
        p.write_bytes(b)
    return dict(path=e['name'],bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),crc32=e['crc32'])
rows=[];errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    work={pool.submit(one,e):e for e in entries}
    for f in concurrent.futures.as_completed(work):
        try:rows.append(f.result())
        except Exception as ex:errors.append(dict(path=work[f]['name'],error=type(ex).__name__+': '+str(ex)))
        if (len(rows)+len(errors))%60==0:print('Metadata',len(rows),'ready;',len(errors),'errors',flush=True)
manifest={'source':index['official_url'],'archive_bytes':SIZE,'archive_etag':index['etag'],'archive_full_sha256':None,'method':'HTTP byte ranges; each selected entry validated by ZIP CRC32 and SHA-256; no upstream code executed','files':sorted(rows,key=lambda r:r['path']),'errors':errors,'retrieved_date':'2026-10-14','license_boundary':'Official public benchmark; code license is not assumed to relicense all upstream skill content. Local research only; no redistribution.'}
(OUT/'download-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Original Gym metadata download complete',len(rows),'files;',len(errors),'errors',flush=True)
assert not errors,errors[:2]
