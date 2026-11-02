"""Mobile objects crossing rooms (GAME.EXE 0x0802 phases 1-4, 0x0521, 0x0A13 sweep).
L1 R5's top edge leads to R6; a ball chasing Joe up and out should turn up in R6."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402

Ball = J.Ball


def setup(ball_dy):
    d = Driver()
    g = d.g
    g.enemies_enabled = False               # no generators: only our hand-placed ball
    g.set_level(0)
    g.jump_to_room(5)
    d.run(2)
    g.player.time = 9999
    jx, jy = d.place(160, 40)
    spot = next(((jx + dx, jy + ball_dy + dy) for dy in range(0, 30, 2) for dx in range(0, 40, 2)
                 if Ball.can_spawn(g, jx + dx, jy + ball_dy + dy)), None)
    assert spot, "no spawnable spot below Joe"
    ball = Ball(g, *spot)                   # retarget=1: aims at Joe (up) on its first update
    g.entities.append(ball)
    d.run(4)                                # let it take aim before Joe leaves
    return d, g, ball


def fly_out_top(d, g):
    d.run(120, keys={"thrust"}, until=lambda g: g.current_room != 5)
    assert g.current_room == 6, f"Joe did not reach room 6 (room {g.current_room})"


def balls_live(g):
    return [e for e in g.entities if isinstance(e, Ball)]


def test_near_ball_follows_into_next_room():
    d, g, ball = setup(50)
    fly_out_top(d, g)
    assert not balls_live(g), "R5's own ball object must not be live in R6 on arrival"
    assert any(b.room == 6 for b in g.dormant if isinstance(b, Ball)), "clone should be dormant in R6"
    # Keep thrusting so Joe stays up in R6 instead of dropping back into R5.
    d.run(120, keys={"thrust"}, until=lambda g: balls_live(g) or g.current_room != 6)
    assert g.current_room == 6, "Joe fell back into room 5"
    live = balls_live(g)
    assert live, "ball never appeared in room 6"
    assert live[0].y > 150, f"it should enter from the bottom edge, got y={live[0].y}"


def test_far_ball_arrives_later():
    d, g, ball = setup(100)                  # 100px below Joe, still above R5's floor
    fly_out_top(d, g)
    d.run(40, keys={"thrust"})
    assert g.current_room == 6 and not balls_live(g), "a ball 100px away should not be in R6 within 40 frames"
    d.run(300, keys={"thrust"}, until=lambda g: balls_live(g) or g.current_room != 6)
    assert g.current_room == 6 and balls_live(g), "far ball never arrived"


def test_ball_left_behind_is_still_there_on_quick_return():
    d, g, ball = setup(50)
    fly_out_top(d, g)
    # Drop straight back down into R5 (R6's bottom edge leads to R5).
    d.run(240, until=lambda g: g.current_room == 5)
    assert g.current_room == 5, "did not get back to room 5"
    d.run(3)
    assert balls_live(g), "the original ball should wake up where it was"


def test_stale_dormant_objects_are_swept():
    d, g, ball = setup(50)
    ball.room = 7                            # pretend it crossed into a room Joe never enters
    g.make_dormant(ball)
    g.entities.remove(ball)
    d.run(int(0x1B58 / J.TICKS_PER_FRAME) + 10)
    assert ball not in g.dormant, "dormant object should be destroyed after 0x1B58 ticks"


def test_exit_room_matches_joe_transition_table():
    d = Driver()
    g = d.g
    g.set_level(0)
    assert g.exit_room(5, 100, -1) == (6, 100, 191)        # top edge → R6
    assert g.exit_room(5, 100, 192) == (4, 260, 0)         # bottom-left → R4 (half-room offset)
    assert g.exit_room(5, 200, 192)[0] is None             # bottom-right: no room
    assert g.exit_room(5, 320, 50)[0] is None              # right: no room
    assert g.exit_room(5, 100, 50) is None                 # inside


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
