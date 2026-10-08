"""Promote an exact quarantined candidate after frozen paired execution evaluation."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skillnet.catalog import SkillLibrary
from skillnet.governance import promote

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('candidate',type=Path)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    skill=promote(args.candidate,args.report,SkillLibrary.load())
    print('Promoted',skill.name)
