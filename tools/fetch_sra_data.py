"""Fetch pinned public SRA research data with byte/SHA checks; execute no upstream code."""
from pathlib import Path
import argparse,hashlib,json,urllib.request,zipfile

PIN='277fd8d2bbd7d3b81a5cf4ffa6e87e18c7906e4f'
FILES={
    'README.md':(18092,'55c4e37e5e96c5cc9eeecf586b83f8095721c1aacdd4cdbaef6233c3a47628aa'),
    'LICENSE':(1067,'47bef547eb656e100323e67b6808dc59bf14846e0c1b4cef0bb9020e9c237b2a'),
    'data/bench/corpus/corpus.json.zip':(71440203,'2e8abf91ad992bebe2c1bf87cb7b77996edf1828bf55ddeba44c456956673849'),
    'data/bench/instances/bigcodebench.json':(4623115,'0ed01363e2c93134cf8696fea47b6d640f32f0d7ae9d7b478a05595c3f5ae788'),
    'data/bench/instances/champ.json':(72375,'d61346716cede953afb352e739e170b96d2bfb98824edd91b8783dc3526c7cec'),
    'data/bench/instances/logicbench.json':(531231,'af5055caac041ea08cee47622f5d922b47b2ba0a8e3a60b87349599eeff1bdfe'),
    'data/bench/instances/medcalcbench.json':(3693279,'814f6b082f56cf89dd9c50be7ab87b5bcb0e41633138951e42b38d6923c3244e'),
    'data/bench/instances/theoremqa.json':(320643,'c969a7291e23361ba9f377e464be76093804deb628b964fb846c6eff6b28deeb'),
    'data/bench/instances/toolqa.json':(413554,'e41eb4d4b67c1dd8e1178c88e9e8ff15525b31803694e9459d115c274fb04f0e'),
}
CORPUS_SHA='16ee509ae5bea8c2e17167dffecd89100a7d8dfa31256c3742426758c7169b5e'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    out=a.output.resolve()/'sra-data';out.mkdir(parents=True,exist_ok=True);rows=[]
    for name,(size,expected) in FILES.items():
        target=out/Path(name).name
        if not target.exists() or target.stat().st_size!=size or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            temporary=target.with_suffix(target.suffix+'.partial');sha=hashlib.sha256();count=0
            url=f'https://raw.githubusercontent.com/oneal2000/SR-Agents/{PIN}/{name}'
            with urllib.request.urlopen(url,timeout=60) as response,temporary.open('wb') as f:
                while block:=response.read(1024*1024):
                    count+=len(block)
                    if count>size:raise ValueError('Downloaded source exceeds its frozen size')
                    sha.update(block);f.write(block)
            if count!=size or sha.hexdigest()!=expected:raise ValueError('Pinned source integrity mismatch: '+name)
            temporary.replace(target)
        rows.append(dict(upstream_path=name,local_name=target.name,bytes=size,sha256=expected));print('Verified',target.name,size,'bytes',flush=True)
    with zipfile.ZipFile(out/'corpus.json.zip') as archive:
        entries=archive.infolist()
        if len(entries)!=1 or entries[0].filename!='corpus.json' or entries[0].file_size!=232255987:raise ValueError('Unexpected bounded corpus archive')
        corpus=archive.read(entries[0])
    if hashlib.sha256(corpus).hexdigest()!=CORPUS_SHA:raise ValueError('Expanded corpus integrity mismatch')
    (out/'corpus.json').write_bytes(corpus)
    rows.append(dict(upstream_path='zip:corpus.json',local_name='corpus.json',bytes=len(corpus),sha256=CORPUS_SHA))
    manifest=dict(source='https://github.com/oneal2000/SR-Agents',commit=PIN,files=rows,code_executed=False,
        schema_preview_ids=['logicbench_00000','logicbench_00001'],scope='Public data for local research; upstream executable code not executed')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')


if __name__=='__main__':main()
