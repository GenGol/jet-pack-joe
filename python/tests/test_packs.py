"""Enhanced mode: the nine packs added after the charge shot (time cell, bounce, homing, bombs,
afterburner, hover, phase, cage remote, freeze).

Run:   python3 python/tests/test_packs.py
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402

LEVEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TESTLEVEL.JPL")
FLOOR_Y = 164


def room(n, enemies=False, enhanced=True):
    d = Driver(level_file=LEVEL, enhanced=enhanced)
    d.g.enemies_enabled = enemies
    d.goto(3, n)
    return d, d.g


def hover(d, g, frames, altitude, keys=(), until=None):
    for _ in range(frames):
        if until is not None and until(g):
            return True
        d.run(1, set(keys) | ({"thrust"} if g.player.y > altitude else set()))
    return until is not None and until(g)


def pick_up(d, g, kind):
    pack = [p for p in d.entities(J.Pack) if p.kind == kind][0]
    d.place(pack.x + 8, FLOOR_Y)
    d.run(60, until=lambda g: not pack.alive)
    assert not pack.alive, f"pack {kind} not picked up"
    return pack


def test_time_cell_adds_to_the_clock_and_is_not_carried():
    d, g = room(0)
    g.player.time = 100
    g.player.pack = J.PACK_SHIELD
    pick_up(d, g, J.PACK_TIME)
    assert g.player.time == 100 + J.TIME_CELL_SECONDS and g.player.pack == J.PACK_SHIELD
    assert J.SND_PICKUP in g.sound.history
    g.player.time = 990
    g.switch_state[40] = 0xFF
    d.place(200, FLOOR_Y)                                   # off the pack's tile, then re-enter
    g.last_room = None
    d.run(1)
    pick_up(d, g, J.PACK_TIME)
    assert g.player.time == 999, "capped at the three digits of the status bar"


def test_bounce_shot_turns_round_at_a_wall_then_dies():
    """Fired left from near the left wall it comes back right, passes Joe, bounces off the right
    wall, and dies at the left wall on its third hit. On the way back it kills a ball behind Joe."""
    d, g = room(7)
    d.place(60, 60)
    g.player.direction = 0
    g.player.pack = J.PACK_BOUNCE
    ball = J.Ball(g, 200, 62)
    g.entities.append(ball)
    hover(d, g, 1, 60, keys={"fire"})
    shot = d.entities(J.BounceShot)[0]
    assert shot.speed < 0
    hover(d, g, 60, 60, until=lambda g: shot.speed > 0)
    assert shot.speed > 0 and shot.bounces == 1 and shot.alive, "it turned round at the left wall"
    hover(d, g, 120, 60, until=lambda g: not ball.alive)
    assert not ball.alive and not shot.alive, "the returning shot kills the ball and dies on it"
    assert g.death is None


def test_bounce_shot_dies_after_its_bounces():
    d, g = room(7)
    d.place(160, 60)
    g.player.direction = 1
    g.player.pack = J.PACK_BOUNCE
    hover(d, g, 1, 60, keys={"fire"})
    shot = d.entities(J.BounceShot)[0]
    hover(d, g, 400, 60, until=lambda g: not shot.alive)
    assert not shot.alive and shot.bounces == J.BOUNCE_MAX


def test_homing_shot_steers_to_a_ball_and_uses_up_its_pack():
    d, g = room(7)
    d.place(60, 60)
    g.player.direction = 1
    g.player.pack, g.player.ammo = J.PACK_HOMING, 2
    ball = J.Ball(g, 200, 110)                              # 50 px below the shot's row
    g.entities.append(ball)
    hover(d, g, 1, 60, keys={"fire"})
    shots = d.entities(J.HomingShot)
    assert len(shots) == 1 and g.player.ammo == 1 and g.player.pack == J.PACK_HOMING
    hover(d, g, 120, 60, until=lambda g: not ball.alive)
    assert not ball.alive and d.entities(J.EnemyExplosion), "the shot found the ball"
    assert shots[0].y > 80, f"it dived toward the ball, y={shots[0].y}"
    hover(d, g, 1, 60)
    hover(d, g, 1, 60, keys={"fire"})
    assert g.player.pack is None and g.player.ammo == 0, "the last round takes the pack with it"


def test_homing_shot_flies_straight_without_a_target():
    d, g = room(7)
    d.place(60, 60)
    g.player.direction = 1
    g.player.pack, g.player.ammo = J.PACK_HOMING, 5
    hover(d, g, 1, 60, keys={"fire"})
    shot = d.entities(J.HomingShot)[0]
    y0 = shot.y
    hover(d, g, 20, 60)
    assert shot.y == y0 and shot.x > 100


def test_bomb_drops_in_mid_air_and_clears_the_floor():
    d, g = room(7)
    d.place(160, 60)
    g.player.pack, g.player.ammo = J.PACK_BOMBS, 2
    ball = J.Ball(g, 160, 150)                              # below Joe, near the floor
    g.entities.append(ball)
    hover(d, g, 1, 60, keys={"fire"})
    bombs = d.entities(J.Bomb)
    assert len(bombs) == 1 and not d.entities(J.Shot) and g.player.ammo == 1
    hover(d, g, 120, 60, until=lambda g: not bombs[0].alive)
    hover(d, g, 4, 60)                                      # the ball dies on its own next check
    assert not bombs[0].alive and not ball.alive, "the blast erases the ball"
    assert len(d.entities(J.EnemyExplosion)) == 2 and g.death is None
    assert J.cb_check(g.cbm, 16, ball.x >> 1, ball.y >> 1, 0)[1][J.CT_ENEMY] == 0


def test_bomb_pack_shoots_normally_on_the_ground():
    d, g = room(7)
    d.place(140, FLOOR_Y)                                   # clear of the packs on the floor
    g.player.pack, g.player.ammo = J.PACK_BOMBS, 2
    d.run(2)
    d.run(1, keys={"fire"})
    assert d.entities(J.Shot) and not d.entities(J.Bomb) and g.player.ammo == 2


def test_bomb_kills_a_turret_under_it():
    d, g = room(7, enemies=True)
    turret = d.entities(J.Turret)[0]
    d.place(turret.x, 80)
    g.player.pack, g.player.ammo = J.PACK_BOMBS, 5
    hover(d, g, 1, 80, keys={"fire"})
    hover(d, g, 120, 80, until=lambda g: not turret.alive)
    assert not turret.alive and g.death is None


def climb(pack):
    d, g = room(7)
    d.place(160, FLOOR_Y)
    g.player.pack = pack
    d.run(2)
    d.run(40, keys={"thrust"})
    return FLOOR_Y - g.player.y


def test_afterburner_climbs_faster():
    plain, burner = climb(None), climb(J.PACK_BURNER)
    assert burner > plain * 1.3, f"{burner} px vs {plain} px in 40 frames"


def fall(pack):
    d, g = room(7)
    d.place(160, 40)
    g.player.pack = pack
    d.run(40)
    return g.player.y - 40


def test_hover_pack_falls_slower():
    plain, hov = fall(None), fall(J.PACK_HOVER)
    assert hov < plain * 0.6, f"{hov} px vs {plain} px in 40 frames"


def test_phase_pack_walks_through_a_live_field():
    """Room 1's vertical field (var 13 on) kills Joe on touch and blocks him. With the phase
    pack used (X) he walks through it; the field keeps animating and is solid again after."""
    d, g = room(1)
    g.switch_state[13] = 0xFF
    d.place(110, FLOOR_Y)
    d.run(300, keys={"right"}, until=lambda g: g.death is not None or g.player.x > 150)
    assert g.death is not None, "without the pack the field kills him"
    d, g = room(1)
    g.switch_state[13] = 0xFF
    d.place(110, FLOOR_Y)
    g.player.pack = J.PACK_PHASE
    d.run(1, keys={"use"})
    assert g.player.pack is None and g.phasing()
    d.run(300, keys={"right"}, until=lambda g: g.death is not None or g.player.x > 150)
    assert g.death is None and g.player.x > 150, "phased through"
    d.run(int(J.PHASE_TICKS / J.TICKS_PER_FRAME) + 5)
    assert not g.phasing()
    field = [o for o in g.room_objects[1] if o["type"] == 8][0]
    assert field["field_active"] and field["fg_tiles"], "the field is back and still drawn"


def test_cage_remote_frees_the_nearest_captive():
    d, g = room(2)
    d.place(250, FLOOR_Y)                                   # right of the plates' sweep, off the pack
    g.player.pack = J.PACK_REMOTE
    cages = sorted((o for o in g.room_objects[2] if o["type"] == 10), key=lambda o: o["x"])
    assert all(o.get("disappear", -1) < 0 for o in cages)
    before = g.captive_count
    d.run(1, keys={"use"})
    assert g.player.pack is None
    assert cages[1]["disappear"] >= 0 and cages[0].get("disappear", -1) < 0, "the nearer cage opens"
    assert J.SND_THANKS in g.sound.history
    d.run(400, until=lambda g: g.captive_count < before)
    assert g.captive_count == before - 1


def test_cage_remote_is_kept_when_there_is_no_cage():
    d, g = room(7)
    d.place(160, FLOOR_Y)
    g.player.pack = J.PACK_REMOTE
    d.run(1, keys={"use"})
    assert g.player.pack == J.PACK_REMOTE


def test_freeze_stops_enemies_and_the_turret():
    d, g = room(7, enemies=True)
    turret = d.entities(J.Turret)[0]
    turret.fired_at = g.tick - 10 ** 6                       # warm-up over
    d.place(turret.x + 70, FLOOR_Y)
    ball = J.Ball(g, 160, 60)
    g.entities.append(ball)
    g.player.pack = J.PACK_FREEZE
    d.run(1, keys={"use"})
    assert g.player.pack is None and g.tick < g.freeze_until
    bx, by = ball.x, ball.y
    d.run(int(J.FREEZE_TICKS / J.TICKS_PER_FRAME) - 10)
    assert (ball.x, ball.y) == (bx, by) and not d.entities(J.TurretShot) and g.death is None
    d.run(80, until=lambda g: (ball.x, ball.y) != (bx, by))
    assert (ball.x, ball.y) != (bx, by), "it moves again when the freeze ends"


def test_freeze_halts_plates():
    d, g = room(2)
    plate = [o for o in g.room_objects[2] if o["type"] == 15][0]
    d.place(160, FLOOR_Y)
    g.player.pack = J.PACK_FREEZE
    d.run(1, keys={"use"})
    phase = g.switch_state[18]
    d.run(60)
    assert g.switch_state[18] == phase, "the plate's phase variable stops counting"


def test_status_bar_counts_ammo():
    import pygame
    d, g = room(7, enemies=True)                            # "NO ENEMIES" would replace the slot
    d.place(160, 60)
    g.player.pack, g.player.ammo, g.player.time = J.PACK_BOMBS, 3, 150
    d.run(1)
    pal = g.levels[3]["pal"]
    ref = pygame.Surface((17 * 8, 8))
    J.draw_text8(ref, 0, 0, "PACK: BOMBS X3   ", pal[11])
    assert all(g.screen.get_at((96 + x, 192 + y))[:3] == ref.get_at((x, y))[:3]
               for x in range(17 * 8) for y in range(8))


def test_classic_mode_ignores_the_new_packs_and_the_use_key():
    d, g = room(1, enhanced=False)
    assert not d.entities(J.Pack)
    g.player.pack = J.PACK_PHASE
    d.run(1, keys={"use"})
    assert g.player.pack == J.PACK_PHASE and not g.phasing()


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
