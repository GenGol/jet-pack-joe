"""The status bar: one 8-px row of the GAME.EXE font at y=192, grey labels, green TIME."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402
import pygame                     # noqa: E402


def expected_line(surface_w, text, color):
    s = pygame.Surface((surface_w, 8))
    J.draw_text8(s, 0, 0, text, color)
    return s


def same(a, b, rect):
    x0, y0, w, h = rect
    return all(a.get_at((x0 + x, y0 + y))[:3] == b.get_at((x, y))[:3] for y in range(h) for x in range(w))


def test_screen_is_200_lines_with_an_8px_bar():
    assert J.STATUS_H == 8 and J.TOTAL_H == 200


def test_status_line_matches_the_original_string_and_colours():
    d = Driver()
    g = d.g
    d.goto(0, 4)
    g.player.time = 123
    d.run(1)
    pal = g.levels[0]["pal"]
    grey, green = pal[7], pal[10]
    assert grey == (168, 168, 168) and green == (84, 252, 84)
    line = "TIME: 123   JET PACK JOE DEMO   ROOM: 04"
    assert len(line) == 40
    ref = expected_line(320, line, grey)
    J.draw_text8(ref, 48, 0, "123", green)
    assert same(g.screen, ref, (0, 192, 320, 8)), "status bar pixels differ from the font rendering"
    # the bar is black apart from the glyphs
    assert g.screen.get_at((9 * 8 + 1, 196))[:3] == (0, 0, 0)


def test_font_glyphs_match_the_binary():
    """Spot-check the extracted font against the glyph pointers in GAME.EXE itself."""
    import struct
    exe = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "GAME.EXE")
    if not os.path.exists(exe):
        return
    g = open(exe, "rb").read()
    base, tbl = 0x200, 0x31EC + 0x200
    for ch in "TIME:JPKROD0129 ":
        p = struct.unpack_from("<H", g, tbl + ord(ch) * 2)[0] + base
        assert g[p:p + 8] == J.STATUS_FONT[(ord(ch) - 32) * 8:(ord(ch) - 32) * 8 + 8], ch


def test_debug_prompt_replaces_the_middle_text():
    d = Driver()
    g = d.g
    d.goto(0, 0)
    g.goto_buf = "1"
    d.run(1)
    ref = expected_line(320, "GO TO ROOM: 1_".ljust(17), (255, 255, 0))
    assert same(g.screen, ref, (96, 192, 17 * 8, 8))
    g.goto_buf = None
    g.enemies_enabled = False
    d.run(1)
    ref = expected_line(320, "   NO ENEMIES    ", (255, 255, 0))
    assert same(g.screen, ref, (96, 192, 17 * 8, 8))


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
