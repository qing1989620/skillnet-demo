"""Cache is an optimization; concurrent writes must not break in-memory routing."""
from concurrent.futures import ThreadPoolExecutor
import threading

import numpy as np
import pytest

from skillnet import semantic


def index(embed):
    value=semantic.DenseIndex.__new__(semantic.DenseIndex)
    value.np=np
    value.status={'revision':'test','max_tokens':256}
    value.embed=embed
    return value


def test_same_process_simultaneous_builds_use_unique_temporary_files(tmp_path,monkeypatch):
    monkeypatch.setattr(semantic,'ROOT',tmp_path)
    barrier=threading.Barrier(2)
    def embed(texts,prefix):
        barrier.wait(timeout=5)
        return np.ones((len(texts),384),dtype=np.float32)
    indices=[index(embed),index(embed)]
    paths=[]
    save=np.savez_compressed
    def capture(path,**kwargs):
        paths.append(path)
        return save(path,**kwargs)
    monkeypatch.setattr(np,'savez_compressed',capture)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda i:i.fit(['s'],['text']),indices))
    assert len(paths)==len(set(paths))==2
    assert all(i.snapshot[1].shape==(1,384) for i in indices)
    assert not list((tmp_path/'data/semantic-cache').glob('*.tmp.npz'))
    cached=index(lambda *_:pytest.fail('valid cache must be reused'))
    cached.fit(['s'],['text'])
    assert np.array_equal(cached.snapshot[1],indices[0].snapshot[1])


def test_windows_reader_lock_does_not_prevent_valid_in_memory_index(tmp_path,monkeypatch):
    monkeypatch.setattr(semantic,'ROOT',tmp_path)
    def locked(*_):raise PermissionError('reader holds destination')
    monkeypatch.setattr(semantic.os,'replace',locked)
    i=index(lambda texts,prefix:np.ones((len(texts),384),dtype=np.float32))
    i.fit(['s'],['text'])
    assert i.snapshot[0]==['s'] and np.all(i.snapshot[1]==1)
    assert not list((tmp_path/'data/semantic-cache').glob('*.tmp.npz'))


@pytest.mark.parametrize('damage',['bytes','shape'])
def test_damaged_cache_is_recomputed(tmp_path,monkeypatch,damage):
    monkeypatch.setattr(semantic,'ROOT',tmp_path)
    i=index(lambda texts,prefix:np.ones((len(texts),384),dtype=np.float32))
    i.fit(['s'],['text'])
    path=next((tmp_path/'data/semantic-cache').glob('*.npz'))
    if damage=='bytes':path.write_bytes(b'not a zip')
    else:np.savez_compressed(path,embeddings=np.zeros((9,384)))
    i.fit(['s'],['text'])
    assert i.snapshot[1].shape==(1,384) and np.all(i.snapshot[1]==1)
