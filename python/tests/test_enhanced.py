"""Enhanced mode: packs (type 22), the turret (type 23), the shield and the twin shot.

Run:   python3 python/tests/test_enhanced.py     (plain runner, no pytest needed)
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402
import pygame                     # noqa: E402

LEVEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TESTLEVEL.JPL")
ROOM = 7
FLOOR_Y = 164                     # Joe standing on the floor of a test-level room
TURRET_X, TURRET_Y = 10 * 16 + 8, 14 * 12 + 3           # centre of the 16x18 body in its tile
WARMUP_FRAMES = int(J.TURRET_WARMUP / J.TICKS_PER_FRAME) + 1


def armoury(enhanced=True, enemies=True):
    d = Driver(level_file=LEVEL, enhanced=enhanced)
    d.g.enemies_enabled = enemies
    d.goto(3, ROOM)
    return d, d.g


def test_original_levels_contain_no_enhanced_objects():
    """The faithful port is untouched: no pack or turret in any room of levels 1-3."""
    d = Driver()
    for lvl in range(3):
        d.g.set_level(lvl)
        found = [(room, o["type"]) for room, objs in d.g.room_objects.items()
                 for o in objs if o["type"] in (22, 23)]
        assert not found, f"level {lvl + 1}: {found}"


def test_room_has_two_packs_and_a_turret():
    d, g = armoury()
    packs = sorted(d.entities(J.Pack), key=lambda e: e.x)
    assert [p.kind for p in packs] == [J.PACK_TWIN, J.PACK_SHIELD]
    t = d.entities(J.Turret)
    assert len(t) == 1 and (t[0].x, t[0].y) == (TURRET_X, TURRET_Y) and t[0].hp == J.TURRET_HP
    total, hist = t[0].check(g.cbm, 0)
    assert total == 8 * 9 and hist[J.CT_ENEMY] == total, "a solid 16x18 block of type 6"


def test_classic_flag_ignores_packs_and_turrets():
    d, g = armoury(enhanced=False)
    assert not d.entities(J.Pack) and not d.entities(J.Turret)
    g.player.pack = J.PACK_TWIN
    d.run(1, keys={"fire"})
    assert len(d.entities(J.Shot)) == 1, "classic mode fires a single shot even with a pack set"


def test_pack_pickup_is_remembered():
    d, g = armoury(enemies=False)                        # the turret would shoot at Joe here
    pack = min(d.entities(J.Pack), key=lambda e: e.x)
    d.place(pack.x + 8, FLOOR_Y)
    d.run(60, until=lambda g: g.player.pack is not None)
    assert g.player.pack == J.PACK_TWIN
    assert g.switch_state[pack.var] == 0 and not any(p.kind == J.PACK_TWIN for p in d.entities(J.Pack))
    assert J.SND_PICKUP in g.sound.history
    g.last_room = None                                   # re-enter the room: the pack is gone
    d.run(1)
    assert [p.kind for p in d.entities(J.Pack)] == [J.PACK_SHIELD]


def test_twin_shot_fires_two_shots_per_press():
    d, g = armoury()
    d.place(160, 60)
    d.run(1, keys={"fire"})
    assert len(d.entities(J.Shot)) == 1
    d.run(130)                                           # the shot has crossed the room
    assert not d.entities(J.Shot)
    g.player.pack = J.PACK_TWIN
    d.run(1, keys={"fire"})
    shots = d.entities(J.Shot)
    assert len(shots) == 2 and len({s.y for s in shots}) == 1, "two shots on the same path"
    assert abs(shots[0].x - shots[1].x) == 8


def test_twin_shot_lands_two_hits_on_the_turret():
    """Both shots of a volley hit the turret and count separately: two presses destroy it."""
    d, g = armoury()
    d.place(TURRET_X + 70, FLOOR_Y)
    g.player.direction = 0
    g.player.pack = J.PACK_TWIN
    turret = d.entities(J.Turret)[0]
    d.run(1, keys={"fire"})
    d.run(60, until=lambda g: not d.entities(J.Shot))
    d.run(4)                                             # the turret notices a hit at its next update
    assert turret.hp == J.TURRET_HP - 2, f"one volley should take two hit points, hp={turret.hp}"


def test_shield_absorbs_one_death_then_breaks():
    """L1 R5's balls kill an unprotected Joe in under 2400 frames (test_ball_kills_joe)."""
    d = Driver()
    d.goto(0, 5)
    g = d.g
    d.place(160, 120)
    g.player.pack = J.PACK_SHIELD
    d.run(2400, until=lambda g: g.player.pack is None or g.death is not None)
    assert g.death is None, "the shield should have taken the first hit"
    assert g.player.pack is None and g.player.invuln_until > g.tick, "shield consumed, Joe invulnerable"
    d.run(2400, until=lambda g: g.death is not None)
    assert g.death is not None, "without the shield Joe dies"


def test_turret_fires_at_joe_in_its_row_and_the_bullet_kills():
    d, g = armoury()
    d.place(TURRET_X + 70, FLOOR_Y)
    assert abs(g.player.y - TURRET_Y) <= J.TURRET_RANGE_Y
    d.run(WARMUP_FRAMES - 6, until=lambda g: any(isinstance(e, J.TurretShot) for e in g.entities))
    assert not d.entities(J.TurretShot), "no shot during the warm-up (Cam died on --start entry)"
    d.run(30, until=lambda g: any(isinstance(e, J.TurretShot) for e in g.entities))
    bullets = d.entities(J.TurretShot)
    assert bullets and bullets[0].speed > 0, "a bullet flies right, toward Joe"
    assert J.SND_TURRET in g.sound.history
    d.run(120, until=lambda g: g.death is not None)
    assert g.death is not None, "the bullet should have killed Joe"


def test_turret_does_not_fire_at_joe_above_its_row():
    d, g = armoury()
    d.place(TURRET_X + 70, 60)
    for _ in range(WARMUP_FRAMES + 60):
        d.run(1, keys={"thrust"} if g.player.y > 60 else set())
    assert not any(isinstance(e, J.TurretShot) for e in g.entities) and g.death is None


def test_three_hits_destroy_the_turret():
    """Joe stands in the turret's row with a shield, which absorbs the turret's first bullet
    and keeps him alive long enough for three shots to land."""
    d, g = armoury()
    d.place(TURRET_X + 70, FLOOR_Y)
    g.player.direction = 0
    g.player.pack = J.PACK_SHIELD
    turret = d.entities(J.Turret)[0]
    d.run(150, keys={"fire"}, until=lambda g: not turret.alive or g.death is not None)
    assert g.death is None, f"Joe died with the turret at {turret.hp} hp"
    assert not turret.alive and d.entities(J.EnemyExplosion), "turret should explode after 3 hits"
    assert turret.check(g.cbm, 0)[0] == 0, "its collision is erased"


def shot_into_next_room(enhanced):
    """Fire right from the edge of room 3; the shot parks dormant at the edge of room 4."""
    d = Driver(level_file=LEVEL, enhanced=enhanced)
    d.g.enemies_enabled = False
    d.goto(3, 3)
    g = d.g
    d.place(290, FLOOR_Y)
    g.player.direction = 1
    d.run(1, keys={"fire"})
    d.run(30, until=lambda g: any(isinstance(e, J.Shot) for e in g.dormant))
    parked = [e for e in g.dormant if isinstance(e, J.Shot)]
    assert parked and parked[0].room == 4 and parked[0].x < 8, "shot should park at room 4's left edge"
    return d, g


def test_parked_shot_is_caught_up_when_joe_follows():
    """Cam: a shot fired into the next room reappeared at its edge 10 s later. Enhanced mode runs
    the missed updates on wake-up, so a 3 s old shot has long crossed the room or hit a wall."""
    d, g = shot_into_next_room(enhanced=True)
    d.run(180)
    d.run(200, keys={"right"}, until=lambda g: g.current_room == 4)
    assert g.current_room == 4
    stale = [(s.x, s.y) for s in d.entities(J.Shot) if s.x < 100]
    assert not stale, f"shot resumed from the edge: {stale}"
    assert not g.player.explosions, "no stale wall explosion either"


def test_classic_mode_resumes_the_parked_shot_like_the_original():
    d, g = shot_into_next_room(enhanced=False)
    d.run(180)
    d.run(200, keys={"right"}, until=lambda g: g.current_room == 4)
    shots = d.entities(J.Shot)
    assert shots and shots[0].x < 40, "GAME.EXE 0x06F8 wakes the shot where it was parked"


def hover(d, g, frames, altitude, keys=()):
    for _ in range(frames):
        d.run(1, set(keys) | ({"thrust"} if g.player.y > altitude else set()))


def test_turret_bullet_follows_joe_into_the_next_room():
    """Cam: the bullet should follow like Joe's shots do. Joe stands by room 7's left exit in
    the turret's row, waits for the shot, and steps out left; the bullet arrives in room 4."""
    d, g = armoury()
    d.place(30, FLOOR_Y)
    d.run(WARMUP_FRAMES + 30, until=lambda g: any(isinstance(e, J.TurretShot) for e in g.entities))
    assert d.entities(J.TurretShot) and g.death is None
    d.run(60, keys={"left"}, until=lambda g: g.current_room == 4)
    assert g.current_room == 4 and g.death is None
    assert any(e.room == 4 for e in g.dormant if isinstance(e, J.TurretShot)), "clone parked in room 4"
    # Joe arrives at room 4's right edge, exactly where the bullet will come in: climb out of
    # its row, then watch it fly past underneath.
    seen = []
    for _ in range(90):
        d.run(1, {"thrust"} if g.player.y > 100 else set())
        seen += [(e.x, e.y) for e in g.entities if isinstance(e, J.TurretShot)]
    assert seen and g.death is None, "the bullet should wake in room 4 and keep flying"
    assert seen[0][0] > 300 and seen[-1][0] < seen[0][0], f"it enters at the right edge and flies left: {seen[:3]}"


def test_sentry_waits_where_it_was_and_respawns_after_the_sweep():
    """GAME.EXE: the sentry's init clears its variable (0x2335); leaving the room hides it but
    keeps its slot (0x237B), so it is re-activated where it was if Joe is back within the
    stale sweep's 0x1B58 ticks; the sweep destroys it and restores the variable (0x23A5), so a
    later visit spawns a fresh one at its tile. Cam saw the port reset it every time."""
    d = Driver(level_file=LEVEL)
    d.goto(3, 4)
    g = d.g
    sentry = d.entities(J.Sentry)[0]
    home = (sentry.x, sentry.y)
    assert g.switch_state[sentry.var] == 0, "spawning clears the variable"
    d.place(300, FLOOR_Y)
    d.run(90)                                            # it chases Joe for a while
    d.run(60, keys={"right"}, until=lambda g: g.current_room == 7)
    assert g.current_room == 7 and sentry in g.dormant and sentry.visible == 0
    left_at = (sentry.x, sentry.y)
    assert abs(left_at[0] - home[0]) + abs(left_at[1] - home[1]) > 40, "it should have chased Joe"
    hover(d, g, 30, 60)                                  # stay clear of the turret's row
    d.run(120, keys={"left"}, until=lambda g: g.current_room == 4)
    back = d.entities(J.Sentry)
    # On wake it catches up on the updates it missed (8 per frame, 1 px each, with the fall
    # speed it had when hidden), and two frames run before this line: allow up to 24 px.
    assert back == [sentry] and abs(sentry.x - left_at[0]) <= 24 and abs(sentry.y - left_at[1]) <= 24, \
        f"sentry should resume near {left_at}, is at {(sentry.x, sentry.y)}"
    assert g.switch_state[sentry.var] == 0
    # Leave again and stay away past the sweep: it is destroyed and the variable restored.
    d.place(300, FLOOR_Y)
    d.run(60, keys={"right"}, until=lambda g: g.current_room == 7)
    hover(d, g, int(0x1B58 / J.TICKS_PER_FRAME) + 70, 60)
    assert sentry not in g.dormant and g.switch_state[sentry.var] == 0xFF
    d.run(120, keys={"left"}, until=lambda g: g.current_room == 4)
    fresh = d.entities(J.Sentry)
    assert len(fresh) == 1 and fresh[0] is not sentry and abs(fresh[0].x - home[0]) <= 2 \
        and abs(fresh[0].y - home[1]) <= 2, "a fresh sentry spawns at its tile"
    assert g.switch_state[fresh[0].var] == 0


def test_turret_bullet_kills_a_sentry_in_its_path():
    """Cam: a sentry in the bullet's path should die. The sentry's footprint is CT_WALL, the
    same as the room's walls, so the bullet tells it apart by position. A sentry is dropped in
    the turret's row with a bullet flying at it; the sentry dies with the enemy explosion, its
    footprint is erased, and its variable stays 0 so it does not come back."""
    d, g = armoury(enemies=False)
    hover(d, g, 30, 60)                                   # well clear of the turret's row
    sentry = J.Sentry(g, 60, TURRET_Y - 2, 30)
    g.entities.append(sentry)
    cells = sentry.cells()
    assert all(g.cbm[hy * J.HALF_W + hx] == J.CT_WALL for hx, hy in cells)
    g.entities.append(J.TurretShot(g, 150, TURRET_Y - 1, 0))
    d.run(200, until=lambda g: not sentry.alive or not d.entities(J.TurretShot))
    assert not sentry.alive, "the bullet should have destroyed the sentry"
    assert d.entities(J.EnemyExplosion), "enemy explosion where it was"
    assert not d.entities(J.TurretShot), "the bullet is spent"
    assert all(g.cbm[hy * J.HALF_W + hx] == g.cbm_bak[hy * J.HALF_W + hx] for hx, hy in cells), \
        "its footprint is erased"
    assert g.switch_state[30] == 0
    d.run(60, keys={"left"}, until=lambda g: g.current_room == 4)
    d.run(60, keys={"right"}, until=lambda g: g.current_room == 7)
    assert g.current_room == 7 and not d.entities(J.Sentry), "it stays dead"
    assert g.death is None


def test_turret_bullet_still_kills_joe_when_a_sentry_is_elsewhere():
    """The sentry check must not swallow the hit on Joe or on a wall."""
    d, g = armoury(enemies=False)
    d.place(60, FLOOR_Y)
    g.entities.append(J.Sentry(g, 250, 60, 30))          # far from the bullet's row
    g.entities.append(J.TurretShot(g, 150, TURRET_Y - 1, 0))
    d.run(200, until=lambda g: g.death is not None)
    assert g.death is not None and d.entities(J.Sentry)[0].alive


def test_status_bar_shows_the_pack():
    d, g = armoury()
    g.player.pack = J.PACK_TWIN
    g.player.time = 150
    d.run(1)
    pal = g.levels[3]["pal"]
    ref = pygame.Surface((17 * 8, 8))
    J.draw_text8(ref, 0, 0, "PACK: TWIN SHOT  ", pal[11])
    assert all(g.screen.get_at((96 + x, 192 + y))[:3] == ref.get_at((x, y))[:3]
               for y in range(8) for x in range(17 * 8)), "pack slot text differs"
    g.player.pack = None
    d.run(1)
    assert g.screen.get_at((96 + 1, 192 + 1))[:3] != pal[11], "slot reverts to the demo text"


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
