#!/usr/bin/env python3
"""Compare movement, every collision probe, jump flight and assist trials to x86."""
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import time
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_SP, UC_X86_REG_BP, UC_X86_REG_SI, UC_X86_REG_DI
from skyroads_movement import (Position, Flight, Environment, resolve_movement,
                               predict_landing, adjust_jump, s16, u16, u32)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'analysis/skyroads'
spec = importlib.util.spec_from_file_location('collision_fixture', ROOT / 'scripts/validate-skyroads-collision.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
BASE, DATA = fixture.BASE, fixture.STACK
ALLOWED = [(0x04c0, 0x0533), (0x1631, 0x1b49), (0x1c62, 0x1dfa),
           (0x1dfa, 0x1fd9), (0x5d4c, 0x5d80), (0x5d8c, 0x5ded), (0x5e5a, 0x5ef6)]


class Original(fixture.Original):
    def __init__(self):
        super().__init__(allowed=ALLOWED, instruction_limit=2000000)
        self.events = []
        self.writable = []
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.write)

    def word(self, offset):
        return struct.unpack('<H', self.uc.mem_read(DATA + offset, 2))[0]

    def dword(self, offset):
        return struct.unpack('<I', self.uc.mem_read(DATA + offset, 4))[0]

    def put(self, offset, value, size=2):
        self.uc.mem_write(DATA + offset, int(value & ((1 << (size * 8)) - 1)).to_bytes(size, 'little'))

    def write(self, uc, access, address, size, value, _):
        offset = address - DATA
        if not any(a <= offset and offset + size <= b for a, b in [(0xe000, 0xf020), *self.writable]):
            self.error = f'Unexpected write {address:x} size {size}'
            uc.emu_stop()

    def code(self, uc, address, size, user):
        super().code(uc, address, size, user)
        at = address - BASE
        if at in (0x1732, 0x1c62, 0x1ccd):
            sp = uc.reg_read(UC_X86_REG_SP)
            f, x = self.dword(sp + 2), self.word(sp + 6)
            if at == 0x1732:
                self.events.append(('collision', f, x, self.word(sp + 8)))
            elif at == 0x1c62:
                self.events.append(('landing', f, x))
            else:
                self.events.append(('predict', f, x, self.word(sp + 8), self.dword(sp + 10),
                                    s16(self.word(sp + 14)), s16(self.word(sp + 16))))
        elif at == 0x1cd9:
            bp = uc.reg_read(UC_X86_REG_BP)
            self.events.append(('flight', self.dword(bp + 4), uc.reg_read(UC_X86_REG_SI),
                                uc.reg_read(UC_X86_REG_DI), self.dword(bp + 12), s16(self.word(bp + 18))))

    def configure(self, flight, env):
        flight = flight.wrapped()
        self.put(0x9618, flight.position.forward, 4)
        self.put(0xaf1c, flight.position.lateral)
        self.put(0xaf2c, flight.position.height)
        self.put(0x54ac, flight.speed, 4)
        self.put(0x4568, flight.steering)
        self.put(0x9336, flight.vertical_speed)
        self.put(0xaf2e, flight.speed_delta, 4)
        self.put(0x455a, flight.assist_flag)
        self.put(0x54aa, env.gravity)
        self.put(0x5496, env.drift)
        self.put(0x9330, env.throttle)
        self.events = []

    def position(self):
        return Position(self.dword(0x9618), self.word(0xaf1c), self.word(0xaf2c))

    def flight(self):
        return Flight(self.position(), self.dword(0x54ac), s16(self.word(0x4568)),
                      s16(self.word(0x9336)), self.dword(0xaf2e), self.word(0x455a))


def position_args(p):
    return [p.forward & 65535, (p.forward >> 16) & 65535, p.lateral, p.height]


def main():
    start = time.monotonic()
    original = Original()
    counts, outcomes, event_counts = Counter(), Counter(), Counter()
    rng = random.Random(18611993)
    digest = hashlib.sha256()
    examples = {}
    max_instructions = 0
    manifest = json.loads((OUT / 'roads/manifest.json').read_text())

    def check(group, road, state, env, target=None, road_index=None):
        nonlocal max_instructions
        original.road(road)
        original.configure(state, env)
        events = []
        case = {'group': group, 'state': asdict(state), 'environment': asdict(env),
                'target': asdict(target) if target else None, 'road_index': road_index,
                'road_sha256': hashlib.sha256(road).hexdigest()}
        instructions_before = original.instructions
        try:
            if group.startswith('resolve'):
                original.writable = [(0x9618, 0x961c), (0xaf1c, 0xaf1e), (0xaf2c, 0xaf2e)]
                expected = resolve_movement(road, state.position, target, observer=events.append)
                original.call(0x186b, position_args(target))
                observed = original.position()
                outcome = 'resolved_target' if expected == target.wrapped() else 'resolved_partial'
                # All other shared fields must remain intact.
                assert original.flight() == Flight(expected, state.wrapped().speed, state.wrapped().steering,
                                                    state.wrapped().vertical_speed, state.wrapped().speed_delta,
                                                    state.wrapped().assist_flag)
            elif group.startswith('predict'):
                original.writable = []
                expected = predict_landing(road, state, env, observer=events.append)
                observed = original.call(0x1ccd, position_args(state.position) +
                                         [state.speed & 65535, (state.speed >> 16) & 65535,
                                          state.steering, state.vertical_speed])
                assert original.flight() == state.wrapped()
                outcome = f'prediction_{expected}'
            else:
                original.writable = [(0x4568, 0x456a), (0x54ac, 0x54b0), (0xaf2e, 0xaf32), (0x455a, 0x455c)]
                expected = adjust_jump(road, state, env, observer=events.append)
                original.call(0x1dfa, [])
                observed = original.flight()
                trials = sum(e[0] == 'predict' for e in events)
                outcome = ('assist_already_safe' if trials == 1 else
                           'assist_adjusted' if expected.assist_flag == 1 and
                           (expected.speed != state.speed or expected.steering != state.steering) else 'assist_no_solution')
            assert expected == observed, f'State mismatch: {expected} != {observed}'
            assert events == original.events, 'Intermediate trace mismatch'
        except Exception as exc:
            failure = {**case, 'error': repr(exc), 'python_events': events, 'original_events': original.events,
                       'original_state': asdict(original.flight()), 'completed_counts': dict(counts)}
            (OUT / 'movement-failure.json').write_text(json.dumps(failure, indent=2) + '\n')
            raise
        used = original.instructions - instructions_before
        max_instructions = max(max_instructions, used)
        counts[group] += 1
        outcomes[outcome] += 1
        event_counts.update(e[0] for e in events)
        result = asdict(expected) if not isinstance(expected, int) else expected
        digest.update(json.dumps([case, result, events], separators=(',', ':')).encode())
        key = outcome
        if road_index is not None and key not in examples:
            examples[key] = {**case, 'result': result, 'events': events}

    env = Environment(-115)
    # Profile transitions at row4 and lane edges, including fractional rounding.
    for kind in range(6):
        road = struct.pack('<84H', *([1] * 28 + [(kind << 8) | 1] * 56))
        for x in (29824, 32768, 35584):
            for y in (10239, 10240, 11775, 11776, 12799, 12800, 15359, 15360):
                for dx, dy in ((0, 0), (125, -106), (-125, 106), (2048, -512), (-2048, 512)):
                    p = Position(4 * 65536 - 4096, x, y)
                    check('resolve_profile_boundary', road, Flight(p, 4096, 0, 0), env,
                          Position(p.forward + 8192, x + dx, y + dy))
    empty = bytes(140)
    for x, y, dx, dy in [(32768,10240,0,0), (32768,10240,32768,0), (32768,10240,-32768,0),
                         (32768,10240,6553,0), (32768,10240,6554,0), (32768,10240,-6554,0),
                         (32768,10240,0,6554), (32768,10240,0,-6554), (0,65535,1,-1),
                         (65535,0,-1,1)]:
        p = Position(3 << 16, x, y)
        check('resolve_wrap_and_noop', empty, Flight(p, 0, 0, 0), env, Position(p.forward, x + dx, y + dy))
    print('Movement synthetic boundaries passed', flush=True)

    # Uniform tiles isolate safety semantics, world edge checks and signed steer.
    for tile in (0, 1, 12, 0x101, 0x200, 0x2c1, 0x5c1):
        road = struct.pack('<700H', *([tile] * 700))
        for x in (12159, 12160, 12161, 32768, 53375, 53376, 53377):
            for steering in (-64, 0, 64):
                state = Flight(Position(3 << 16, x, 10240), 8192, steering, 1100, 123, 7)
                check('predict_boundary', road, state, env)
                check('assist_boundary', road, state, env)
    for speed in (-1, 0, 74, 75, 10921, 10922, 10923):
        for throttle in (-1, 0, 1):
            road = struct.pack('<700H', *([1] * 700))
            state = Flight(Position(3 << 16, 32768, 10240), speed, -1, 1)
            check('predict_speed_clamp', road, state, Environment(-115, -1, throttle))
    print('Landing and jump-assist synthetic boundaries passed', flush=True)

    for record in manifest['roads']:
        index = record['index']
        road = (OUT / 'roads' / record['decoded_file']).read_bytes()
        rows = len(road) // 14
        gravity = -(record['metadata_words'][0] * 0x1680 // 400)
        for _ in range(40):
            row = rng.randrange(1, rows - 2)
            p = Position((row << 16) | rng.randrange(65536), rng.randrange(12000, 53500),
                         rng.choice((10240, 12800, 15360, rng.randrange(7800, 17000))))
            speed = rng.randrange(10923)
            state = Flight(p, speed, rng.randrange(-64, 65), rng.randrange(-500, 1501),
                           rng.randrange(65536), rng.choice((0, 1, 7)))
            env = Environment(gravity, rng.randrange(-125, 126), rng.randrange(-1, 2))
            target = Position(p.forward + speed, p.lateral + rng.randrange(-1700, 1701),
                              p.height + rng.randrange(-700, 701))
            check('resolve_real_roads', road, state, env, target, index)
            check('predict_real_roads', road, state, env, road_index=index)
            if _ < 12:
                check('assist_real_roads', road, state, env, road_index=index)
        progress = {'status': 'running', 'last_completed_road': index, 'counts': dict(counts),
                    'outcomes': dict(outcomes), 'elapsed_seconds': round(time.monotonic() - start, 2)}
        (OUT / 'movement-validation.progress.json').write_text(json.dumps(progress, indent=2) + '\n')
        print(f'Road {index:02d} passed; {sum(counts.values())} cases', flush=True)

    report = {'verified': True, 'counts': dict(counts), 'total_cases': sum(counts.values()),
              'outcomes': dict(outcomes), 'compared_intermediate_events': dict(event_counts),
              'result_stream_sha256': digest.hexdigest(), 'seed': 18611993,
              'instructions_including_return_hooks': original.instructions,
              'max_instructions_per_case': max_instructions,
              'elapsed_seconds': round(time.monotonic() - start, 2),
              'code_allowlist_module_offsets': [[hex(a), hex(b)] for a,b in ALLOWED],
              'write_guard': 'Stack e000:f020 plus function-specific output globals; all other writes rejected.',
              'input_sha256': {'unpacked_exe': hashlib.sha256((OUT / 'unpacked/SKYROADS_UNPACKED.EXE').read_bytes()).hexdigest(),
                               'roads_lzs': manifest['source_sha256']},
              'implementation_sha256': {name: hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest()
                                        for name in ('skyroads_movement.py', 'skyroads_collision.py',
                                                     'validate-skyroads-movement.py', 'validate-skyroads-collision.py')},
              'limitations': ['Isolated resolver, landing predictor and adjustment caller; no full game loop.',
                              'All31 real roads plus synthetic boundaries; sampled states are not proof of exhaustive equivalence.',
                              'Port restricts road accesses to the recovered7000-byte allocation and imposes execution budgets.',
                              'Landing prediction ignores intervening collisions, as does the original helper.']}
    (OUT / 'movement-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    (OUT / 'movement-examples.json').write_text(json.dumps(examples, indent=2) + '\n')
    (OUT / 'movement-validation.progress.json').write_text(json.dumps({'status': 'complete', 'total_cases': report['total_cases']}, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
