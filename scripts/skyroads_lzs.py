"""SkyRoads resource LZS decoder, derived from x86 routine 1000:66e6.

This is the resource format, separate from DIET executable compression.
No external LZ algorithm identity is assumed. Input and output are bounded.
"""
from dataclasses import dataclass, asdict


class LzsError(ValueError):
    pass


@dataclass
class DecodeResult:
    data: bytes
    consumed_bytes: int
    meaningful_bits: int
    length_bits: int
    short_distance_bits: int
    long_distance_bits: int
    literals: int
    short_matches: int
    long_matches: int

    def summary(self):
        result = asdict(self)
        result.pop('data')
        return result


class BitReader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    def read(self, width):
        if not 0 <= width <= 16:
            raise LzsError(f'Unsupported bit width: {width}')
        if self.position + width > len(self.data) * 8:
            raise LzsError(f'Truncated input at bit {self.position}, need {width}')
        value = 0
        for _ in range(width):
            value = (value << 1) | ((self.data[self.position // 8] >> (7 - self.position % 8)) & 1)
            self.position += 1
        return value


def decode(data: bytes, output_length: int) -> DecodeResult:
    if len(data) < 3:
        raise LzsError('Missing three-byte width header')
    if not 0 <= output_length <= 65535:
        raise LzsError('Output length exceeds 16-bit routine bounds')
    length_bits, short_bits, long_bits = data[:3]
    if any(width > 16 for width in (length_bits, short_bits, long_bits)):
        raise LzsError('Width header exceeds supported 16-bit arithmetic')
    reader = BitReader(data[3:])
    output = bytearray()
    literals = short_matches = long_matches = 0
    while len(output) < output_length:
        if reader.read(1) == 0:
            distance = reader.read(short_bits) + 2
            short_matches += 1
        elif reader.read(1) == 0:
            distance = reader.read(long_bits) + (1 << short_bits) + 2
            long_matches += 1
        else:
            output.append(reader.read(8))
            literals += 1
            continue
        length = reader.read(length_bits) + 2
        if distance > len(output):
            raise LzsError(f'Backreference before output start: distance {distance}, output {len(output)}')
        if len(output) + length > output_length:
            raise LzsError('Backreference exceeds declared output length')
        for _ in range(length):
            output.append(output[-distance])
    return DecodeResult(bytes(output), 3 + (reader.position + 7) // 8,
                        reader.position, length_bits, short_bits, long_bits,
                        literals, short_matches, long_matches)
