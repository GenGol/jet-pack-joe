"""The standalone test level (TESTLEVEL.JPL, built by tools/build_test_level.py) loads and runs."""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402

LEVEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TESTLEVEL.JPL")
EXPECTED = {0: {1, 2, 3, 4, 5, 6, 17}, 1: {6, 7, 8, 9, 13, 17}, 2: {10, 15, 16}, 3: {11, 12, 20},
            4: {5, 14, 18}, 5: {19}, 6: {19}}


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
    for room in range(7):
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
