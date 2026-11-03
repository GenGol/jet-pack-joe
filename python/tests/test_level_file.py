"""The standalone test level (TESTLEVEL.JPL, built by tools/build_test_level.py) loads and runs."""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402

LEVEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TESTLEVEL.JPL")
EXPECTED = {0: {1, 2, 3, 4, 5, 6, 17}, 1: {6, 7, 8, 9, 13, 17}, 2: {10, 15, 16}, 3: {11, 12, 20},
            4: {5, 14, 18}, 5: {19}, 6: {19}, 7: {22, 23}}


def test_level_file_loads_with_every_object_type():
    d = Driver(level_file=LEVEL)
    g = d.g
    assert g.current_level == 3 and g.levels[3]["name"] == "Test Level"
    for room, types in EXPECTED.items():
        got = {o["type"] for o in g.room_objects.get(room, [])}
        assert got == types, f"room {room}: {got} != {types}"
    assert g.captive_count == 2
    assert g.switch_state[10] == 0 and g.switch_state[13] == 255


def test_every_room_runs_and_spawns_its_entities():
    d = Driver(level_file=LEVEL)
    g = d.g
    failures = []
    for room in range(8):
        try:
            d.goto(3, room)
            d.run(40)
        except Exception:
            failures.append((room, traceback.format_exc()))
    assert not failures, failures
    d.goto(3, 4)
    assert d.entities(J.Sentry) and len(d.entities(J.SensorSwitch)) == 2
    d.goto(3, 3)
    assert d.entities(J.BallGen) and d.entities(J.BirdGen) and d.entities(J.OrbGen)
    d.goto(3, 5)
    assert len(d.entities(J.Teleporter)) == 3
    d.goto(3, 7)
    assert len(d.entities(J.Pack)) == 2 and len(d.entities(J.Turret)) == 1


from collections import deque   # noqa: E402

LEFT_ENTRY = (17, 165)          # where Joe lands after walking in from the room to the left


def reachable(g, start):
    """Every (even x, even y) Joe position connected to `start` through cells his collision
    shape clears, in the room's current collision bitmap. Joe moves 1 px at a time in any
    direction when flying, so 2 px connectivity is a slightly conservative stand-in. His own
    marker and enemy markers are ignored; walls, closed doors and active fields block."""
    cbm = bytearray(g.get_collision_bitmap(g.current_room)[0])
    for i, b in enumerate(cbm):
        if b in (J.CT_JOE, J.CT_ENEMY):
            cbm[i] = 0
    clear = J.Player._clear
    sx, sy = start[0] & ~1, start[1] & ~1
    seen, q = set(), deque()
    if clear(cbm, sx, sy):
        seen.add((sx, sy))
        q.append((sx, sy))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)):
            if (nx, ny) in seen or not (0 <= nx < J.SCREEN_W and 0 <= ny < J.SCREEN_H):
                continue
            if clear(cbm, nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


def touches(seen, x0, y0, w=16, h=12):
    """Can Joe's 28x30 body overlap the rectangle from some reachable position?"""
    return any(jx - 12 < x0 + w and jx + 15 > x0 and jy - 14 < y0 + h and jy + 15 > y0
               for jx, jy in seen)


def right_exit(seen):
    return any((J.SCREEN_W - 2, y) in seen for y in range(120, 180, 2))


def room_state(d, room, switches, start=LEFT_ENTRY):
    """Enter a room, force switch variables, let objects write their collision, flood fill."""
    g = d.g
    d.goto(3, room)
    for var, val in switches.items():
        g.switch_state[var] = val
    d.run(80)                               # doors take 14 x 0x59 ticks to open or close
    objs = {(o["type"], o["x"] // 16, o["y"] // 12): o for o in g.room_objects[room]}
    return reachable(g, start if start is not None else (g.player.x, g.player.y)), objs


def test_every_room_is_traversable_and_its_gates_gate():
    """Joe is 28x30 px, so a one-tile pocket traps him (the first room 1 layout did exactly
    that next to the left exit). Each room must be crossable from its left entry once its
    gates are open, and each gate must really block until its switch is used."""
    d = Driver(level_file=LEVEL)
    g = d.g
    g.enemies_enabled = False

    # Room 0: wall switch -> door 1, toggle pad -> door 2 (beam-in spot is the start).
    seen, o = room_state(d, 0, {}, start=None)
    assert touches(seen, o[(6, 5, 13)]["x"], o[(6, 5, 13)]["y"]), "wall switch must be reachable"
    assert not touches(seen, o[(17, 12, 14)]["x"], o[(17, 12, 14)]["y"]), "door 1 should block the pad"
    seen, o = room_state(d, 0, {10: 255}, start=None)
    assert touches(seen, o[(17, 12, 14)]["x"], o[(17, 12, 14)]["y"])
    assert not right_exit(seen), "door 2 should block the exit"
    seen, o = room_state(d, 0, {10: 255, 11: 255}, start=None)
    assert right_exit(seen)

    # Room 1: left switch -> vertical field gate, right switch -> horizontal field gate.
    seen, o = room_state(d, 1, {})
    assert touches(seen, o[(7, 5, 13)]["x"], o[(7, 5, 13)]["y"]), "left switch must be reachable"
    assert not touches(seen, o[(6, 11, 13)]["x"], o[(6, 11, 13)]["y"]), "vertical field should block"
    seen, o = room_state(d, 1, {13: 0})
    assert touches(seen, o[(6, 11, 13)]["x"], o[(6, 11, 13)]["y"]), "right switch behind the open gate"
    assert not right_exit(seen), "horizontal field should block the exit chamber"
    seen, o = room_state(d, 1, {13: 0, 14: 0})
    assert right_exit(seen)
    assert touches(seen, o[(17, 17, 14)]["x"], o[(17, 17, 14)]["y"]), "toggle pad in the exit chamber"

    # Room 2: both cages touchable (rescue box is 48x36 from the cage tile), exit open.
    seen, o = room_state(d, 2, {})
    for key in ((10, 2, 2), (10, 15, 2)):
        assert touches(seen, o[key]["x"], o[key]["y"], 48, 36), f"cage {key} out of reach"
    for key in ((15, 5, 9), (16, 12, 9)):        # plates sweep 52 px from their tile (0x39BF)
        x0 = o[key]["x"] - (52 if key[0] == 16 else 0)
        assert touches(seen, x0, o[key]["y"], 52 + 16, 60), f"cannot reach plate {key}'s sweep"
    assert right_exit(seen)

    # Room 3: generators only; the floor runs straight through.
    seen, o = room_state(d, 3, {})
    assert right_exit(seen)

    # Room 4: doors start open, the sensor pads behind them are reachable; forced shut they block.
    seen, o = room_state(d, 4, {})
    assert touches(seen, o[(18, 8, 14)]["x"], o[(18, 8, 14)]["y"])
    assert touches(seen, o[(18, 14, 14)]["x"], o[(18, 14, 14)]["y"])
    assert right_exit(seen)
    seen, o = room_state(d, 4, {21: 0})
    assert not touches(seen, o[(18, 8, 14)]["x"], o[(18, 8, 14)]["y"]), "closed door 1 should block"

    # Room 7: both packs can be touched; the turret (an enemy, so ignored by the flood fill)
    # stands on the floor between them and the exit is open.
    seen, o = room_state(d, 7, {})
    for key in ((22, 3, 13), (22, 16, 13)):
        assert touches(seen, o[key]["x"] + 4, o[key]["y"] + 4, 8, 4), f"pack {key} out of reach"
    assert right_exit(seen)

    # Rooms 5 and 6: every teleporter trigger (shape 4 at tile +16,+12) can be entered.
    seen, o = room_state(d, 5, {})
    for key in ((19, 3, 10), (19, 9, 10), (19, 15, 10)):
        assert touches(seen, o[key]["x"] + 16, o[key]["y"] + 12), f"teleporter {key} out of reach"
    seen, o = room_state(d, 6, {}, start=None)
    assert touches(seen, o[(19, 8, 10)]["x"] + 16, o[(19, 8, 10)]["y"] + 12)


def hop_right(d, g, frames, until):
    """Hold right; when Joe stops moving, thrust for 25 frames (a hop over a low block). A
    closed door plus its pillar is far too tall for a hop, so doors still gate progress."""
    burst = 0
    last_x = None
    for _ in range(frames):
        if until(g):
            return True
        keys = {"right"}
        if burst:
            keys.add("thrust")
            burst -= 1
        elif last_x is not None and g.player.x == last_x and g.player.vy == 0:
            burst = 25
        last_x = g.player.x
        d.run(1, keys=keys)
    return until(g)


def test_start_room_walkthrough():
    """Beam in, flip the wall switch, hop its block, walk through door 1, step on the toggle
    pad, walk through door 2, leave into room 1."""
    d = Driver(level_file=LEVEL)
    g = d.g
    g.enemies_enabled = False
    d.run(60)                                   # beam-in
    assert g.current_room == 0 and g.death is None
    assert hop_right(d, g, 120, lambda g: g.switch_state[10] != 0), "wall switch should flip var 10"
    assert hop_right(d, g, 400, lambda g: g.player.x > 11 * 16), "door 1 should be open"
    assert hop_right(d, g, 200, lambda g: g.switch_state[11] != 0), "toggle pad at col 12 should flip var 11"
    assert hop_right(d, g, 400, lambda g: g.current_room == 1), "should pass door 2 and leave into room 1"
    assert g.death is None


def hover_right(d, g, frames, target_x, altitude=80):
    """Hold right, thrusting whenever Joe is below `altitude`, until he reaches target_x."""
    for _ in range(frames):
        if g.death or g.player.x >= target_x:
            return g.death is None
        d.run(1, {"right", "thrust"} if g.player.y > altitude else {"right"})
    return False


def test_field_room_walkthrough():
    """Room 1 with real controls: hop the block, step back left into the left switch, walk
    through the dead vertical field, flip the right switch, fly under the glow balls and over
    the slab, drop through the dead horizontal field onto the toggle pad, leave for room 2."""
    d = Driver(level_file=LEVEL)
    g = d.g
    g.enemies_enabled = False
    d.goto(3, 1)
    g.player.x, g.player.y = LEFT_ENTRY
    g.player.vy = g.player.frac = 0
    g.joe_marked = None
    assert hop_right(d, g, 400, lambda g: g.player.x >= 112), "should hop the first block"
    d.run(300, {"left"}, until=lambda g: g.switch_state[13] == 0 or g.death)
    assert g.switch_state[13] == 0, "left switch is pressed from its right"
    assert hop_right(d, g, 600, lambda g: g.switch_state[14] == 0), "right switch behind the gate"
    assert hover_right(d, g, 600, 272), "fly over the slab to the hole"
    d.run(400, {}, until=lambda g: g.player.y >= 160 or g.death)
    assert g.death is None and g.player.y >= 160, "drop through the open horizontal field"
    d.run(400, {"right"}, until=lambda g: g.current_room == 2 or g.death)
    assert g.current_room == 2 and g.death is None
    assert g.switch_state[15] == 0, "the pad in the chamber should have turned the glow balls off"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        if sys.argv[1:] and t.__name__ not in sys.argv[1:]:
            continue
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
            if os.environ.get("JPJ_DEBUG"):
                traceback.print_exc()
    sys.exit(1 if failed else 0)
