#!/usr/bin/env python3
"""Inventory ROADS.LZS using the layout observed in LoadRoadByIndex (5614h).

This parses the directory and pre-decode bytes; it does not decode level tiles.
"""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/ROADS.LZS'
OUTPUT = ROOT / 'analysis/skyroads/roads-directory.json'


def main():
    data = SOURCE.read_bytes()
    first_block = struct.unpack_from('<H', data)[0]
    assert first_block % 4 == 0 and 0 < first_block < len(data)
    count = first_block // 4
    directory = [struct.unpack_from('<HH', data, i * 4) for i in range(count)]
    entries = []
    for index, (offset, decoded_length) in enumerate(directory):
        end = directory[index + 1][0] if index + 1 < count else len(data)
        assert first_block <= offset < end <= len(data)
        assert offset + 6 + 216 + 3 <= end
        assert 0 < decoded_length <= 7000 and decoded_length % 14 == 0
        entries.append({
            'index': index, 'file_offset': offset, 'next_offset_or_eof': end,
            'stored_block_bytes': end - offset,
            'decoded_tile_bytes': decoded_length,
            'returned_units_decoded_length_div_14': decoded_length // 14,
            'metadata_words_to_ds_4562_54a2_4566': list(struct.unpack_from('<3H', data, offset)),
            'metadata_216_bytes_to_ds_41c2': data[offset + 6:offset + 222].hex(),
            'decoder_file_offset': offset + 222,
            'decoder_control_bytes': list(data[offset + 222:offset + 225]),
            'encoded_stream_bytes_including_controls': end - offset - 222,
        })
    report = {
        'source': str(SOURCE), 'source_sha256': hashlib.sha256(data).hexdigest(),
        'source_size': len(data), 'basis': 'static instructions at 1000:5614; directory extent inferred from first block offset',
        'entry_count': count, 'directory_bytes': first_block, 'entries': entries,
        'limitations': ['No level decompression or game execution.',
                        'Metadata meanings, tile encoding, and index-to-name mapping remain unknown.',
                        'The first block offset bounds the inferred directory; this is not an explicit count field.'],
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'entries': count, 'directory_bytes': first_block,
                      'file_size': len(data), 'output': str(OUTPUT)}, indent=2))


if __name__ == '__main__':
    main()
