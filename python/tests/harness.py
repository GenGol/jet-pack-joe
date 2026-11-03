"""Headless test harness for jet_pack_joe.py.

Runs the real game loop under SDL's dummy video driver with scripted keys, so gameplay can be
checked without a display. Import this module before anything else in a test (it sets the SDL
environment variables and patches pygame.quit so the game can be run repeatedly).

Usage:
    from harness import Driver
    d = Driver()
    d.goto(level=0, room=5)            # level index 0-2, room index
    d.place(160, 150)                  # nearest free spot to (x, y); pass nothing to keep Joe
    d.run(600, keys={"right", "fire"}, until=lambda g: g.death is not None)
    d.save("shot.png")
"""
import os
import sys
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame                                   # noqa: E402
import jet_pack_joe as J                        # noqa: E402

pygame.quit = lambda: None                      # run() calls it; keep fonts alive between runs

KEYS = {
    "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
    "up": pygame.K_UP, "thrust": pygame.K_SPACE, "fire": pygame.K_z,
}


class _NoClock:
    def tick(self, fps=0):
        return 0


class _Keys:
    def __init__(self, held):
        self.held = {KEYS.get(k, k) for k in held}

    def __getitem__(self, key):
        return key in self.held


class Driver:
    def __init__(self, seed=1, level_file=None):
        random.seed(seed)
        self.g = J.JetPackJoe()
        self.g.clock = _NoClock()
        self.frame = 0
        if level_file:
            self.g.levels.append(J.load_level_file(level_file))
            self.g.set_level(len(self.g.levels) - 1)

    # --- setup -------------------------------------------------------------------------
    def goto(self, level, room, skip_beam=True):
        """Switch to a level and room. Joe keeps the level's beam-in position unless placed."""
        self.g.set_level(level)
        self.g.jump_to_room(room)                # also drops Joe on a free spot of that room
        if not skip_beam:
            self.g.beam_in = {"tile": self.g.beam_tile, "frame": 15, "timer": 0}
        self.g.player.time = 9999                # don't let the timer end a long test
        self.g.enter_room()

    def place(self, x, y, radius=40):
        """Put Joe at the free spot nearest (x, y) in the current room, or raise."""
        g = self.g
        cbm = g.get_collision_bitmap(g.current_room)[0]
        best = None
        for dy in range(-radius, radius + 1, 2):
            for dx in range(-radius, radius + 1, 2):
                px, py = x + dx, y + dy
                if not (8 <= px < J.SCREEN_W - 8 and 8 <= py < J.SCREEN_H - 8):
                    continue
                if J.joe_hits_bg(cbm, px, py):
                    continue
                d = dx * dx + dy * dy
                if best is None or d < best[0]:
                    best = (d, px, py)
        if best is None:
            raise RuntimeError(f"no free spot near ({x},{y}) in room {g.current_room}")
        g.player.x, g.player.y = float(best[1]), float(best[2])
        g.player.vy = g.player.frac = 0
        g.joe_marked = None
        return best[1], best[2]

    # --- running -------------------------------------------------------------------------
    def run(self, frames, keys=(), until=None):
        """Run the real game loop for up to `frames` frames. `keys` is a set of names from KEYS
        (or pygame constants) held down the whole time. `until(game)` stops the run early when
        it returns true. Returns the number of frames actually run."""
        g = self.g
        start = self.frame
        held = _Keys(keys)
        limit = frames

        def fake_events():
            self.frame += 1
            # The game processes QUIT at the top of a loop iteration and still runs that
            # frame, so the QUIT poll is the n-th frame: run(n) executes exactly n frames.
            if self.frame - start >= limit or (until is not None and until(g)):
                return [pygame.event.Event(pygame.QUIT)]
            return []

        saved = pygame.event.get, pygame.key.get_pressed
        pygame.event.get = fake_events
        pygame.key.get_pressed = lambda: held
        try:
            g.run()
        finally:
            pygame.event.get, pygame.key.get_pressed = saved
        return self.frame - start

    # --- inspection ----------------------------------------------------------------------
    def entities(self, cls=None):
        return [e for e in self.g.entities if cls is None or isinstance(e, cls)]

    def save(self, path):
        pygame.image.save(self.g.screen, path)

    def dump_room(self, room=None):
        """ASCII map of the room's collision bitmap: # wall, 6 enemy, J Joe, . empty."""
        g = self.g
        cbm = g.get_collision_bitmap(room if room is not None else g.current_room)[0]
        chars = {0: ".", J.CT_WALL: "#", J.CT_ENEMY: "6", J.CT_JOE: "J"}
        rows = []
        for y in range(J.HALF_H):
            row = cbm[y * J.HALF_W:(y + 1) * J.HALF_W]
            rows.append("".join(chars.get(b, "?") for b in row))
        return "\n".join(rows)


def enemy_rooms(g):
    """{level: {room: [type names]}} for every room with an enemy or generator object."""
    names = {11: "birds", 12: "balls", 13: "glow", 14: "sentry", 20: "orbs"}
    out = {}
    for lvl in range(3):
        g.set_level(lvl)
        for room, objs in sorted(g.room_objects.items()):
            ts = sorted({names[o["type"]] for o in objs if o["type"] in names})
            if ts:
                out.setdefault(lvl, {})[room] = ts
    return out
