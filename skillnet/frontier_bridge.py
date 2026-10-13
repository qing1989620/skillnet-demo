"""Read-only scoped frontier projection for an exact host-owned research input.

The production pipeline continues to execute its own plan and frozen contracts.
This bridge observes a registered input and compares finite declarations only;
it never runs an experimental operator or changes routing, rewards or skills.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re

from . import frontier_ops, frontier_runtime, state_policy

VERSION = 'skillnet-frontier-bridge-v1'
SCOPE = 'registered experimental CSV operators / readonly projection'
INPUT_NAME = 'input_raw_predictions.csv'
INPUT_LOGICAL_NAME = 'raw_predictions.csv'
OPERATOR_IDS = ('deduplicate', 'exclude_cross_split', 'drop_missing_score', 'metrics_decimal')


def project(run, workspace: Path) -> dict | None:
    """Return an observation bound to registered host bytes, or leave unmeasured.

    Policy labels, file paths and apparent schemas alone are insufficient. The
    exact public task catalog, registered task input, and observed byte snapshot
    must agree before the narrower experimental registry is projected.
    """
    policy = run.staged.get('state_policy') or {}
    if not isinstance(policy, dict) or policy.get('host_reference') != 'research-reproducibility-v1':
        return None
    task_sha = hashlib.sha256(run.task.strip().encode()).hexdigest()
    catalog = state_policy.input_catalog(run.task)
    if (policy.get('task_sha256') != task_sha or len(catalog) != 1
            or catalog[0].get('file') != INPUT_LOGICAL_NAME):
        return None
    matches = [artifact for artifact in run.artifacts if artifact.name == INPUT_NAME]
    if len(matches) != 1:
        return None
    registered = matches[0]
    expected = catalog[0]
    if (registered.kind != '任务输入' or registered.logical_name != INPUT_LOGICAL_NAME
            or registered.source_run_id != run.run_id or registered.from_step is not None
            or not re.fullmatch(r'[a-f0-9]{64}', registered.sha256 or '')
            or registered.sha256 != expected.get('sha256')
            or registered.bytes != expected.get('bytes')):
        return None
    observation = frontier_ops.observe(Path(workspace) / 'artifacts' / INPUT_NAME)
    rows = observation.get('checks', {}).get('checks', [])
    file_check = next((check for check in rows if check.get('fact_id') == 'data.file'), None)
    if not file_check or file_check.get('state') != 'passed':
        return None
    evidence = file_check.get('evidence') or {}
    if evidence.get('sha256') != registered.sha256 or evidence.get('bytes') != registered.bytes:
        return None
    # Every data condition came from the same complete byte snapshot. Refuse a
    # partial/mixed observation rather than borrowing a path's current identity.
    if any((check.get('evidence') or {}).get('sha256') != registered.sha256
           for check in rows if str(check.get('fact_id', '')).startswith('data.')):
        return None
    operators = [operator for operator in frontier_ops.registry() if operator['id'] in OPERATOR_IDS]
    if {operator['id'] for operator in operators} != set(OPERATOR_IDS):
        return None
    diagnosis = frontier_runtime.diagnose(observation['facts'], operators, operators)
    result = {'version': VERSION, 'scope': SCOPE, 'input_sha256': registered.sha256,
              'input': {'name': registered.name, 'logical_name': registered.logical_name,
                        'bytes': registered.bytes, 'source_run_id': registered.source_run_id},
              'observation': observation, 'diagnosis': diagnosis, 'registry': operators,
              'registry_sha256': frontier_runtime.digest(operators),
              'host_reference': policy['host_reference'], 'task_sha256': task_sha,
              'source': 'registered_host_input_observed_before_pipeline_execution',
              'boundary': frontier_runtime.BOUNDARY + '此处只读诊断，不替代原生产计划或验收，也不执行实验程序。',
              'read_only': True, 'experimental_execution_applied': False,
              'reward_applied': False, 'formal_library_changed': False}
    result['report_sha256'] = frontier_runtime.digest(result)
    return result


def with_integrity(recorded: dict, files: list[dict]) -> dict:
    """Retain execution-time facts and qualify their input's current integrity."""
    projection = copy.deepcopy(recorded)
    recorded_sha = projection.get('report_sha256')
    try:
        record_intact = (isinstance(recorded_sha, str)
                         and recorded_sha == frontier_runtime.digest({key: value for key, value in projection.items()
                                                                      if key != 'report_sha256'}))
    except (TypeError, ValueError):
        record_intact = False
    expected_name = (projection.get('input') or {}).get('name')
    matches = [item for item in files if item.get('name') == expected_name
               and item.get('sha256') == projection.get('input_sha256') and item.get('role') == 'input']
    projection['record_integrity'] = 'passed' if record_intact else 'failed'
    projection['input_integrity'] = 'passed' if record_intact and len(matches) == 1 and matches[0].get('integrity') == 'passed' else 'failed'
    projection['observation_time'] = 'recorded_before_execution; not re-inferred on capsule read'
    # This qualified projection is a new value; retain its source digest and
    # recompute the outer digest rather than presenting altered signed content.
    projection['recorded_report_sha256'] = projection.pop('report_sha256', None)
    projection['report_sha256'] = frontier_runtime.digest(projection)
    return projection
