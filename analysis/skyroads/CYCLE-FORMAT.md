# Original gameplay scheduling and skyroads-cycle-v2

The original timer wait is released at nominal PIT 1193182 / 6628 / 5 Hz.
Keyboard scans: 48,50,4b,4d,47,49,4f,51,01,39,19 (hex), in mask-bit order.
Direction groups OR before opposing groups cancel. Input is decoded after wait,
before catch-up physics. Pause/Escape/return gates follow physics at the outer
loop boundary. P pauses until release, any game key press and all-key release;
these busy polls can occur with no timer advance.

Crash exit is gated until crash_ticks > 42; fall/resource end waits reach 108.
Finish resets height/timer and advances forward once per wait until counter 72.
Success notice waits 27 timer counts; ordinary keyboard dismissal is disabled
by original af32=0. Failures reinstall/clear keyboard state before retry.
Main menu index 0–29 maps to road archive 1–30. Completion counters wrap u16.

Unspecified stack words jump_height, edge_distance and previous_target_height
use explicit seeds. Original arithmetic, counter wrap and sound timestamps are
preserved in muted mode. VGA calls draw after physics/gates; P and return retain
the previous drawing. Surface 2 subtracts 128 from displayed ship height.

## Recording

Fields: format, road_index, assist, road_sha256, model_sha256,
initial_completed (30 u16 counters), samples and final snapshot. Each sample
contains its zero-based frame, input (mask, elapsed, notice_key), snapshot and
ordered lifecycle/sound events. elapsed=0 is allowed only during original pause.
notice_key represents an effective BIOS dismissal flag; normal UI keeps false.
Optional browser_timing records native event timestamps, target/applied quantum,
late events, clock segments and CPU/render timing measurements.

Replay verifies identity and each complete sample/final snapshot. V2 is a
strict model revision contract; legacy skyroads-session-v1 uses its unchanged
model. Saves are limited to 20,000 samples and a 32 MiB HTTP request body.

## Original-code evidence

See cycle-validation.json, lifecycle-validation.json, local-validation.json and
cycle-ui-validation.json. Functions are persisted in Ghidra and exported in
ghidra-cycle-functions.json / cycle-annotations.json. Raw x86 decoding is the
authority where segmented Ghidra disassembly/decompilation is misleading.
Physical DOS input-to-photon equality, original graphics and full-game completion
remain beyond this evidence. See CYCLE-CHECKPOINT.md for resumption instructions.
