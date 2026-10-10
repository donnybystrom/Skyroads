# Movement resolution and jump prediction

Verified on 2026-10-09. Three integer routines have independent Python ports in
`../../scripts/skyroads_movement.py`, with unchanged original x86 as the oracle.
**3,897 cases passed**, spanning all31 road records and synthetic boundaries.
Every recorded intermediate collision query, projected-flight state, landing
query and assist candidate matched, as well as the final outputs.

This completes the movement-resolver and jump-helper milestone. The full
`RunGameplayLoop` tick, its input handling and timing are still to be recovered.

## Evidence and reproduction

| Routine | Original entry | Direct cases |
| --- | --- | ---: |
| ResolveShipMovement | 1000:186b | 1,970 |
| PredictSafeLanding | 1000:1ccd | 1,408 |
| AdjustJumpForSafeLanding | 1000:1dfa | 519 |

Across those cases we compared 26,645 collision probes, 8,794 predictor entries,
96,408 projected-flight states, and 6,913 landing-tile queries. There were689
partial movements, 59 successful assist adjustments, 176 already-safe assist
inputs, and284 exhausted assist searches. These categories describe the test
corpus, not frequencies measured during gameplay.

- `movement-validation.json`: exact counts, source/code hashes, limits and result digest.
- `movement-examples.json`: seven saved real-road examples and their full matched traces.
- `movement-instructions.txt`: Capstone listing from the unpacked module bytes.
- `movement-analysis-initial.json`: original Ghidra export before renaming.
- `movement-annotated-functions.json`: three named helpers plus their gameplay caller.
- `movement-function-annotations.json`: reusable names and evidence comments.

From the project root:

```bash
# Full differential verification; needs the installed Unicorn environment.
runtime/re-venv/bin/python scripts/validate-skyroads-movement.py

# A single portable replay of saved evidence; no x86 emulator is run.
runtime/re-venv/bin/python scripts/replay-skyroads-movement.py --example assist_adjusted
runtime/re-venv/bin/python scripts/replay-skyroads-movement.py --example resolved_partial --trace
```

The Unicorn fixture loads the MZ module, applies its three relocations, and sets
CS=1000h and SS=DS=ES=1676h. Only allowlisted original routines run. Memory writes
are restricted to the test stack and each routine's documented output globals;
unexpected writes, code and interrupts fail the run. There is a two-million
instruction limit per call. The largest tested call used153,184 instructions.
On this Mac Unicorn requires the previously approved execution outside the
shell sandbox. No DOS process, display, audio or hardware interrupt runs.

The geometry suite was rerun after making its fixture configurable:
41,328 cases still pass with the same result digest as before.

## State and units

All values below are raw machine units. Do not convert to floating point inside
the port. Forward position is unsigned32; road lookup uses its upper16 bits as
the row. Lateral and height positions wrap16. Signed steering/vertical velocity
also occupy16 bits. Long products wrap32; signed divisions truncate toward zero.

| DS offset | Value used by these routines |
| --- | --- |
| 9618 / 961a | Forward position, low/high words |
| af1c | Lateral position |
| af2c | Height |
| 54ac / 54ae | Forward speed |
| 4568 | Signed steering multiplier |
| 9336 | Signed vertical speed |
| 54aa | Gravity increment |
| 5496 | Lateral drift increment |
| 9330 | Acceleration input, multiplied by75 |
| af2e / af30 | Forward-speed change made by jump adjustment |
| 455a | Jump-assist success flag; not cleared by every helper path |

Ground support is10240 (2800h); the flat structure tops are12800 and15360.
Lateral12160..53376 is the predictor's inclusive permitted range. A whole lane
is5888 lateral units. Real-world distances and seconds are not assigned here.

## ResolveShipMovement: 186bh

Near C arguments are target forward low/high, target lateral, target height.
Current position is read and updated in the globals above. An identical target
returns immediately, without even testing whether the current point is solid.

1. Probe fractions1/5,2/5,...,5/5 of the movement, stopping at the first collision.
2. Commit the fraction immediately before that collision (or5/5 if none).
3. Refine forward using step sizes4096,256,16,1.
4. Refine lateral using signed steps125,25,5,1.
5. Refine height in the same way.

At each refinement size, keep taking clear steps while the remaining distance
is at least that size. Axis order matters: this is an ordered discrete search.
It does not promise a continuous swept-volume collision solution.

Crucial machine behavior: the lateral/height interpolation multiplies in16
bits, discards the high product, sign-extends the low word, then divides by5.
Thus large target deltas can wrap even in the apparent5/5 case. Forward uses a
32-bit product and signed long division. Lateral/height step direction uses
unsigned position comparison; remaining distance uses signed16 absolute value,
including the NEG8000h overflow. Forward refinement compares unsigned32
remaining distance. Arbitrary backwards targets can therefore lead to a long
forward search if the fractional stage collides. The host port imposes a probe
budget rather than inventing new backwards-motion behavior.

Concrete verified boundary: on flat ground ending at row4 in a low block,
moving from `(258048,32768,10240)` toward `(266240,32768,10240)` ends at
`(262143,32768,10240)`: one forward subunit before row4.

## PredictSafeLanding: 1ccdh

Arguments are position, forward speed, steering and vertical speed. The helper
copies and updates its argument words on the stack; shared game globals remain
unchanged. It always takes at least one projected step:

1. Add gravity to vertical speed, wrapping16.
2. Advance forward by the current speed, wrapping32.
3. Advance lateral by `trunc(signed32((speed+1560)*steering)/512) + drift`, wrapping16.
4. Return0 immediately if lateral is outside12160..53376.
5. Add vertical speed to height, wrapping16.
6. Add `75 * signed16(accelerationInput)` to speed, wrapping32, then signed-clamp to0..10922.
7. Repeat while the unsigned height exceeds10240.

At the crossing, test the tile at the previous position and then the current
position with `IsUnsafeLandingTile`. The first unsafe result short-circuits;
otherwise return1. The actual landing filter is described in
`COLLISION-FORMAT.md`: hole and surface12 handling depends on structure bits.

The predictor neither calls the movement resolver nor checks intermediate
walls/roofs. It also projects to ground height even when structures have higher
support surfaces. Its accepted result is the original heuristic's output, not
a guarantee that the whole jump is traversable.

## AdjustJumpForSafeLanding: 1dfah

The initial safe prediction leaves all fields, including old flag/delta, intact.
Otherwise, for n=1..6 it tries these candidates in order, always relative to the
original steering and speed:

1. Steering + truncated10*n percent of steering.
2. Steering - the same amount.
3. Speed + truncated10*n percent of speed, tested only if signed speed<10922.
4. Speed - the same amount.

Steering percentage products wrap16; speed products wrap32. Each division is
by10 after multiplying by n. The first accepted candidate wins. Steering and
speed are not cumulatively scaled and are not changed together in a candidate.

Success writes the chosen steering/speed, speed delta and flag1. Exhausting all
trials restores steering/speed, writes delta0 and preserves the existing flag.
One saved road0 case changes steering57 to23 while keeping speed6735. The
saved flag changes from7 to1;7 is a deliberately adversarial fixture value,
not an assertion about reachable gameplay state.

## Next verification boundary

The caller export now names these helpers, but its remaining semantics are
static-analysis leads. The next step is a deterministic gameplay tick, including
caller stack locals that persist between ticks. In particular:

- Establish tick entry/exit and map ground/jump/assist flags and previous target.
- Recover acceleration, input-to-steering, jump initiation and gravity order.
- Preserve surface effects, bounce, lateral shove, crash and landing responses.
- Recover when the assist flag is enabled and when its temporary speed delta is undone.
- Compare resource depletion and terminal states after the physics core is established.

Do not substitute the landing predictor for the live integrator: acceleration
order and surface-dependent lateral motion differ in the caller. Do not zero
apparently uninitialized stack locals without examining the original flow.
See `PHYSICS-CHECKPOINT.md` for the resumption contract.
