# Skyroads

A playable reconstruction of BlueMoon's 1993 SkyRoads, built from observations
of the running DOS original and recovered game code/assets. The browser prototype
uses deterministic integer physics at the recovered 36.004 Hz game rate.

**Play:** https://donnybystrom.github.io/Skyroads/

**Original-menu preview:** https://donnybystrom.github.io/Skyroads/menu-viewer.html

## Controls

- Desktop: arrow keys steer, accelerate and brake; Space jumps. P uses the original
  pause behavior, Escape leaves the road. The Start/Pause button freezes the test
  host separately from the original game pause.
- Mobile: rotate to landscape, tap **Starta**, hold **GAS**, steer with **◀ ▶**,
  and tap/hold **HOPP** to jump. **BROMS** brakes. Multiple fingers can hold
  different controls together. **Bana / ljud** opens road, assistance and audio
  settings; close it and tap Starta to resume.
- Fullscreen is optional and depends on the browser. Audio starts after a user
  gesture. Rotation, losing focus and opening settings release held inputs and
  pause the host.

## Run locally or build GitHub Pages

Python 3.10+ and Node.js 18+ are sufficient for the static build and its tests;
no Ghidra, DOSBox, Python packages or running backend is needed to play it.

```sh
python3 scripts/build-skyroads-pages.py
node scripts/test-skyroads-pages.cjs
node scripts/validate-skyroads-running-original.js
python3 -m http.server 8000 --directory dist
```

Open http://localhost:8000/ . `dist/` is the complete static site. Root-relative
asset requests from the unchanged game scripts are adapted to the site's own
path, so deployment under `/Skyroads/` works. Replay verification runs in the
browser; Save downloads the verified recording as JSON.

The Pages workflow builds, validates and deploys on pushes to `main`. In GitHub,
**Settings → Pages → Source: GitHub Actions** enables this workflow. Generated
`dist/` files are excluded from Git; Actions publishes its build artifact.

For the local Python-backed analysis UI:

```sh
python3 scripts/skyroads-prototype-server.py
# http://127.0.0.1:8766/physics-viewer.html
```

## Evidence and current limits

- The continuous-original regression covers 4,667 physics steps, 212 finish
  advances and nine attempt initializations/returns. See
  [running-original-js-validation.json](analysis/skyroads/running-original-js-validation.json).
- Static-host tests replay saved recordings, reject corrupt recordings, check
  combined keyboard/pointer input and ensure the exported core scripts match
  their original source bytes.
- Mobile controls feed the same timestamped input queue as the keyboard.
  Browser viewport tests and source-aggregation tests do not establish physical
  phone-to-display latency or certify universal frame-perfect behavior.
- Original menus have a separately verified preview. Full menu/game transitions,
  fades, durable profiles, first timer phase, stalled-host input behavior and
  remaining native crash/resource/end-game scenarios still need work.
- Rust and Windows/macOS/Linux/WebAssembly releases are planned after gameplay
  fidelity work; this repository currently ships the JavaScript prototype and
  Python reference implementation.

Source scripts are in `scripts/`; recovered assets, comparison reports, corpora,
replays and checkpoints are in `analysis/skyroads/`. Original SkyRoads data is in
`Skyroads-binary/`; original game art and music are credited to BlueMoon.

Large raw DOSBox/HUD captures and local tool installations are excluded from Git.
They can be regenerated with the native-analysis scripts; the portable continuous
regression uses the checked-in corpus and hash-verified original DEMO.REC.

See [PAGES-MOBILE-CHECKPOINT.md](analysis/skyroads/PAGES-MOBILE-CHECKPOINT.md) for
this deployment step and [REVERSE-ENGINEERING.md](docs/REVERSE-ENGINEERING.md) for
the original Mac/Ghidra/REA setup notes and earlier experiment instructions.
