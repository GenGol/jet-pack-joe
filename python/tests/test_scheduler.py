"""Room objects run on the original's tick scheduler: each handler's [DI+8] interval."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402

TPF = J.TICKS_PER_FRAME


def objects(g, typ):
    return [o for o in g.room_objects[g.current_room] if o["type"] == typ]


def test_intervals_come_from_the_handlers():
    d = Driver()
    g = d.g
    d.goto(0, 4)                                   # L1 R4: fans, switch, door, cage
    d.run(1)
    for o in g.room_objects[4]:
        t = o["type"]
        if t in (1, 2, 3, 4):
            assert 0x4B <= o["interval"] < 0x4B + 0x64, o["interval"]
        elif t in J.JetPackJoe.OBJ_INTERVAL:
            assert o["interval"] == J.JetPackJoe.OBJ_INTERVAL[t]
        else:
            assert o["interval"] is None


def test_door_takes_fourteen_updates_of_0x59_ticks():
    d = Driver(level_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TESTLEVEL.JPL"))
    g = d.g
    d.goto(3, 0)
    d.run(1)
    door = next(o for o in objects(g, 5) if o["params"][1] == 10)
    var = door["params"][2]
    assert g.switch_state[var] == 0
    g.switch_state[10] = 255                       # the wall switch is on
    t0 = g.tick
    d.run(200, until=lambda g: g.switch_state[var] == 14)
    took = g.tick - t0
    assert 13 * 0x59 <= took <= 15 * 0x59 + TPF, took      # ~1.07 s, not 0.25 s


def test_fans_advance_one_frame_per_interval():
    d = Driver()
    g = d.g
    d.goto(0, 4)
    d.run(1)
    fan = objects(g, 1)[0] if objects(g, 1) else [o for o in g.room_objects[4] if o["type"] in (1, 2, 3, 4)][0]
    frames = []
    t0 = g.tick
    while g.tick - t0 < fan["interval"] * 6:
        d.run(1)
        if not frames or frames[-1][1] != fan["frame"]:
            frames.append((g.tick, fan["frame"]))
    gaps = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
    assert len(gaps) >= 4
    assert all(abs(gap - fan["interval"]) <= TPF for gap in gaps[1:]), gaps
    assert [f for _, f in frames][:4] in ([0, 1, 2, 0], [1, 2, 0, 1], [2, 0, 1, 2])


def test_plates_step_every_four_updates_of_ten_ticks():
    d = Driver()
    g = d.g
    d.goto(1, 18)
    d.run(1)
    plate = objects(g, 15)[0]
    var = plate["params"][1]
    v0 = g.switch_state[var]
    t0 = g.tick
    d.run(60, until=lambda g: (g.switch_state[var] - v0) % 52 >= 10)
    took = (g.tick - t0) / 10
    assert 38 <= took <= 42 + TPF / 10, took          # 40 ticks per position


def test_cage_beam_runs_at_0x46_ticks_and_counts_the_captive_late():
    from test_cage import touch_cage
    d = Driver()
    g = d.g
    g.enemies_enabled = False
    g.set_level(2)
    g.jump_to_room(13)
    cage = next(o for o in g.room_objects[13] if o["type"] == 10)
    captives = g.captive_count
    assert touch_cage(d, cage, wait=False)
    t0 = g.tick
    d.run(200, until=lambda g: cage.get("disappear", -1) >= 17)
    took = g.tick - t0
    assert 16 * 0x46 <= took <= 18 * 0x46 + TPF, took
    assert g.captive_count == captives - 1


def test_beam_in_waits_500_ticks_and_frees_joe_near_its_end():
    d = Driver()
    g = d.g
    g.set_level(0)
    assert g.beam_in["frame"] == 16 and g.beam_in["next"] == g.tick + 0x1F4   # 16 = not started
    assert g.player.next_time == g.tick + 0x1F4 + 0x410
    x0 = g.player.x
    d.run(20, keys={"right"})                     # 388 ticks: still waiting
    assert g.beam_in["frame"] == 16 and g.player.x == x0
    d.run(60, keys={"right"})                     # 1553 ticks: frame 1, Joe moves
    assert g.beam_in is not None and g.beam_in["frame"] <= 1
    d.run(10, keys={"right"})
    assert g.player.x > x0 and g.beam_in is None


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        if sys.argv[1:] and t.__name__ not in sys.argv[1:]:
            continue
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:                      # noqa: BLE001
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    sys.exit(1 if failed else 0)
