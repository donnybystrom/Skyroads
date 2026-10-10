# Tile geometry and collision predicates

This milestone reconstructs isolated geometry queries from the unpacked
SkyRoads executable. Python predictions matched unchanged original x86 code
in **41,328 cases**, and the viewer's JavaScript model matched the Python port
in **15,808 additional cases**. All original EXE/resource bytes are preserved.
Full movement, perspective rendering and gameplay have not been reconstructed.

## Tile fields

Each cell is a little-endian uint16 word:

| Bits | Meaning and evidence |
| --- | --- |
| 0..3 | Ground surface; used by ground collision, rendering and surface effects |
| 4..7 | Upper surface of a structure; rendering routines use the shifted nibble, and `1c62` selects it for landing filtering |
| 8..11 | Structure/profile ID; six values 0..5 occur in the shipped roads |
| 12..15 | Zero in every one of the 30,436 decoded cells; no universal unused-bit claim |

Ground surface 0 means no ground. Upper surface 0 on a structured tile is
treated differently: the renderer substitutes a default color and the landing
filter does not reject it as a hole. Surface 12 is rejected by the landing
filter. The main loop shifts the tile by four bits before applying upper-surface
effects when the ship is at a structured support height. Exact names for all
surface types, colors and textures remain unverified.

## Structure profiles

The names below describe collision geometry. They do not claim reproduction
of original meshes, textures or perspective projection.

| ID | Name | Profile test at index `i` | Standard support height |
| --- | --- | --- | ---: |
| 0 | No structure | False | Ground: 10240, or 0 for ground nibble 0 |
| 1 | Arch / valv | `lower[i] <= q < upper[i]` | 0; no flat support returned |
| 2 | Low block | `height < 12800` | 12800 |
| 3 | Low tunnel block | `height < 12800 && lower[i] <= q` | 12800 |
| 4 | High block | `height < 15360` | 15360 |
| 5 | High tunnel block | `height < 15360 && lower[i] <= q` | 15360 |

`q = uint16(height - 8704) / 128`. Index `i >= 38` returns 0. The exact two
38-entry uint16 tables are read from `DS:004c` and `DS:0098` and saved in
`collision-geometry.json` and `collision-validation.json`. Heights in the
support table at `DS:00e4` are original integer units, not meters.

For unknown structure IDs 6..15, `TestStructureCollision` returns the masked
structure bits unchanged rather than a normalized boolean. This behavior is
preserved in both ports and checked on deterministic random raw tile words.
The viewer only encounters shipped structure IDs 0..5.

The folded lateral index is:

```
r = uint16(lateral / 128 - 49) % 46
i = uint16(23 - r)
if i == 0 or i > 32767: i = uint16(1 - i)
```

The subtraction wraps before the unsigned remainder. Replacing this with
floating-point absolute distance, ordinary signed modulo or an ellipse
approximation changes the original's decisions at boundaries.

## Position collision

`TestPositionCollision`, `1000:1732`, takes a 32-bit forward coordinate,
16-bit lateral coordinate and 16-bit height. Its tile lookup uses seven
columns and `row = forward / 65536`, as recorded in `LZS-FORMAT.md`.

1. Sample ground at `uint16(lateral +/- 1792)`.
2. If either ground nibble is nonzero, collide when `height < 10240` and
   `uint16(height + 1536) > 9344`.
3. Otherwise, the structure path requires `uint16(height + 1664) > 10240`
   and at least one nonzero structure ID at the side samples.
4. Test the center cell with its folded index. If it does not collide, test
   the adjacent column, 5888 units to the selected side, at index `47 - i`.

All additions, subtractions and comparisons retain the original 16-bit
unsigned behavior. The test is designed for the game's state domain. For
example, extremely low heights can bypass its vertical-band fast path;
the returned value should not be generalized to an arbitrary world's solid
volume. The viewer displays the exact query result for the chosen position.

## Tunnel context, support and landing filter

`IsBelowTunnelMidline`, `1000:0533`, only considers IDs 1, 3 and 5. It returns
whether `q < (lower[i] + upper[i]) / 2`. The rendering path uses this flag for
context and passes it to `GetRoadSupportHeight` (`1000:0c26`) to force a
ground-height query. It is **not a collision-free-space predicate**.

For instance, on road index 3, row 4, height 10240:

- Center x=32768: position collision 0, tunnel flag 1.
- Near the side x=35584: position collision 1, tunnel flag 1.
- At x=35584, height 11878: position collision 1, tunnel flag 0.

These states were also exercised through the browser controls. The viewer
shows standard support and forced-ground support separately, so tunnel context
does not silently turn a block's top into the ground below it.

`IsUnsafeLandingTile`, `1000:1c62`, is a filter used by the jump predictor at
`1ccd`. Arch ID 1 returns 0. Other structured tiles use the upper surface;
unstructured tiles use ground surface. It returns 1 for no ground at structure
0, or effective surface 12. Passing this filter is not a complete guarantee of
safe landing, since the jump trajectory and movement resolver are separate.

## Verification

`scripts/validate-skyroads-collision.py` loads the reconstructed MZ module,
applies its relocations and executes the original routines plus their original
integer multiplication/division helpers in Unicorn. It uses SS=DS, resets
registers and flags per case, rejects unexpected code/interrupts, and compares
raw AX values. The road allocation is zero-padded to 7000 bytes, matching the
loader's initialization. Out-of-allocation row accesses are not claimed.

| Coverage group | Cases |
| --- | ---: |
| Structure profile and height boundaries | 4260 |
| Random structure words/index/height, raw AX | 6000 |
| Standard support, forced-ground support, landing combinations | 4608 |
| Synthetic position and tunnel boundaries | 15300 |
| Lookup, position and tunnel queries on all 31 original roads | 11160 |
| **Original-code comparisons** | **41328** |

No mismatches or prohibited execution occurred. The deterministic result
stream hash, seed, tables and exact source identities are in
`collision-validation.json`. `geometry-js-validation.json` records another
15,808 comparisons of the browser's pure integer model against the checked
Python port. These are boundary/random tests, not exhaustive proof over every
possible game state.

UI verification exercised the cross-section on all 31 road selectors, all four
color modes (ground/top/structure/full word), tile selection, lateral and height
controls, and the three tunnel/wall/roof states above. No warning/error console
entries were observed. The graph samples height in 64-unit bands for display;
the interactive query uses the exact integer predicates, without graph rounding.

## Artifacts and reproduction

- `scripts/skyroads_collision.py`: standalone geometry predicates.
- `scripts/skyroads-geometry.js`: browser model, also importable by Node tests.
- `collision-geometry.json`: original tables, field populations and profile labels.
- `collision-validation.json`: original-x86 comparison report.
- `geometry-js-validation.json`: JavaScript/Python comparison report.
- `collision-function-annotations.json`: reusable Ghidra names/comments.
- `road-viewer.html`: self-contained interactive cross-section and road viewer.

```bash
# Unicorn needs an approved run outside the shell sandbox on this Mac.
runtime/re-venv/bin/python scripts/validate-skyroads-collision.py
runtime/re-venv/bin/python scripts/validate-skyroads-geometry-js.py
runtime/re-venv/bin/python scripts/build-skyroads-viewer.py
```

The persistent Ghidra project now documents 28 functions. The next milestone
is the movement resolver at `186b`, then the fixed-point ship state, jump
predictor and tick updates. Astra High is a reasonable next model setting for
combining those subsystems; the current Sol Extra High was sufficient for this
bounded geometry milestone. This is a task recommendation, not a benchmark.
