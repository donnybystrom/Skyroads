#!/usr/bin/env python3
"""Compare Python road decoding with isolated original x86 code, all 31 blocks.

Uses the original decoder and bitreader machine instructions unchanged,
including their self-modifying immediates. Preloads input in place of DOS I/O.
No DOS, BIOS, device, or other game code is allowed to run.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_INSN, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from skyroads_lzs import decode

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / 'analysis/skyroads'
EXE = ANALYSIS / 'unpacked/SKYROADS_UNPACKED.EXE'
SOURCE = ROOT / 'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/ROADS.LZS'
BASE, DS, DEST, BUFFER = 0x10000, 0x1676, 0x40000, 0x8000
# Near-runtime helpers use [BX+2] with BX=SP, relying on the game's SS=DS.
STACK = DS * 16
SENTINEL = BASE + 0x6800
ALLOWED = [(0x6326, 0x633d), (0x6490, 0x6499), (0x64ab, 0x64e1),
           (0x64ff, 0x6543), (0x6679, 0x6689), (0x66e6, 0x6767)]


def replay(module, encoded, length):
    uc = Uc(UC_ARCH_X86, UC_MODE_16)
    uc.mem_map(0, 2 * 1024 * 1024)
    uc.mem_write(BASE, module)
    # One explicit lookahead byte models the reader's advance after final data.
    uc.mem_write(DS * 16 + BUFFER, encoded + b'\xa5')
    uc.mem_write(DEST, b'\xcc' * (length + 16))
    for offset, value in [(0x41aa, 0), (0x41ae, 8), (0x41b0, encoded[0]),
                          (0x41b2, BUFFER), (0x41b4, BUFFER + len(encoded) + 1),
                          (0x41b6, BUFFER + 1)]:
        uc.mem_write(DS * 16 + offset, struct.pack('<H', value))
    uc.mem_write(STACK + 0xff00, struct.pack('<4H', 0x6800, 0, DEST // 16, length))
    for reg, val in [(UC_X86_REG_CS, BASE // 16), (UC_X86_REG_IP, 0x66e6),
                     (UC_X86_REG_DS, DS), (UC_X86_REG_ES, DS),
                     (UC_X86_REG_SS, STACK // 16), (UC_X86_REG_SP, 0xff00),
                     (UC_X86_REG_EFLAGS, 0x202)]:
        uc.reg_write(reg, val)
    state = {'returned': False, 'instructions': 0, 'prohibited': [], 'written': set(), 'bit_width_counts': {}, 'first_bit_reads': []}
    trace = deque(maxlen=12)

    def code_hook(emulator, address, size, _):
        state['instructions'] += 1
        trace.append(hex(address))
        if address == BASE + 0x64ff:
            sp = emulator.reg_read(UC_X86_REG_SP)
            width = struct.unpack('<H', emulator.mem_read(STACK + sp + 2, 2))[0]
            state['bit_width_counts'][width] = state['bit_width_counts'].get(width, 0) + 1
            if len(state['first_bit_reads']) < 16:
                state['first_bit_reads'].append({'width': width, 'di': emulator.reg_read(UC_X86_REG_DI)})
        if address == SENTINEL:
            state['returned'] = True
            emulator.emu_stop()
        elif not any(BASE + start <= address < BASE + end for start, end in ALLOWED):
            state['prohibited'].append({'unexpected_code': hex(address)})
            emulator.emu_stop()

    def interrupt_hook(emulator, number, _):
        state['prohibited'].append({'interrupt': number})
        emulator.emu_stop()

    def input_hook(emulator, port, size, _):
        state['prohibited'].append({'input_port': port})
        emulator.emu_stop()
        return 0

    def output_hook(emulator, port, size, value, _):
        state['prohibited'].append({'output_port': port})
        emulator.emu_stop()

    def write_hook(emulator, access, address, size, value, _):
        if DEST <= address < DEST + length:
            state['written'].update(range(address - DEST, address - DEST + size))

    uc.hook_add(UC_HOOK_CODE, code_hook)
    uc.hook_add(UC_HOOK_INTR, interrupt_hook)
    uc.hook_add(UC_HOOK_INSN, input_hook, None, 1, 0, UC_X86_INS_IN)
    uc.hook_add(UC_HOOK_INSN, output_hook, None, 1, 0, UC_X86_INS_OUT)
    uc.hook_add(UC_HOOK_MEM_WRITE, write_hook, None, DEST, DEST + length - 1)
    error = None
    try:
        uc.emu_start(BASE + 0x66e6, 0, timeout=10_000_000, count=2_000_000)
    except Exception as cause:
        error = str(cause)
    observed = bytes(uc.mem_read(DEST, length))
    # Current byte is prefetched; the position of that byte is next_ptr - 1.
    next_ptr = struct.unpack('<H', uc.mem_read(DS * 16 + 0x41b6, 2))[0]
    remaining_bits = struct.unpack('<H', uc.mem_read(DS * 16 + 0x41ae, 2))[0]
    result = {k: v for k, v in state.items() if k != 'written'}
    result.update({'emulation_error': error, 'written_bytes': len(state['written']),
                   'guard_unchanged': bytes(uc.mem_read(DEST + length, 16)) == b'\xcc' * 16,
                   'consumed_bytes': next_ptr - BUFFER - 1, 'remaining_bits': remaining_bits,
                   'patched_width_immediates': [uc.mem_read(BASE + p, 1)[0] for p in (0x6729, 0x671f, 0x674c)],
                   'patched_long_distance_base': struct.unpack('<H', uc.mem_read(BASE + 0x6751, 2))[0],
                   'last_addresses': list(trace)})
    return observed, result


def main():
    original = EXE.read_bytes()
    header_bytes = struct.unpack_from('<H', original, 8)[0] * 16
    module = original[header_bytes:]
    # The replay routines contain no relocated immediates, but load all MZ
    # relocations anyway so the complete code image is faithful to DOS loading.
    module = bytearray(module)
    reloc_count, reloc_offset = struct.unpack_from('<H', original, 6)[0], struct.unpack_from('<H', original, 24)[0]
    for i in range(reloc_count):
        off, seg = struct.unpack_from('<HH', original, reloc_offset + i * 4)
        location = seg * 16 + off
        val = struct.unpack_from('<H', module, location)[0]
        struct.pack_into('<H', module, location, (val + BASE // 16) & 0xffff)
    source = SOURCE.read_bytes()
    first = struct.unpack_from('<H', source)[0]
    directory = [struct.unpack_from('<HH', source, i) for i in range(0, first, 4)]
    results = []
    for index, (offset, length) in enumerate(directory):
        end = directory[index + 1][0] if index + 1 < len(directory) else len(source)
        encoded = source[offset + 222:end]
        expected = decode(encoded, length)
        observed, result = replay(bytes(module), encoded, length)
        differences = [i for i, (a, b) in enumerate(zip(expected.data, observed)) if a != b]
        result.update({'index': index, 'length': length, 'differing_bytes': len(differences),
                       'first_differences': differences[:12],
                       'python_sha256': hashlib.sha256(expected.data).hexdigest(),
                       'x86_sha256': hashlib.sha256(observed).hexdigest(),
                       'python_consumed_bytes': expected.consumed_bytes})
        result['verified'] = (result['returned'] and not result['prohibited'] and not result['emulation_error']
                              and not differences and result['written_bytes'] == length and result['guard_unchanged']
                              and result['consumed_bytes'] == expected.consumed_bytes and result['remaining_bits'] == 8)
        results.append(result)
        print(f"road {index:02d}: {'PASS' if result['verified'] else 'FAIL'} ({length} bytes)", flush=True)
    report = {'method': 'standalone Python decoder compared with unchanged x86 66e6/bitreader instructions',
              'exe_sha256': hashlib.sha256(original).hexdigest(),
              'roads_sha256': hashlib.sha256(source).hexdigest(), 'results': results,
              'verified': all(r['verified'] for r in results),
              'compared_bytes': sum(r['length'] for r in results),
              'limitations': ['Input is preloaded; DOS file refill and full loader are not exercised.',
                              'One explicit lookahead byte models prefetch after final encoded byte.',
                              'Equivalence covers these 31 valid road streams, not every possible LZS input.',
                              'Game rendering, physics and device execution are not exercised.']}
    (ANALYSIS / 'lzs-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['verified'], 'Inspect lzs-validation.json'
    print(f"Verified {len(results)} blocks, {report['compared_bytes']} bytes", flush=True)


if __name__ == '__main__':
    main()
