#!/usr/bin/env python3
"""Run only DIET's unpacker in Unicorn and compare the recovered DOS load image.

No BIOS, DOS, filesystem, port, or game code is implemented. Stop before the
first instruction of the reconstructed EXE's entry point.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_INSN
from unicorn.x86_const import (
    UC_X86_REG_CS, UC_X86_REG_IP, UC_X86_REG_DS, UC_X86_REG_ES,
    UC_X86_REG_SS, UC_X86_REG_SP, UC_X86_REG_EFLAGS, UC_X86_INS_IN, UC_X86_INS_OUT,
)

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/SKYROADS.EXE"
UNPACKED = ROOT / "analysis/skyroads/unpacked/SKYROADS_UNPACKED.EXE"
OUTPUT = ROOT / "analysis/skyroads"
LOAD_SEGMENT = 0x1000
BASE = LOAD_SEGMENT * 16


def load_image(data):
    h = struct.unpack_from("<14H", data)
    assert h[0] == 0x5A4D
    file_size = (h[2] - 1) * 512 + (h[1] or 512)
    assert file_size == len(data), (file_size, len(data))
    header_size = h[4] * 16
    assert header_size <= len(data) and h[12] + h[3] * 4 <= header_size
    module = bytearray(data[header_size:file_size])
    relocations = []
    for index in range(h[3]):
        offset, segment = struct.unpack_from("<HH", data, h[12] + index * 4)
        location = segment * 16 + offset
        assert location + 2 <= len(module)
        value = struct.unpack_from("<H", module, location)[0]
        struct.pack_into("<H", module, location, (value + LOAD_SEGMENT) & 0xffff)
        relocations.append({"offset": offset, "segment": segment, "module_offset": location})
    return h, module, relocations


def main():
    original = ORIGINAL.read_bytes()
    unpacked = UNPACKED.read_bytes()
    packed_header, packed_image, _ = load_image(original)
    recovered_header, expected, relocations = load_image(unpacked)
    entry = BASE + recovered_header[11] * 16 + recovered_header[10]
    emulator = Uc(UC_ARCH_X86, UC_MODE_16)
    emulator.mem_map(0, 2 * 1024 * 1024)
    emulator.mem_write(BASE, bytes(packed_image))
    psp = LOAD_SEGMENT - 0x10
    emulator.mem_write(psp * 16, b"\xcd\x20")
    for register, value in [
        (UC_X86_REG_CS, LOAD_SEGMENT + packed_header[11]),
        (UC_X86_REG_IP, packed_header[10]),
        (UC_X86_REG_DS, psp), (UC_X86_REG_ES, psp),
        (UC_X86_REG_SS, LOAD_SEGMENT + packed_header[7]),
        (UC_X86_REG_SP, packed_header[8]), (UC_X86_REG_EFLAGS, 0x202),
    ]:
        emulator.reg_write(register, value)
    trace = deque(maxlen=32)
    instructions = 0
    reached = False
    prohibited = []

    def on_code(uc, address, size, _):
        nonlocal instructions, reached
        instructions += 1
        trace.append({"address": hex(address), "cs": hex(uc.reg_read(UC_X86_REG_CS)),
                      "ip": hex(uc.reg_read(UC_X86_REG_IP)), "bytes": bytes(uc.mem_read(address, size)).hex()})
        if address == entry:
            reached = True
            uc.emu_stop()

    def on_interrupt(uc, number, _):
        prohibited.append({"interrupt": number})
        uc.emu_stop()

    def on_input(uc, port, size, _):
        prohibited.append({"input_port": port, "size": size})
        uc.emu_stop()
        return 0

    def on_output(uc, port, size, value, _):
        prohibited.append({"output_port": port, "size": size})
        uc.emu_stop()

    emulator.hook_add(UC_HOOK_CODE, on_code)
    emulator.hook_add(UC_HOOK_INTR, on_interrupt)
    emulator.hook_add(UC_HOOK_INSN, on_input, None, 1, 0, UC_X86_INS_IN)
    emulator.hook_add(UC_HOOK_INSN, on_output, None, 1, 0, UC_X86_INS_OUT)
    error = None
    try:
        emulator.emu_start(BASE + packed_header[11] * 16 + packed_header[10], 0, timeout=30_000_000, count=5_000_000)
    except Exception as cause:
        error = str(cause)
    observed = bytes(emulator.mem_read(BASE, len(expected)))
    differences = [i for i, (a, b) in enumerate(zip(expected, observed)) if a != b]
    registers = {name: emulator.reg_read(reg) for name, reg in [
        ("CS", UC_X86_REG_CS), ("IP", UC_X86_REG_IP), ("DS", UC_X86_REG_DS),
        ("ES", UC_X86_REG_ES), ("SS", UC_X86_REG_SS), ("SP", UC_X86_REG_SP),
    ]}
    report = {
        "method": "original DIET x86-16 unpacker emulated in Unicorn; stop before recovered entry",
        "load_segment": hex(LOAD_SEGMENT), "expected_entry": hex(entry),
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "unpacked_sha256": hashlib.sha256(unpacked).hexdigest(),
        "initialized_module_bytes_compared": len(expected), "reconstructed_relocations": relocations,
        "reached_entry": reached, "instructions_including_entry_hook": instructions,
        "prohibited_runtime_operations": prohibited, "emulation_error": error,
        "registers_at_handoff": registers,
        "expected_load_image_sha256": hashlib.sha256(expected).hexdigest(),
        "observed_load_image_sha256": hashlib.sha256(observed).hexdigest(),
        "differing_bytes": len(differences), "first_differences": differences[:32],
        "last_instructions": list(trace),
        "limitations": ["DOS/BIOS/device behavior and game execution are not verified.",
                        "Compares the entire initialized MZ module; not the uninitialized allocation or historical file byte identity."],
    }
    report["verified"] = reached and not prohibited and not error and not differences
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "unpack-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUTPUT / "runtime-load-image.bin").write_bytes(observed)
    print(json.dumps({k: v for k, v in report.items() if k not in ["last_instructions", "limitations"]}, indent=2))
    assert report["verified"], "Unpack validation did not pass; inspect the report"


if __name__ == "__main__":
    main()
