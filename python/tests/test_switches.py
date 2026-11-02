"""Sensor switch (object type 18, GAME.EXE 0x2061) tests in L3 R13."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def test_sensor_switches_spawn_with_correct_tiles():
    d = Driver()
    d.goto(2, 13)
    g = d.g
    sensors = sorted(d.entities(J.SensorSwitch), key=lambda e: e.x)
    assert [(e.sw1, e.sw2) for e in sensors] == [(22, 41), (23, 41), (24, 41)]
    # sw1 vars start at 255, sw2 (41) at 0, nobody touching: tile 0x116 + 1
    assert all(e.tile == 0x117 for e in sensors), [hex(e.tile) for e in sensors]
    assert all(g.switch_state[e.sw1] == 255 for e in sensors) and g.switch_state[41] == 0


def test_standing_on_sensor_copies_variable_and_lights_tile():
    d = Driver()
    d.goto(2, 13)
    g = d.g
    d.run(30)                                                   # let the three doors open
    s = min(d.entities(J.SensorSwitch), key=lambda e: e.x)      # pad at (128,144): sw1 22, sw2 41
    door = next(o for o in g.room_objects[13] if o["type"] == 5 and o["params"][1] == s.sw1)
    assert g.switch_state[door["params"][2]] == 14, "door controlled by var 22 should be open"
    jx, jy = d.place(s.x + 4, s.y - 4)
    d.run(180, until=lambda g: g.switch_state[s.sw1] == 0)
    assert g.switch_state[s.sw1] == 0, f"sw{s.sw1} still {g.switch_state[s.sw1]}; Joe at ({int(g.player.x)},{int(g.player.y)}) from ({jx},{jy})"
    assert s.tile == 0x116 + 0x28, hex(s.tile)                  # touching, both variables clear
    # The pad copied 0 into var 22, so the door at x=80 (the one to the pad's left) closes.
    d.run(60, until=lambda g: g.switch_state[door["params"][2]] == 0)
    assert g.switch_state[door["params"][2]] == 0, "door 80 did not close"
    # Walk away: the tile returns to the plain "both clear" look.
    d.run(240, keys={"right"}, until=lambda g: s.tile == 0x116)
    assert s.tile == 0x116, hex(s.tile)


def test_sensor_tile_is_drawn_on_screen():
    d = Driver()
    d.goto(2, 13)
    g = d.g
    d.run(30)                                                   # door above the pad is open
    s = min(d.entities(J.SensorSwitch), key=lambda e: e.x)
    for px, py in ((8, 6), (2, 2), (14, 10)):
        at = (s.col * J.TILE_W + px, s.row * J.TILE_H + py)
        assert g.screen.get_at(at) == g.tile_surfs[s.tile].get_at((px, py)), (px, py)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    import traceback
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
