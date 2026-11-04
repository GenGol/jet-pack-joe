"""Sound bank tests: DS00.DAT decodes to five samples and the right events trigger them."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def test_bank_loads_five_samples():
    d = Driver()
    bank = d.g.sound
    assert bank.enabled, "mixer did not initialise under the dummy audio driver"
    assert len(bank.sounds) == 8, "the five DS00.DAT samples plus the three synthesized enhanced-mode ones"
    # Durations at 9321.7 Hz: 7424/5888/11520/9728/4352 bytes.
    expect = [7424, 5888, 11520, 9728, 4352, len(J.synth_pickup()), len(J.synth_turret()), len(J.synth_charge())]
    for snd, n in zip(bank.sounds, expect):
        assert abs(snd.get_length() - n / J.SOUND_RATE) < 0.02, (snd.get_length(), n / J.SOUND_RATE)
    assert all(0 <= b < 64 for b in J.synth_pickup() + J.synth_turret()), "6-bit samples"


def test_level_start_plays_transporter():
    d = Driver()
    assert d.g.sound.history[-1:] == [J.SND_TRANSPORTER]


def test_fire_plays_shoot_then_explosion_on_wall():
    d = Driver()
    d.goto(0, 0)
    g = d.g
    cbm = g.get_collision_bitmap(0)[0]
    # Find a free spot with a wall 20-60 px to the right at gun height, so the shot must hit it.
    spot = None
    for jy in range(40, 170, 4):
        gy = (jy + 2) >> 1
        for jx in range(20, 240, 4):
            if J.joe_hits_bg(cbm, jx, jy):
                continue
            row = cbm[gy * J.HALF_W:(gy + 1) * J.HALF_W]
            if any(row[(jx + k) >> 1] == J.CT_WALL for k in range(20, 60, 2)):
                spot = (jx, jy)
                break
        if spot:
            break
    assert spot, "no spot facing a wall found in L1 R0"
    g.player.x, g.player.y = float(spot[0]), float(spot[1])
    g.player.direction = 1
    hist = g.sound.history
    del hist[:]
    d.run(1, keys={"fire"})
    assert hist[:1] == [J.SND_SHOOT]
    d.run(200, until=lambda g: J.SND_EXPLOSION in g.sound.history)
    assert J.SND_EXPLOSION in hist, "shot never hit a wall"


def test_entering_cage_room_plays_help():
    d = Driver()
    g = d.g
    g.set_level(0)
    rooms = [r for r, objs in g.room_objects.items() if any(o["type"] == 10 for o in objs)]
    assert rooms, "level 1 has no cages?"
    del g.sound.history[:]
    d.goto(0, rooms[0])
    assert J.SND_HELP in g.sound.history


def test_popped_ball_plays_explosion():
    d = Driver()
    d.goto(0, 5)
    jx, jy = d.place(100, 120)
    g = d.g
    g.entities.append(J.Ball(g, jx + 60, jy + 2))
    del g.sound.history[:]
    d.run(240, keys={"fire"}, until=lambda g: any(isinstance(e, J.EnemyExplosion) for e in g.entities))
    assert J.SND_EXPLOSION in g.sound.history


def test_death_plays_a_run_of_explosions():
    d = Driver()
    d.goto(0, 5)
    d.place(160, 120)
    d.run(2400, until=lambda g: g.death is not None)
    g = d.g
    del g.sound.history[:]
    d.run(600, until=lambda g: g.death is None)
    assert g.sound.history.count(J.SND_EXPLOSION) >= 20, g.sound.history


def test_sound_can_be_disabled_like_the_original():
    assert J.sound_enabled_from_args(["jet_pack_joe.py"])
    assert not J.sound_enabled_from_args(["jet_pack_joe.py", "0"])
    assert not J.sound_enabled_from_args(["jet_pack_joe.py", "1"])
    assert J.sound_enabled_from_args(["jet_pack_joe.py", "2"])


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
