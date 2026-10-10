"""Integer ports of SkyRoads movement resolution and jump-assist routines.

Positions are raw machine units, not floats. Arithmetic deliberately preserves
16/32-bit wrap and division toward zero. Limits protect the analysis host; they
are not inferred game rules. The caller supplies decoded road bytes.
"""
from dataclasses import dataclass, replace
from skyroads_collision import u16, lookup, position_hit, unsafe_landing


def u32(value):
    return value & 0xffffffff


def s16(value):
    return (value + 0x8000) % 0x10000 - 0x8000


def s32(value):
    return (value + 0x80000000) % 0x100000000 - 0x80000000


def trunc_div(value, divisor):
    """Signed division without floats or Python's negative floor rounding."""
    quotient = abs(value) // abs(divisor)
    return -quotient if (value < 0) != (divisor < 0) else quotient


def abs16(value):
    # NEG 8000h remains 8000h; the following comparison is signed.
    value = s16(value)
    return s16(-value) if value <= 0 else value


@dataclass(frozen=True)
class Position:
    forward: int
    lateral: int
    height: int

    def wrapped(self):
        return Position(u32(self.forward), u16(self.lateral), u16(self.height))


@dataclass(frozen=True)
class Flight:
    position: Position
    speed: int
    steering: int
    vertical_speed: int
    speed_delta: int = 0
    assist_flag: int = 0

    def wrapped(self):
        return Flight(self.position.wrapped(), u32(self.speed), s16(self.steering),
                      s16(self.vertical_speed), u32(self.speed_delta), u16(self.assist_flag))


@dataclass(frozen=True)
class Environment:
    gravity: int
    drift: int = 0
    throttle: int = 0


def emit(observer, kind, *values):
    if observer is not None:
        observer((kind, *values))


def resolve_movement(road, current, target, *, observer=None, max_probes=4096):
    """186bh: five fractional probes, then forward/lateral/height refinement."""
    current, target = current.wrapped(), target.wrapped()
    if current == target:
        return current
    probes = 0

    def hit(pos):
        nonlocal probes
        probes += 1
        if probes > max_probes:
            raise RuntimeError('Movement probe budget exceeded')
        emit(observer, 'collision', pos.forward, pos.lateral, pos.height)
        return position_hit(road, pos.forward, pos.lateral, pos.height)

    def fraction(n):
        return Position(
            u32(current.forward + trunc_div(s32((target.forward - current.forward) * n), 5)),
            u16(current.lateral + trunc_div(s16((target.lateral - current.lateral) * n), 5)),
            u16(current.height + trunc_div(s16((target.height - current.height) * n), 5)))

    n = 1
    while n <= 5:
        if hit(fraction(n)):
            break
        n += 1
    position = fraction(n - 1)
    for step in (4096, 256, 16, 1):
        # This subtraction is UNSIGNED, including for a backwards target.
        while step <= u32(target.forward - position.forward):
            candidate = replace(position, forward=u32(position.forward + step))
            if hit(candidate):
                break
            position = candidate
    for axis in ('lateral', 'height'):
        goal = getattr(target, axis)
        step = 125 if getattr(position, axis) < goal else -125
        while step:
            while abs16(goal - getattr(position, axis)) >= abs(step):
                candidate = replace(position, **{axis: u16(getattr(position, axis) + step)})
                if hit(candidate):
                    break
                position = candidate
            step = trunc_div(step, 5)
    return position


def predict_landing(road, flight, environment, *, observer=None, max_ticks=1024):
    """1ccdh: projected ground crossing, then two tile-safety predicates.

    Does not call collision resolution or test intervening walls/roofs.
    Returns the original AX boolean. Even a start at ground gets one step.
    """
    flight = flight.wrapped()
    f, x, y = flight.position.forward, flight.position.lateral, flight.position.height
    speed, steering, vertical = flight.speed, flight.steering, flight.vertical_speed
    emit(observer, 'predict', f, x, y, speed, steering, vertical)
    for _ in range(max_ticks):
        emit(observer, 'flight', f, x, y, speed, vertical)
        previous_f, previous_x = f, x
        vertical = s16(vertical + environment.gravity)
        f = u32(f + speed)
        x = u16(x + trunc_div(s32(u32(speed + 0x618) * steering), 512) + environment.drift)
        if x < 0x2f80 or x > 0xd080:
            return 0
        y = u16(y + vertical)
        speed = u32(max(0, min(0x2aaa, s32(speed + s16(environment.throttle) * 75))))
        if y <= 0x2800:
            for landing_f, landing_x in ((previous_f, previous_x), (f, x)):
                emit(observer, 'landing', landing_f, landing_x)
                if unsafe_landing(lookup(road, landing_f, landing_x)):
                    return 0
            return 1
    raise RuntimeError('Landing prediction tick budget exceeded')


def adjust_jump(road, flight, environment, *, observer=None, max_ticks=1024):
    """1dfah: first successful steering/speed candidate, up to six passes.

    Existing flag/delta survive an immediately safe prediction. If all trials
    fail, steering/speed are restored, delta becomes zero, flag is preserved.
    """
    flight = flight.wrapped()

    def safe(candidate):
        return predict_landing(road, candidate, environment,
                               observer=observer, max_ticks=max_ticks)

    if safe(flight):
        return flight
    for n in range(1, 7):
        steering_delta = trunc_div(s16(flight.steering * n), 10)
        speed_delta = trunc_div(s32(flight.speed * n), 10)
        candidates = [replace(flight, steering=s16(flight.steering + steering_delta)),
                      replace(flight, steering=s16(flight.steering - steering_delta))]
        faster = u32(flight.speed + speed_delta)
        if s32(faster) < 0x2aaa:  # Strict inequality in the original caller.
            candidates.append(replace(flight, speed=faster))
        candidates.append(replace(flight, speed=u32(flight.speed - speed_delta)))
        for candidate in candidates:
            if safe(candidate):
                return replace(candidate, speed_delta=u32(candidate.speed - flight.speed), assist_flag=1)
    return replace(flight, speed_delta=0)
