#!/usr/bin/env python3
"""Differential geometry tests against unchanged original x86 routines."""
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import random
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE, UC_HOOK_INTR
from unicorn.x86_const import *
from skyroads_collision import TABLES, structure_hit, support_height, lookup, inside_tunnel, position_hit, unsafe_landing

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / 'analysis/skyroads'
BASE, DS = 0x10000, 0x1676
STACK = DS * 16
ALLOWED = [(0x04c0, 0x05f6), (0x0c26, 0x0c98), (0x1631, 0x186b),
           (0x1c62, 0x1ccd), (0x5d4c, 0x5d80), (0x5d8c, 0x5ded)]


class Original:
    def __init__(self, allowed=None, instruction_limit=10000):
        self.allowed = ALLOWED if allowed is None else allowed
        self.instruction_limit = instruction_limit
        exe = (ANALYSIS / 'unpacked/SKYROADS_UNPACKED.EXE').read_bytes()
        header = struct.unpack_from('<14H', exe)
        module = bytearray(exe[header[4] * 16:])
        for i in range(header[3]):
            off, seg = struct.unpack_from('<HH', exe, header[12] + 4 * i)
            at = seg * 16 + off
            struct.pack_into('<H', module, at, (struct.unpack_from('<H', module, at)[0] + 0x1000) & 0xffff)
        self.uc = Uc(UC_ARCH_X86, UC_MODE_16)
        self.uc.mem_map(0, 2 * 1024 * 1024)
        self.uc.mem_write(BASE, bytes(module))
        self.returned = False
        self.error = None
        self.trace = deque(maxlen=8)
        self.instructions = 0
        self.uc.hook_add(UC_HOOK_CODE, self.code)
        self.uc.hook_add(UC_HOOK_INTR, self.interrupt)

    def code(self, uc, address, size, _):
        self.instructions += 1
        if address == BASE + 0x6800:
            self.returned = True
            uc.emu_stop()
        elif not any(BASE + start <= address < BASE + end for start, end in self.allowed):
            self.error = f'Unexpected code {address:x}'
            uc.emu_stop()

    def interrupt(self, uc, number, _):
        self.error = f'Unexpected interrupt {number}'
        uc.emu_stop()

    def road(self, data):
        assert len(data) <= 7000
        self.uc.mem_write(STACK + 0x162c, data + bytes(7000 - len(data)))

    def call(self, entry, args):
        self.returned = False
        self.error = None
        # Near C helpers rely on SS=DS. Reinitialize registers/flags per case.
        for reg, value in [(UC_X86_REG_CS, 0x1000), (UC_X86_REG_DS, DS),
                           (UC_X86_REG_SS, DS), (UC_X86_REG_ES, DS),
                           (UC_X86_REG_SP, 0xf000), (UC_X86_REG_BP, 0),
                           (UC_X86_REG_AX, 0xaaaa), (UC_X86_REG_BX, 0xbbbb),
                           (UC_X86_REG_CX, 0xcccc), (UC_X86_REG_DX, 0xdddd),
                           (UC_X86_REG_SI, 0xeeee), (UC_X86_REG_DI, 0xffff),
                           (UC_X86_REG_EFLAGS, 0x202)]:
            self.uc.reg_write(reg, value)
        self.uc.mem_write(STACK + 0xf000, struct.pack('<' + 'H' * (len(args) + 1), 0x6800, *[v & 0xffff for v in args]))
        self.uc.emu_start(BASE + entry, 0, count=self.instruction_limit)
        assert self.returned and not self.error, (entry, args, self.error)
        return self.uc.reg_read(UC_X86_REG_AX)


def main():
    original = Original()
    counts = defaultdict(int)
    failures = []
    digest = hashlib.sha256()
    rng = random.Random(1993)

    def check(group, entry, args, expected):
        observed = original.call(entry, args)
        counts[group] += 1
        digest.update(json.dumps([group, args, expected, observed], separators=(',', ':')).encode())
        if observed != expected and len(failures) < 20:
            failures.append({'group': group, 'entry': hex(entry), 'args': args, 'expected': expected, 'observed': observed})

    # Every profile-table column and every shipped structure; threshold +/-1
    # includes curve bounds, 16-bit wrap and solid block top boundaries.
    for kind in range(6):
        for index in range(48):
            heights = {0, 1, 0xffff, 0x21ff, 0x2200, 0x27ff, 0x2800, 0x31ff, 0x3200, 0x3bff, 0x3c00}
            if index < 38:
                for h in (0x2200 + 128 * TABLES['lower'][index], 0x2200 + 128 * TABLES['upper'][index]):
                    heights.update((h - 1, h, h + 1))
            for height in sorted(heights):
                tile = (kind << 8) | 0xc9
                check('structure_boundary', 0x1631, [tile, index, height], structure_hit(tile, index, height))
    for _ in range(6000):
        tile, index, height = rng.randrange(65536), rng.randrange(64), rng.randrange(65536)
        check('structure_random_raw_ax', 0x1631, [tile, index, height], structure_hit(tile, index, height))
    print('Structure profiles checked', flush=True)

    # Synthetic 7-column row isolates each possible pair of surface nibbles
    # and all shipped structure kinds. Lookup uses the true original routine.
    for kind in range(6):
        for ground in range(16):
            for top in range(16):
                tile = (kind << 8) | (top << 4) | ground
                road = struct.pack('<7H', *([tile] * 7))
                original.road(road)
                check('support', 0x0c26, [0, 0, 0x8000, 0], support_height(tile))
                check('support_forced_ground', 0x0c26, [0, 0, 0x8000, 1], support_height(tile, 1))
                check('landing', 0x1c62, [0, 0, 0x8000], unsafe_landing(tile))
    print('Support and landing combinations checked', flush=True)

    # Uniform profile neighborhoods, then abrupt/asymmetric actual road cells.
    heights = [0, 7808, 7809, 8576, 8577, 9344, 10239, 10240, 10751, 10752, 11775, 11776, 12799, 12800, 15359, 15360, 65535]
    for kind in range(6):
        road = struct.pack('<7H', *([(kind << 8) | 1] * 7))
        original.road(road)
        for lateral in range(29824 - 1792, 35712 + 1793, 128):
            for height in heights:
                check('position_synthetic', 0x1732, [0, 0, lateral, height], position_hit(road, 0, lateral, height))
                check('tunnel_synthetic', 0x0533, [0, 0, lateral, height], inside_tunnel(road, 0, lateral, height))
    print('Synthetic collision boundaries checked', flush=True)

    manifest = json.loads((ANALYSIS / 'roads/manifest.json').read_text())
    for r in manifest['roads']:
        road = (ANALYSIS / 'roads' / r['decoded_file']).read_bytes()
        original.road(road)
        for _ in range(120):
            row = rng.randrange(len(road) // 14)
            forward = (row << 16) | rng.randrange(65536)
            lateral = rng.choice([12159,12160, 53375,53376, rng.randrange(65536)])
            height = rng.choice(heights + [rng.randrange(65536)])
            args = [forward & 65535, forward >> 16, lateral]
            check('lookup_real_roads', 0x04c0, args, lookup(road, forward, lateral))
            check('position_real_roads', 0x1732, args + [height], position_hit(road, forward, lateral, height))
            check('tunnel_real_roads', 0x0533, args + [height], inside_tunnel(road, forward, lateral, height))
        print(f"Road {r['index']:02d} checked", flush=True)

    report = {'verified': not failures, 'counts': dict(counts), 'total_cases': sum(counts.values()),
              'failures': failures, 'result_stream_sha256': digest.hexdigest(),
              'seed': 1993, 'instructions_including_return_hooks': original.instructions,
              'exe_sha256': hashlib.sha256((ANALYSIS / 'unpacked/SKYROADS_UNPACKED.EXE').read_bytes()).hexdigest(),
              'roads_sha256': manifest['source_sha256'], 'tables': TABLES,
              'limitations': ['Isolated predicates; full movement resolver186b, physics and rendering are not executed.',
                              'Original road allocation is zero-padded to7000 bytes; no claims for out-of-allocation row access.',
                              'Boundary and deterministic random coverage, not exhaustive coverage of every complete game state.']}
    (ANALYSIS / 'collision-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('tables','limitations')}, indent=2), flush=True)
    assert report['verified'], 'Inspect collision-validation.json'


if __name__ == '__main__':
    main()
