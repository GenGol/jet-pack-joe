"""Joe's exact physics (GAME.EXE 0x0CCC, every 10 ticks) and shots crossing rooms (0x1095)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def test_walk_speed_is_one_pixel_per_update():
    d = Driver()
    d.goto(0, 0)
    g = d.g
    jx, jy = d.place(60, 100)
    d.run(60, keys={"right"})
    moved = g.player.x - jx
    assert 112 <= moved <= 120, moved          # 1 px per 10 ticks = 116.5 px/s


def test_fall_is_capped_at_one_pixel_per_update_and_accelerates_by_41():
    d = Driver()
    d.goto(0, 0)
    g = d.g
    d.place(160, 30)
    g.player.vy = g.player.frac = 0
    prev = g.player.y
    steps = []
    for _ in range(30):
        d.run(1)
        steps.append(g.player.y - prev)
        prev = g.player.y
    assert max(steps) <= 2, steps                      # ~1.94 updates per frame, 1 px each at most
    assert steps[0] <= 1 and steps[-1] == 2, steps     # gravity ramps vy up to the 1000 cap
    assert g.player.vy == J.JOE_VMAX


def test_thrust_lifts_joe_and_flame_sprite_grows():
    d = Driver()
    d.goto(0, 0)
    g = d.g
    d.place(160, 120)
    y0 = g.player.y
    d.run(30, keys={"thrust"})
    assert g.player.y < y0 - 10
    assert g.player.flame_sprite >= 12                 # +4 while thrusting
    d.run(10)
    assert 8 <= g.player.flame_sprite <= 15            # idle flame still drawn, flickering


def test_fire_once_per_press_then_every_200_ticks():
    d = Driver()
    d.goto(0, 0)
    g = d.g
    d.place(60, 100)
    shots = lambda: [e for e in g.entities if isinstance(e, J.Shot)]
    d.run(1, keys={"fire"})
    assert len(shots()) == 1
    d.run(4, keys={"fire"})
    assert len(shots()) == 1, "held fire must wait 0xC8 ticks"
    d.run(int(0xC8 / J.TICKS_PER_FRAME) + 2, keys={"fire"})
    assert len(shots()) + sum(1 for e in g.dormant if isinstance(e, J.Shot)) >= 2 or g.sound.history.count(J.SND_SHOOT) >= 2
    d.run(2)
    d.run(1, keys={"fire"})                            # released and pressed again: immediate
    assert g.sound.history.count(J.SND_SHOOT) >= 3


def test_shot_crosses_into_next_room_and_keeps_flying_if_joe_follows():
    d = Driver()
    g = d.g
    g.enemies_enabled = False
    g.set_level(0)
    g.jump_to_room(5)                                  # R5's top edge → R6
    d.run(2)
    g.player.time = 9999
    d.place(160, 40)
    g.player.direction = 1
    # Shots only fly sideways, so exercise the crossing directly: a shot leaving R5's top edge.
    shot = J.Shot(g, 160, 2, 1)
    shot.speed = 0
    g.entities.append(shot)
    assert shot.cross(g, 160, -1), "leaving the top edge should park the shot in R6"
    assert shot.room == 6 and shot.visible == 0 and shot in g.dormant and shot.y == 191
    d.run(120, keys={"thrust"}, until=lambda g: g.current_room != 5)
    assert g.current_room == 6
    d.run(3, keys={"thrust"})
    assert shot in g.entities and shot.visible == 1, "parked shot should wake in R6"


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
