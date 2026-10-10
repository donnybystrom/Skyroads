"""Recovered IRQ0 phase rule, with the conventional PC PIT input frequency."""
PIT_HZ = 1193182  # DOSBox Staging src/hardware/timer.h, PC PIT model.
PIT_DIVISOR = 0x19e4
IRQ_HZ = PIT_HZ / PIT_DIVISOR
TICK_HZ = PIT_HZ / (PIT_DIVISOR * 5)
TICK_SECONDS = PIT_DIVISOR * 5 / PIT_HZ


def irq_phase(phase, counter):
    phase &= 255
    counter = (counter + int(phase in (0, 5))) & 65535
    phase = (phase - 1) & 255
    chain_bios = bool(phase & 128)
    return (9 if chain_bios else phase), counter, chain_bios
