# Recovered timer cadence

The original gameplay counter advances **once every five PIT IRQs**. With the
conventional PC PIT input clock, the recovered cadence is **36.00428485 Hz**,
or **27.77447196 ms per physics tick**. This is a frequency derived from code
and a nominal clock; it is not a physical timing measurement on a DOS machine.

## Original code

`InstallTimerHandlers` at `1000:3acc` replaces interrupt vectors 08h and 24h.
It saves the old IRQ08h vector into the far-jump operands at `CS:3b67/3b69`,
installs `CS:3b17` as IRQ08h, and programs PIT channel 0 with control byte 36h
and little-endian divisor **19e4h = 6628**. Channel 2 receives control b6h and
initial divisor 2. INT24h points to the immediate IRET at `CS:3b14`.

`HandleTimerInterrupt` at `1000:3b17` preserves registers, establishes DS from
the relocated word at `CS:3aca`, and calls the audio stream helper at 5a55.
The relevant phase logic is:

```text
if byte DS:3192 is 0 or 5:
    word DS:1600 += 1          # wraps at 65536
    program speaker from the current word at [DS:bd0], plus 2
    advance DS:bd0 by 2 when that word is nonzero
byte DS:3192 -= 1
if the result is signed-negative:
    DS:3192 = 9
    restore registers; far-jump to the saved old BIOS handler
else:
    send PIC EOI; restore registers; IRET
```

The normal phase cycle is 9,8,7,6,5,4,3,2,1,0. Phases 5 and 0 produce evenly
spaced gameplay increments; phase 0 also chains to BIOS after decrementing.
Starting with BSS phase 0 puts the first increment at IRQ1, followed by
IRQ6,11,16,... . The steady cadence does not depend on this first phase.

The conventional `PIT_TICK_RATE = 1193182` is documented in the primary
[DOSBox Staging timer header](https://github.com/dosbox-staging/dosbox-staging/blob/main/src/hardware/timer.h).
Its [timer implementation](https://github.com/dosbox-staging/dosbox-staging/blob/main/src/hardware/timer.cpp)
derives delay from divisor/input frequency. Thus:

```text
IRQ Hz     = 1193182 / 6628       = 180.0214242607
physics Hz = 1193182 / (6628 * 5) =  36.0042848521
tick time  = (6628 * 5) / 1193182 =   0.027774471958 s
```

The outer gameplay loop waits on DS:1600 and catches up processed physics
ticks. This establishes the counter cadence, not a guaranteed rendering FPS.

## Verification and boundaries

`scripts/validate-skyroads-timer.py` executes unchanged installer/IRQ code in
the relocated load image. It captures virtual OUT operations and IVT writes.
It checks all 256 phase bytes, counter values 0/ffff, and sound words 0/1000:
**1024 boundary cases**, plus a **300-IRQ stream**, for **1324 comparisons**.
The stream produces 60 gameplay increments and 30 BIOS chain decisions.
Registers/stack restoration, ports and sound pointer progression agree.

The actual audio helper executes only its idle-delay branch. The fixture
stops before the old BIOS handler executes. Audio decoding, physical port
timing, IRQ latency and a complete running DOS environment remain outside
the test. Results and hashes are in `timer-validation.json`; raw instructions
are in `timer-instructions.txt`. Ghidra's handler body currently stops at
3b65; the self-modified EA far jump at3b66 is included in the raw evidence.

The portable phase rule and nominal constants are in `scripts/skyroads_timer.py`.

```bash
runtime/re-venv/bin/python scripts/validate-skyroads-timer.py
```

As with the earlier original-code fixtures, Unicorn requires the previously
approved execution outside the shell sandbox on this Mac.
