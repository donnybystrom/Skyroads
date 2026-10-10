# SkyRoads resource compression and road layout

This describes resource `.LZS` compression, separate from the executable's DIET
compression. Derived from `DecodeLzsBlock` at `1000:66e6`, its bitreader helpers,
and `LoadRoadByIndex` at `1000:5614`.

## Verified decoder

Three byte-aligned header bytes specify `length_bits`, `short_distance_bits`,
and `long_distance_bits`. All following fields are read MSB first.

| Prefix | Token | Remaining fields |
| --- | --- | --- |
| `0` | Short backreference | Distance field of `short_distance_bits`, then length field of `length_bits` |
| `10` | Long backreference | Distance field of `long_distance_bits`, then length field of `length_bits` |
| `11` | Literal | 8-bit byte |

Short distance is `field + 2`. Long distance is
`field + (1 << short_distance_bits) + 2`. Match length is `field + 2`.
Copies advance one byte at a time and can overlap, allowing repetition.
Decoded length comes from the surrounding resource container; it is not in
this three-byte header. The routine stops when that many bytes are produced,
then consumes padding bits to align input to the next byte.

All 31 road streams use `[5, 8, 10]` except index 6, which uses `[5, 8, 9]`.
Every encoded block is consumed exactly, without spare bytes. Across the
road corpus, the decoder processed 713 literals, 4,383 short matches and
669 long matches; all three token branches were exercised.

`scripts/skyroads_lzs.py` rejects truncated input, unsupported widths,
references preceding the output, and output overruns. This is stricter than
the original assembly and is not a claim that every malformed input has
identical behavior. The port is verified on the shipped road corpus.

## Independent comparison

`scripts/validate-skyroads-lzs.py` runs the original x86 instructions for the
decoder, input-byte advance, bitreaders and alignment routines in Unicorn.
It allows the code to patch its own width immediates. The input buffer is
preloaded, with one explicit lookahead byte for the reader's final prefetch;
DOS refill, devices, and the rest of the game are not emulated. Leaving the
allowed routines or issuing an interrupt/port operation fails validation.

The near-runtime helpers use `BX=SP` followed by DS-relative argument reads,
so **SS must equal DS**, as the game's startup establishes. An initial replay
with a separate stack segment failed; correcting the fixture to this actual
runtime convention removed the discrepancy without changing either decoder.

All 31 decoded outputs match byte-for-byte (**60,872 bytes**). Each replay
returns normally, writes every expected destination byte, preserves the
post-output guard, consumes the same encoded extent, and leaves input aligned.
See `lzs-validation.json` for hashes, per-block checks and patched immediates.
This validates the decoding routine, not DOS file loading or gameplay.

## Road container

`ROADS.LZS` is 17,095 bytes, SHA-256
`19551b52d5a9e87d62ebea5e98a559f3fe76a98947924f85d2787d00f8333d83`.
The first block offset is 124, implying 31 four-byte directory entries.
Each entry is little-endian `{uint16 file_offset, uint16 decoded_length}`.
All offsets increase and stay in bounds. The next offset, or EOF for the last
entry, bounds the stored block.

At each block offset:

| Relative byte offset | Size | Contents |
| --- | ---: | --- |
| 0 | 6 | Three uint16 metadata values, copied to DS:4562, DS:54a2, DS:4566 |
| 6 | 216 | Metadata copied to DS:41c2 |
| 222 | 3 | LZS bit-width header |
| 225 | Variable | Bitstream including final byte padding |

All 216-byte fields contain values 0..63, consistent with 72 six-bit RGB
triples. The viewer exposes this as a **provisional** palette interpretation;
the actual video palette upload and color-to-tile mapping have not been traced.

## Tile lookup and effects

`GetRoadTileAtPosition` (`1000:04c0`) supplies a code-based interpretation of
decoded rows, rather than inferring dimensions only from divisible lengths:

```
u = unsigned_lateral / 128 - 95
if unsigned(u) >= 322: return 0
column = u / 46                         # 0..6
row = (unsigned_forward32 / 8192) / 8   # forward32 / 65536
return uint16_le_at(DS:162c + row*14 + column*2)
```

Each row therefore has **seven little-endian 16-bit cells**. Coordinate
arithmetic follows the binary's unsigned integer divisions. This lookup has
no row-bound check; the standalone viewer bounds accesses by decoded length.

`ApplyRoadSurfaceEffect` (`1000:1b49`) examines bits 0..3. Observed effects:

- Type 2 subtracts 303 from the 32-bit speed-like accumulator at DS:54ac/54ae.
- Type 10 adds 303 to it. The function clamps the accumulator to 0..10922.
- Type 9 restores two resource counters at DS:5494 and DS:b13c to 30000.
- Type 12 sets an exit/crash state and starts its animation.

`GetRoadSupportHeight` (`1000:0c26`) and collision routines use bits 8..11 as
a structure/profile field. Ground baseline is 0 for low nibble 0, otherwise
`0x2800`; nonzero structure selects additional branches and a height table.
Those were the initial findings. Structure profiles and the upper-surface
field in bits4..7 are now verified; see [COLLISION-FORMAT.md](COLLISION-FORMAT.md).
Bits12..15 are zero throughout the shipped road corpus. Resource-counter names, speed units, input mapping and the
complete physics model remain to be verified.

## Viewer and reproduction

`road-viewer.html` is self-contained and works offline. It offers all 31
records, three coloring modes, row zoom, raw-value inspection, keyboard
navigation, metadata and CSV/BIN export. Colors are analytical; the viewer
does not reproduce original graphics or gameplay. It deliberately uses index
labels until original level names/order and index 0's role are proven.

```bash
runtime/re-venv/bin/python scripts/test_skyroads_lzs.py
runtime/re-venv/bin/python scripts/decode-skyroads-roads.py
# This Mac requires approved execution outside the shell sandbox for Unicorn.
runtime/re-venv/bin/python scripts/validate-skyroads-lzs.py
runtime/re-venv/bin/python scripts/build-skyroads-viewer.py
runtime/re-venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory analysis/skyroads
```

UI verification exercised all 31 selectors, the three coloring modes, index
30-to-0 wraparound, keyboard tile selection and zoom endpoints (8/28 px).
The browser's exported index-0 BIN matched the verified 2,240-byte file exactly.
No warning/error console entries were observed. Desktop and narrow layouts
were visually inspected; CSV export has not separately been downloaded/tested.

Tile profiles and isolated collision helpers are now verified in
`COLLISION-FORMAT.md`. Next: model the ship's fixed-point position, speed,
jumping and resource drain against controlled original-code replay. Full perspective rendering comes after those contracts.
