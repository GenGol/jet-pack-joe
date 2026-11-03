"""Cage (object type 10): walls persist while active and vanish for good after the rescue."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Driver, J     # noqa: E402


def rescue(d, room):
    """The cage checks shape 14, the two columns just outside its walls (0x143D), so Joe
    frees the captive by pressing against the cage from outside, not by standing in it."""
    g = d.g
    cage = next(o for o in g.room_objects[room] if o["type"] == 10)
    assert touch_cage(d, cage), "Joe did not rescue the captive"
    assert cage.get("disappear", -1) >= 17, "the beam did not finish"
    return cage


def touch_cage(d, cage, wait=True):
    """Hover beside the cage at wall height and push into its side wall from whichever side
    has room (Joe's body is 28 px wide: left of the cage his centre must be <= x-14, right
    of it >= x+58). With `wait`, keep hovering there until the beam has finished."""
    g = d.g
    room = g.current_room
    for offsets, key in (((-18, -26, -34), "right"), ((60, 68, 76), "left")):
        spot = None
        for off in offsets:
            try:
                spot = d.place(cage["x"] + off, cage["y"] + 18, radius=6)
                break
            except RuntimeError:
                continue
        if spot is None:
            continue
        jx, jy = spot
        for _ in range(120):
            if cage.get("disappear", -1) >= 0 or g.death is not None or g.current_room != room:
                break
            d.run(1, keys={key, "thrust"} if g.player.y > jy else {key})
        if cage.get("disappear", -1) >= 0:
            if wait:
                for _ in range(200):
                    if cage.get("disappear", -1) >= 17 or g.death is not None or g.current_room != room:
                        break
                    d.run(1, keys={"thrust"} if g.player.y > jy else set())
            return True
        if g.death is not None or g.current_room != room:
            return False
    return False


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
    d.run(8)                                                # the cage updates every 0x7D ticks
    assert cbm[(hy + 5) * J.HALF_W + hx + 1] == 1, "active cage should rewrite its walls"


def test_cage_stays_open_after_leaving_and_returning_by_teleporter():
    d = Driver()
    g = d.g
    g.enemies_enabled = False
    g.set_level(2)
    g.jump_to_room(13)
    d.run(2)
    cage = rescue(d, 13)
    # Out through the pedestal teleporter to room 14 and straight back.
    d.place(244, 138)
    d.run(8)
    d.run(90, keys={"right"}, until=lambda g: g.beam_out is not None)
    d.run(300, until=lambda g: g.current_room == 14 and g.beam_in is None)
    assert g.current_room == 14
    d.run(14, keys={"left"})
    d.run(8)
    d.run(120, keys={"right"}, until=lambda g: g.beam_out is not None)
    d.run(300, until=lambda g: g.current_room == 13 and g.beam_in is None)
    assert g.current_room == 13, "did not get back to room 13"
    cbm = g.get_collision_bitmap(13)[0]
    hx, hy = cage["x"] // 2, cage["y"] // 2
    walls = [(hy + r) * J.HALF_W + hx + c for r in range(18) for c in (1, 2, 21, 22)]
    d.run(3)
    assert not any(cbm[i] for i in walls), "cage walls came back after the room reload"
    # And Joe can actually walk into the cage.
    d.place(cage["x"] + 36, cage["y"] + 20)
    d.run(120, keys={"left"}, until=lambda g: g.player.x < cage["x"] - 8 or g.death is not None)
    assert g.death is None and g.player.x < cage["x"] - 8, f"Joe stuck at x={int(g.player.x)}"


def test_every_cage_in_the_game_opens_and_stays_open_after_reload():
    """Rescue all 30 captives; after the room reload a teleporter causes, the four wall columns
    must be gone and the cage interior must have room for Joe."""
    failures = []
    for lvl in range(3):
        d = Driver()
        g = d.g
        g.set_level(lvl)
        keys = [(r, i) for r, objs in sorted(g.room_objects.items()) for i, o in enumerate(objs) if o["type"] == 10]
        for room, idx in keys:
            g.set_level(lvl)
            g.enemies_enabled = False
            cage = g.room_objects[room][idx]
            g.jump_to_room(room)                     # no frames yet: a plate may sit over the drop spot
            g.player.time = 9999
            # Press against a cage wall from outside (hovering, some cages hang over pits),
            # then wait for the beam to finish.
            if not touch_cage(d, cage):
                failures.append((lvl + 1, room, "could not touch the cage"))
                continue
            if cage.get("disappear", -1) < 17:
                failures.append((lvl + 1, room, "rescue did not complete"))
                continue
            g.cbm_cache.pop(room, None)
            g.cbm_backup.pop(room, None)
            g.last_room = None
            g.joe_marked = None
            g.player.x, g.player.y = 8.0, 8.0          # keep Joe's own marker out of the probe
            d.run(3)
            cbm = g.get_collision_bitmap(room)[0]
            hx, hy = cage["x"] // 2, cage["y"] // 2
            walls = sum(cbm[(hy + r) * J.HALF_W + hx + c] for r in range(18) for c in (1, 2, 21, 22)
                        if 0 <= hy + r < J.HALF_H and 0 <= hx + c < J.HALF_W)
            free = any(not J.joe_hits_bg(cbm, cx, cy)
                       for cy in range(cage["y"] + 8, cage["y"] + 34, 2)
                       for cx in range(cage["x"] + 8, cage["x"] + 40, 2))
            if walls or not free:
                failures.append((lvl + 1, room, f"walls={walls} interior_free={free}"))
    assert not failures, failures


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
