"""Deterministic feasibility fence for the three reviewed tabular operators.

This guard checks the proposed action's data boundary, not whether the action
matches an ambiguous natural-language request. It cannot certify task success.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import time
from . import conditional_boundary as cb, utility_ops

VERSION='reviewed-tabular-preflight-v1'


def preflight(raw:bytes, mask:int):
    if type(raw) is not bytes or len(raw)>1048576:raise ValueError('bounded bytes required')
    if type(mask) is not int or not 0<=mask<=7:raise ValueError('registered mask required')
    intent={k:bool(mask & (1<<j)) for j,k in enumerate(utility_ops.NAMES)}
    intent['goal']='group_mean'
    observed=cb.observe(raw,intent,mask)
    reasons=['unsupported_schema'] if not observed['supported'] else [k for k,v in observed['conditions'].items() if v]
    return {'version':VERSION,'allowed':not reasons,'reasons':reasons,'observed':observed,
            'input_sha256':hashlib.sha256(raw).hexdigest(),'operator_code_sha256':utility_ops.CODE_SHA,
            'checked_at_ns':time.time_ns(),'semantic_scope_validated':False,
            'warning':'Only reviewed data feasibility; request ambiguity and wrong effect selection remain unverified.'}


def execute(raw:bytes,mask:int,workspace:Path):
    check=preflight(raw,mask)
    if not check['allowed']:
        return {'state':'preflight_rejected','preflight':check,'execution':None,'artifacts':{}}
    root=Path(workspace).absolute()
    from .frontier_ops import _linked
    if _linked(root):raise ValueError('linked workspace forbidden')
    root.mkdir(parents=True,exist_ok=False)
    # Execute the exact checked snapshot, rather than reopen a caller's source.
    source=root/'input.snapshot.csv';source.write_bytes(raw)
    ex=utility_ops.execute(mask,source,root/'program')
    if ex['input_sha256']!=check['input_sha256']:raise ValueError('snapshot changed')
    return {'state':ex['status'],'preflight':check,'execution':ex,'artifacts':ex['artifacts'],
            'directory':str(root/'program')}
