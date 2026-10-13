"""Download only pinned model data from its official Hugging Face repository."""
import hashlib
import json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Xenova/multilingual-e5-small'
REVISION = '761b726dd34fb83930e26aab4e9ac3899aa1fa78'


def main():
    target = ROOT / '.models/multilingual-e5-small'
    target.mkdir(parents=True, exist_ok=True)
    files = {}
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for name in ('config.json', 'tokenizer.json', 'onnx/model_quantized.onnx'):
            dst = target / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            with client.stream('GET', f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}') as res:
                res.raise_for_status()
                tmp = dst.with_suffix(dst.suffix + '.partial')
                size, sha = 0, hashlib.sha256()
                with tmp.open('wb') as out:
                    for block in res.iter_bytes():
                        size += len(block)
                        if size > 150_000_000:
                            raise ValueError('Model file exceeds expected bound')
                        sha.update(block)
                        out.write(block)
                tmp.replace(dst)
                files[name] = dict(bytes=size, sha256=sha.hexdigest())
                print(name, size, flush=True)
    manifest = dict(repository=REPO, revision=REVISION, files=files,
                    pooling='attention-mask mean pooling + L2 normalization', prefixes=['query: ', 'passage: '])
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (ROOT / 'config/semantic_model.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
