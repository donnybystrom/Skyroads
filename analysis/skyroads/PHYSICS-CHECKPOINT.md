# Current physics checkpoint — 2026-10-10

Latest milestone: [HUD-CHECKPOINT.md](HUD-CHECKPOINT.md): original dynamic
instruments render; 4,291 native updates, 554 sampled panels and 467 isolated
original-code cases pass. Physics/input/audio remain unchanged.

Previous milestone: [AUDIO-CHECKPOINT.md](AUDIO-CHECKPOINT.md): ten original music
scores and five effects now play, with native code/event comparisons passing.
Physics/input and recording identity are unchanged.

Previous milestone: [GRAPHICS-CHECKPOINT.md](GRAPHICS-CHECKPOINT.md). The playable
scene now uses original graphics/projection; 287 indexed native scene buffers
match. Physics/input files are unchanged and the 4,667-step native comparisons
still pass. Traversal response remains the priority; original fades are desired
but exact retry waiting time is explicitly lower priority.

Continue from [CYCLE-CHECKPOINT.md](CYCLE-CHECKPOINT.md). The local browser now
runs verified integer physics, original input/lifecycle and deterministic replay.
The old HTTP-driven physics prototype is retained as legacy v1 support.

Previous evidence remains: geometry 41,328 original comparisons; movement 3,897;
tick 5,370; timer 1,324; previous prototype 2,876 additional original ticks.
Current cycle evidence and precise verification limits are in the new checkpoint.
The full running DOS reference now matches 4,667 recorded physics steps in Python
and JS, including DEMO.REC and ordinary-road completion. See
[RUNNING-ORIGINAL.md](RUNNING-ORIGINAL.md). The first concrete gameplay gap is
wrapper timing: the original retries after palette transitions, the clone
immediately. Profile initialization/persistence is also pending.
Current priority: complete functional/gameplay parity, including wrapper phases,
remaining native scenarios and physical input/display timing. Rust comes
after this verification, targeting Windows, macOS, Linux and a simple web export.
