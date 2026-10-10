# GitHub Pages and landscape touch controls — 2026-10-10

Repository: https://github.com/donnybystrom/Skyroads
Site target: https://donnybystrom.github.io/Skyroads/

## Implementation

`build-skyroads-pages.py` exports 95 static files (~64 MiB) including decoded
original graphics, menus, music and sound. GitHub Actions builds and tests the
site, then publishes its `dist/` artifact. Ghidra, REA, native binaries, local
runtimes and raw original/HUD captures stay out of Git. Reports, portable
comparison corpora, source assets and saved recordings remain versioned.

The exported geometry, physics, cycle, presentation and UI scripts remain
byte-identical to their recovered/validated sources. `skyroads-static-api.js`
adapts catalog, replay/save and asset fetches for project-relative static hosting.
Replay runs the same deterministic JavaScript core; Save verifies and downloads
JSON locally. The Python-backed development server remains available separately.

`skyroads-mobile.js` adds landscape steering, gas, brake and jump pads, host
start/pause, options and optional fullscreen. Pointer IDs and keyboard sources
are reference-counted before feeding the existing timestamped input queue.
Pointer capture/cancellation, host pause, rotation, resize and restart release
contacts. Multiple fingers can combine gas, steering and jump without one source
releasing a key that another still holds. Portrait phones show a rotation prompt.

Original menus are exported as their existing separate preview, not newly
integrated into the gameplay state machine in this step.

## Verification

- A clean copy containing only repository-eligible files builds successfully with
  system Python and passes both Node test commands without local raw captures.
- Static tests replay 10 current-identity recordings / 5,755 samples, reject six
  corrupt-recording cases, check ten aggregated source transitions and assert
  byte-identical exported core source files.
- Existing original regression still matches: 4,667 physics ticks, three
  completion requests, 212 finish advances, 15 pause polls, nine initializations
  and nine attempt returns; digest remains
  `d903222452af50ee824af3ca3e66c70f6e96815f7faaab9b95773d36d56eacff`.
- Browser test at `http://127.0.0.1:8771/Skyroads/`, viewport 844×390:
  Start, held Gas (44 sampled ticks), Jump (8), Right (6), pause and options.
  Saved recording has 339 total steps; independent Python replay matches every
  recorded sample and final state. Browser static replay also completes with
  “Replay klar · varje originalsteg matchade.”
- Recording: `recordings/pages-touch-landscape-339.json`.
  Screenshot: `screenshots/pages-mobile-landscape.png`.
- Static menu preview loads its original main screen under `/Skyroads/`; both
  inspected pages have no captured JavaScript warnings/errors.

These are browser viewport and software checks, not tests on a physical mobile
phone. True simultaneous physical touch, portrait behavior on touch hardware,
optional fullscreen support and key/touch-to-photon latency remain to verify on
devices. Existing first-timer-phase, stalled-host-input and remaining native
coverage limits in RESPONSE-MENUS-CHECKPOINT.md still apply. Physics identity is
unchanged; no claim of universally frame-perfect hardware response is added.

## Reproduce

```sh
python3 scripts/build-skyroads-pages.py
node scripts/test-skyroads-pages.cjs
node scripts/validate-skyroads-running-original.js
python3 scripts/replay-skyroads-session.py analysis/skyroads/recordings/pages-touch-landscape-339.json
python3 -m http.server 8000 --directory dist
```

The continuous-original validator now accepts the checked-in original DEMO.REC
when local raw demo dumps are absent. All nine captured dumps were compared to
that file before this change; their SHA-256 is explicitly checked in the test.
