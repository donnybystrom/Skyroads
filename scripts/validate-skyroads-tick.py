#!/usr/bin/env python3
"""Differential state/trace checks of original gameplay tick2324h..2afdh."""
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import time
from unicorn.x86_const import *
from skyroads_tick import TickState, TickConfig, TickInput, TickResult, GLOBALS, LOCALS, tick
from skyroads_movement import s16

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'analysis/skyroads'
spec = importlib.util.spec_from_file_location('movement_fixture', ROOT / 'scripts/validate-skyroads-movement.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
BASE, DATA, FRAME = fixture.BASE, fixture.DATA, 0xf000
BRANCHES = {0x2388:'surface_effect', 0x23c5:'airborne_surface', 0x2499:'bounce_sound',
            0x24a1:'bounce', 0x24b4:'vertical_stop', 0x2596:'jump_start',
            0x25d3:'jump_assist', 0x2604:'fall_speed_floor', 0x260d:'crash_vertical',
            0x274b:'shove_left', 0x2788:'shove_right', 0x27df:'frontal_crash',
            0x2828:'low_speed_bump', 0x2848:'lateral_block', 0x28f2:'landing',
            0x2a13:'edge_drift', 0x2a2f:'height_underflow', 0x2a64:'oxygen_underflow',
            0x2aa1:'fuel_underflow', 0x2abc:'exit_fall', 0x2acc:'exit_fuel',
            0x2adc:'exit_oxygen', 0x2ae5:'exit_timer', 0x2af4:'crash_timer'}


class OriginalTick(fixture.Original):
    def __init__(self):
        super().__init__()
        self.allowed = [(0x2324, 0x2afd), (0x04c0, 0x05f6), (0x1631, 0x1fd9),
                        (0x5d4c, 0x5ded), (0x5e5a, 0x5ef6),
                        (0x03c2, 0x03d8), (0x0472, 0x04a1), (0x04bc, 0x04c0)]
        self.writable = [(offset, offset + width) for offset, width, _ in GLOBALS.values()]
        self.branches = Counter()
        self.completion_requested = False

    def code(self, uc, address, size, user):
        at = address - BASE
        if at in (0x2afd, 0x0f05):
            self.instructions += 1
            self.returned = True
            self.completion_requested = at == 0x0f05
            if self.completion_requested:
                self.events.append(('finish',))
                self.branches['finish_boundary'] += 1
            uc.emu_stop()
            return
        super().code(uc, address, size, user)
        if at in BRANCHES:
            self.branches[BRANCHES[at]] += 1
        if at == 0x186b:
            sp = uc.reg_read(UC_X86_REG_SP)
            self.events.append(('resolve', self.dword(sp + 2), self.word(sp + 6), self.word(sp + 8)))
        elif at == 0x03c2:
            self.events.append(('sound', self.word(uc.reg_read(UC_X86_REG_SP) + 2)))
        elif at == 0x0476:
            self.events.append(('sound_busy', int(self.word(0x1600) < ((self.word(0xaf38) + 8) & 65535))))

    def execute(self, road, state, config, controls):
        self.road(road)
        state = state.wrapped()
        for name, (offset, width, _) in GLOBALS.items():
            self.put(offset, getattr(state, name), width)
        self.uc.mem_write(DATA + FRAME - 0x40, bytes([0xa5]) * 0x60)
        for name, offset in LOCALS.items():
            self.put(FRAME + offset, getattr(state, name))
        for offset, value in [(0x4562, config.gravity_factor), (0x54a2, config.fuel_divisor),
                              (0x4566, config.oxygen_factor), (0x41c0, config.road_rows),
                              (0x4570, config.assist_enabled), (0x54aa, config.gravity),
                              (0x9330, controls.throttle), (0x95f4, controls.direction),
                              (0x547a, controls.jump), (0x1600, controls.timer),
                              (0x451a, 1), (0x0cb6, 1)]:
            self.put(offset, value)
        for reg, value in [(UC_X86_REG_CS, 0x1000), (UC_X86_REG_DS, 0x1676),
                           (UC_X86_REG_SS, 0x1676), (UC_X86_REG_ES, 0x1676),
                           (UC_X86_REG_SP, FRAME - 0x2c), (UC_X86_REG_BP, FRAME),
                           (UC_X86_REG_AX, 0xaaaa), (UC_X86_REG_BX, 0xbbbb),
                           (UC_X86_REG_CX, 0xcccc), (UC_X86_REG_DX, 0xdddd),
                           (UC_X86_REG_SI, 0xeeee), (UC_X86_REG_DI, 0xffff), (UC_X86_REG_EFLAGS, 0x202)]:
            self.uc.reg_write(reg, value)
        self.events = []
        self.error = None
        self.returned = False
        self.completion_requested = False
        self.uc.emu_start(BASE + 0x2324, 0, count=self.instruction_limit)
        assert self.returned and not self.error, self.error or 'Instruction budget exceeded'
        assert self.uc.reg_read(UC_X86_REG_BP) == FRAME
        expected_sp = FRAME - 0x2e if self.completion_requested else FRAME - 0x2c
        assert self.uc.reg_read(UC_X86_REG_SP) == expected_sp
        values = {}
        for name, (offset, width, signed) in GLOBALS.items():
            values[name] = int.from_bytes(self.uc.mem_read(DATA + offset, width), 'little', signed=signed)
        for name, offset in LOCALS.items():
            values[name] = self.word(FRAME + offset)
        return TickResult(TickState(**values), self.completion_requested)


def main():
    started = time.monotonic()
    original = OriginalTick()
    rng = random.Random(23241993)
    counts, events_count, outcomes = Counter(), Counter(), Counter()
    examples = {}
    digest = hashlib.sha256()
    max_instructions = 0
    manifest = json.loads((OUT / 'roads/manifest.json').read_text())

    def check(group, road, state, config, controls, road_index=None):
        nonlocal max_instructions
        events = []
        case = {'group': group, 'state': asdict(state), 'config': asdict(config),
                'input': asdict(controls), 'road_index': road_index,
                'road_sha256': hashlib.sha256(road).hexdigest()}
        old_branches = original.branches.copy()
        before = original.instructions
        expected = None
        try:
            expected = tick(road, state, config, controls, observer=events.append)
            observed = original.execute(road, state, config, controls)
            assert expected == observed, f'State mismatch: {expected} != {observed}'
            assert events == original.events, 'Intermediate trace mismatch'
        except Exception as exc:
            failure = {**case, 'error': repr(exc), 'expected': asdict(expected) if expected else None,
                       'python_events': events, 'original_events': original.events,
                       'counts_before_failure': dict(counts)}
            (OUT / 'tick-failure.json').write_text(json.dumps(failure, indent=2) + '\n')
            raise
        counts[group] += 1
        events_count.update(e[0] for e in events)
        outcomes[f'exit_{expected.state.exit_state}'] += 1
        max_instructions = max(max_instructions, original.instructions - before)
        digest.update(json.dumps([case, asdict(expected), events], separators=(',', ':')).encode())
        for branch in original.branches - old_branches:
            if branch not in examples:
                # Include synthetic bytes so every saved example is independently replayable.
                examples[branch] = {**case, 'road_hex': road.hex(), 'result': asdict(expected), 'events': events}
        return expected

    def road_of(tile, rows=100):
        return struct.pack('<' + str(rows * 7) + 'H', *([tile] * (rows * 7)))

    config = TickConfig(8, 130, 60, 100)
    # Every surface type and shipped support structure; controlled response/flags.
    for profile in range(6):
        for surface in range(16):
            road = road_of((profile << 8) | (surface << 4) | surface)
            for height in (10240, 12800, 15360):
                s = TickState(height=height, previous_target_height=height, speed=4000,
                              fuel=26000, oxygen=26000)
                check('surface_matrix', road, s, config, TickInput(1, 1, 0, 50))
    # Near a row transition: crash threshold, upward/downward motion and edges.
    for speed in (0, 1, 3639, 3640, 3641, 10922):
        for x in (29824, 31616, 32768, 33920, 35712):
            for vertical in (-800, -115, 0, 500):
                road = struct.pack('<700H', *([1] * 28 + [0x201] * 672))
                s = TickState(forward=(4 << 16) - 100, lateral=x, speed=speed,
                              vertical_speed=vertical, grounded=0, previous_target_height=10240)
                check('collision_thresholds', road, s, config, TickInput(timer=50))
    # A single low block at row4/column3 distinguishes the left shove branch.
    tiles = [1] * 84
    tiles[4 * 7 + 3] = 0x201
    narrow_road = struct.pack('<84H', *tiles)
    check('left_shove_boundary', narrow_road,
          TickState(forward=(4 << 16) - 100, lateral=28056, speed=4000),
          replace(config, road_rows=12), TickInput(timer=50))
    # Special persistent-local, wrap and exit ordering cases.
    for gravity in (0, 8, 19, 20, 30):
        for jump in (0, 1):
            s = TickState(speed=7000, previous_target_height=0xa5a5, edge_distance=0xa5a5,
                          jump_height=0xa5a5)
            check('jump_gate_and_initial_locals', road_of(1), s, replace(config, gravity_factor=gravity),
                  TickInput(1, -1, jump, 65535))
    for fuel, oxygen in ((0,0), (1,1), (0,30000), (30000,0), (65535,65535)):
        s = TickState(speed=10922, fuel=fuel, oxygen=oxygen, height=9000, grounded=0,
                      previous_target_height=9000, vertical_speed=-1)
        check('resource_exit_priority', road_of(0), s, config, TickInput(timer=50))
    for vy in (-32768, -1500, -260, -259, 259, 260, 1500):
        for timer in (0, 7, 8, 65535):
            s = TickState(vertical_speed=vy, previous_target_height=9999, grounded=0,
                          speed=2000, height=15360, jumping=1, assist_used=1)
            check('bounce_and_audio_clock', road_of(1), s, config, TickInput(timer=timer))
    for state in (TickState(height=0, previous_target_height=0, vertical_speed=-106, grounded=0),
                  TickState(lateral=65530, drift=100, previous_target_height=10240),
                  TickState(lateral=5, drift=-100, previous_target_height=10240),
                  TickState(height=12000, previous_target_height=12000, exit_state=1,
                            crash_ticks=65535, end_ticks=65535, tick_counter=65535)):
        check('wrap_boundaries', road_of(0), state, config, TickInput(timer=65535))
    finish_road = road_of(0x101, 10)
    for f in ((10 << 16) - 32769, (10 << 16) - 32768, (10 << 16) - 1):
        check('finish_boundary', finish_road, TickState(forward=f), replace(config, road_rows=10), TickInput())
    print(f'Synthetic tick boundaries passed: {sum(counts.values())}', flush=True)

    # Sustained trajectories exercise locals carried over from the previous tick.
    for surface in (1, 2, 8, 9, 10):
        road = road_of(surface, 500)
        cfg = replace(config, road_rows=500)
        s = TickState(fuel=20000, oxygen=20000)
        for n in range(180):
            controls = TickInput(1 if n < 120 else -1, 0, int(n in (20, 65, 110)), n + 50)
            result = check('synthetic_trajectory', road, s, cfg, controls)
            s = result.state
            if result.completion_requested:
                break
    print('Persistent-state synthetic trajectories passed', flush=True)

    for record in manifest['roads']:
        index = record['index']
        road = (OUT / 'roads' / record['decoded_file']).read_bytes()
        cfg = TickConfig(*record['metadata_words'], len(road) // 14)
        for _ in range(40):
            height = rng.choice((10240, 12800, 15360, rng.randrange(8000,17000)))
            s = TickState(forward=(rng.randrange(1,cfg.road_rows-2) << 16) | rng.randrange(65536),
                          lateral=rng.randrange(11500,54000), height=height,
                          speed=rng.randrange(10923), steering=rng.randrange(-60,61),
                          vertical_speed=rng.randrange(-1500,1501), drift=rng.randrange(-150,151),
                          previous_target_height=rng.choice((height, height-1)),
                          fuel=rng.randrange(30001), oxygen=rng.randrange(30001),
                          grounded=rng.randrange(2), jumping=rng.randrange(2), assist_used=rng.randrange(2),
                          surface8=rng.randrange(2), surface2=rng.randrange(2),
                          edge_distance=rng.randrange(15), jump_height=rng.randrange(10240,15361),
                          speed_delta=rng.choice((0,0,500,-500)), assist_flag=rng.randrange(2),
                          exit_state=rng.choice((0,0,0,1,2,3,4,5)), crash_ticks=rng.choice((0,0,0,1,42)))
            check('real_road_states', road, s, cfg, TickInput(rng.randrange(-1,2),rng.randrange(-1,2),rng.randrange(2),100),index)
        s = TickState()
        for n in range(100):
            result = check('real_road_trajectory', road, s, cfg,
                           TickInput(1, 0, int(n in (25,60)), n + 50), index)
            s = result.state
            if result.completion_requested or s.exit_state:
                break
        (OUT / 'tick-validation.progress.json').write_text(json.dumps({'status':'running','last_road':index,'counts':dict(counts)},indent=2)+'\n')
        print(f'Road {index:02d} tick checks passed; total {sum(counts.values())}', flush=True)

    # These semantic branches must have been exercised, not merely implemented.
    required = set(BRANCHES.values()) | {'finish_boundary'}
    missing = sorted(required - set(original.branches))
    report = {'verified': not missing, 'total_cases':sum(counts.values()),'counts':dict(counts),
              'branch_hits':dict(original.branches),'required_branches_missing':missing,
              'compared_events':dict(events_count),'outcomes':dict(outcomes),
              'result_stream_sha256':digest.hexdigest(),'seed':23241993,
              'instructions_including_stop_hooks':original.instructions,'max_instructions_per_tick':max_instructions,
              'elapsed_seconds':round(time.monotonic()-started,2),
              'input_sha256':{'exe':hashlib.sha256((OUT/'unpacked/SKYROADS_UNPACKED.EXE').read_bytes()).hexdigest(),
                              'roads':manifest['source_sha256']},
              'code_sha256':{name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                            for name in ('skyroads_tick.py','validate-skyroads-tick.py','skyroads_movement.py','skyroads_collision.py',
                                         'validate-skyroads-movement.py','validate-skyroads-collision.py')},
              'boundary':{'start':'1000:2324','normal_stop':'1000:2afd','completion_stop':'1000:0f05 before execution',
                          'audio':'Original muted digital configuration451a=1,cb6=1. Sound calls/timestamp/busy checks execute.',
                          'inputs':'Post-poll controls and fixed timer are explicitly supplied; keyboard/device polling excluded.',
                          'locals':'Nine persistent BP-relative words supplied and compared; other stack scratch filleda5.',
                          'state':'Every modeled global/local plus all collision, resolve, prediction and sound traces compared.'},
              'limitations':['No renderer, real timer interrupts, audio hardware or finish animation execution.',
                             'Not an exhaustive proof for all states; malformed resource indices and unbounded movement remain outside port domain.',
                             'Default TickState specifies a synthetic initial frame, not recovered historical stack garbage.']}
    (OUT/'tick-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'tick-examples.json').write_text(json.dumps(examples,indent=2)+'\n')
    (OUT/'tick-validation.progress.json').write_text(json.dumps({'status':'complete' if not missing else 'coverage_incomplete','total_cases':report['total_cases']},indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    assert not missing, f'Add distinguishing coverage for {missing}'


if __name__ == '__main__':
    main()
