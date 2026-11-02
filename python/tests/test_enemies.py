"""Gameplay regression tests for the enemy AI, death and shots.

Run from anywhere:   python3 python/tests/test_enemies.py        (plain runner, no pytest needed)
or:                  pytest python/tests
Each test builds a fresh game, so they are independent and can be run one at a time by name:
                     python3 python/tests/test_enemies.py test_shot_pops_ball
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, enemy_rooms, J     # noqa: E402

Ball, Bird, Orb, Sentry, Exp = J.Ball, J.Bird, J.Orb, J.Sentry, J.EnemyExplosion


def wait_for_death(d, frames):
    d.run(frames, until=lambda g: g.death is not None)
    assert d.g.death is not None, f"Joe survived {frames} frames in L{d.g.current_level + 1} R{d.g.current_room}"


def test_level_start_is_safe():
    """Plain level 1 start with the beam-in: Joe must not die or lose a life."""
    d = Driver()
    d.run(180)
    assert d.g.death is None and d.g.player.lives == 3 and not d.g.game_over


def test_ball_kills_joe():
    d = Driver()
    d.goto(0, 5)
    d.place(160, 120)
    wait_for_death(d, 2400)


def test_sentry_present_and_kills_joe():
    d = Driver()
    d.goto(2, 11)
    assert d.entities(Sentry), "sentry should spawn in L3 R11 (its switch variable starts non-zero)"
    d.place(160, 153)
    wait_for_death(d, 1800)


def test_birds_spawn_and_kill_joe():
    d = Driver()
    d.goto(0, 8)
    gen = d.entities(J.BirdGen)[0]
    # Stand in the generator's column so the bird's laser (shape 15) finds Joe.
    d.place(gen.x, max(24, gen.y - 60))
    seen = []
    d.run(3000, until=lambda g: (seen.append(1) if any(isinstance(e, Bird) for e in g.entities) else None)
          or g.death is not None)
    assert seen, "no bird ever spawned in L1 R8"
    assert d.g.death is not None, "bird or laser should have killed Joe standing in its column"


def test_orbs_spawn():
    d = Driver()
    d.goto(1, 1)
    seen = []
    d.run(1500, until=lambda g: bool(seen) or (seen.append(1) if any(isinstance(e, Orb) for e in g.entities) else False))
    assert seen, "no orb spawned in L2 R1"


def test_shot_pops_ball():
    d = Driver()
    d.goto(0, 5)
    jx, jy = d.place(100, 120)
    g = d.g
    g.player.direction = 1
    bx, by = jx + 60, jy + 2
    assert Ball.can_spawn(g, bx, by), "ball spawn point is blocked; pick another spot"
    ball = Ball(g, bx, by)
    g.entities.append(ball)
    d.run(240, keys={"fire"}, until=lambda g: not any(isinstance(e, Ball) for e in g.entities) or g.death is not None)
    assert g.death is None, "the ball reached Joe before a shot hit it"
    assert not d.entities(Ball), "ball still alive after 240 frames of fire"
    assert d.entities(Exp), "popped ball should leave an EnemyExplosion"


def test_death_restarts_level_with_one_less_life():
    d = Driver()
    d.goto(0, 5)
    d.place(160, 120)
    wait_for_death(d, 2400)
    d.run(600, until=lambda g: g.death is None)
    g = d.g
    assert g.death is None, "death animation never finished"
    assert g.player.lives == 2, f"lives = {g.player.lives}, expected 2"
    assert g.current_room == 0 and g.beam_in is not None, "level should restart with the beam-in"


def test_game_over_after_last_life():
    d = Driver()
    d.goto(0, 5)
    d.g.player.lives = 1
    d.place(160, 120)
    wait_for_death(d, 2400)
    d.run(600, until=lambda g: g.game_over)
    assert d.g.game_over and d.g.player.lives == 0


def test_all_enemy_rooms_run_without_errors():
    d = Driver()
    rooms = enemy_rooms(d.g)
    failures = []
    for lvl, by_room in rooms.items():
        for room in by_room:
            d.goto(lvl, room)
            try:
                d.run(40)
            except Exception:
                failures.append((lvl + 1, room, traceback.format_exc()))
    assert not failures, "\n".join(f"L{l} R{r}:\n{tb}" for l, r, tb in failures)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    wanted = sys.argv[1:]
    failed = 0
    for t in TESTS:
        if wanted and t.__name__ not in wanted:
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
