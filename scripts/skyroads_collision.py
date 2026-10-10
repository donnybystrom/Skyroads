"""Road geometry predicates ported from SkyRoads' unsigned 16-bit x86 code.

Raw return values are preserved, including 1631's non-boolean fallback for
unknown structure IDs. Public lookup bounds the recovered road allocation;
the original routine itself does not bounds-check rows.
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / 'analysis/skyroads/unpacked/SKYROADS_UNPACKED.EXE'


def read_tables():
    exe = EXE.read_bytes()
    header_size = struct.unpack_from('<H', exe, 8)[0] * 16
    data = exe[header_size + 0x6760:]
    return {'lower': list(struct.unpack_from('<38H', data, 0x4c)),
            'upper': list(struct.unpack_from('<38H', data, 0x98)),
            'support': list(struct.unpack_from('<16H', data, 0xe4))}


TABLES = read_tables()


def u16(value):
    return value & 0xffff


def folded_profile_index(lateral):
    # The subtraction wraps BEFORE unsigned remainder by 46.
    value = u16(23 - (u16(u16(lateral) // 128 - 49) % 46))
    return u16(1 - value) if value > 0x7fff or value == 0 else value


def structure_hit(tile, index, height):
    """Original 1631h AX, not merely bool(AX)."""
    index, height = u16(index), u16(height)
    if index >= 38:
        return 0
    adjusted_height = u16(height + 0xde00) // 128
    kind = tile & 0xf00
    if kind == 0x100:
        return int(TABLES['lower'][index] <= adjusted_height < TABLES['upper'][index])
    if kind == 0x200:
        return int(height < 0x3200)
    if kind == 0x300:
        return int(height < 0x3200 and TABLES['lower'][index] <= adjusted_height)
    if kind == 0x400:
        return int(height < 0x3c00)
    if kind == 0x500:
        return int(height < 0x3c00 and TABLES['lower'][index] <= adjusted_height)
    return kind


def support_height(tile, force_ground=0):
    kind = (tile >> 8) & 15
    if not kind or u16(force_ground):
        return 0x2800 if tile & 15 else 0
    return 0 if kind == 1 else TABLES['support'][kind]


def lookup(road, forward, lateral):
    u = u16(u16(lateral) // 128 - 95)
    if u >= 322:
        return 0
    # row*14 and DS-near address arithmetic are both 16-bit in the executable.
    address = u16(0x162c + ((forward & 0xffffffff) // 65536) * 14 + (u // 46) * 2)
    offset = address - 0x162c
    if not 0 <= offset < 7000:
        raise ValueError('Lookup left the 7000-byte recovered road allocation')
    if offset + 2 > len(road):
        return 0  # The loader zero-fills the remainder of its 7000-byte buffer.
    return struct.unpack_from('<H', road, offset)[0]


def inside_tunnel(road, forward, lateral, height):
    tile = lookup(road, forward, lateral)
    if (tile & 0xf00) not in (0x100, 0x300, 0x500):
        return 0
    index = folded_profile_index(lateral)
    if index >= 38:
        return 0
    midpoint = u16(TABLES['lower'][index] + TABLES['upper'][index]) // 2
    return int(u16(u16(height) + 0xde00) // 128 < midpoint)


def position_hit(road, forward, lateral, height):
    lateral, height = u16(lateral), u16(height)
    right = lookup(road, forward, u16(lateral + 0x700))
    left = lookup(road, forward, u16(lateral - 0x700))
    if ((right & 15) or (left & 15)) and height < 0x2800 and u16(height + 0x600) > 0x2480:
        return 1
    if u16(height + 0x680) <= 0x2800 or not ((left | right) & 0xf00):
        return 0
    tile = lookup(road, forward, lateral)
    index = folded_profile_index(lateral)
    # Signed/zero fold also selects which adjacent column gets tested.
    raw = u16(23 - (u16(lateral // 128 - 49) % 46))
    neighbor_step = 0x1700 if raw > 0x7fff or raw == 0 else -0x1700
    if structure_hit(tile, index, height):
        return 1
    neighbor = lookup(road, forward, u16(lateral + neighbor_step))
    return int(bool(structure_hit(neighbor, u16(47 - index), height)))


def unsafe_landing(tile):
    kind = tile & 0xf00
    if kind == 0x100:
        return 0
    surface = ((tile >> 4) if kind else tile) & 15
    return int((surface == 0 and not kind) or surface == 12)
