#!/usr/bin/env python3
"""Rerun all original tick checks, retaining independent x86 results for JS."""
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('tick_fixture',ROOT/'scripts/validate-skyroads-tick.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
execute=fixture.OriginalTick.execute
output=ROOT/'analysis/skyroads/tick-corpus.jsonl'
with output.open('w') as stream:
    def capture(self,road,state,config,controls):
        result=execute(self,road,state,config,controls)
        stream.write(json.dumps({'road_hex':road.hex(),'state':asdict(state),'config':asdict(config),
                                'input':asdict(controls),'result':asdict(result),'events':self.events},separators=(',',':'))+'\n')
        return result
    fixture.OriginalTick.execute=capture
    fixture.main()
