import hashlib
from pathlib import Path

import pytest

from bench.run_bench import dataset_provenance, load_tasks


@pytest.mark.parametrize('dataset,version,file,prefix', [
    ('dev','dev-v1','tasks/benchmark.json','T'),
    ('heldout','heldout-v1','tasks/heldout.json','H'),
])
def test_experiment_metadata_identifies_the_actual_selected_tasks(dataset,version,file,prefix):
    record=dataset_provenance(dataset)
    assert record['dataset']==version and record['split']==dataset
    assert record['dataset_file']==file
    root=Path(__file__).resolve().parents[1]
    assert record['dataset_sha256']==hashlib.sha256((root/file).read_bytes()).hexdigest()
    tasks=load_tasks(dataset)
    assert tasks and all(task['id'].startswith(prefix) for task in tasks)
