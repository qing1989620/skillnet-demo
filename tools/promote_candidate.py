"""Promote an exact quarantined candidate after frozen paired execution evaluation."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skillnet.catalog import SkillLibrary
from skillnet.governance import promote
from skillnet.promotion import inspect_promotion
from skillnet import config
import json
import os
from contextlib import contextmanager


@contextmanager
def promotion_lock():
    """Serialize CLI writers before loading the library; a crash fails closed."""
    path=config.OUT_DIR/'.promotion.lock'
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('Promotion writer lock exists; inspect the previous writer before retrying')
    try:
        with os.fdopen(fd,'w',encoding='ascii') as stream:
            stream.write(str(os.getpid()))
        from skillnet.worker import acquire_writer_lock
        try:
            writer=acquire_writer_lock(config.OUT_DIR/'worker.lock')
        except OSError as exc:
            raise RuntimeError('Stop the API writer and external worker before promotion; restart after the atomic library update') from exc
        try:
            yield
        finally:
            writer.close()
    finally:
        path.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('candidate',type=Path)
    parser.add_argument('report',type=Path)
    parser.add_argument('--audit-only',action='store_true',help='Read physical evidence and print every gate; no writes or model calls')
    args=parser.parse_args()
    if args.audit_only:
        decision=inspect_promotion(args.candidate,args.report,SkillLibrary.load())
        print(json.dumps(decision,ensure_ascii=False,indent=2))
        sys.exit(0 if decision['eligible'] else 2)
    with promotion_lock():
        skill=promote(args.candidate,args.report,SkillLibrary.load())
        print(json.dumps(dict(promoted=skill.name,receipt=skill.stats['verified_improvement_receipt']),ensure_ascii=False,indent=2))
