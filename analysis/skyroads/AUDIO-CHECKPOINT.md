# Original music and sound checkpoint — 2026-10-10

The playable browser surface now plays ten original AdLib music scores and five
original unsigned PCM sound effects. Music and effects have independent gain
controls; effects share one interruptible channel. The verified physics/input
sources and recording identity are unchanged. Start at
http://127.0.0.1:8766/physics-viewer.html ; the first user gesture activates Web Audio.

## Recovered formats and behavior

`MUZAX.LZS` starts with ten six-byte little-endian directory records:
`{file_offset, instrument_paragraphs, decoded_length}`. Each entry is decoded
with the existing verified LZS decoder. Instruments occupy paragraph-aligned
blocks at the beginning; the score starts at `instrument_paragraphs*16`.

The original IRQ0 calls the AdLib interpreter at `1000:5a55` every
`6628/1193182` seconds, about 180.0214 Hz, independently of the 36.0043 Hz
physics counter. Score words dispatch eight commands: delay, instrument,
note-on, note-off, volume, loop-back, loop-mark and control. Register writes
use AL/AH through `1000:5892` to ports 388h/389h. Original instruction execution
retains the delay decrement in the same IRQ that sets it; summing delay words
naively would shift timing. Native track changes also inherit the previous
delay byte at DS:0c83.

Title/demo uses score 0. Normal road selection chooses 1–9 from hardware-timer
entropy and avoids an immediate repeat. Retry does not reload the score.
Original P-pause continues music because IRQ0 still runs. The browser follows
these semantics, using a recorded host selection for the nondeterministic song
choice. The inspection UI can explicitly select a score. Inspection pause and
hidden/focus-lost pages pause audio with the simulated session.

`SFX.SND` begins with six uint16 offsets delimiting five samples. Each block
starts with a Sound Blaster time-constant byte; the remaining bytes are unsigned
8-bit mono PCM. The original stops the old DMA sample, programs DSP 40h, then
DSP 14h and length minus one. No invented jump beep or engine noise is added.

| Index | Original event | PCM bytes | DSP constant | Browser sample rate |
| --- | --- | ---: | ---: | ---: |
| 0 | Crash | 3,983 | 6 | 4,000 Hz |
| 1 | Landing | 5,153 | 131 | 8,000 Hz |
| 2 | Obstruction/bump | 8,084 | 236 | 45,454 Hz |
| 3 | Resource warning | 800 | 131 | 8,000 Hz |
| 4 | Refill | 7,770 | 131 | 8,000 Hz |

The reference is SB16 with DOSBox-X's default sample-rate limits enabled.
Effect 2 requests 50,000 Hz, but that card model caps the effective constant at
234 and uses integer 45,454 Hz. This is reflected in the generated WAV header;
the original requested constant and unchanged PCM bytes remain in the manifest.
See pinned `tools/dosbox-x/src/hardware/sblaster.cpp`,
`DSP_RateLimitedFinalTC_Old` and `DSP_PrepareDMA_Old`. Different historical sound
cards may impose other limits.

`INTRO.SND` is 32,100 unsigned PCM bytes. A native intro call verifies constant
90, giving integer 6,024 Hz. It is extracted as `intro.wav` for later title/intro
integration; it is not played when starting a normal road in the current UI.

## Music rendering

`extract-skyroads-audio.py` executes the unchanged original sequencer in an
isolated Unicorn x86 fixture. IN returns a ready AdLib status, OUT records
register/value pairs; the original driver, tables and score commands execute.
Each of the ten scores is run through its first loop-back. Streams and decoded
bytes are saved under `audio/`, including original loop-mark/end IRQs.

`render-skyroads-audio.py` builds a standalone synthesis tool from the pinned
DOSBox-X DBOPL OPL2 core, retaining its license headers and excluding only its
DOSBox mixer/savestate adapters. The unchanged core renders 48 kHz mono PCM,
stored as lossless FLAC. All tracks have nonzero signal and no clipped int16
samples. DBOPL is GPL-2.0-or-later; the manifest includes upstream commit and
source hashes. Generated build sources remain in `runtime/skyroads-audio/`.

Pre-rendered PCM is suitable for this inspection prototype. A repeated segment
repeats its captured chip/noise state; it is not a continuously running physical
Yamaha chip. Physical DAC filtering, output levels and hardware/OS latency are
not claimed identical. The beginning of a newly selected score currently starts
at its own extracted timeline rather than inheriting a previous native stream's
remaining delay. Exact wrapper/audio-entry timing remains later work.

## Verification

`audio-validation.json` passes:

- **21,552 ordered native OPL register/value writes and IRQ-relative timestamps**
  agree with the isolated original score executions. All ten scores are covered
  by continuous prefixes from full, unpatched DOS runs.
- **67 decoded native score captures** match extracted asset bytes.
- **All five original digital driver cases** produce the expected sample
  pointers, lengths, time constants and DSP bytes; WAV PCM bytes match the
  original source exactly.
- **55 native sound requests** match the original-state Python tick model at
  the corresponding physics step. Native runs include landing, crash, refill,
  obstruction and intro playback. Resource-warning playback is verified through
  the isolated driver, with trigger logic retained from the existing core tests.

Reference runs: `original-runs/audio-gallery`, `audio-keyboard`, `audio-demo`.
Their manifests archive probe/runner/config/build identities and source hashes.
The observer is read-only; all asset files remain unchanged. The early
`audio-all-roads` trace has a short music-dump-length instrumentation error and
is retained only as investigation history; final validation uses the three runs
above. Host output was muted in native reference runs; register/sample comparisons
do not constitute a recorded waveform or a listening comparison with DOSBox.

Browser evidence is in `audio-ui-validation.json`. All ten FLAC scores and five
WAV buffers load, music/effect graphs produce nonzero signal, P-pause retains
music, and replay reproduces recorded song selections. A short 63-sample run
plays its two landing requests again during replay and pauses audio at the end.
A 975-sample run includes an automatic retry with music continuing. The 1,991
sample recording exercises all score selections and P-pause. Effect audits match
the saved core events. Web Audio reports base/output latency, but physical
keyboard-to-speaker latency has not been measured.

The final source also passes a 271-step browser/save smoke check. The controlled
load-race check in `audio-load-validation.json` verifies that a cold effect plays
when decoded, a newer request supersedes an older pending effect, and inspection
pause cancels pending playback. First-use decoding can still delay an effect;
all five small WAVs are preloaded on the first play gesture.

Physics regression: Python and JS still match the previous **4,667 continuous
native physics steps**, 212 finish advances and 15 pause polls. Existing v2
recordings remain valid. `audio-replay-validation.json` checks the new metadata
without changing core recording identity. The user's preexisting 1,069-sample
browser run was saved before reloading the page.

## Files and continuation

- `scripts/skyroads-audio.js`: Web Audio player, single effect channel, independent
  music, mute/volume, loop points and asynchronous load cancellation.
- `scripts/skyroads-audio-ui.js`: subscribes to the existing cycle events and
  records song selections/effect audit as extra metadata. No audio hardware
  state feeds back into `sound_busy`, physics state or the input queue.
- `scripts/dosbox-skyroads-probe.h` / `run-skyroads-original.py --audio`:
  read-only native score/DSP/event observations.
- `audio/manifest.json`: original hashes, decoded/PCM hashes, per-score events,
  loop points, sample rates and synthesizer identity.
- `audio-instructions.txt`, `audio-function-analysis.json`,
  `audio-driver-analysis.json`, `audio-function-annotations.json`: reverse
  engineering evidence. Six new function names and updated sound documentation
  are saved in the persistent Ghidra project.

Reproduce from the project root (Unicorn's JIT requires a host context outside
the restricted sandbox on this Mac):

```bash
runtime/re-venv/bin/python scripts/extract-skyroads-audio.py
runtime/re-venv/bin/python scripts/render-skyroads-audio.py
runtime/re-venv/bin/python scripts/validate-skyroads-audio.py \
  analysis/skyroads/original-runs/audio-gallery \
  analysis/skyroads/original-runs/audio-keyboard \
  analysis/skyroads/original-runs/audio-demo
runtime/re-venv/bin/python scripts/skyroads-prototype-server.py --port 8766
```

`clang++` and `ffmpeg` are used only to build/render audio artifacts. Browser
playback needs the local static files and Web Audio. A portable Rust runtime
can later choose an appropriate synthesizer/backend while keeping the original
score and sound-event contracts.

Next: original dynamic instruments, then real-time input/image/audio response
comparison during traversal and remaining native crash/resource/final-road
coverage. Original fades/messages and profile saving still remain. Exact retry
waiting time is lower priority than traversal feel under the user's instruction.
