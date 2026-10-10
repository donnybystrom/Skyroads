#!/usr/bin/env python3
"""Decode the entire road directory, retaining source identity and exact bytes."""
import hashlib
import json
from pathlib import Path
import struct
from skyroads_lzs import decode

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/ROADS.LZS'
OUTPUT = ROOT / 'analysis/skyroads/roads'


def main():
    source = SOURCE.read_bytes()
    first = struct.unpack_from('<H', source)[0]
    assert first % 4 == 0 and 0 < first < len(source)
    directory = [struct.unpack_from('<HH', source, i) for i in range(0, first, 4)]
    roads = []
    OUTPUT.mkdir(exist_ok=True)
    for index, (offset, length) in enumerate(directory):
        end = directory[index + 1][0] if index + 1 < len(directory) else len(source)
        assert first <= offset < offset + 225 <= end <= len(source)
        assert length <= 7000 and length % 14 == 0
        encoded = source[offset + 222:end]
        decoded = decode(encoded, length)
        assert decoded.consumed_bytes == len(encoded), (index, decoded.summary(), len(encoded))
        filename = f'road-{index:02d}.bin'
        (OUTPUT / filename).write_bytes(decoded.data)
        rows = [list(struct.unpack_from('<7H', decoded.data, i)) for i in range(0, length, 14)]
        roads.append({
            'index': index, 'file_offset': offset, 'end_offset_exclusive': end,
            'metadata_words': list(struct.unpack_from('<3H', source, offset)),
            'metadata_216_bytes': list(source[offset + 6:offset + 222]),
            'decoded_file': filename, 'decoded_length': length,
            'decoded_sha256': hashlib.sha256(decoded.data).hexdigest(),
            'decode': decoded.summary(), 'rows_as_seven_uint16_le': rows,
        })
    manifest = {'source': str(SOURCE), 'source_sha256': hashlib.sha256(source).hexdigest(),
                'decoder_basis': '1000:66e6 and its bit-reading helpers',
                'layout_status': 'Seven uint16 words per 14-byte row; tile bit semantics need code tracing.',
                'road_count': len(roads), 'roads': roads}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'roads': len(roads), 'decoded_bytes': sum(x['decoded_length'] for x in roads),
                      'all_encoded_blocks_consumed_exactly': True,
                      'manifest': str(OUTPUT / 'manifest.json')}, indent=2))


if __name__ == '__main__':
    main()
