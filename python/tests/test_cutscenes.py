"""Cutscenes (FA00-FA03 via GAME.EXE 0x2750), the level flow around them, and the time-out."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def test_fa_files_decode_to_the_expected_frames():
    counts = {}
    for idx in range(4):
        frames, pal = J.load_anim(idx)
        counts[idx] = len(frames)
        assert all(len(f) == 64000 for f in frames)
        assert len(pal) == 256
    assert counts == {0: 15, 1: 14, 2: 2, 3: 2}, counts
    thumbs = J.load_anim(J.ANIM_THUMBS_UP)[0]
    assert thumbs[0] != thumbs[-1], "the thumbs-up animation should move"
    title = J.load_anim(J.ANIM_TITLE)[0]
    assert title[0] == title[1], "the title card is a still image"


def test_cutscene_timing_follows_the_table():
    """Fade in (33 vsyncs), one frame per delay, fade out once the last frame is up."""
    import pygame
    for idx, (_, _, delay) in enumerate(J.ANIMS):
        n = len(J.load_anim(idx)[0])
        cs = J.Cutscene(idx, 0.0)
        total = 2 * J.FADE_TICKS + (n - 1) * delay
        cs.update(total - 10)
        assert not cs.done, f"anim {idx} ended early"
        cs.update(J.FADE_TICKS + 1)                       # (phase changes need a pass each)
        cs = J.Cutscene(idx, 0.0)
        t = 0.0
        while not cs.done and t < total + 200:
            t += 20
            cs.update(t)
        assert cs.done and abs(t - total) <= 60, (idx, t, total)
        assert cs.frame == n - 1
        surf = pygame.Surface((J.SCREEN_W, J.TOTAL_H))
        cs.draw(surf)


def test_first_death_shows_the_reaper_once():
    d = Driver(anims=True)
    g = d.g
    d.goto(0, 5)
    d.place(160, 120)
    d.run(2400, until=lambda g: g.death is not None)
    assert g.death is not None
    d.run(1200, until=lambda g: g.cutscene is not None)
    assert g.cutscene is not None and g.cutscene.idx == J.ANIM_REAPER
    d.run(600, until=lambda g: g.cutscene is None)
    assert g.cutscene is None and g.reaper_shown
    assert g.current_room == 0 and g.beam_in is not None, "the level restarts after the reaper"
    # Second death: straight back to the level.
    d.goto(0, 5)
    d.place(160, 120)
    d.run(2400, until=lambda g: g.death is not None)
    seen = []
    d.run(1200, until=lambda g: seen.append(g.cutscene) or (g.beam_in is not None and g.current_room == 0 and g.death is None))
    assert all(c is None for c in seen), "no second reaper"


def test_level_complete_plays_thumbs_up_then_next_level():
    d = Driver(anims=True)
    g = d.g
    d.goto(0, 3)
    g.captive_count = 0                                   # pretend the last captive is free
    d.run(300, until=lambda g: g.cutscene is not None)
    assert g.cutscene is not None and g.cutscene.idx == J.ANIM_THUMBS_UP
    d.run(600, until=lambda g: g.cutscene is None)
    assert g.current_level == 1 and g.beam_in is not None and g.player.time == 400


def test_last_level_plays_thumbs_up_credits_title_then_level_one():
    d = Driver(anims=True)
    g = d.g
    d.goto(2, 1)
    g.captive_count = 0
    order = []
    def watch(g):
        if g.cutscene is not None and (not order or order[-1] != g.cutscene.idx):
            order.append(g.cutscene.idx)
        return g.current_level == 0 and g.cutscene is None and g.beam_in is not None
    d.run(3000, until=watch)
    assert order == [J.ANIM_THUMBS_UP, J.ANIM_CREDITS, J.ANIM_TITLE], order
    assert g.current_level == 0


def test_no_anims_flag_goes_straight_on():
    d = Driver(anims=False)
    g = d.g
    d.goto(0, 3)
    g.captive_count = 0
    d.run(400, until=lambda g: g.current_level == 1)
    assert g.current_level == 1 and g.cutscene is None


def test_time_out_beams_in_balls():
    d = Driver()
    g = d.g
    d.goto(0, 1)
    g.player.time = 0
    d.run(200, until=lambda g: any(isinstance(e, J.TimeoutBeam) for e in g.entities))
    beams = [e for e in g.entities if isinstance(e, J.TimeoutBeam)]
    assert beams, "a beam should appear within a second or two of TIME reaching 000"
    b = beams[0]
    col, row = b.tile % 20, b.tile // 20
    assert col <= 17 and row <= 13
    d.run(120, until=lambda g: any(isinstance(e, J.Ball) for e in g.entities))
    assert any(isinstance(e, J.Ball) for e in g.entities), "a ball materialises at frame 12"
    assert g.sound.history[-2:].count(J.SND_TRANSPORTER) >= 1


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
