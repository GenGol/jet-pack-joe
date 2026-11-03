#!/usr/bin/env python3
"""Build TESTLEVEL.JPL: a standalone eight-room level with every object type, for testing.

Load it with:   python3 jet_pack_joe.py --level TESTLEVEL.JPL        (it becomes level 4)

Rooms (all exits are left/right along the floor unless noted):
  0  start: four fans (types 1-4), a door opened by a wall switch, a door opened by a toggle pad
  1  fields: vertical field gate + its switch, horizontal field gate + its switch, glow balls + toggle pad
  2  two cages (rescue both to finish) and a pair of crushing plates
  3  generators: balls, birds, orbs
  4  sentry, two doors with sensor pads that close the door behind you
  7  enhanced mode: a twin-shot pack, a turret on the floor, a shield pack
  5  teleporters: one to room 6, a same-room pair      6  teleporter back to room 5
Visuals are stamped from the real levels (MP11/12/13) so every object looks as it should.
File format: b"JPL1", u32 map/lv/pal sizes, map (MPxx layout), level data (LVxx layout),
palette (PL11), then the level name.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
COLS, ROWS, ROOM_BYTES, N_ROOMS = 20, 16, 960, 68
BG = 417                                    # plain dark background tile

MAPS = {1: open(os.path.join(BASE, "MP11.DAT"), "rb").read(),
        2: open(os.path.join(BASE, "MP12.DAT"), "rb").read(),
        3: open(os.path.join(BASE, "MP13.DAT"), "rb").read()}


def stamp(level, room, col, row, w, h):
    """Copy a w×h block (bg words + fg bytes) out of a real level."""
    m = MAPS[level]
    base = room * ROOM_BYTES
    words = struct.unpack_from('<320H', m, base)
    fg = m[base + 640:base + 960]
    out = []
    for dr in range(h):
        for dc in range(w):
            i = (row + dr) * COLS + col + dc
            out.append((dc, dr, words[i], fg[i]))
    return out


# Stamps, each keyed by where the game expects the object's tile relative to the block.
STAMPS = {
    "fan":     (stamp(1, 1, 8, 7, 3, 3), 0, 0),        # 3x3, object tile = top-left
    "door":    (stamp(1, 4, 6, 1, 1, 4), 0, 0),        # 1x4 rails+track, tile = top
    "rswitch": (stamp(1, 4, 13, 7, 1, 1), 0, 0),       # wall must be to its right
    "lswitch": (stamp(1, 0, 3, 8, 1, 1), 0, 0),        # wall must be to its left
    "cage":    (stamp(1, 4, 1, 0, 3, 5), 0, 1),        # 3x5, object tile = row 1 of block
    "vfield":  (stamp(1, 0, 16, 4, 1, 1), 0, 1),       # emitter; field hangs 3 tiles below
    "hfield":  (stamp(2, 13, 10, 5, 1, 1), 1, 0),      # emitter; field runs 3 tiles right
    "tele":    (stamp(3, 13, 15, 10, 3, 5), 0, 1),     # 3x5, object tile = row 1 of block
    "glow":    (stamp(3, 3, 6, 6, 2, 2), 0, 0),
    "ballgen": (stamp(1, 5, 4, 3, 2, 2), 0, 0),
    "birdgen": (stamp(1, 8, 10, 13, 2, 3), 0, 0),      # nest + 2 rows of its base
    "orbgen":  (stamp(2, 1, 14, 4, 2, 2), 0, 0),
}

# Grey bordered block: top row, middle row, bottom row (left, middle, right)
BLK = ((260, 261, 262), (280, 281, 282), (300, 301, 302))
EXIT_ROWS = range(10, 15)


class Room:
    def __init__(self):
        self.words = [BG] * (COLS * ROWS)
        self.fg = [0] * (COLS * ROWS)
        self.exits = [0xFF] * 8            # top0 top1 | right2 right3 | bottom4 bottom5 | left6 left7
        self.objects = []

    def put(self, c, r, tile, flag=0, fg=0):
        if 0 <= c < COLS and 0 <= r < ROWS:
            self.words[r * COLS + c] = (tile & 0x3FF) | ((flag & 0x3F) << 10)
            self.fg[r * COLS + c] = fg

    def box(self, c0, r0, c1, r1):
        """Solid bordered block covering cols c0..c1, rows r0..r1 (inclusive)."""
        for r in range(r0, r1 + 1):
            tr = 0 if r == r0 else (2 if r == r1 else 1)
            for c in range(c0, c1 + 1):
                tc = 0 if c == c0 else (2 if c == c1 else 1)
                self.put(c, r, BLK[tr][tc], 1, 255)

    def stamp(self, name, c, r):
        """Place a stamp so that the OBJECT tile lands at (c, r); returns the object tile."""
        block, ac, ar = STAMPS[name]
        for dc, dr, w, f in block:
            self.put(c - ac + dc, r - ar + dr, w & 0x3FF, (w >> 10) & 0x3F, f)
        return r * COLS + c

    def obj(self, typ, c, r, *params):
        self.objects.append((typ, [r * COLS + c] + list(params)))

    def frame(self, left_exit=False, right_exit=False):
        self.box(0, 0, COLS - 1, 0)                     # ceiling
        self.box(0, ROWS - 1, COLS - 1, ROWS - 1)       # floor
        for r in range(1, ROWS - 1):
            if not (left_exit and r in EXIT_ROWS):
                self.put(0, r, 280, 1, 255)
            if not (right_exit and r in EXIT_ROWS):
                self.put(COLS - 1, r, 282, 1, 255)

    def pillar_door(self, c, switch_var, state_var):
        """A door hanging under a pillar that reaches the ceiling (so it cannot be flown over):
        pillar rows 1-9, door rows 10-13 (object tile row 10), one free row under it."""
        self.box(c, 1, c, 9)
        self.stamp("door", c, 10)
        self.obj(5, c, 10, switch_var, state_var)


def build():
    rooms = [Room() for _ in range(8)]

    # ---- Room 0: start, fans, doors ----
    r = rooms[0]
    r.frame(right_exit=True)
    r.exits[2] = r.exits[3] = 1
    for i, typ in enumerate((1, 2, 3, 4)):
        c = 2 + i * 4
        r.stamp("fan", c, 2)
        r.obj(typ, c, 2)
    r.box(6, 12, 6, 14)                      # wall block carrying the right switch
    r.stamp("rswitch", 5, 13)                # at row 13 Joe can touch it on foot
    r.obj(6, 5, 13, 10)                      # right switch toggles var 10
    r.pillar_door(9, 10, 31)                 # door 1 opens when var 10 is on
    r.obj(17, 12, 14, 11, 11)                # toggle pad flips var 11
    r.pillar_door(16, 11, 32)                # door 2 opens when var 11 is on
    BEAM_TILE = 12 * COLS + 2                # Joe beams in at col 2, row 12

    # ---- Room 1: fields and glow balls ----
    # Joe is 28x30 px: every pocket he must stand or rise in is at least two tiles wide,
    # and each field spans a gap he has to pass through, as in the original levels.
    r = rooms[1]
    r.frame(left_exit=True, right_exit=True)
    r.exits[6] = r.exits[7] = 0
    r.exits[2] = r.exits[3] = 2
    r.box(4, 12, 4, 14)                      # wall block carrying the left switch
    r.stamp("lswitch", 5, 13)
    r.obj(7, 5, 13, 13)                      # left switch toggles var 13
    r.box(8, 1, 8, 9)                        # pillar; the emitter hangs under it at row 10
    r.stamp("vfield", 8, 11)                 # vertical field fills the gap rows 11-14
    r.obj(8, 8, 11, 13)                      # (var 13 on -> active)
    r.box(12, 12, 12, 14)                    # wall block carrying the right switch
    r.stamp("rswitch", 11, 13)
    r.obj(6, 11, 13, 14)                     # right switch toggles var 14
    r.box(14, 9, 14, 14)                     # wall from the slab to the floor
    r.stamp("hfield", 16, 9)                 # emitter at col 15 is part of the slab;
    r.obj(9, 16, 9, 14)                      # the field spans the hole cols 16-18 (var 14)
    for c in (10, 13, 16):
        r.stamp("glow", c, 1)
        r.obj(13, c, 1, 15)                  # glow balls (var 15) hug the ceiling; Joe flies
                                             # under them (rows 3-8) on his way over the slab
    r.obj(17, 17, 14, 15, 15)                # toggle pad in the exit chamber flips var 15

    # ---- Room 2: cages and plates ----
    r = rooms[2]
    r.frame(left_exit=True, right_exit=True)
    r.exits[6] = r.exits[7] = 1
    r.exits[2] = r.exits[3] = 3
    r.stamp("cage", 2, 2)
    r.obj(10, 2, 2, 16, 58)                  # captive (var 16, sprite 58)
    r.stamp("cage", 15, 2)
    r.obj(10, 15, 2, 17, 62)                 # captive (var 17, sprite 62)
    r.box(4, 9, 4, 13)                       # left plate's wall
    r.obj(15, 5, 9, 18)                      # left plate (var 18 = its phase)
    r.box(13, 9, 13, 13)                     # right plate's wall
    r.obj(16, 12, 9, 19)                     # right plate (var 19)

    # ---- Room 3: generators ----
    r = rooms[3]
    r.frame(left_exit=True, right_exit=True)
    r.exits[6] = r.exits[7] = 2
    r.exits[2] = r.exits[3] = 4
    r.stamp("ballgen", 3, 3)
    r.obj(12, 3, 3)
    r.stamp("birdgen", 9, 12)
    r.obj(11, 9, 12)
    r.stamp("orbgen", 15, 3)
    r.obj(20, 15, 3)

    # ---- Room 4: sentry, doors with sensor pads ----
    r = rooms[4]
    r.frame(left_exit=True, right_exit=True)
    r.exits[6] = r.exits[7] = 3
    r.exits[2] = r.exits[3] = 7
    r.obj(14, 10, 3, 20)                     # sentry (var 20 on → present)
    r.pillar_door(6, 21, 33)                 # door, open while var 21 is on
    r.obj(18, 8, 14, 21, 23)                 # pad: var 21 := var 23 (0) → closes door behind you
    r.pillar_door(12, 22, 34)
    r.obj(18, 14, 14, 22, 23)

    # ---- Room 7: enhanced mode (packs and a turret) ----
    # The turret stands on the floor at walking height, so Joe must fly over it or shoot it
    # three times; after a warm-up it fires at him whenever he is level with it on either side.
    r = rooms[7]
    r.frame(left_exit=True, right_exit=True)
    r.exits[6] = r.exits[7] = 4
    r.exits[2] = r.exits[3] = 5
    r.obj(22, 3, 13, 1, 24)                  # twin-shot pack (kind 1), gone once var 24 is 0
    r.obj(23, 10, 14, 26, 2)                 # turret standing on the floor, present while var 26 is on, fires both ways
    r.obj(22, 16, 13, 2, 25)                 # shield pack (kind 2), var 25

    # ---- Rooms 5 and 6: teleporters ----
    r = rooms[5]
    r.frame(left_exit=True)
    r.exits[6] = r.exits[7] = 7
    t1 = r.stamp("tele", 3, 10)
    t2 = r.stamp("tele", 9, 10)
    t3 = r.stamp("tele", 15, 10)
    r6 = rooms[6]
    r6.frame()
    t4 = r6.stamp("tele", 8, 10)
    r.obj(19, 3, 10, 6, t4)                  # to room 6
    r.obj(19, 9, 10, 5, t3)                  # same-room pair
    r.obj(19, 15, 10, 5, t2)
    r6.obj(19, 8, 10, 5, t1)                 # back to room 5

    # ---- map: 68 rooms, unused ones blank (0xFFFF words) ----
    map_out = bytearray()
    for i in range(N_ROOMS):
        if i < len(rooms):
            map_out += struct.pack('<320H', *rooms[i].words) + bytes(rooms[i].fg)
        else:
            map_out += b'\xff' * 640 + bytes(320)

    # ---- level data: 70 entries like the originals; entry 68 holds the trailer ----
    entries = []
    for i in range(70):
        if i < len(rooms):
            body = bytes(rooms[i].exits)
            for typ, params in rooms[i].objects:
                body += struct.pack('<H', typ) + struct.pack(f'<{len(params)}H', *params)
            body += b'\xff\xff'
        elif i == 68:
            captives = sum(1 for rm in rooms for t, _ in rm.objects if t == 10)
            off_list = [10, 11, 31, 32, 18, 19, 23, 33, 34]      # variables that start OFF
            body = bytes(8) + struct.pack('<4H', captives, 150, 0, BEAM_TILE)
            body += struct.pack(f'<{len(off_list)}H', *off_list) + b'\xff\xff'
        else:
            body = b'\xff' * 8 + b'\xff\xff'
        entries.append(body)
    lv_out = bytearray()
    pos = 2 * 70
    for body in entries:
        lv_out += struct.pack('<H', pos)
        pos += len(body)
    for body in entries:
        lv_out += body

    pal = open(os.path.join(BASE, "PL11.DAT"), "rb").read()
    name = "Test Level".encode()
    out = b"JPL1" + struct.pack('<III', len(map_out), len(lv_out), len(pal)) + map_out + lv_out + pal + name
    path = os.path.join(BASE, "TESTLEVEL.JPL")
    with open(path, "wb") as f:
        f.write(out)
    print(f"wrote {path}: {len(out)} bytes, {len(rooms)} rooms, {captives} captives")


if __name__ == "__main__":
    build()
