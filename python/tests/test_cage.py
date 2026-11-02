"""Cage (object type 10): walls persist while active and vanish for good after the rescue."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def rescue(d, room):
    g = d.g
    cage = next(o for o in g.room_objects[room] if o["type"] == 10)
    d.place(cage["x"] + 23, cage["y"] + 40)
    d.run(60, until=lambda g: cage.get("disappear", -1) >= 0)
    assert cage.get("disappear", -1) >= 0, "Joe did not rescue the captive"
    d.run(120, until=lambda g: cage.get("done"))
    assert cage.get("done")
    return cage


def test_backup_bitmap_has_no_cage_walls():
    d = Driver()
    g = d.g
    g.set_level(2)
    g.jump_to_room(13)
    cage = next(o for o in g.room_objects[13] if o["type"] == 10)
    cbm = g.get_collision_bitmap(13)[0]
    bak = g.cbm_backup[13]
    hx, hy = cage["x"] // 2, cage["y"] // 2
    walls = [(hy + r) * J.HALF_W + hx + c for r in range(18) for c in (1, 2, 21, 22)]
    assert all(cbm[i] == 1 for i in walls), "live bitmap should hold the cage walls"
    assert not any(bak[i] for i in walls), "backup must be the bare tile map"


def test_joe_walks_through_cage_after_rescue():
    d = Driver()
    g = d.g
    g.enemies_enabled = False
    g.set_level(2)
    g.jump_to_room(13)
    d.run(2)
    cage = rescue(d, 13)
    start_x = int(g.player.x)
    d.run(240, keys={"left"}, until=lambda g: g.player.x < cage["x"] - 8 or g.death is not None or g.current_room != 13)
    assert g.death is None, "Joe died walking through the cleared cage"
    assert g.player.x < cage["x"] - 8, f"Joe stuck at x={int(g.player.x)} (started {start_x}, cage x={cage['x']})"


def test_cage_walls_survive_a_restore_while_active():
    d = Driver()
    g = d.g
    g.set_level(2)
    g.jump_to_room(13)
    d.run(2)
    cage = next(o for o in g.room_objects[13] if o["type"] == 10)
    cbm = g.get_collision_bitmap(13)[0]
    hx, hy = cage["x"] // 2, cage["y"] // 2
    J.cb_restore(cbm, g.cbm_backup[13], 13, hx, hy)        # something erased over the cage
    d.run(1)
    assert cbm[(hy + 5) * J.HALF_W + hx + 1] == 1, "active cage should rewrite its walls"


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
