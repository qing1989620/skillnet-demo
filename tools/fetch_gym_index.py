"""Read public archive metadata using ordinary HTTP byte ranges, without executing code."""
from pathlib import Path
from html.parser import HTMLParser
import urllib.request,urllib.parse,json,io,zipfile,re,hashlib
import argparse
_parser=argparse.ArgumentParser();_parser.add_argument('--output',type=Path,required=True);_args=_parser.parse_args()
ROOT=_args.output.resolve();ROOT.mkdir(parents=True,exist_ok=True)
(ROOT/'sources').mkdir(exist_ok=True)
class Form(HTMLParser):
    def __init__(self):super().__init__();self.action='';self.fields={}
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='form':self.action=d.get('action','')
        if tag=='input' and d.get('name'):self.fields[d['name']]=d.get('value','')
html=urllib.request.urlopen('https://drive.google.com/uc?export=download&id=1AEA2WD5cV8KuVOJfZw28juc52NJdOkZG',timeout=40).read().decode()
form=Form();form.feed(html)
assert form.action.startswith('https://drive.usercontent.google.com/'),form.action
url=form.action+'?'+urllib.parse.urlencode(form.fields)
def fetch(start,end):
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'SkillNet-S1-Research'})
    with urllib.request.urlopen(req,timeout=90) as response:
        assert response.status==206,'Public server did not provide partial content'
        cr=response.headers['Content-Range'];total=int(cr.split('/')[-1]);b=response.read(end-start+2)
        assert len(b)==end-start+1,(start,end,len(b))
        return b,total,response.headers.get('ETag','')
first,size,etag=fetch(0,0)
print('Official Gym archive byte-range access:',size,'bytes',flush=True)
class Remote(io.RawIOBase):
    def __init__(self):self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else size+offset;return self.pos
    def read(self,n=-1):
        n=size-self.pos if n<0 else min(n,size-self.pos)
        assert 0<=n<=32*1024*1024,'Bounded metadata reader refuses a bulk archive read'
        if not n:return b''
        value,total,tag=fetch(self.pos,self.pos+n-1);assert total==size
        if etag and tag:assert tag==etag,'Archive changed while reading'
        self.pos+=n;return value
with zipfile.ZipFile(Remote()) as z:
    entries=[{'name':i.filename,'bytes':i.file_size,'compressed':i.compress_size,'offset':i.header_offset,'crc32':i.CRC,'compression':i.compress_type} for i in z.infolist()]
(ROOT/'sources/Gym-archive-index.json').write_text(json.dumps({'official_url':'https://drive.google.com/file/d/1AEA2WD5cV8KuVOJfZw28juc52NJdOkZG/view','bytes':size,'etag':etag,'entries':entries},ensure_ascii=False),encoding='utf-8')
print('Archive entries',len(entries),flush=True)
print('\n'.join(i['name'] for i in entries[:85]),flush=True)
(ROOT/'sources/Gym-range-url.local.txt').write_text(url,encoding='utf-8')
