"""One SkyRoads gameplay tick: original 2324h through 2afdh.

Input has already been polled. Rendering/timer scheduling are outside this
boundary. Sound runs in the original muted digital-mode configuration: requests
still update the sound timestamp. Completion stops before the finish animation.
"""
from dataclasses import dataclass, fields, replace
from skyroads_collision import TABLES, lookup, inside_tunnel, position_hit, u16
from skyroads_movement import (Position, Flight, Environment, resolve_movement,
                               adjust_jump, s16, s32, u32, trunc_div, emit)

# offset, byte width, signed interpretation. Locals are relative to main BP.
GLOBALS = {
    'forward': (0x9618, 4, False), 'lateral': (0xaf1c, 2, False),
    'height': (0xaf2c, 2, False), 'speed': (0x54ac, 4, False),
    'steering': (0x4568, 2, True), 'vertical_speed': (0x9336, 2, True),
    'drift': (0x5496, 2, True), 'speed_delta': (0xaf2e, 4, False),
    'assist_flag': (0x455a, 2, False), 'fuel': (0x5494, 2, False),
    'oxygen': (0xb13c, 2, False), 'exit_state': (0x456e, 2, False),
    'crash_ticks': (0x456a, 2, False), 'end_ticks': (0x4558, 2, False),
    'sound_tick': (0xaf38, 2, False),
}
LOCALS = {'tick_counter': -2, 'assist_used': -6, 'jumping': -8,
          'jump_height': -10, 'grounded': -12, 'surface8': -14,
          'surface2': -16, 'edge_distance': -24, 'previous_target_height': -28}


@dataclass
class TickState:
    forward: int = 3 << 16
    lateral: int = 32768
    height: int = 10240
    speed: int = 0
    steering: int = 0
    vertical_speed: int = 0
    drift: int = 0
    speed_delta: int = 0
    assist_flag: int = 0
    fuel: int = 30000
    oxygen: int = 30000
    exit_state: int = 0
    crash_ticks: int = 0
    end_ticks: int = 0
    sound_tick: int = 0
    tick_counter: int = 0
    assist_used: int = 0
    jumping: int = 0
    jump_height: int = 10240
    grounded: int = 1
    surface8: int = 0
    surface2: int = 0
    edge_distance: int = 0
    previous_target_height: int = 10240

    def wrapped(self):
        values = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in GLOBALS:
                _, size, signed = GLOBALS[field.name]
                value = (s16 if signed else u16)(value) if size == 2 else u32(value)
            else:
                value = u16(value)
            values[field.name] = value
        return TickState(**values)


@dataclass(frozen=True)
class TickConfig:
    gravity_factor: int
    fuel_divisor: int
    oxygen_factor: int
    road_rows: int
    assist_enabled: int = 1

    @property
    def gravity(self):
        return s16(-(u16(self.gravity_factor) * 5760 // 400))


@dataclass(frozen=True)
class TickInput:
    throttle: int = 0
    direction: int = 0
    jump: int = 0
    timer: int = 0


@dataclass
class TickResult:
    state: TickState
    completion_requested: bool = False


def clamp_speed(value):
    return max(0, min(10922, s32(value)))


def tick(road, state, config, controls, *, observer=None):
    s = state.wrapped()
    timer = u16(controls.timer)

    def sound(which):
        emit(observer, 'sound', which)
        s.sound_tick = timer

    def hit(f, x, y):
        f, x, y = u32(f), u16(x), u16(y)
        emit(observer, 'collision', f, x, y)
        return position_hit(road, f, x, y)

    tile = lookup(road, s.forward, s.lateral)
    tile_present = tile != 0  # Saved before any upper-surface conversion.
    if s.grounded:
        surface = tile
        if s.height > 10240:
            kind = tile >> 8
            if kind >= len(TABLES['support']):
                raise ValueError('Unsupported unshipped structure table index')
            surface = tile >> 4 if s.height == TABLES['support'][kind] else 0
        kind = surface & 15
        if kind == 2 and not s.crash_ticks:
            s.speed = u32(s.speed - 303)
        elif kind == 9 and not s.exit_state:
            if s.fuel < 27000 or s.oxygen < 27000:
                sound(4)
            s.fuel = s.oxygen = 30000
        elif kind == 10 and not s.crash_ticks:
            s.speed = u32(s.speed + 303)
        elif kind == 12:
            if not s.exit_state:
                s.exit_state = 2
            if not s.crash_ticks:
                s.crash_ticks = 1
                sound(0)
        s.speed = clamp_speed(s.speed)
        s.surface8, s.surface2 = int(kind == 8), int(kind == 2)
    else:
        s.surface2 = 0  # surface8 deliberately persists while airborne.

    end_forward = u32((u16(config.road_rows) << 16) - 32768)
    if s.forward >= end_forward and inside_tunnel(road, s.forward, s.lateral, s.height) and not s.exit_state:
        emit(observer, 'finish')
        return TickResult(s, True)

    if s.height != s.previous_target_height:
        threshold = u16(u16(config.gravity_factor) * 260) // 8
        magnitude = u16(-s.vertical_speed) if s.vertical_speed <= 0 else s.vertical_speed
        if (s.drift == 0 or s.edge_distance >= 2) and magnitude >= threshold and not s.crash_ticks:
            if not s.exit_state and s.vertical_speed < 0:
                # Original digital-audio busy helper0476, including16-bit wrap.
                busy = timer < u16(s.sound_tick + 8)
                emit(observer, 'sound_busy', int(busy))
                if not busy:
                    sound(1)
            s.vertical_speed = trunc_div(s16(-5 * s.vertical_speed), 10)
        else:
            s.vertical_speed = 0

    if not s.exit_state:
        s.speed = clamp_speed(s.speed + s16(controls.throttle) * 75)
        if not s.surface8 and ((not s.jumping and tile_present) or
                              (s.steering == 0 and s.vertical_speed > 0 and
                               u16(s.height - s.jump_height) < 3840)):
            s.steering = s16(s16(controls.direction) * 29)
        if not s.jumping and tile_present and u16(controls.jump) and u16(config.gravity_factor) < 20:
            s.vertical_speed = 1152
            s.jumping = 1
            s.jump_height = s.height

    if u16(config.assist_enabled) and s.jumping and not s.assist_used and s.height >= 14080:
        flight = Flight(Position(s.forward, s.lateral, s.height), s.speed, s.steering,
                        s.vertical_speed, s.speed_delta, s.assist_flag)
        result = adjust_jump(road, flight, Environment(config.gravity, s.drift, controls.throttle), observer=observer)
        s.speed, s.steering = result.speed, result.steering
        s.speed_delta, s.assist_flag = result.speed_delta, result.assist_flag
        s.assist_used = 1

    if not s.crash_ticks:
        if s.height < 10240:
            s.vertical_speed = min(s.vertical_speed, -106)
        else:
            s.vertical_speed = s16(s.vertical_speed + config.gravity)
    else:
        s.vertical_speed = max(s.vertical_speed, 0)
        s.vertical_speed = s16(s.vertical_speed + 39) if s.vertical_speed < 71 else 71

    target_f = u32(s.forward + s.speed)
    base = 0 if s.surface2 else 1560
    target_x = u16(s.lateral + s.drift + trunc_div(s32(u32(s.speed + base) * s.steering), 512))
    target_y = u16(s.height + s.vertical_speed)
    if (s.lateral < 12160 and target_x > 53376) or (target_x < 12160 and s.lateral > 53376):
        target_x = s.lateral
    s.previous_target_height = target_y
    emit(observer, 'resolve', target_f, target_x, target_y)
    p = resolve_movement(road, Position(s.forward, s.lateral, s.height),
                         Position(target_f, target_x, target_y), observer=observer)
    s.forward, s.lateral, s.height = p.forward, p.lateral, p.height

    if s.forward != target_f and s.lateral == target_x and hit(target_f, s.lateral, s.height):
        for side in (-928, 928):
            if not hit(target_f, s.lateral + side, s.height):
                s.lateral = u16(s.lateral + side)
                target_f = s.forward
                sound(2)
                break
    if s.forward != target_f:
        if s32(s.speed) < 3640 or s.crash_ticks:
            if s.forward > u32(target_f - s.speed):
                sound(2)
        else:
            s.crash_ticks = 1
            sound(0)
            if not s.exit_state:
                s.exit_state = 1
        s.speed = 0
    if s.lateral != target_x:
        s.steering = 0
        if (s.drift > 0 and s.lateral < target_x) or (s.drift < 0 and target_x < s.lateral):
            s.drift = 0
        s.speed = clamp_speed(s.speed - 151)

    s.grounded = 0
    if s.height != target_y and s.vertical_speed < 0:
        s.assist_flag = s.assist_used = s.jumping = 0
        s.grounded = 1
        s.speed = clamp_speed(s.speed - s.speed_delta)
        s.speed_delta = 0
        edge_direction = 0
        for sign in (1, -1):
            for distance in range(1, 15):
                if not hit(s.forward, s.lateral + sign * distance * 128, s.height - 1):
                    edge_direction += sign
                    s.edge_distance = distance
                    break
        s.drift = s16(s.drift + edge_direction * 17) if edge_direction else 0
    if s.height > 32767:
        s.height = 0

    if not s.exit_state:
        oxygen_divisor = u16(config.oxygen_factor * 36)
        fuel_divisor = u16(config.fuel_divisor)
        if not oxygen_divisor or not fuel_divisor:
            raise ValueError('Original tick would divide by zero with these metadata')
        s.oxygen = u16(s.oxygen - 30000 // oxygen_divisor)
        if s.oxygen > 30000:
            s.oxygen = 0
        drain = trunc_div(s32((30000 // fuel_divisor) * s.speed), 65536)
        s.fuel = u16(s.fuel - drain)
        if s.fuel > 30000:
            s.fuel = 0
    if not s.exit_state:
        if s.height < 10240:
            s.exit_state = 3
        if s.fuel == 0:
            s.exit_state = 4
        if s.oxygen == 0:
            s.exit_state = 5  # Later checks override earlier new exit reasons.
    else:
        s.end_ticks = u16(s.end_ticks + 1)
    if s.crash_ticks:
        s.crash_ticks = u16(s.crash_ticks + 1)
    s.tick_counter = u16(s.tick_counter + 1)
    return TickResult(s)
