"""Debug navigation: jump_to_room places Joe on a free spot; --start parsing."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def test_jump_to_room_lands_joe_on_free_spot_everywhere():
    d = Driver()
    g = d.g
    bad = []
    for lvl in range(3):
        g.set_level(lvl)
        for room in range(g.num_rooms):
            if not g.jump_to_room(room):
                continue
            cbm = g.get_collision_bitmap(room)[0]
            if J.joe_hits_bg(cbm, int(g.player.x), int(g.player.y)):
                bad.append((lvl + 1, room))
    assert not bad, f"Joe inside a wall after jump in: {bad}"


def test_jump_to_room_then_running_is_safe():
    d = Driver()
    g = d.g
    g.set_level(2)
    assert g.jump_to_room(13)
    d.run(5)
    assert g.current_room == 13 and g.death is None
    assert d.entities(J.SensorSwitch), "room 13 objects should be spawned after the jump"


def test_jump_rejects_bad_room():
    d = Driver()
    assert not d.g.jump_to_room(-1)
    assert not d.g.jump_to_room(d.g.num_rooms)


def test_parse_start_arg():
    assert J.parse_start_arg(["x"]) is None
    assert J.parse_start_arg(["x", "--start", "3:13"]) == (2, 13)
    assert J.parse_start_arg(["x", "2", "--start=1:5"]) == (0, 5)
    try:
        J.parse_start_arg(["x", "--start", "9:1"])
    except SystemExit:
        pass
    else:
        raise AssertionError("level 9 should be rejected")


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
