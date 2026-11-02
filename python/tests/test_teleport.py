"""Teleporter (object type 19, GAME.EXE 0x2219): fires on a walk-in from a side, never on a
drop onto the centre, and never bounces Joe straight back after arrival."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def room13():
    d = Driver()
    g = d.g
    g.enemies_enabled = False
    g.set_level(2)
    g.jump_to_room(13)
    d.run(2)
    return d, g


def test_walk_in_from_left_fires():
    d, g = room13()
    d.place(244, 138)                     # left end of the pedestal, on the side column
    d.run(8)                              # at least one 62-tick check sees Joe on the side
    d.run(90, keys={"right"}, until=lambda g: g.beam_out is not None)
    assert g.beam_out is not None, f"no teleport; Joe at ({int(g.player.x)},{int(g.player.y)})"


def test_walk_in_from_right_fires():
    d, g = room13()
    d.place(286, 138)                     # right end of the pedestal, on the side column
    d.run(8)
    d.run(90, keys={"left"}, until=lambda g: g.beam_out is not None)
    assert g.beam_out is not None, f"no teleport; Joe at ({int(g.player.x)},{int(g.player.y)})"


def test_standing_on_centre_without_crossing_a_side_does_not_fire():
    d, g = room13()
    d.place(256, 138)                     # dropped straight onto the trigger
    d.run(120)
    assert g.beam_out is None


def test_arrival_does_not_bounce_back():
    d, g = room13()
    d.place(244, 138)
    d.run(8)
    d.run(90, keys={"right"}, until=lambda g: g.beam_out is not None)
    d.run(300, until=lambda g: g.current_room == 14 and g.beam_in is None)
    assert g.current_room == 14, "never arrived in room 14"
    d.run(240)                            # stand still on the destination teleporter
    assert g.current_room == 14 and g.beam_out is None, "bounced back"
    # Walking off through a side and back in fires the return trip.
    d.run(14, keys={"left"})
    d.run(8)
    d.run(120, keys={"right"}, until=lambda g: g.beam_out is not None)
    assert g.beam_out is not None, "return trip did not fire after re-entering from a side"


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
