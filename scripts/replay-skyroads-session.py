#!/usr/bin/env python3
"""Replay a browser recording through the same verified Python core."""
import argparse
import json
from pathlib import Path
from skyroads_session import Catalog,replay

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recording',type=Path)
args=parser.parse_args();recording=json.loads(args.recording.read_text())
if recording.get('format')=='skyroads-cycle-v2':
    from skyroads_cycle import replay
result=replay(Catalog(),recording)
print(json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2))
