"""
Jet Pack Joe — Python Recreation
Original by Joe Lowe (early 1990s), x86 Assembly / DOS / VGA Mode X
Recreated in Python with Pygame, using original game data decompressed from JET.RSC.

Map format (reverse-engineered from GAME.EXE EXPAND_MAP routine):
  Each room = 960 bytes: 640 bytes (320 tile words) + 320 bytes (overlay layer)
  Room grid: 20 columns × 16 rows
  Tile word: bits 0-9 = tile index, bits 10-15 = collision flags

Tile format:
  16×12 pixels, 192 bytes each, linear 8-bit palette-indexed
  682 tiles in BK00.DAT (130944 / 192)

Sprite format (reverse-engineered from GAME.EXE DRAW_SPRITE routine):
  Vertical column RLE, drawn in Mode X plane order.
  4-byte header: x_off, y_off, x_end, y_end (signed bytes)
  Body: segments of (delta_x, delta_y) then column strips
  Each strip: [skip_h] [row_offset_signed] [draw_count] [pixels...]
  Pixels drawn vertically (one per row). Terminated by 0x0000.

Controls:
  Arrow keys — Move left/right
  Space/Up   — Jetpack thrust
  Z          — Fire
  ESC        — Quit
  R          — Restart
  [ / ]      — Previous/Next room (debug)
  1 / 2 / 3  — Switch level

Flags: --level FILE (a JPL1 level, becomes level 4), --start L:R, --no-enemies, --no-anims,
       --classic (ignore the enhanced-mode objects: packs and turrets; see "Enhanced mode").
"""

import struct, os, sys, time, random, copy
from array import array
import pygame

BASE = os.path.dirname(os.path.abspath(__file__))

TILE_W, TILE_H = 16, 12
MAP_COLS, MAP_ROWS = 20, 16
ROOM_BYTES = 960
SCREEN_W = MAP_COLS * TILE_W   # 320
SCREEN_H = MAP_ROWS * TILE_H   # 192
STATUS_H = 8                   # one row of the 8x8 status font at y=192 (0x4761: DX=0xC0)
TOTAL_H = SCREEN_H + STATUS_H  # 200: the whole Mode X screen
SCALE = 3
WIN_W, WIN_H = SCREEN_W * SCALE, TOTAL_H * SCALE
FPS = 60
SHOT_SPEED = 5
SHOT_LIFE = 40

# Joe sprite indices: 0-7 (even=left, odd=right)


def load_raw(fn):
    with open(os.path.join(BASE, fn), "rb") as f:
        return f.read()


def load_palette(fn):
    raw = load_raw(fn)
    return [(min(255, raw[i*3]*4), min(255, raw[i*3+1]*4), min(255, raw[i*3+2]*4)) for i in range(256)]


# Status bar font: GAME.EXE CS:0x31EC is a table of 128 glyph pointers, 8 bytes per glyph, one
# bit per pixel with bit 0 on the LEFT (0x350C shifts the row out plane by plane), drawn 8 rows
# tall. Characters 32-127 copied verbatim.
STATUS_FONT = bytes.fromhex("0000000000000000000c0c0c0c000c0c000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0c0600000000000000000000000000000c0c0000000000000000007f63636363637f0060606060606060007f60607f03037f007f60607f60607f006363637f606060007f03037f60607f007f03037f63637f007f606060606060007f63637f63637f007f63637f60607f00000c0c000c0c000000000000000000000000000000000000000000000000000000000000000000003e633018000c0c0000000000000000003e63637f636363003f63633f63633f003e63030303633f003f63636363633f007f03031f03037f007f03031f030303003e63030373637e006363637f636363000c0c0c0c0c0c0c006060606060633e0063331b0f1b3363000303030303037f0063777f6b6363630063676f7b736363003e63636363633e003e63633f030303003e6363637b337e003f63633f1b3363003e63033e60633e003f0c0c0c0c0c0c006363636363633e0063636363361c08006363636b7f77630063361c081c36630033331e0c0c0c0c007f6030180c067f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
_glyph_cache = {}


def draw_text8(surface, x, y, text, color):
    """Draw `text` in the original 8x8 status font (0x35A0 draws a string 8 px per glyph)."""
    for ch in text:
        c = ord(ch) if 32 <= ord(ch) < 128 else 32
        key = (c, color)
        glyph = _glyph_cache.get(key)
        if glyph is None:
            glyph = pygame.Surface((8, 8))
            glyph.set_colorkey((0, 0, 0))
            rows = STATUS_FONT[(c - 32) * 8:(c - 32) * 8 + 8]
            for r, bits in enumerate(rows):
                for b in range(8):
                    if bits & (1 << b):
                        glyph.set_at((b, r), color)
            _glyph_cache[key] = glyph
        surface.blit(glyph, (x, y))
        x += 8


def decode_sprites(sp_data, pal):
    """Decode all sprites from SP00.DAT into pygame Surfaces."""
    first_off = struct.unpack_from('<H', sp_data, 0)[0]
    num_sprites = first_off // 2
    offsets = [struct.unpack_from('<H', sp_data, i*2)[0] for i in range(num_sprites)]
    sprites = []

    for idx in range(num_sprites):
        start = offsets[idx]
        end = offsets[idx + 1] if idx + 1 < num_sprites else len(sp_data)
        if start + 4 > len(sp_data):
            sprites.append({"surf": pygame.Surface((1, 1), pygame.SRCALPHA),
                            "x_off": 0, "y_off": 0, "x_end": 0, "y_end": 0, "w": 1, "h": 1})
            continue
        x_off, y_off, x_end, y_end = struct.unpack_from('4b', sp_data, start)
        w = x_end - x_off + 1
        h = y_end - y_off + 1

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pos = start + 4
        cur_x, cur_y = 0, 0

        try:
            while pos < end - 1:
                if sp_data[pos] == 0 and sp_data[pos+1] == 0:
                    break
                cur_x += struct.unpack_from('b', sp_data, pos)[0]; pos += 1
                cur_y += struct.unpack_from('b', sp_data, pos)[0]; pos += 1
                col_x, base_y = cur_x, cur_y
                count = sp_data[pos]; pos += 1
                for i in range(count):
                    ci = sp_data[pos]; pos += 1
                    sx, sy = col_x - x_off, base_y + i - y_off
                    if 0 <= sx < w and 0 <= sy < h:
                        surf.set_at((sx, sy), (*pal[ci], 255))
                while pos < end - 1:
                    if sp_data[pos] == 0 and sp_data[pos+1] == 0:
                        pos += 2; break
                    col_x += sp_data[pos]; pos += 1
                    base_y += struct.unpack_from('b', sp_data, pos)[0]; pos += 1
                    count = sp_data[pos]; pos += 1
                    for i in range(count):
                        ci = sp_data[pos]; pos += 1
                        sx, sy = col_x - x_off, base_y + i - y_off
                        if 0 <= sx < w and 0 <= sy < h:
                            surf.set_at((sx, sy), (*pal[ci], 255))
        except (IndexError, struct.error):
            pass

        sprites.append({"surf": surf, "x_off": x_off, "y_off": y_off,
                         "x_end": x_end, "y_end": y_end, "w": w, "h": h})
    return sprites


HALF_W, HALF_H = SCREEN_W // 2, SCREEN_H // 2  # 160x96 — original uses half-res collision

# Joe's collision shape from SH00.DAT entry 0 — 14w x 15h half-res rounded rectangle
# (row_offset, col_offset, count) relative to player's half-res position
JOE_COL_SHAPE = (
    (-7, -2, 6), (-6, -4, 10), (-5, -5, 12), (-4, -5, 12),
    (-3, -6, 14), (-2, -6, 14), (-1, -6, 14), ( 0, -6, 14),
    ( 1, -6, 14), ( 2, -6, 14), ( 3, -6, 14), ( 4, -6, 14),
    ( 5, -6, 14), ( 6, -6, 14), ( 7, -6, 14),
)


def build_collision_bitmap(blk, map_data, room_idx, num_tiles):
    """Build a 160x96 half-res collision bitmap using CB00.DAT shapes.
    Each flag value (0-63) indexes an 8x6 collision shape."""
    cbm = bytearray(HALF_W * HALF_H)
    pipe_floors = []
    pipe_ceilings = []
    if room_idx < 0 or room_idx * ROOM_BYTES + ROOM_BYTES > len(map_data):
        return cbm, pipe_floors, pipe_ceilings
    base = room_idx * ROOM_BYTES
    bg_words = struct.unpack_from('<320H', map_data, base)
    cb_data = load_raw("CB00.DAT")
    for i, w in enumerate(bg_words):
        if w == 0xFFFF:
            continue
        flags = (w >> 10) & 0x3F
        if flags == 0:
            continue
        # Invisible pipe floor/ceiling barriers
        if flags == 8:
            col, row = i % MAP_COLS, i // MAP_COLS
            pipe_floors.append((col * TILE_W, col * TILE_W + TILE_W, row * TILE_H + TILE_H - 4))
        if flags == 9:
            col, row = i % MAP_COLS, i // MAP_COLS
            pipe_ceilings.append((col * TILE_W, col * TILE_W + TILE_W, row * TILE_H))
        # Copy collision shape from CB00.DAT into half-res bitmap
        shape_off = flags * 48
        if shape_off + 48 > len(cb_data):
            continue
        col, row = i % MAP_COLS, i // MAP_COLS
        hx0 = col * (TILE_W // 2)
        hy0 = row * (TILE_H // 2)
        for sy in range(6):
            hy = hy0 + sy
            if hy >= HALF_H:
                continue
            for sx in range(8):
                hx = hx0 + sx
                if hx >= HALF_W:
                    continue
                if cb_data[shape_off + sy * 8 + sx] != 0:
                    cbm[hy * HALF_W + hx] = 1
    return cbm, pipe_floors, pipe_ceilings


def sprite_hits_bg(cbm, sp, ox, oy):
    """Check if any opaque pixel of sprite overlaps a solid pixel in half-res cbm."""
    mask = sp.get("mask")
    if not mask:
        return False
    x_off, y_off = sp["x_off"], sp["y_off"]
    bx = int(ox) + x_off
    by = int(oy) + y_off
    for row_idx, row in enumerate(mask):
        if not row:
            continue
        sy = (by + row_idx) // 2
        if sy < 0 or sy >= HALF_H:
            continue
        row_base = sy * HALF_W
        for sx_rel in row:
            sx = (bx + sx_rel) // 2
            if 0 <= sx < HALF_W and cbm[row_base + sx]:
                return True
    return False


def joe_hits_bg(cbm, ox, oy):
    """Check Joe's collision using SH00.DAT shape (14x15 half-res rounded rect).
    Matches original GAME.EXE CHECK_COLLISION at 0x043C.
    ox, oy are screen coordinates (0-320, 0-192)."""
    hx = int(ox) >> 1
    hy = int(oy) >> 1
    for row_off, col_off, count in JOE_COL_SHAPE:
        sy = hy + row_off
        if sy < 0 or sy >= HALF_H:
            continue
        row_base = sy * HALF_W
        sx_start = hx + col_off
        for c in range(count):
            sx = sx_start + c
            if 0 <= sx < HALF_W and cbm[row_base + sx]:
                return True
    return False

# ---------------------------------------------------------------------------
# Collision bitmap engine — faithful port of GAME.EXE 0x2ED8 / 0x2F11 / 0x2F8A / 0x2FCB
# ---------------------------------------------------------------------------
TICKS_PER_FRAME = 1165.2 / FPS   # original 1193182/1024 Hz object counter, spread over our frames

# Collision byte types. CHECK_COLLISION histograms the bytes under a shape by type:
#   1  = solid (walls, doors, fields, cages, plates, sentry)
#   6  = ball or bird (written with BL=6)
#   14 = Joe (written with BL=0x0E at 0x0CC4 / 0x0E3E)
CT_WALL, CT_ENEMY, CT_JOE = 1, 6, 14

_SH_DATA = load_raw("SH00.DAT")
_SH_CACHE = {}


def sh_shape(idx):
    """Decode SH00.DAT entry idx into (row_off, col_off, count) half-res scan segments."""
    if idx in _SH_CACHE:
        return _SH_CACHE[idx]
    off = struct.unpack_from('<H', _SH_DATA, idx * 2)[0]
    pos, di, scans = off, 0, []
    while pos + 2 < len(_SH_DATA):
        delta = struct.unpack_from('<h', _SH_DATA, pos)[0]
        pos += 2
        count = _SH_DATA[pos]
        pos += 1
        if count == 0:
            break
        di += delta
        row = round(di / 192)
        scans.append((row, di - row * 192, count))
        di += count
    _SH_CACHE[idx] = tuple(scans)
    return _SH_CACHE[idx]


def cb_check(cbm, shape, hx, hy, filt=0):
    """CHECK_COLLISION core (0x2F11). Counts the bytes under `shape` at half-res (hx, hy)
    that differ from `filt`, bucketed by type → (total, hist[16]).
    filt=0  → "is anything solid here" (movement checks)
    filt=own_type → "has anything intruded on my own footprint" (Joe uses 14, balls/birds 6).
    Bytes outside the bitmap are skipped (the original's padding is written and read alike)."""
    hist = [0] * 16
    total = 0
    for row_off, col_off, count in sh_shape(shape):
        sy = hy + row_off
        if sy < 0 or sy >= HALF_H:
            continue
        base = sy * HALF_W
        x0 = hx + col_off
        for sx in range(max(0, x0), min(HALF_W, x0 + count)):
            v = cbm[base + sx]
            if v != filt:
                hist[v & 15] += 1
                total += 1
    return total, hist


def cb_write(cbm, shape, hx, hy, val):
    """DRAW_COLLISION core (0x2ED8): fill the shape with collision type `val`."""
    for row_off, col_off, count in sh_shape(shape):
        sy = hy + row_off
        if sy < 0 or sy >= HALF_H:
            continue
        base = sy * HALF_W
        x0 = hx + col_off
        for sx in range(max(0, x0), min(HALF_W, x0 + count)):
            cbm[base + sx] = val


def cb_restore(cbm, backup, shape, hx, hy):
    """DRAW_VISUAL core (0x2F8A): restore the shape area from the room's backup bitmap.
    The original relies on the side effect: it wipes any object marker in the area
    (Joe's 14, a ball's 6). This is how fields, lasers, orbs and enemies kill Joe."""
    if backup is None:
        return
    for row_off, col_off, count in sh_shape(shape):
        sy = hy + row_off
        if sy < 0 or sy >= HALF_H:
            continue
        base = sy * HALF_W
        x0 = hx + col_off
        for sx in range(max(0, x0), min(HALF_W, x0 + count)):
            cbm[base + sx] = backup[base + sx]


def cb_restore_if(cbm, backup, shape, hx, hy, val):
    """0x048C → 0x2FCB: restore from backup only where the byte equals `val`
    (an object erasing its own marker without disturbing anything else)."""
    if backup is None:
        return
    for row_off, col_off, count in sh_shape(shape):
        sy = hy + row_off
        if sy < 0 or sy >= HALF_H:
            continue
        base = sy * HALF_W
        x0 = hx + col_off
        for sx in range(max(0, x0), min(HALF_W, x0 + count)):
            if cbm[base + sx] == val:
                cbm[base + sx] = backup[base + sx]


# Joe's collision handler (0x0CFB-0x0D5B): 9 positions tried before giving up and dying (crush).


def in_room(x, y):
    """ROOM_TRANSITION (0x0521) exit test for moving objects: leaving the 320x192 area."""
    return 0 <= x < SCREEN_W and 0 <= y < SCREEN_H


# ---------------------------------------------------------------------------
# Enemy / generator entities — ports of the GAME.EXE object handlers.
# Each runs on the original tick scheduler: update() is called whenever game.tick has
# passed next_time, then next_time += interval (handlers may also adjust next_time).
# ---------------------------------------------------------------------------
class Entity:
    """Object slot. `visible` mirrors slot byte +1: 1 live, 2 transit clone (room change
    simulation), 0 dormant (hidden in some room, waiting to be activated). `mobile` objects
    (slot state 3: balls, birds, orbs) cross room edges and survive room changes; everything
    else is destroyed when Joe leaves the room."""
    interval = 20
    mobile = False
    keeps_slot = False   # non-mobile, but its HIDE path (AX=3) keeps the slot (state 2) instead
                         # of destroying it, so it waits dormant in its room (the sentry)

    def __init__(self, x, y, tick):
        self.x, self.y = int(x), int(y)
        self.next_time = tick
        self.alive = True
        self.sprite_idx = None
        self.visible = 1
        self.room = None

    def activate(self, g):
        """AX=1: (re)write collision and become live."""
        self.visible = 1

    def hide(self, g):
        """AX=3 for a keeps_slot object: erase its collision in the room being left."""

    def destroy(self, g):
        """AX=5: side effects of the slot being freed (the stale sweep 0x0A13)."""

    def cross(self, g, nx, ny):
        """0x0521 exit test for a move to (nx, ny). Inside the room → False. Otherwise the object
        moves into the neighbouring room at the wrapped position and goes dormant there (the
        handlers jump to their HIDE path); if no room lies that way it is gone for good."""
        ex = g.exit_room(self.room, nx, ny)
        if ex is None:
            return False
        new_room, wx, wy = ex
        if new_room is None:
            self.alive = False
        else:
            self.room, self.x, self.y = new_room, wx, wy
            g.make_dormant(self)
        return True

    def update(self, g):
        pass

    def draw(self, surface, sprites, frame):
        if self.sprite_idx is not None and self.sprite_idx < len(sprites):
            sp = sprites[self.sprite_idx]
            surface.blit(sp["surf"], (self.x + sp["x_off"], self.y + sp["y_off"]))


class EnemyExplosion(Entity):
    """Handler 0x11BA: glow explosion (sprites 33-38) at a dead enemy's position. The enemy's
    last sprite ("ghost") stays visible until the explosion advances to sprite 37."""
    interval = 71

    def __init__(self, g, x, y, ghost):
        super().__init__(x, y, g.tick)
        self.idx = 33        # [DI+0x1C]
        self.shown = None
        self.ghost = ghost
        play_sound(SND_EXPLOSION)                # 0x120A

    def update(self, g):
        if self.idx == 39:
            self.alive = False
            return
        self.shown = self.idx
        self.idx += 1
        if self.idx == 37:
            self.ghost = None   # FREE_SPRITE of inherited handle at 0x126F

    def draw(self, surface, sprites, frame):          # enemy layer: the ghost
        if self.ghost is not None:
            sp = sprites[self.ghost]
            surface.blit(sp["surf"], (self.x + sp["x_off"], self.y + sp["y_off"]))

    def draw_top(self, surface, sprites):              # top layer: the explosion
        if self.shown is not None:
            sp = sprites[self.shown]
            surface.blit(sp["surf"], (self.x + sp["x_off"], self.y + sp["y_off"]))


class Sentry(Entity):
    """Object type 14, handler 0x22EF. Pink UFO (sprites 39/40/41 = moving left / hovering /
    moving right) that chases Joe with Joe's own jetpack physics (gravity 41, thrust 82,
    velocity clamped to ±1000 thousandths/update). Collision shapes 19/20/21 written as type 1.
    It never checks for intrusions, so it cannot be killed. Two glow sprites (50-53) trail it.
    Init (0x2317) is skipped when its variable is 0 and otherwise CLEARS the variable (0x2335);
    slot state is 2, not 3, and it never calls ROOM_TRANSITION, so it does not follow Joe out.
    Its HIDE path (0x237B, room change) erases it and sets visible 0 but keeps the slot, so the
    main loop (0x06F8) re-activates it where it was if Joe is back before the stale sweep
    (0x0A13, ~6 s) destroys it; DESTROY (0x23A0) sets the variable back to 0xFF, so the next
    visit spawns a fresh one at its tile."""
    interval = 27
    keeps_slot = True

    def __init__(self, g, x, y, var=0):
        super().__init__(x, y, g.tick)
        self.facing = 1    # [DI+0x1C]
        self.vy = 0        # [DI+0x16]
        self.frac = 0      # [DI+0x18]
        self.thrust = 0    # [DI+0x1D]: 0 idle, 2 thrusting (selects glow sprite 50/51 vs 52/53)
        self.var = var     # [DI+0x1F]
        self.room = g.current_room
        g.switch_state[var] = 0                                              # 0x2335
        self.activate(g)

    def activate(self, g):
        self.visible = 1
        cb_write(g.cbm, 19 + self.facing, self.x >> 1, self.y >> 1, CT_WALL)   # 0x23EA

    def hide(self, g):
        cb_restore(g.cbm, g.cbm_bak, 19 + self.facing, self.x >> 1, self.y >> 1)   # 0x2393

    def destroy(self, g):
        g.switch_state[self.var] = 0xFF                                      # 0x23A5

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        cb_restore(cbm, backup, 19 + self.facing, x >> 1, y >> 1)   # DRAW_VISUAL old footprint
        self.thrust = 0
        tx, ty = int(g.player.x), int(g.player.y)
        # Horizontal: step toward Joe unless within 8px (0x240F-0x243C)
        diff = x - tx
        if -8 <= diff < 8:
            d = 1
        elif diff < 0:
            d = 2
        else:
            d = 0
        nx = x + d - 1
        total, hist = cb_check(cbm, 19 + d, nx >> 1, y >> 1, 0)
        if total == 0:
            self.facing = d
        elif total != hist[CT_JOE]:
            nx = x              # blocked by something other than Joe
        # Vertical: gravity, thrust when level with or below Joe (0x2462-0x24B6)
        vy = self.vy + 41
        if y >= ty:
            vy -= 82
            self.thrust = 2
        vy = max(-1000, min(1000, vy))
        self.vy = vy
        frac = self.frac + vy
        ny = y
        if frac < 0:
            frac += 1000
            ny -= 1
        elif frac >= 1000:
            frac -= 1000
            ny += 1
        self.frac = frac
        total, hist = cb_check(cbm, 19 + self.facing, nx >> 1, ny >> 1, 0)
        if total != hist[CT_JOE]:
            ny = y
            self.vy = 0
        self.x, self.y = nx, ny
        cb_write(cbm, 19 + self.facing, nx >> 1, ny >> 1, CT_WALL)

    def draw(self, surface, sprites, frame):
        x, y = self.x, self.y
        glow_a = sprites[50 + (frame & 1) + self.thrust]            # under the body
        surface.blit(glow_a["surf"], (x + glow_a["x_off"], y + 10 + glow_a["y_off"]))
        glow_b = sprites[52 + ((~frame) & 1)]                       # trailing behind
        gx = x - (17 * self.facing - 17)
        surface.blit(glow_b["surf"], (gx + glow_b["x_off"], y - 2 + glow_b["y_off"]))
        body = sprites[39 + self.facing]
        surface.blit(body["surf"], (x + body["x_off"], y + body["y_off"]))


class Ball(Entity):
    """Handler 0x15A2 (spawned by ball_generator). Electric ball (sprites 42-45) that walks a
    Bresenham line toward Joe, re-aiming every 25 updates. Writes shape 16 as type 6 and
    restores the surrounding ring (shape 17) every update — touching it kills Joe. It explodes
    when anything (a shot's erase, Joe's marker, another ball's ring) disturbs its own bytes."""
    interval = 16
    mobile = True

    @staticmethod
    def can_spawn(g, x, y):
        return cb_check(g.cbm, 2, x >> 1, y >> 1, 0)[0] == 0      # init check at 0x15C8

    def __init__(self, g, x, y):
        super().__init__(x, y, g.tick)
        self.retarget = 1        # [DI+0x1E]
        self.err = 0             # [DI+0x1A]
        self.frame = 0           # [DI+0x1C]
        self.frame_acc = 0       # [DI+0x1D]
        self.sx = self.sy = 1    # [DI+0x16] / [DI+0x18]
        self.adx = self.ady = 0  # [DI+0x10] / [DI+0x12]
        self.phase = 0           # [DI+0x1F]
        self.sprite_idx = 42
        self.room = g.current_room
        self.activate(g)

    def activate(self, g):
        self.visible = 1
        cb_write(g.cbm, 16, self.x >> 1, self.y >> 1, CT_ENEMY)   # activate (0x1657)

    def explode(self, g, cbm, backup, hx, hy):
        """0x176A: only a live ball in Joe's room leaves an explosion; clones/dormant just die."""
        cb_restore_if(cbm, backup, 16, hx, hy, CT_ENEMY)
        if self.visible == 1 and self.room == g.current_room:
            g.entities.append(EnemyExplosion(g, self.x, self.y, self.sprite_idx))
        self.alive = False

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        hx, hy = x >> 1, y >> 1
        if self.visible == 1:                            # 0x1666: clones keep their heading
            self.retarget -= 1
        if self.visible == 1 and self.retarget == 0:
            self.retarget = 25
            self.sx = self.sy = 1
            if self.room == g.current_room:              # 0x1688: else aim at (0,0)
                cx = int(g.player.x) - x
                cy = int(g.player.y) - y
            else:
                cx, cy = -x, -y
            if cx <= 0:
                cx = -cx
                self.sx = -1
            if cy <= 0:
                cy = -cy
                self.sy = -1
            self.adx, self.ady = cx, cy
        total, hist = cb_check(cbm, 16, hx, hy, CT_ENEMY)
        if total:                                        # something intruded → explode (0x176A)
            self.explode(g, cbm, backup, hx, hy)
            return
        cb_restore_if(cbm, backup, 16, hx, hy, CT_ENEMY)
        nx, ny = x, y
        if self.err <= 0:
            self.err += self.ady
            nx += self.sx
            if self.phase:
                self.phase = 0
                self.next_time -= 7
        else:
            self.err -= self.adx
            ny += self.sy
            self.next_time += 3
            if not self.phase:
                self.phase = 1
                self.next_time -= 7
        if self.cross(g, nx, ny):                        # 0x1716: left the room → dormant
            return
        total, hist = cb_check(cbm, 16, nx >> 1, ny >> 1, 0)
        if total:
            nx, ny = x, y
            self.retarget = 1
        self.x, self.y = nx, ny
        hx, hy = nx >> 1, ny >> 1
        cb_restore(cbm, backup, 17, hx, hy)
        cb_write(cbm, 16, hx, hy, CT_ENEMY)
        self.frame_acc += 22
        if self.frame_acc >= 256:
            self.frame_acc -= 256
            self.frame = (self.frame + 1) & 3
        self.sprite_idx = 42 + self.frame


class Orb(Entity):
    """Handler 0x25C1 (spawned by orb_generator). Aimed once at Joe on spawn, flies a straight
    Bresenham line (sprite 50 at spawn, 51 in flight). Explodes on anything solid, restoring the
    backup under its 5x3 shape (22) — which wipes Joe's marker and kills him."""
    interval = 9
    mobile = True

    @staticmethod
    def can_spawn(g, x, y):
        return cb_check(g.cbm, 2, x >> 1, y >> 1, 0)[0] == 0      # init check at 0x2627

    def __init__(self, g, x, y):
        super().__init__(x, y, g.tick + 50)
        self.err = 0
        self.phase = 0
        self.sx = self.sy = 1
        cx = int(g.player.x) - x
        cy = int(g.player.y) - y
        if cx <= 0:
            cx = -cx
            self.sx = -1
        if cy <= 0:
            cy = -cy
            self.sy = -1
        self.adx, self.ady = cx, cy
        self.sprite_idx = 50
        self.room = g.current_room

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        nx, ny = x, y
        if self.err <= 0:
            self.err += self.ady
            nx += self.sx
            if self.phase:
                self.phase = 0
                self.next_time -= 3
        else:
            self.err -= self.adx
            ny += self.sy
            self.next_time += 1
            if not self.phase:
                self.phase = 1
                self.next_time -= 3
        if self.cross(g, nx, ny):                        # 0x26EE: left the room → dormant
            return
        total, hist = cb_check(cbm, 22, nx >> 1, ny >> 1, 0)
        if total == 0:
            self.x, self.y = nx, ny
            self.sprite_idx = 51
        else:
            cb_restore(cbm, backup, 22, nx >> 1, ny >> 1)
            if self.visible == 1 and self.room == g.current_room:    # 0x270F
                g.entities.append(EnemyExplosion(g, x, y, self.sprite_idx))
            self.alive = False


class Bird(Entity):
    """Handler 0x199A (spawned by bird_generator). Red bird (sprites 29-32) rising 1px per
    update. When Joe's marker is found in the 1-wide column above it (shape 15) it fires a
    laser (sprite 25/26 flickering, 89px tall) for 10 updates; the DRAW_VISUAL of that column
    wipes Joe's marker and kills him. Vanishes silently on hitting a ceiling (type 1)."""
    interval = 20
    mobile = True

    @staticmethod
    def can_spawn(g, x, y):
        return cb_check(g.cbm, 2, x >> 1, y >> 1, 0)[0] == 0      # init check at 0x19C0

    def __init__(self, g, x, y):
        super().__init__(x, y, g.tick)
        self.sprite_idx = 29     # [DI+0x1C]
        self.frame_acc = 0       # [DI+0x1D]
        self.laser = 0           # [DI+0x16]
        self.room = g.current_room
        self.activate(g)

    def activate(self, g):
        self.visible = 1
        self.laser = 0
        cb_write(g.cbm, 2, self.x >> 1, self.y >> 1, CT_ENEMY)   # activate (0x1A54)

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        hx, hy = x >> 1, y >> 1
        if self.laser == 0 and self.room == g.current_room:      # 0x1A75
            total, hist = cb_check(cbm, 15, hx, hy, 0)
            if hist[CT_JOE]:
                self.laser = 10
                cb_restore(cbm, backup, 15, hx, hy)
        total, hist = cb_check(cbm, 2, hx, hy, CT_ENEMY)
        if total:                                        # intruded → explode (0x1B42)
            cb_restore_if(cbm, backup, 2, hx, hy, CT_ENEMY)
            if self.visible == 1 and self.room == g.current_room:
                g.entities.append(EnemyExplosion(g, x, y, self.sprite_idx))
            self.alive = False
            return
        cb_restore_if(cbm, backup, 2, hx, hy, CT_ENEMY)
        ny = y - 1
        if self.cross(g, x, ny):                         # 0x1ACC: rose out of the room → dormant
            return
        total, hist = cb_check(cbm, 2, hx, ny >> 1, 0)
        if total:
            if hist[CT_WALL]:
                self.alive = False                       # hit ceiling: hide + destroy (0x1B77)
                return
            ny = y
        self.y = ny
        cb_write(cbm, 2, hx, ny >> 1, CT_ENEMY)
        self.frame_acc += 0x2A
        if self.frame_acc >= 256:
            self.frame_acc -= 256
            self.sprite_idx += 1
            if self.sprite_idx >= 33:
                self.sprite_idx = 29
        if self.laser:
            self.laser -= 1

    def draw_laser(self, surface, sprites, frame):
        if self.laser:
            sp = sprites[25 + (frame & 1)]
            surface.blit(sp["surf"], (self.x + sp["x_off"], self.y + sp["y_off"]))


class Generator(Entity):
    """Common base for the three generators (object types 11/12/20). Position is the tile's
    top-left + (15, 11), i.e. the center of the 2x2 tile block the generator occupies."""
    FRAMES = ()

    def __init__(self, g, tile):
        self.col, self.row = tile % MAP_COLS, tile // MAP_COLS
        super().__init__(self.col * TILE_W + 15, self.row * TILE_H + 11, g.tick)
        self.frame = None

    def draw(self, surface, sprites, frame):
        pass

    def draw_tiles(self, surface, tile_surfs):
        """MODIFY_SCREEN_MAP (0x04D2): background-layer 2x2 tile replacement, drawn opaque."""
        if self.frame is None:
            return
        tiles = self.FRAMES[self.frame]
        for i, (dc, dr) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
            ti = tiles[i]
            if ti < len(tile_surfs):
                surface.blit(tile_surfs[ti], ((self.col + dc) * TILE_W, (self.row + dr) * TILE_H))


class SensorSwitch(Entity):
    """Object type 18, handler 0x2061. A floor pad. Every 0x80 ticks (first run at init, then
    random(0x80) later) it CHECKs shape 4 with BL=1; if Joe's marker is inside, it copies
    switch_state[sw2] into switch_state[sw1] (0x20F8-0x2104). Its tile is written straight into
    the background screen map (0x2137): 0x116 + (sw1 set ? 1 : 0) + (sw2 set ? 0x14 : 0)
    + (touching ? (sw1 set ? 0x14 : 0x28) : 0)."""
    interval = 0x80

    def __init__(self, g, obj):
        params = obj["params"]
        tile = params[0]
        super().__init__(obj["x"], obj["y"], g.tick)
        self.col, self.row = tile % MAP_COLS, tile // MAP_COLS
        self.sw1 = params[1] if len(params) > 1 else 0
        self.sw2 = params[2] if len(params) > 2 else 0
        self.tile = 0x116
        self.next_time = g.tick + random.randrange(0x80)      # 0x20A4: random(0x80) + counter
        self.update(g)                                        # 0x20CB: one update at init

    def update(self, g):
        total, hist = cb_check(g.cbm, 4, self.x >> 1, self.y >> 1, CT_WALL)
        touching = hist[CT_JOE] != 0                          # [0x3175]
        ss = g.switch_state
        if touching:
            ss[self.sw1] = ss[self.sw2]
        tile, bump = 0x116, 0x28
        if ss[self.sw1]:
            tile, bump = tile + 1, 0x14
        if ss[self.sw2]:
            tile += 0x14
        if touching:
            tile += bump
        self.tile = tile

    def draw(self, surface, sprites, frame):
        pass

    def draw_tiles(self, surface, tile_surfs):
        if self.tile < len(tile_surfs):
            surface.blit(tile_surfs[self.tile], (self.col * TILE_W, self.row * TILE_H))


class Teleporter(Entity):
    """Object type 19, handler 0x2219. Every 0x3E ticks (first after random(0x3E)) it CHECKs
    shape 13 (the two side columns of the teleporter area, the cage-wall shape) at (x, y) and
    shape 4 (the trigger) at (x+16, y+12), looking for Joe's marker bytes. [DI+0x1D] is a
    BLOCKED flag, set at init:
      not in trigger → blocked = not on the side columns   (crossing a side clears it)
      in trigger, clear of the sides, not blocked → teleport, blocked = 1
    So Joe must walk in through a side; materialising at the centre after a beam-in, or
    dropping onto it from above, never fires it. That is the original's bounce-back guard."""
    interval = 0x3E

    def __init__(self, g, obj):
        super().__init__(obj["x"], obj["y"], g.tick)
        self.obj = obj
        self.blocked = True                                   # 0x2289
        self.next_time = g.tick + random.randrange(0x3E)      # 0x2262

    def update(self, g):
        hx, hy = self.x >> 1, self.y >> 1
        on_side = cb_check(g.cbm, 13, hx, hy, 0)[1][CT_JOE] != 0
        in_trigger = cb_check(g.cbm, 4, hx + 8, hy + 6, 0)[1][CT_JOE] != 0
        if not in_trigger:
            self.blocked = not on_side                        # 0x22E2
        elif not on_side and not self.blocked:
            self.blocked = True                               # 0x22C1
            g.start_teleport(self.obj)                        # 0x22C5


class BallGen(Generator):
    """Object type 12, handler 0x14F5. Counts down 4-7 updates (then 8 between balls); frames
    1-3 of table DS:0x31BF play on the last three counts, a ball spawns at zero if the spot
    (shape 16) is clear, otherwise it retries next update."""
    interval = 257
    FRAMES = ((506, 507, 526, 527), (508, 509, 528, 529), (546, 547, 566, 567), (548, 549, 568, 569))

    def __init__(self, g, tile):
        super().__init__(g, tile)
        self.countdown = random.randrange(4) + 4

    def update(self, g):
        c = self.countdown - 1
        if c == 0:
            if cb_check(g.cbm, 16, self.x >> 1, self.y >> 1, 0)[0]:
                return                                  # blocked: countdown not stored, retry
            if Ball.can_spawn(g, self.x, self.y):
                g.entities.append(Ball(g, self.x, self.y))
            self.countdown = 8
            self.frame = 0
        else:
            self.countdown = c
            if c <= 3:
                self.frame = 4 - c


class OrbGen(Generator):
    """Object type 20, handler 0x2526. Counts down 4-17 updates (then 18 between orbs); the
    background tiles pulse through table DS:0x3233 indexed by the countdown value."""
    interval = 43
    _A, _B, _C, _D, _E, _F = ((622, 623, 642, 643), (624, 625, 644, 645), (626, 627, 646, 647),
                              (628, 629, 648, 649), (630, 631, 650, 651), (632, 633, 652, 653))
    FRAMES = (_F, _E, _D, _F, _E, _D, _C, _B, _A, _B, _C, _B, _A, _B, _C, _B, _A, _B)

    def __init__(self, g, tile):
        super().__init__(g, tile)
        self.countdown = random.randrange(14) + 4

    def update(self, g):
        c = self.countdown - 1
        if c == 0:
            if Orb.can_spawn(g, self.x, self.y):
                g.entities.append(Orb(g, self.x, self.y))
            self.countdown = 18
            self.frame = 0
        else:
            self.countdown = c
            self.frame = c


class BirdGen(Generator):
    """Object type 11, handler 0x1488. Releases a bird every 1511 ticks (~1.3s), first one
    after a random delay. No tile animation."""
    interval = 1511

    def __init__(self, g, tile):
        super().__init__(g, tile)
        self.next_time = g.tick + random.randrange(1511)

    def update(self, g):
        if Bird.can_spawn(g, self.x, self.y):
            g.entities.append(Bird(g, self.x, self.y))



# ---------------------------------------------------------------------------------------------
# Sound — GAME.EXE's sample mixer, decoded from the binary (see RESUME_STATE.md, "Sound")
#
#   DS00.DAT      = the five DRAW/LIST samples, converted to 6-bit (0-63, silence 0x20) and
#                   padded to 256-byte blocks, behind a table of paragraph (16-byte) offsets.
#   PLAY_SOUND    = 0x02DC: AX = sound id → ES:SI/CX from that table → INT 62h DX=4.
#   START_SOUND   = 0x42B3 (INT 62h DX=4): takes the mixer channel with the fewest blocks left.
#   SOUND_MIXER   = 0x4308: every 32 counter ticks sums the 4 channels (silence = 0x20 each)
#                   into a 256-sample buffer, maps the sum through a table that is linear for
#                   ±31 around 0x80 and clips beyond, then the ISR plays one sample per PIT
#                   interrupt at 1193182/128 Hz (the speaker driver runs at twice that and
#                   repeats each sample, so every driver sounds the same).
# Drivers (GAME.EXE N): 0/1 no sound, 2 internal speaker (default), 3 Covox Speech Thing,
# 4 Covox Sound Master II. There is no Sound Blaster code.
# ---------------------------------------------------------------------------------------------
SOUND_RATE = 1193182 / 128                     # 9321.7 Hz
SND_EXPLOSION, SND_SHOOT, SND_HELP, SND_TRANSPORTER, SND_THANKS = range(5)
SND_PICKUP, SND_TURRET = 5, 6                  # enhanced mode only: synthesized, not in DS00.DAT
SOUND_NAMES = ("explosion", "shoot", "help me", "transporter", "thank you", "pickup", "turret")


def synth_tone(freq, ms, amp=12):
    """A square wave as 6-bit mixer samples (centre 0x20) at the mixer's 9.3 kHz."""
    n = int(SOUND_RATE * ms / 1000)
    half = SOUND_RATE / freq / 2
    return bytes(0x20 + (amp if int(i / half) & 1 else -amp) for i in range(n))


def synth_pickup():
    """Three rising notes: the pack pickup."""
    return synth_tone(660, 45) + synth_tone(880, 45) + synth_tone(1320, 90)


def synth_turret():
    """A decaying noise burst: the turret firing."""
    rng = random.Random(7)
    n = int(SOUND_RATE * 0.07)
    return bytes(0x20 + int(rng.uniform(-1, 1) * 24 * (1 - i / n)) for i in range(n))
SOUND = None                                   # the active SoundBank, set by its constructor


def play_sound(idx):
    """PLAY_SOUND 0x02DC. Safe to call before the bank exists or when sound is off."""
    if SOUND is not None:
        SOUND.play(idx)


class SoundBank:
    """Loads DS00.DAT into pygame Sounds and reproduces the original's 4-channel mixer."""
    CHANNELS = 4

    def __init__(self, enabled=True):
        global SOUND
        SOUND = self
        self.enabled = False
        self.sounds = []
        self.history = []                      # ids played, newest last (for tests/debugging)
        self._ends = [0.0] * self.CHANNELS
        self.reason = "off by request (driver 0/1 or JPJ_SOUND=0)"
        if not enabled:
            return
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            info = pygame.mixer.get_init()
            self.reason = "mixer did not initialise"
        except pygame.error as e:
            info = None
            self.reason = f"mixer error: {e}"
        if not info:
            return
        self.reason = f"on, {info[0]} Hz via {pygame.mixer.get_init() and os.environ.get('SDL_AUDIODRIVER', 'default driver')}"
        rate, fmt, nch = info
        data = load_raw("DS00.DAT")
        offs = [struct.unpack_from('<H', data, 2 * i)[0] * 16 for i in range(6)]
        for i in range(5):
            self.sounds.append(self._convert(data[offs[i]:offs[i + 1]], rate, nch))
        for raw in (synth_pickup(), synth_turret()):           # SND_PICKUP, SND_TURRET
            self.sounds.append(self._convert(raw, rate, nch))
        pygame.mixer.set_num_channels(self.CHANNELS)
        self._channels = [pygame.mixer.Channel(i) for i in range(self.CHANNELS)]
        self.enabled = True

    @staticmethod
    def _convert(raw, rate, nch):
        """6-bit sample block → 16-bit PCM at the mixer rate. The output table (0x3EB6) is
        linear over ±31 around the 0x20 centre, so one full-scale sample spans the whole range;
        pygame's own clipping then stands in for the table's clip when channels overlap.
        Zero-order hold (sample repeat) keeps the hardware's 9.3 kHz character."""
        step = SOUND_RATE / rate
        n_out = int(len(raw) / step)
        out = array('h')
        scale = 32767 // 31
        for j in range(n_out):
            v = raw[int(j * step)] - 0x20
            v = -31 if v < -31 else (31 if v > 31 else v)
            out.append(v * scale)
        if nch == 2:
            st = array('h')
            for v in out:
                st.append(v); st.append(v)
            out = st
        return pygame.mixer.Sound(buffer=out.tobytes())

    def play(self, idx):
        self.history.append(idx)
        del self.history[:-64]
        if not self.enabled:
            return
        now = time.monotonic()
        # START_SOUND 0x42B3: the channel with the least time left is taken, finished or not.
        ch = min(range(self.CHANNELS), key=lambda c: max(0.0, self._ends[c] - now))
        snd = self.sounds[idx]
        self._channels[ch].play(snd)
        self._ends[ch] = now + snd.get_length()


def sound_enabled_from_args(argv):
    """Mirror the original's `GAME.EXE N`: 0 or 1 = no sound, anything else = sound on.
    JPJ_SOUND=0 in the environment also turns it off."""
    if os.environ.get("JPJ_SOUND", "1") == "0":
        return False
    return not (len(argv) > 1 and argv[1] in ("0", "1"))


class Explosion:
    """Wall-hit explosion from original GAME.EXE handler 0x1103.
    Static position, cycles sprites 33→34→35→36→37→38.
    Original: [DI+8]=0x47(71) tick interval, game loop consumes ~20 ticks/frame,
    so each sprite shows for ~71/20 ≈ 3.5 render frames."""
    FRAME_HOLD = 4  # ~71/20 ticks per render frame

    def __init__(self, x, y):
        self.x, self.y = int(x), int(y)
        self.sprite_idx = 33
        self.timer = self.FRAME_HOLD
        self.alive = True
        play_sound(SND_EXPLOSION)                # 0x1151

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.timer = self.FRAME_HOLD
            self.sprite_idx += 1
            if self.sprite_idx > 38:
                self.alive = False

    def draw(self, surface, sprites):
        if self.alive and self.sprite_idx < len(sprites):
            sp = sprites[self.sprite_idx]
            surface.blit(sp["surf"], (self.x + sp["x_off"], self.y + sp["y_off"]))


class Shot(Entity):
    """Handler 0x0FE3 (slot state 3: mobile). Init 0x1005: sprite 23+dir, speed dir*4-2 (±2),
    interval 15 ticks. Update 0x1084: x += speed; ROOM_TRANSITION (0x521) → crossing an edge
    parks it dormant in the next room (it keeps flying if Joe follows within ~6 s); then
    CHECK shape 1 (BL=0): nothing → fly on; no Joe bytes → DRAW_VISUAL shape 1 (this wipes a
    ball's/bird's bytes so it explodes on its next self-check) + Explosion 0x1103 if live and
    in Joe's room, die; Joe plus something else → vanish; only Joe → fly on."""
    interval = 15
    mobile = True

    def __init__(self, g, x, y, direction):
        super().__init__(x, y, g.tick)
        self.direction = direction                      # 0 left, 1 right ([0x23CD])
        self.speed = direction * 4 - 2
        self.sprite_idx = 23 + direction
        self.room = g.current_room

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        nx = self.x + self.speed
        if self.cross(g, nx, self.y):                   # 0x1095
            return
        self.x = nx
        hx, hy = nx >> 1, self.y >> 1
        total, hist = cb_check(cbm, 1, hx, hy, 0)
        if total == 0:
            return
        joe = hist[CT_JOE]
        if joe == 0:
            cb_restore(cbm, backup, 1, hx, hy)          # 0x10CC DRAW_VISUAL
            if self.visible == 1 and self.room == g.current_room:
                g.player.explosions.append(Explosion(nx, self.y))
            self.alive = False
        elif total != joe:
            self.alive = False                          # 0x10F9: Joe + other → vanish


# Joe's update (0x0CCC), run every JOE_INTERVAL ticks from the main loop (0x06BB).
JOE_INTERVAL = 10
JOE_GRAVITY = 41          # thousandths of a pixel per update, added every update (0x0DBF)
JOE_THRUST = 82           # subtracted while the thrust key is held (0x0D7F)
JOE_VMAX = 1000           # |vy| clamp (0x0DC2-0x0DD1): at most 1 px per update
FIRE_REPEAT = 0xC8        # ticks between shots while fire is held (0x0EBF)
FIRE_POSE = 0x28          # ticks the "firing" body sprite shows after a shot (0x0E78)
INP_THRUST, INP_RIGHT, INP_LEFT, INP_FIRE = 1, 2, 8, 0x10   # INT 62h DX=1 bits


class Player:
    """Joe. x/y is the centre of collision shape 0 (cols -6..7, rows -7..7 at half res)."""

    def __init__(self, x, y):
        self.x, self.y = int(x), int(y)
        self.vy = 0               # [0x23C5] thousandths of a pixel per update
        self.frac = 0             # [0x23C7] sub-pixel accumulator
        self.direction = 1        # [0x23CD] 0 left, 1 right
        self.last_fire = -10000   # [0x23CF]
        self.fire_released = True # [0x23D1]
        self.next_time = 0        # [0x23D2]
        self.body_sprite = 1
        self.flame_sprite = 9
        self.time = 0             # [0x23DA]: the level trailer's timer, set by set_level
        self.explosions = []
        self.pack = None          # enhanced mode: PACK_TWIN / PACK_SHIELD / None
        self.invuln_until = -1.0  # enhanced mode: tick until which a broken shield protects Joe

    # -- helpers --
    @staticmethod
    def _clear(cbm, x, y):
        return cb_check(cbm, 0, x >> 1, y >> 1, 0)[0] == 0

    def _unstick(self, cbm, x, y):
        """0x0CFB-0x0D5B: the nine positions tried when something has moved into Joe. The odd
        arithmetic ((v-2)|1, then +3) is the original's."""
        c1, c3 = (x - 2) | 1, ((x - 2) | 1) + 3
        r1, r3 = (y - 2) | 1, ((y - 2) | 1) + 3
        for px, py in ((x, y), (c1, y), (c3, y), (x, r1), (x, r3), (c1, r3), (c3, r3), (c3, r1), (c1, r1)):
            if self._clear(cbm, px, py):
                return px, py
        return None

    def step(self, g, inp):
        """One Joe update (0x0CCC-0x0F04)."""
        cbm = g.cbm = g.get_collision_bitmap(g.current_room)[0]
        backup = g.cbm_bak = g.cbm_backup[g.current_room]
        x, y = int(self.x), int(self.y)
        # 0x0CCC: with last update's marker still in place, anything under Joe that is neither
        # his marker nor a wall killed him; then the marker is lifted.
        g.joe_check_and_unmark(cbm, backup)
        if g.death is not None:
            return
        pos = self._unstick(cbm, x, y)                   # 0x0CFB crush check
        if pos is None:
            pos = g.shield_knockback(x, y)               # enhanced mode: shield / invulnerable
        if pos is None:
            if os.environ.get("JPJ_DEBUG"):
                print(f"CRUSHED at ({x},{y}) room {g.current_room}")
            g.start_death()
            return
        x, y = pos
        self.x, self.y = x, y                            # 0x0D5E
        y0 = y
        vy = self.vy
        if inp & INP_THRUST:
            vy -= JOE_THRUST
        nx, ny = x, y
        if inp & (INP_RIGHT | INP_LEFT):                 # 0x0D82: ±1 px, both keys cancel
            if inp & INP_RIGHT:
                nx += 1
            if inp & INP_LEFT:
                nx -= 1
            if not self._clear(cbm, nx, ny):             # 0x0D9C: step up 1 (odd) or down 2
                ty = (ny - 2) | 1
                if self._clear(cbm, nx, ty):
                    ny = ty
                elif self._clear(cbm, nx, ty + 3):
                    ny = ty + 3
                else:
                    nx, ny = x, y
        vy += JOE_GRAVITY                                # 0x0DBF
        vy = max(-JOE_VMAX, min(JOE_VMAX, vy))
        self.vy = vy
        f = self.frac + vy                               # 0x0DD8
        if f < 0:
            f += 1000
            ny -= 1
        if f >= 1000:
            f -= 1000
            ny += 1
        self.frac = f
        sx = nx
        if not self._clear(cbm, nx, ny):                 # 0x0DF5: slide left 1 (odd) or right 2
            tx = (nx - 2) | 1
            if self._clear(cbm, tx, ny):
                nx = tx
            elif self._clear(cbm, sx + 2, ny & ~1):
                nx, ny = sx + 2, ny & ~1
            else:
                nx, ny = sx, y0
                self.vy = 0
        ex = g.exit_room(g.current_room, nx, ny)         # 0x0E28
        if ex is not None:
            new_room, wx, wy = ex
            if new_room is None:
                nx = max(1, min(SCREEN_W - 1, nx))        # no room that way: stay put
                ny = max(1, min(SCREEN_H - 1, ny))
            else:
                g.change_room(new_room, wx, wy)          # 0x0802
                nx, ny = wx, wy
        self.x, self.y = nx, ny                          # 0x0E33
        g.joe_mark()                                     # 0x0E3B DRAW_COLLISION shape 0 type 14
        # 0x0E43 sprites: body = dir + 2*moving + 4*recently fired; flame = 8 + (body&3)
        # + 4*(bit 6 of the counter) + 4*thrust, always shown.
        moving = 0
        if inp & INP_RIGHT:
            if not inp & INP_LEFT:
                self.direction, moving = 1, 2
        elif inp & INP_LEFT:
            self.direction, moving = 0, 2
        body = moving + self.direction
        if g.tick - self.last_fire <= FIRE_POSE:
            body += 4
        self.body_sprite = body
        self.flame_sprite = 8 + (body & 3) + ((int(g.tick) >> 4) & 4) + (4 if inp & INP_THRUST else 0)
        # 0x0EAA fire: once per press, then every FIRE_REPEAT ticks while held
        if not inp & INP_FIRE:
            self.fire_released = True
        elif self.fire_released or g.tick - self.last_fire >= FIRE_REPEAT:
            self.fire(g)

    def fire(self, g):
        self.last_fire = g.tick
        self.fire_released = False
        sx = self.x - 12 + 24 * self.direction
        g.entities.append(Shot(g, sx, self.y + 2, self.direction))  # 0x0EDD
        if self.pack == PACK_TWIN and g.enhanced:        # enhanced: a second shot trails the first
            # Same path, 8 px behind (a stacked pair did not match the gun's muzzle animation):
            # 8 px = 60 ticks later, past the turret's 32-tick update, so a volley counts as
            # two hits.
            g.entities.append(Shot(g, sx - 8 * (2 * self.direction - 1), self.y + 2, self.direction))
        play_sound(SND_SHOOT)                            # 0x0EF8

    def update_explosions(self):
        for e in self.explosions:
            e.update()
        self.explosions[:] = [e for e in self.explosions if e.alive]

    def draw(self, surface, sprites, g=None):
        x, y = int(self.x), int(self.y)
        enhanced = g is not None and g.enhanced
        # A broken shield's invulnerability flickers Joe on alternate frames.
        if not (enhanced and g.tick < self.invuln_until and g.frame_no & 1):
            for idx in (self.body_sprite, self.flame_sprite):
                if idx < len(sprites):
                    sp = sprites[idx]
                    surface.blit(sp["surf"], (x + sp["x_off"], y + sp["y_off"]))
        if enhanced and self.pack == PACK_SHIELD:
            pal = g.levels[g.current_level]["pal"]
            pygame.draw.ellipse(surface, pal[11 if g.frame_no & 2 else 3], (x - 19, y - 18, 39, 36), 1)
        for e in self.explosions:
            e.draw(surface, sprites)


# Transporter beam frames (DS:0x3389): 3x3 tiles per frame, 17 frames, 0 = leave the tile.
BEAM_FRAMES = [
    [(0,0),(1,213),(2,0),(20,0),(21,213),(22,0),(40,0),(41,213),(42,0)],
    [(0,0),(1,214),(2,0),(20,0),(21,214),(22,0),(40,0),(41,214),(42,0)],
    [(0,0),(1,215),(2,0),(20,0),(21,215),(22,0),(40,0),(41,215),(42,0)],
    [(0,234),(1,214),(2,235),(20,234),(21,214),(22,235),(40,234),(41,214),(42,235)],
    [(0,216),(1,215),(2,216),(20,216),(21,215),(22,216),(40,216),(41,215),(42,216)],
    [(0,215),(1,214),(2,215),(20,215),(21,214),(22,215),(40,215),(41,214),(42,215)],
    [(0,216),(1,215),(2,216),(20,216),(21,215),(22,216),(40,216),(41,215),(42,216)],
    [(0,215),(1,214),(2,215),(20,215),(21,214),(22,215),(40,215),(41,214),(42,215)],
    [(0,216),(1,215),(2,216),(20,216),(21,215),(22,216),(40,216),(41,215),(42,216)],
    [(0,215),(1,214),(2,215),(20,215),(21,214),(22,215),(40,215),(41,214),(42,215)],
    [(0,217),(1,217),(2,217),(20,217),(21,217),(22,217),(40,217),(41,217),(42,217)],
    [(0,218),(1,218),(2,218),(20,218),(21,218),(22,218),(40,218),(41,218),(42,218)],
    [(0,236),(1,236),(2,236),(20,218),(21,218),(22,218),(40,237),(41,237),(42,237)],
    [(0,238),(1,238),(2,238),(20,218),(21,218),(22,218),(40,239),(41,239),(42,239)],
    [(0,0),(1,0),(2,0),(20,218),(21,218),(22,218),(40,0),(41,0),(42,0)],
    [(0,0),(1,0),(2,0),(20,219),(21,219),(22,219),(40,0),(41,0),(42,0)],
    [(0,0),(1,0),(2,0),(20,0),(21,0),(22,0),(40,0),(41,0),(42,0)],
]


# ---------------------------------------------------------------------------
# Cutscenes — GAME.EXE 0x2750 plays entry AX of the table at DS:0x3D12:
#   0 FA00 thumbs-up (after each level), 1 FA01 reaper (after the first death),
#   2 FA02 title (at start), 3 FA03 credits (after the last level). Each entry names the
# resource, its palette and the delay between frames in object-counter ticks (1165.2 Hz).
# ---------------------------------------------------------------------------
ANIM_THUMBS_UP, ANIM_REAPER, ANIM_TITLE, ANIM_CREDITS = range(4)
ANIMS = [("FA00.DAT", "PL00.DAT", 140), ("FA01.DAT", "PL00.DAT", 200),
         ("FA02.DAT", "PL01.DAT", 3000), ("FA03.DAT", "PL01.DAT", 6000)]
FADE_STEPS = 33                            # 0x2A24/0x29F2: palette scaled 0..256 by 8 per vsync
FADE_TICKS = FADE_STEPS * 1165.2 / 70      # one vsync per step at 70 Hz


def decode_fa(data):
    """FA resource (0x285D): a 64000-byte 320x200 base image followed by delta frames. Each
    frame is a stream of op bytes: bits 7-6 op, bit 5 "count has a second byte", bits 4-0 the
    count-1 (high bits when extended). Ops: 0 skip, 1 literal bytes follow, 2 repeat the
    previous pixel, 3 copy from the base image. FF FF ends a frame; a second FF FF ends the
    file. Returns the list of complete 64000-byte frames in play order."""
    base = data[:64000]
    screen = bytearray(base)
    frames = []
    pos = 64000
    while pos + 1 < len(data) and not (data[pos] == 0xFF and data[pos + 1] == 0xFF):
        di = 0
        while True:
            b = data[pos]
            pos += 1
            count = b & 0x1F
            if b & 0x20:
                lo = data[pos]
                pos += 1
                if b == 0xFF and lo == 0xFF:
                    break
                count = (count << 8) | lo
            count += 1
            op = b >> 6
            if op == 1:
                screen[di:di + count] = data[pos:pos + count]
                pos += count
            elif op == 2:
                screen[di:di + count] = bytes([screen[di - 1]]) * count
            elif op == 3:
                screen[di:di + count] = base[di:di + count]
            di += count
        frames.append(bytes(screen))
    return frames


_anim_cache = {}


def load_anim(idx):
    if idx not in _anim_cache:
        fa, pl, _ = ANIMS[idx]
        _anim_cache[idx] = (decode_fa(load_raw(fa)), load_palette(pl))
    return _anim_cache[idx]


class Cutscene:
    """One run of 0x2750: fade in on the first frame, show the next frame every `delay`
    ticks, fade out as soon as the last one is up. Not skippable, as in the original."""

    def __init__(self, idx, tick):
        frames, self.pal = load_anim(idx)
        self.idx = idx
        self.delay = ANIMS[idx][2]
        self.surfs = [pygame.image.frombuffer(f, (SCREEN_W, TOTAL_H), "P") for f in frames]
        self.t0 = tick
        self.frame = 0
        self.phase = "in"
        self.factor = 0.0
        self.done = False

    def update(self, tick):
        t = tick - self.t0
        if self.phase == "in":
            self.factor = min(1.0, t / FADE_TICKS)
            if t >= FADE_TICKS:
                self.phase, self.t0 = "play", tick
        elif self.phase == "play":
            self.factor = 1.0
            due = int(t // self.delay)
            self.frame = min(due, len(self.surfs) - 1)
            if due >= len(self.surfs) - 1:
                self.phase, self.t0 = "out", tick
        else:
            self.factor = max(0.0, 1.0 - t / FADE_TICKS)
            if t >= FADE_TICKS:
                self.done = True

    def draw(self, screen):
        surf = self.surfs[self.frame]
        k = self.factor
        surf.set_palette([(int(r * k), int(g * k), int(b * k)) for r, g, b in self.pal])
        screen.blit(surf, (0, 0))


def anims_enabled_from_args(argv):
    return "--no-anims" not in argv and os.environ.get("JPJ_ANIMS", "1") != "0"


class TimeoutBeam(Entity):
    """Handler 0x0A38, created by 0x0A5E once TIME has run out: a transporter beam at a random
    clear 3x3 block, interval 0x46 ticks, counter 15 -> 0 drawing BEAM_FRAMES; a Ball
    materialises at its centre when the counter reaches 12 (0x0B30), frame 16 clears it."""
    interval = 0x46

    def __init__(self, g, tile, x, y):
        super().__init__(x, y, g.tick)
        self.tile = tile
        self.counter = 15
        self.room = g.current_room
        self.tiles = g.tile_surfs
        play_sound(SND_TRANSPORTER)                          # 0x0AFC

    def update(self, g):
        if self.counter < 0:
            self.alive = False
            return
        if self.counter == 12:
            g.entities.append(Ball(g, self.x, self.y))
        self.counter -= 1

    def draw(self, surface, sprites, frame):
        f = self.counter + 1                                 # the frame the last update drew
        if 0 <= f <= 15:
            col, row = self.tile % MAP_COLS, self.tile // MAP_COLS
            for toff, ti in BEAM_FRAMES[f]:
                if ti:
                    ts = self.tiles[ti]
                    ts.set_colorkey((0, 0, 0))
                    surface.blit(ts, ((col + toff % 20) * TILE_W, (row + toff // 20) * TILE_H))
                    ts.set_colorkey(None)



# ---------------------------------------------------------------------------
# Enhanced mode — additions that are not in GAME.EXE. They reach the game only through two new
# level-object types, and the three original levels contain neither, so the faithful port is
# unchanged. `--classic` (or JPJ_CLASSIC=1) ignores both types in custom levels as well.
#   22 pack   (tile, kind, var): a pickup Joe wears until he dies or finishes the level. Present
#             while switch variable `var` is non-zero; taking it clears the variable, so it does
#             not come back when the room is re-entered. One pack at a time: a new one replaces
#             the old. kind 1 TWIN SHOT: a second shot follows every shot 8 px behind on the
#             same path. kind 2 SHIELD: absorbs
#             one death (any cause, including a crush, which throws Joe to the nearest free spot),
#             then Joe is invulnerable for SHIELD_INVULN ticks.
#   Also in enhanced mode: a shot that left into another room is caught up on the updates it
#   missed when that room wakes (`catch_up`), instead of resuming from the edge.
#   23 turret (tile, var, sides): a 16x18 px gun standing in its tile (its body pokes 6 px above
#             the tile; collision = SH_TURRET, the same solid rectangle, as type 6, so touching it
#             kills). It cannot fire for TURRET_WARMUP ticks after the room is entered. Every
#             0x20 ticks it looks for Joe within TURRET_RANGE_Y px of
#             its row on an allowed side (0 left, 1 right, 2 either) with no wall between them,
#             and fires a bullet every TURRET_COOLDOWN ticks. Present while `var` is non-zero.
#             Each shot of Joe's that lands takes one of TURRET_HP hit points; it then explodes
#             like any enemy. Like the original enemies it comes back when the room is re-entered.
# ---------------------------------------------------------------------------
PACK_TWIN, PACK_SHIELD = 1, 2
PACK_NAMES = {PACK_TWIN: "TWIN SHOT", PACK_SHIELD: "SHIELD"}
SHIELD_INVULN = 1750             # ticks (~1.5 s) Joe cannot die after his shield takes a hit
TURRET_HP = 3
TURRET_COOLDOWN = 1400           # ticks between turret shots (~1.2 s)
TURRET_WARMUP = 2000             # ticks after room entry before the first shot (~1.7 s)
TURRET_RANGE_Y = 14              # px: Joe's centre must be this close to the turret's row
TURRET_SHOT_INTERVAL = 12        # ticks per 2 px step (~194 px/s; Joe climbs at 116 px/s)
SH_TURRET = 1000                 # a synthetic collision shape (SH00.DAT has 258): 8x9 half-res
_SH_CACHE[SH_TURRET] = tuple((row, -4, 8) for row in range(-4, 5))   # = the 16x18 px body

# Pixel art for the new objects: one hex digit per pixel = palette index 0-15 (the EGA colours
# shared by every level palette), "." = transparent.
ART = {
    "pack1": (                   # twin shot: a yellow pack with two gun barrels
        "..888888888888",
        ".8EEEEEEEEEEE8",
        "8EE66666666EE8",
        "8E6FFFFFFF88E8",
        "8E6F777778E8E8",
        "8EE66666666EE8",
        "8E6FFFFFFF88E8",
        "8E6F777778E8E8",
        "8EE66666666EE8",
        ".8EEEEEEEEEEE8",
        "..888888888888",
        "..8.........8.",
    ),
    "pack2": (                   # shield: a blue pack with a white ring
        "..888888888888",
        ".8BBBBBBBBBBB8",
        "8BB333FFF333B8",
        "8B33F33333F3B8",
        "8B3F3BBBBB3F38",
        "8B3F3BBBBB3F38",
        "8B3F3BBBBB3F38",
        "8B33F33333F3B8",
        "8BB333FFF333B8",
        ".8BBBBBBBBBBB8",
        "..888888888888",
        "..8.........8.",
    ),
    "turret": (                  # 16x18, facing right; flipped for left. Barrel on rows 7-8.
        "......7777......",
        "......7887......",
        "....77777777....",
        "...7FFFFFFFF7...",
        "..7F88888888F7..",
        "..7F8CC88888F7..",
        "..7F8CC88888F7..",
        "..7F88888888F888",
        "..7F88888888F7FF",
        "..7F88888888F7..",
        "..7FFFFFFFFFF7..",
        "...777777777....",
        "..8888888888....",
        ".877777777778...",
        ".877777777778...",
        ".877777777778...",
        ".877777777778...",
        "88888888888888..",
    ),
    "flash": (
        ".EE.",
        "EFFE",
        "EFFE",
        ".EE.",
    ),
    "bullet": (
        ".CCCCCC.",
        "CFFCCCCC",
        "CCCCCC4C",
        ".CCCC4C.",
    ),
}


def make_art(rows, pal, flip=False, white=False):
    h, w = len(rows), len(rows[0])
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                s.set_at((w - 1 - x if flip else x, y), (*pal[15 if white else int(ch, 16)], 255))
    return s


def build_art(pal):
    """The enhanced-mode surfaces in a level's palette."""
    art = {name: make_art(rows, pal) for name, rows in ART.items()}
    art["turret_l"] = make_art(ART["turret"], pal, flip=True)
    art["turret_hit"] = make_art(ART["turret"], pal, white=True)
    art["turret_hit_l"] = make_art(ART["turret"], pal, flip=True, white=True)
    return art


def enhanced_from_args(argv):
    """Enhanced mode is on unless `--classic` or JPJ_CLASSIC=1 asks for the bare port."""
    return "--classic" not in argv and os.environ.get("JPJ_CLASSIC", "0") != "1"


class Pack(Entity):
    """Object type 22. Checks the trigger shape 4 (the middle of its tile) for Joe's marker."""
    interval = 0x20

    def __init__(self, g, obj):
        super().__init__(obj["x"], obj["y"], g.tick)
        self.kind = obj["params"][1] if len(obj["params"]) > 1 else PACK_TWIN
        self.var = obj["params"][2] if len(obj["params"]) > 2 else 0
        self.art = g.art.get("pack%d" % self.kind, g.art["pack1"])
        self.room = g.current_room

    def update(self, g):
        if g.death is None and cb_check(g.cbm, 4, self.x >> 1, self.y >> 1, 0)[1][CT_JOE]:
            g.player.pack = self.kind
            g.switch_state[self.var] = 0
            play_sound(SND_PICKUP)
            self.alive = False

    def draw(self, surface, sprites, frame):
        bob = (0, 0, -1, -2, -2, -2, -1, 0)[(frame >> 2) & 7]
        surface.blit(self.art, (self.x + 1, self.y + bob))


class TurretShot(Entity):
    """A turret's bullet: 2 px per update along its row. Hitting Joe's marker restores the
    backup under shape 1, which is how every original hazard kills him (0x0CCC), so his shield
    sees it like any other death. Anything else solid stops it with a wall explosion. Like
    Joe's shots it is mobile: it crosses room edges and follows Joe into the next room."""
    interval = TURRET_SHOT_INTERVAL
    mobile = True

    def __init__(self, g, x, y, direction):
        super().__init__(x, y, g.tick)
        self.speed = direction * 4 - 2
        self.art = g.art["bullet"]
        self.room = g.current_room

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        nx = self.x + self.speed
        if self.cross(g, nx, self.y):
            return
        self.x = nx
        hx, hy = nx >> 1, self.y >> 1
        total, hist = cb_check(cbm, 1, hx, hy, 0)
        if total == 0:
            return
        if hist[CT_JOE]:
            cb_restore(cbm, backup, 1, hx, hy)
        if self.visible == 1 and self.room == g.current_room:
            g.player.explosions.append(Explosion(nx, self.y))
        self.alive = False

    def draw(self, surface, sprites, frame):
        surface.blit(self.art, (self.x - 4, self.y - 2))


class Turret(Entity):
    """Object type 23. (x, y) is the centre of its 16x18 body, which stands on the bottom of
    its tile and pokes 6 px above it. Its collision is SH_TURRET, the same rectangle."""
    interval = 0x20

    def __init__(self, g, obj):
        super().__init__(obj["x"] + 8, obj["y"] + 3, g.tick)
        self.sides = obj["params"][2] if len(obj["params"]) > 2 else 2
        self.facing = 0 if self.sides == 0 else 1
        self.hp = TURRET_HP
        self.hit_flash = 0          # frames left of the white "hit" look
        self.muzzle = 0             # frames left of the muzzle flash
        self.fired_at = g.tick + TURRET_WARMUP - TURRET_COOLDOWN   # first shot after the warm-up
        self.room = g.current_room
        self.art = g.art
        self.write(g.cbm)

    def write(self, cbm):
        cb_write(cbm, SH_TURRET, self.x >> 1, self.y >> 1, CT_ENEMY)

    def check(self, cbm, filt):
        return cb_check(cbm, SH_TURRET, self.x >> 1, self.y >> 1, filt)

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        hx, hy = self.x >> 1, self.y >> 1
        total, hist = self.check(cbm, CT_ENEMY)
        if total and hist[CT_JOE] != total:          # not just Joe's marker: a shot erased us
            self.hp -= 1
            self.hit_flash = 6
            if self.hp <= 0:
                cb_restore_if(cbm, backup, SH_TURRET, hx, hy, CT_ENEMY)
                g.entities.append(EnemyExplosion(g, self.x, self.y, None))
                self.alive = False
                return
        self.write(cbm)                                # Joe overlapping it dies at his next check
        if g.death is not None or g.beam_in is not None or g.beam_out is not None:
            return
        jx, jy = int(g.player.x), int(g.player.y)
        if abs(jy - self.y) > TURRET_RANGE_Y or abs(jx - self.x) < 16:
            return
        side = 1 if jx > self.x else 0
        if self.sides != 2 and side != self.sides:
            return
        self.facing = side
        if g.tick - self.fired_at < TURRET_COOLDOWN or not self.line_of_sight(cbm, hx, hy, jx >> 1):
            return
        self.fired_at = g.tick
        self.muzzle = 4
        g.entities.append(TurretShot(g, self.x + (12 if side else -12), self.y - 1, side))
        play_sound(SND_TURRET)

    @staticmethod
    def line_of_sight(cbm, hx, hy, tx):
        """No wall byte on the turret's row between its barrel and Joe's column."""
        step = 1 if tx > hx else -1
        for sx in range(hx + 4 * step, tx, step):
            if 0 <= sx < HALF_W and cbm[hy * HALF_W + sx] == CT_WALL:
                return False
        return True

    def draw(self, surface, sprites, frame):
        name = "turret_hit" if self.hit_flash else "turret"
        if self.facing == 0:
            name += "_l"
        surface.blit(self.art[name], (self.x - 8, self.y - 9))
        if self.hit_flash:
            self.hit_flash -= 1
        if self.muzzle:
            self.muzzle -= 1
            fx = self.x + 8 if self.facing else self.x - 12
            surface.blit(self.art["flash"], (fx, self.y - 3))


class JetPackJoe:
    def __init__(self):
        pygame.init()
        self.sound = SoundBank(sound_enabled_from_args(sys.argv))
        self.window = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Jet Pack Joe — Joe Lowe (1990s)")
        self.screen = pygame.Surface((SCREEN_W, TOTAL_H))
        self.clock = pygame.time.Clock()

        self.blk = load_raw("BK00.DAT")
        self.col_data = load_raw("CB00.DAT")
        self.sp_data = load_raw("SP00.DAT")
        self.num_tiles = len(self.blk) // (TILE_W * TILE_H)

        self.levels = [
            {"map": load_raw("MP11.DAT"), "lv": load_raw("LV11.DAT"), "pal": load_palette("PL11.DAT"), "name": "Level 1"},
            {"map": load_raw("MP12.DAT"), "lv": load_raw("LV12.DAT"), "pal": load_palette("PL12.DAT"), "name": "Level 2"},
            {"map": load_raw("MP13.DAT"), "lv": load_raw("LV13.DAT"), "pal": load_palette("PL13.DAT"), "name": "Level 3"},
        ]

        self.current_level = 0
        self.time_counter = 0
        self.tick = 0.0          # object counter (INT 62h DX=0), advanced TICKS_PER_FRAME per frame
        self.frame_no = 0        # render frame number ([0x2361]) — drives sprite flicker
        self.entities = []       # enemies, generators, enemy explosions in the current room
        self.dormant = []        # mobile objects hidden in some room (slot visible=0), any room
        self.last_room = None
        self.joe_marked = None   # the cbm Joe's type-14 marker is currently stamped in
        self.death = None        # Joe death animation state (GAME.EXE 0x0F05)
        self.cbm = self.cbm_bak = None
        self.goto_buf = None     # digits typed after G (debug "go to room"), None when inactive
        self.enemies_enabled = "--no-enemies" not in sys.argv and os.environ.get("JPJ_ENEMIES", "1") != "0"
        self.anims_enabled = anims_enabled_from_args(sys.argv)
        self.enhanced = enhanced_from_args(sys.argv)   # packs and turrets (object types 22/23)
        self.cutscene = None      # a Cutscene while one plays; the game is frozen underneath
        self.cutscene_then = None
        self.fade = None          # level palette fade: {"t0", "dir": +1 in / -1 out, "then"}
        self.reaper_shown = False # [0x2EE]: FA01 plays only after the first death
        self.set_level(0)

    def build_assets(self):
        pal = self.levels[self.current_level]["pal"]
        self.tile_surfs = []
        for t in range(self.num_tiles):
            s = pygame.Surface((TILE_W, TILE_H))
            off = t * TILE_W * TILE_H
            for y in range(TILE_H):
                for x in range(TILE_W):
                    s.set_at((x, y), pal[self.blk[off + y * TILE_W + x]])
            self.tile_surfs.append(s)
        self.sprites = decode_sprites(self.sp_data, pal)
        self.art = build_art(pal)                        # enhanced-mode graphics in this palette
        # Build per-row opaque pixel masks for sprite collision
        for idx, sp in enumerate(self.sprites):
            surf = sp["surf"]
            w, h = sp["w"], sp["h"]
            mask = []
            for y in range(h):
                row = []
                for x in range(w):
                    if surf.get_at((x, y))[3] > 0:
                        row.append(x)
                mask.append(row)
            sp["mask"] = mask
        self.room_cache = {}
        self.cbm_cache = {}
        self.cbm_backup = {}
        self.beam_in = None
        self.beam_out = None
        self.num_rooms = len(self.levels[self.current_level]["map"]) // ROOM_BYTES
        self.load_room_headers()
        self.load_room_objects()
        self.switch_state = bytearray(256)  # DS:0x3067 — switch states, 0=OFF, 0xFF=ON
        # Initialize all switches to ON (0xFF) then turn specific ones OFF
        # (matches GAME.EXE: fill 0xFF at 0x0622, then loop at 0x0654 sets listed IDs to 0)
        for i in range(256):
            self.switch_state[i] = 0xFF
        # Parse switch-off list from level data trailer
        # (GAME.EXE at 0x062D: sets read pointer to room 68, reads header + switch IDs)
        lv_data = self.levels[self.current_level]["lv"]
        first_off = struct.unpack_from('<H', lv_data, 0)[0]
        # Room 68's offset + 8 (skip header) = start of trailer data
        trailer_off = struct.unpack_from('<H', lv_data, 68 * 2)[0] + 8
        self.captive_count = struct.unpack_from('<H', lv_data, trailer_off)[0]     # [0x305F]
        self.level_timer = struct.unpack_from('<H', lv_data, trailer_off + 2)[0]     # [0x23DA]
        self.start_room = struct.unpack_from('<H', lv_data, trailer_off + 4)[0]      # [0x23DC]
        self.beam_tile = struct.unpack_from('<H', lv_data, trailer_off + 6)[0]       # [0x23BF]
        # Beam-in will be started in set_level after player is created
        trailer_pos = trailer_off + 8  # skip 4 header words (captive count, timer, room, value)
        while trailer_pos + 1 < len(lv_data):
            sid = struct.unpack_from('<H', lv_data, trailer_pos)[0]
            trailer_pos += 2
            if sid == 0xFFFF:
                break
            if sid < 256:
                self.switch_state[sid] = 0

    def get_collision_bitmap(self, room_idx):
        if room_idx not in self.cbm_cache:
            self.cbm_cache[room_idx] = build_collision_bitmap(
                self.blk, self.levels[self.current_level]["map"],
                room_idx, self.num_tiles)
            # Backup bitmap for DRAW_VISUAL erase (original ES:0x4820): the bare tile
            # collision, taken BEFORE any object writes. Objects (cages, doors, plates, enemies)
            # re-write their own shapes every update, so a restore never brings them back.
            cbm = self.cbm_cache[room_idx][0]
            self.cbm_backup[room_idx] = bytearray(cbm)
            # Add cage collision walls (shape 13: two 2px walls, 18 rows tall)
            if room_idx in self.room_objects:
                for obj in self.room_objects[room_idx]:
                    if obj["type"] == 10 and obj.get("disappear", -1) < 0:   # rescued → no walls
                        hx, hy = obj["x"] // 2, obj["y"] // 2
                        for r in range(18):
                            for c in [1, 2, 21, 22]:  # left wall cols 1-2, right wall cols 21-22
                                bx, by = hx + c, hy + r
                                if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                    cbm[by * HALF_W + bx] = 1
        return self.cbm_cache[room_idx]

    def is_solid(self, col, row):
        if col < 0 or col >= MAP_COLS:
            return True
        if row < 0:
            return False
        if row >= MAP_ROWS:
            return True
        map_data = self.levels[self.current_level]["map"]
        base = self.current_room * ROOM_BYTES
        idx = row * MAP_COLS + col
        w = struct.unpack_from('<H', map_data, base + idx * 2)[0]
        if w == 0xFFFF:
            return False
        # EXPAND_MAP stores (AH >> 2) = (w >> 10) & 0x3F as collision value
        # Non-zero = solid (value encodes collision type: 1=wall, 8=floor, etc.)
        return (w >> 10) & 0x3F != 0

    def render_room(self, room_idx):
        if room_idx in self.room_cache:
            return self.room_cache[room_idx]
        surf = pygame.Surface((SCREEN_W, SCREEN_H))
        surf.fill((0, 0, 0))
        if room_idx < 0 or room_idx >= self.num_rooms:
            self.room_cache[room_idx] = surf
            return surf
        map_data = self.levels[self.current_level]["map"]
        base = room_idx * ROOM_BYTES
        bg_words = struct.unpack('<320H', map_data[base:base + 640])
        for i, w in enumerate(bg_words):
            if w == 0xFFFF:
                continue
            ti = w & 0x3FF
            if ti < self.num_tiles:
                surf.blit(self.tile_surfs[ti], ((i % MAP_COLS) * TILE_W, (i // MAP_COLS) * TILE_H))
        self.room_cache[room_idx] = surf
        return surf

    def render_foreground(self, room_idx, surface):
        """Draw foreground layer tiles OVER sprites (colorkey: black=transparent)."""
        if room_idx < 0 or room_idx >= self.num_rooms:
            return
        map_data = self.levels[self.current_level]["map"]
        base = room_idx * ROOM_BYTES
        # Only the foreground layer (320 bytes) is drawn over Joe
        # Build tile overrides from switch and fan objects
        fg_overrides = {}
        if room_idx in self.room_objects:
            for obj in self.room_objects[room_idx]:
                if "fg_tile" in obj:
                    fg_overrides[obj["params"][0]] = obj["fg_tile"]
                fg_overrides.update(obj.get("fg_tiles", {}))
        fg_overrides.update(self.beam_fg_tiles())
        fg_bytes = map_data[base + 640:base + 960]
        for i, b in enumerate(fg_bytes):
            tile_id = fg_overrides.get(i, b)
            if tile_id == 0 or tile_id == 255:
                continue
            if tile_id < self.num_tiles:
                s = self.tile_surfs[tile_id]
                s.set_colorkey((0, 0, 0))
                surface.blit(s, ((i % MAP_COLS) * TILE_W, (i // MAP_COLS) * TILE_H))
                s.set_colorkey(None)

    def load_room_headers(self):
        """Load room connectivity from LVxx.DAT for current level."""
        data = self.levels[self.current_level]["lv"]
        first_off = struct.unpack_from('<H', data, 0)[0]
        num_entries = first_off // 2
        offsets = [struct.unpack_from('<H', data, i * 2)[0] for i in range(num_entries)]
        self.room_headers = []
        for i in range(num_entries):
            off = offsets[i]
            if off + 8 <= len(data):
                self.room_headers.append(data[off:off + 8])
            else:
                self.room_headers.append(b'\xff' * 8)

    OBJ_PARAMS = {0:0,1:1,2:1,3:1,4:1,5:3,6:2,7:2,8:2,9:2,10:3,11:1,12:1,13:2,14:2,15:2,16:2,17:3,18:3,19:3,20:1,21:0,22:3,23:3}

    def load_room_objects(self):
        """Parse objects from LVxx.DAT for each room."""
        data = self.levels[self.current_level]["lv"]
        first_off = struct.unpack_from('<H', data, 0)[0]
        num_entries = first_off // 2
        offsets = [struct.unpack_from('<H', data, i * 2)[0] for i in range(num_entries)]
        self.room_objects = {}
        for room in range(num_entries):
            off = offsets[room]
            pos = off + 8  # skip 8-byte header
            objects = []
            # Entry 68 is the level trailer and 69 is empty; unused rooms (L1 16-67) share the
            # trailer's offset. None of them is a room, so none gets an object list.
            if room >= 68 or (num_entries > 68 and off == offsets[68]):
                self.room_objects[room] = objects
                continue
            while pos + 1 < len(data):
                obj_type = struct.unpack_from('<H', data, pos)[0]
                pos += 2
                if obj_type == 0xFFFF:
                    break
                nparams = self.OBJ_PARAMS.get(obj_type, 0)
                params = []
                for _ in range(nparams):
                    if pos + 1 < len(data):
                        params.append(struct.unpack_from('<H', data, pos)[0])
                        pos += 2
                if params:
                    loc = params[0]
                    col, row = loc % MAP_COLS, loc // MAP_COLS
                    px, py = col * TILE_W, row * TILE_H
                    objects.append({"type": obj_type, "params": params,
                                    "x": px, "y": py, "anim": 0, "timer": 0})
            self.room_objects[room] = objects

    # ------------------------------------------------------------------
    # Room objects (fans, doors, switches, fields, cages, plates, pads, glow balls, beams).
    # Each is a slot in the original's object table: its init handler (AX=0) sets a tick
    # interval and a first update time, the main loop (0x06F8) runs it whenever that time has
    # passed, and the update rewrites its collision shape and its foreground/background tiles.
    # Drawing only shows the state the last update left behind.
    # ------------------------------------------------------------------
    OBJ_INTERVAL = {5: 0x59, 6: 0x80, 7: 0x80, 8: 0x4F, 9: 0x4F, 10: 0x7D, 13: 0x4F,
                    15: 0xA, 16: 0xA, 17: 0x80}
    FAN_FRAMES = {1: (200, (0, 1, 2)), 2: (200, (0, 2, 1)), 3: (440, (0, 1, 2)), 4: (440, (0, 2, 1))}
    VFIELD_TILES = ((81, 101, 121, 141, 161, 181), (82, 102, 122, 142, 162, 182),
                    (83, 103, 123, 143, 163, 183), (80, 100, 120, 140, 160, 180))
    HFIELD_TILES = ((64, 65, 66, 67, 68, 69), (104, 105, 106, 107, 108, 109),
                    (84, 85, 86, 87, 88, 89), (124, 125, 126, 127, 128, 129))
    GLOW_FRAMES = ((94, 95, 114, 115), (96, 97, 116, 117), (134, 135, 154, 155),
                   (136, 137, 156, 157), (138, 139, 158, 159))
    CAGE_FF_TILES = (232, 233, 252, 253)                          # DS:0x3AF5
    DOOR_FRAMES = [                                                # DS:0x3599
        [(0, 144), (20, 164), (40, 164), (60, 184)], [(0, 145), (20, 165), (40, 165), (60, 185)],
        [(0, 146), (20, 166), (40, 166), (60, 186)], [(0, 147), (20, 167), (40, 167), (60, 187)],
        [(0, 144), (20, 164), (40, 149), (60, 187)], [(0, 145), (20, 165), (40, 169), (60, 187)],
        [(0, 146), (20, 166), (40, 189), (60, 187)], [(0, 147), (20, 167), (40, 0), (60, 187)],
        [(0, 144), (20, 149), (40, 0), (60, 187)], [(0, 145), (20, 169), (40, 0), (60, 187)],
        [(0, 146), (20, 189), (40, 0), (60, 187)], [(0, 147), (20, 0), (40, 0), (60, 187)],
        [(0, 148), (20, 0), (40, 0), (60, 187)], [(0, 168), (20, 0), (40, 0), (60, 187)],
        [(0, 188), (20, 0), (40, 0), (60, 187)],
    ]
    PLATE_POS = [                                                  # DS:0x39BF: 52 x (x, frame, col)
        (0, 0, 0), (2, 1, 0), (4, 2, 0), (6, 3, 0), (8, 4, 0), (10, 5, 0), (12, 6, 0), (14, 7, 0), (16, 8, 0),
        (18, 1, 1), (20, 2, 1), (22, 3, 1), (24, 4, 1), (26, 5, 1), (28, 6, 1), (30, 7, 1), (32, 8, 1),
        (34, 1, 2), (36, 2, 2), (38, 3, 2), (40, 4, 2), (42, 5, 2), (44, 6, 2), (46, 7, 2), (48, 8, 2),
        (50, 1, 3), (52, 2, 3),
        (50, 1, 3), (48, 0, 3), (46, 7, 2), (44, 6, 2), (42, 5, 2), (40, 4, 2), (38, 3, 2), (36, 9, 2), (34, 1, 2),
        (32, 0, 2), (30, 7, 1), (28, 6, 1), (26, 5, 1), (24, 4, 1), (22, 3, 1), (20, 9, 1), (18, 1, 1),
        (16, 0, 1), (14, 7, 0), (12, 6, 0), (10, 5, 0), (8, 4, 0), (6, 3, 0), (4, 9, 0), (2, 1, 0),
    ]
    PLATE_LEFT = [                                                 # DS:0x3995
        [(0, 72), (20, 72), (40, 72), (60, 72), (80, 72)],
        [(0, 52), (20, 51), (40, 52), (60, 51), (80, 52)],
        [(0, 191), (20, 190), (40, 191), (60, 190), (80, 191)],
        [(0, 171), (20, 170), (40, 171), (60, 170), (80, 171), (1, 172), (21, 172), (41, 172), (61, 172), (81, 172)],
        [(0, 151), (20, 150), (40, 151), (60, 150), (80, 151), (1, 152), (21, 152), (41, 152), (61, 152), (81, 152)],
        [(0, 131), (20, 130), (40, 131), (60, 130), (80, 131), (1, 132), (21, 132), (41, 132), (61, 132), (81, 132)],
        [(0, 111), (20, 110), (40, 111), (60, 110), (80, 111), (1, 112), (21, 112), (41, 112), (61, 112), (81, 112)],
        [(0, 91), (20, 90), (40, 91), (60, 90), (80, 91), (1, 92), (21, 92), (41, 92), (61, 92), (81, 92)],
        [(0, 0), (20, 71), (40, 0), (60, 71), (80, 0), (1, 72), (21, 72), (41, 72), (61, 72), (81, 72)],
        [(0, 191), (20, 190), (40, 191), (60, 190), (80, 191), (1, 0), (21, 0), (41, 0), (61, 0), (81, 0)],
    ]
    PLATE_RIGHT = [                                                # DS:0x39A9
        [(0, 191), (20, 191), (40, 191), (60, 191), (80, 191)],
        [(0, 52), (20, 53), (40, 52), (60, 53), (80, 52)],
        [(0, 72), (20, 73), (40, 72), (60, 73), (80, 72)],
        [(0, 92), (20, 93), (40, 92), (60, 93), (80, 92), (-1, 91), (19, 91), (39, 91), (59, 91), (79, 91)],
        [(0, 112), (20, 113), (40, 112), (60, 113), (80, 112), (-1, 111), (19, 111), (39, 111), (59, 111), (79, 111)],
        [(0, 132), (20, 133), (40, 132), (60, 133), (80, 132), (-1, 131), (19, 131), (39, 131), (59, 131), (79, 131)],
        [(0, 152), (20, 153), (40, 152), (60, 153), (80, 152), (-1, 151), (19, 151), (39, 151), (59, 151), (79, 151)],
        [(0, 172), (20, 173), (40, 172), (60, 173), (80, 172), (-1, 171), (19, 171), (39, 171), (59, 171), (79, 171)],
        [(0, 0), (20, 71), (40, 0), (60, 71), (80, 0), (-1, 191), (19, 191), (39, 191), (59, 191), (79, 191)],
        [(0, 72), (20, 73), (40, 72), (60, 73), (80, 72), (-1, 0), (19, 0), (39, 0), (59, 0), (79, 0)],
    ]
    BEAM_INTERVAL = 0x46                                            # 0x1F4E / 0x200C
    BEAM_IN_DELAY = 0x1F4                                           # 0x2000: first frame +500
    JOE_AFTER_BEAM = 0x410                                          # 0x2006: Joe's first update

    def init_room_object(self, obj):
        """The handler's AX=0 init for one object of the room being entered."""
        t = obj["type"]
        for k in ("fg_tiles", "fg_tile", "bg_tiles", "gb_dormant"):
            obj.pop(k, None)
        obj["frame"] = 0                   # [DI+0xE] / [DI+0x1C] animation frame
        obj["touching"] = False            # [DI+0x1D] last CHECK result (switches, pads)
        obj["field_active"] = False        # [DI+0x1D] of the field handler
        if t in (1, 2, 3, 4):
            obj["interval"] = 0x4B + random.randrange(0x64)     # 0x1289: 75..174 ticks
        elif t in self.OBJ_INTERVAL:
            obj["interval"] = self.OBJ_INTERVAL[t]
        else:
            obj["interval"] = None                               # entities handle it
            return
        if t == 10 and obj.get("disappear", -1) >= 0:
            obj["interval"] = None                               # rescued: 0x141B freed it
            return
        if t in (15, 16):
            obj["next_time"] = self.tick                         # 0x17DF: due at once
            obj["counter"] = 3                                   # 0x17FD: [DI+0x1D]
            obj["plate_hx"] = obj["x"] // 2
            obj["fg_tiles"] = {}
        else:
            obj["next_time"] = self.tick + random.randrange(obj["interval"])   # random phase
        self.step_room_object(obj)                               # every init ends with AX=2

    def update_room_objects(self):
        """0x06F8 for the room's non-entity objects, plus the transporter beams."""
        room = self.current_room
        for obj in self.room_objects.get(room, []):
            n = 0
            while obj.get("interval") is not None and obj["next_time"] <= self.tick and n < 8:
                self.step_room_object(obj)
                if obj.get("interval") is not None:
                    obj["next_time"] += obj["interval"]
                n += 1
            if obj["type"] == 10 and 0 <= obj.get("disappear", -1) < 17:
                while obj["beam_next"] <= self.tick and obj["disappear"] < 17:
                    obj["beam_next"] += self.BEAM_INTERVAL     # 0x1F18: one frame per update
                    obj["disappear"] += 1
                    if obj["disappear"] == 17:                   # 0x1F87: slot freed, captive counted
                        self.captive_count = max(0, self.captive_count - 1)
        self.update_beams()

    def step_room_object(self, obj):
        """One handler update (AX=2)."""
        t = obj["type"]
        room = self.current_room
        x, y = obj["x"], obj["y"]
        hx, hy = x // 2, y // 2
        tile = obj["params"][0]
        col, row = tile % MAP_COLS, tile // MAP_COLS
        cbm = self.get_collision_bitmap(room)[0]
        backup = self.cbm_backup.get(room)
        if t in (1, 2, 3, 4):                                       # 0x1D40 / 0x1DBE
            obj["frame"] = (obj["frame"] + 1) % 3
            base, order = self.FAN_FRAMES[t]
            tiles = {}
            for dr in range(3):
                for dc in range(3):
                    tiles[(row + dr) * MAP_COLS + col + dc] = base + order[obj["frame"]] * 3 + dc + dr * 20
            if t in (1, 2):
                obj["fg_tiles"] = tiles                             # 0x4B4: foreground map
            else:
                obj["bg_tiles"] = tiles                             # 0x4D2: background, under fg 255
        elif t in (6, 7):                                           # 0x1B84 wall switch
            sw = obj["params"][1] if len(obj["params"]) > 1 else 0
            hit = cb_check(cbm, 4, hx, hy, CT_WALL)[1][CT_JOE] != 0
            if hit and not obj["touching"]:
                self.switch_state[sw] = 0 if self.switch_state[sw] else 0xFF
            obj["touching"] = hit
            obj["fg_tile"] = (0xE6 if t == 6 else 0xFA) + (self.switch_state[sw] & 1)
        elif t == 17:                                               # 0x213C toggle pad
            sw1 = obj["params"][1] if len(obj["params"]) > 1 else 0
            sw2 = obj["params"][2] if len(obj["params"]) > 2 else 0
            hit = cb_check(cbm, 4, hx, hy, CT_WALL)[1][CT_JOE] != 0
            if hit and not obj["touching"]:
                self.switch_state[sw1] = ~self.switch_state[sw1] & 0xFF
                if sw2 != sw1:
                    self.switch_state[sw2] = ~self.switch_state[sw2] & 0xFF
            obj["touching"] = hit
            obj["bg_tiles"] = {tile: 556 + (self.switch_state[sw2] & 1) + 2 * (self.switch_state[sw1] & 1)}
        elif t == 8:                                                # 0x1336 → 0x1E3C vertical field
            sw = obj["params"][1] if len(obj["params"]) > 1 else 0
            bg_words = struct.unpack_from('<320H', self.levels[self.current_level]["map"], room * ROOM_BYTES)
            y_top = 0
            for r in range(row - 1, -1, -1):
                if (bg_words[r * MAP_COLS + col] >> 10) & 0x3F:
                    y_top = (r + 1) * TILE_H
                    break
            y_bot = SCREEN_H
            for r in range(row + 1, MAP_ROWS):
                if (bg_words[r * MAP_COLS + col] >> 10) & 0x3F:
                    y_bot = r * TILE_H
                    break
            def restore_field():                                  # DRAW_VISUAL shape 8: 6w x 35h
                if backup:
                    for r in range(1, 36):
                        by = y_top // 2 + r
                        for c in range(1, 7):
                            bx = hx + c
                            if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
            if self.switch_state[sw] == 0:
                if obj["field_active"]:
                    restore_field()
                    obj["field_active"] = False
                    obj["fg_tiles"] = {}
                return
            restore_field()                                       # wipes Joe's marker: the kill
            obj["frame"] = (obj["frame"] + 1) & 3
            tiles = {}
            ty, i = y_top, 0
            while ty < y_bot and i < 6:
                tiles[(ty // TILE_H) * MAP_COLS + col] = self.VFIELD_TILES[obj["frame"]][i]
                ty += TILE_H
                i += 1
            obj["fg_tiles"] = tiles
            for r in range(0, 35, 2):                               # shape 7: cols 3-4, every 2nd row
                by = y_top // 2 + r
                for c in (3, 4):
                    bx = hx + c
                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                        cbm[by * HALF_W + bx] = CT_WALL
            obj["field_active"] = True
        elif t == 9:                                                # 0x131F → 0x1E3C horizontal field
            sw = obj["params"][1] if len(obj["params"]) > 1 else 0
            def restore_field():                                  # DRAW_VISUAL shape 12: 48w x 4h
                if backup:
                    for r in range(1, 5):
                        by = hy + r
                        for c in range(48):
                            bx = hx + c
                            if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
            if self.switch_state[sw] == 0:
                if obj["field_active"]:
                    restore_field()
                    obj["field_active"] = False
                    obj["fg_tiles"] = {}
                return
            restore_field()
            obj["frame"] = (obj["frame"] + 1) & 3
            obj["fg_tiles"] = {tile + i: ti for i, ti in enumerate(self.HFIELD_TILES[obj["frame"]])
                               if tile + i < MAP_ROWS * MAP_COLS}
            for r in (2, 3):                                        # shape 11: 48w x 2h
                by = hy + r
                for c in range(48):
                    bx = hx + c
                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                        cbm[by * HALF_W + bx] = CT_WALL
            obj["field_active"] = True
        elif t == 13:                                               # 0x134D → 0x1E3C glow ball
            sw = obj["params"][1] if len(obj["params"]) > 1 else 0
            if self.switch_state[sw] == 0:
                if obj["field_active"]:
                    obj["field_active"] = False
                    cb_restore(cbm, backup, 5, hx, hy)
                    obj["fg_tiles"] = self._glow_tiles(tile, 4)     # frame 4: dormant look
                return
            cb_restore(cbm, backup, 6, hx, hy)                      # DRAW_VISUAL ring
            obj["frame"] = (obj["frame"] + 1) & 3
            obj["fg_tiles"] = self._glow_tiles(tile, obj["frame"])
            cb_write(cbm, 5, hx, hy, CT_WALL)                       # DRAW_COLLISION
            obj["field_active"] = True
        elif t == 10:                                               # 0x1364 cage
            if obj.get("disappear", -1) >= 0:                       # 0x141B: variable cleared
                for r in range(18):
                    for c in (1, 2, 21, 22):
                        bx, by = hx + c, hy + r
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 0
                obj["interval"] = None
                return
            for r in range(18):                                     # DRAW_COLLISION shape 13
                for c in (1, 2, 21, 22):
                    bx, by = hx + c, hy + r
                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                        cbm[by * HALF_W + bx] = CT_WALL
            if cb_check(cbm, 14, hx, hy, 0)[1][CT_JOE]:             # 0x143D: Joe inside
                obj["disappear"] = 0                                # beam 0x1F18 starts now
                obj["beam_next"] = self.tick + self.BEAM_INTERVAL
                obj["fg_tiles"] = {}
                play_sound(SND_TRANSPORTER)                         # 0x1F62
                play_sound(SND_THANKS)                              # 0x1468
                obj["next_time"] += 0x302                           # 0x146E
                return
            obj["frame"] = (obj["frame"] + 1) & 3
            ti = self.CAGE_FF_TILES[obj["frame"]]
            obj["fg_tiles"] = {(row + dr) * MAP_COLS + col + dc: ti for dr in range(3) for dc in range(3)}
        elif t == 5:                                                # 0x1C51 door
            sw = obj["params"][1] if len(obj["params"]) > 1 else 0
            var = obj["params"][2] if len(obj["params"]) > 2 else 0
            state = min(14, self.switch_state[var])
            dhx = (x + 2) // 2
            if backup:                                              # DRAW_VISUAL shape 3 at the old height
                for r in range(0, 21, 2):
                    by = (y + 4) // 2 - (state * 3) // 2 + r
                    for c in range(6):
                        bx = dhx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
            if self.switch_state[sw]:
                state = min(14, state + 1)
            else:
                state = max(0, state - 1)
            self.switch_state[var] = state
            for r in range(0, 21, 2):                               # DRAW_COLLISION at the new height
                by = (y + 4) // 2 - (state * 3) // 2 + r
                for c in range(6):
                    bx = dhx + c
                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                        cbm[by * HALF_W + bx] = CT_WALL
            obj["fg_tiles"] = {(row + toff // 20) * MAP_COLS + col + toff % 20: ti
                               for toff, ti in self.DOOR_FRAMES[state]}
        elif t in (15, 16):                                         # 0x17A0 / 0x189B plates
            is_right = t == 16
            var = obj["params"][1] if len(obj["params"]) > 1 else 0
            cur_hx = obj["plate_hx"]
            obj["counter"] = (obj["counter"] + 1) & 0xFF
            def write_plate(phx, val):                              # shape 18: 6w, 15 rows every 2
                for r in range(0, 30, 2):
                    by = hy + r
                    for c in range(6):
                        bx = phx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = val
            if obj["counter"] & 3:
                write_plate(cur_hx, CT_WALL)                        # 0x181A: keep it present
                return
            write_plate(cur_hx, 0)                                  # 0x182A: erase at the old spot
            val = (self.switch_state[var] + 1) & 0xFF
            if val >= 52:
                val = 0
            self.switch_state[var] = val
            x_off, anim_frame, tile_col = self.PLATE_POS[val]
            base_tile = tile + tile_col if not is_right else tile - tile_col
            fg = {}
            for toff, ti in (self.PLATE_RIGHT if is_right else self.PLATE_LEFT)[anim_frame]:
                idx = base_tile + toff
                if 0 <= idx < MAP_COLS * MAP_ROWS:
                    fg[idx] = ti
            for c in range(tile_col):                               # 0x1872: trail tile 71, rows +1/+3
                tc = tile + c if not is_right else tile - c
                for row_off in (20, 60):
                    if 0 <= tc + row_off < MAP_COLS * MAP_ROWS:
                        fg[tc + row_off] = 71
            obj["fg_tiles"] = fg
            new_cx = x + x_off if not is_right else x - x_off + 4
            obj["plate_hx"] = new_cx // 2
            write_plate(obj["plate_hx"], CT_WALL)

    def _glow_tiles(self, tile, frame):
        return {tile + dc + dr * MAP_COLS: self.GLOW_FRAMES[frame][i]
                for i, (dc, dr) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1)))}

    def update_beams(self):
        """Transporter beams: beam-in 0x1FBF (frames 15 -> 0 then blank, Joe appears at 12),
        beam-out 0x1F18 (frames 0 -> 16, Joe vanishes at 12, done on the 18th update).
        One frame per 0x46 ticks; the beam-in waits 0x1F4 ticks before its first frame."""
        bi = self.beam_in
        while bi is not None and bi["next"] <= self.tick:
            bi["next"] += self.BEAM_INTERVAL
            bi["frame"] -= 1
            if bi["frame"] < 0:
                self.beam_in = bi = None
        bo = self.beam_out
        while bo is not None and bo["next"] <= self.tick:
            bo["next"] += self.BEAM_INTERVAL
            bo["frame"] += 1
            if bo["frame"] > 16:                                    # 0x1F87: 18th update
                self.beam_out = None
                self.finish_beam_out(bo)
                bo = None

    def finish_beam_out(self, bo):
        if bo is None:
            return
        if "dest_room" in bo:                                       # teleporter: Joe moves, beams in
            dest_room, dest_tile = bo["dest_room"], bo["dest_tile"]
            self.player.x = (dest_tile % MAP_COLS) * TILE_W + 23
            self.player.y = (dest_tile // MAP_COLS) * TILE_H + 16
            self.player.vy = self.player.frac = 0
            if dest_room != self.current_room:
                self.carry_mobiles()
                self.current_room = dest_room
                self.player.explosions.clear()
            self.cbm_cache.pop(self.current_room, None)
            self.cbm_backup.pop(self.current_room, None)
            self.last_room = None                                   # objects re-init
            self.start_beam_in(dest_tile)                           # 0x2020
        else:
            self.end_level(won=True)                                # level-complete beam-out

    def start_beam_in(self, tile):
        # frame 16 = not started yet; the first update (after the delay) shows frame 15
        self.beam_in = {"tile": tile, "frame": 16, "next": self.tick + self.BEAM_IN_DELAY}
        self.player.next_time = self.tick + self.BEAM_IN_DELAY + self.JOE_AFTER_BEAM   # 0x2006
        play_sound(SND_TRANSPORTER)                                 # 0x2020 / 0x0AFC

    def beam_fg_tiles(self):
        """Foreground tiles the active beam has written (0x4B4 through table DS:0x3389)."""
        beam = self.beam_out or self.beam_in
        if beam is None:
            return {}
        f = beam["frame"]
        if not 0 <= f <= 16 or (beam is self.beam_in and f == 16):
            return {}
        col, row = beam["tile"] % MAP_COLS, beam["tile"] // MAP_COLS
        return {(row + toff // 20) * MAP_COLS + col + toff % 20: ti for toff, ti in BEAM_FRAMES[f]}

    def draw_objects(self, surface, room_idx):
        """Background-layer parts of the room objects: fans of types 3-4 and the toggle pad's
        tile (0x4D2 / a direct map write), and the captive sprite in a cage."""
        if room_idx not in self.room_objects:
            return
        fg = self.levels[self.current_level]["map"][room_idx * ROOM_BYTES + 640:room_idx * ROOM_BYTES + 960]
        for obj in self.room_objects[room_idx]:
            for idx, ti in obj.get("bg_tiles", {}).items():
                if obj["type"] in (3, 4) and fg[idx] == 255:        # 0x4EA: opaque foreground wins
                    continue
                surface.blit(self.tile_surfs[ti], ((idx % MAP_COLS) * TILE_W, (idx // MAP_COLS) * TILE_H))
            if obj["type"] == 10 and obj.get("disappear", -1) < 12 and len(obj["params"]) >= 3 \
                    and obj["params"][2] < len(self.sprites):
                sp = self.sprites[obj["params"][2]]                 # freed at beam frame 12 (0x1FA7)
                surface.blit(sp["surf"], (obj["x"] + 23 + sp["x_off"], obj["y"] + 10 + sp["y_off"]))

    def start_teleport(self, obj):
        """0x22C5: begin the beam-out at the teleporter; its completion moves Joe to
        dest_room/dest_tile and starts the beam-in there."""
        dest_room = obj["params"][1] if len(obj["params"]) > 1 else 0
        dest_tile = obj["params"][2] if len(obj["params"]) > 2 else 0
        play_sound(SND_TRANSPORTER)                       # 0x1F62 (beam-out object init)
        self.beam_out = {"tile": obj["params"][0], "frame": 0, "next": self.tick,
                         "dest_room": dest_room, "dest_tile": dest_tile,
                         "src_room": self.current_room}

    # ------------------------------------------------------------------
    # Room entry, enemy scheduling, Joe's collision marker and death
    # ------------------------------------------------------------------
    def exit_room(self, room, x, y):
        """ROOM_TRANSITION 0x0521 for any object at (x, y) in `room`: None while inside the
        320x192 area, else (new_room or None, wrapped_x, wrapped_y) using the room's exit table
        (two rooms per edge, split at the middle of that edge). None room = no exit that way."""
        cx, dy = x - 160, y - 96
        if room is None or room >= len(self.room_headers):
            return None
        hdr = self.room_headers[room]
        if dy < -96:
            dy += 192
            new = hdr[0]
            if hdr[0] != hdr[1]:
                if cx >= 0:
                    new = hdr[1]
                    cx -= 320
                cx += 160
        elif dy >= 96:
            dy -= 192
            new = hdr[5]
            if hdr[4] != hdr[5]:
                if cx >= 0:
                    new = hdr[4]
                    cx -= 320
                cx += 160
        elif cx < -160:
            cx += 320
            new = hdr[7]
            if hdr[6] != hdr[7]:
                if dy >= 0:
                    new = hdr[6]
                    dy -= 192
                dy += 96
        elif cx >= 160:
            cx -= 320
            new = hdr[2]
            if hdr[2] != hdr[3]:
                if dy >= 0:
                    new = hdr[3]
                    dy -= 192
                dy += 96
        else:
            return None
        return (None if new == 0xFF else new), cx + 160, dy + 96

    def make_dormant(self, e):
        """A mobile object leaves the live list and waits in self.dormant (slot visible=0)."""
        e.visible = 0
        self.dormant.append(e)

    def carry_mobiles(self):
        """Room change 0x0802, phases 1-3, run BEFORE current_room changes. Every live mobile
        object is cloned (AX=4, 0x09A6): the original goes dormant where it is (it wakes if Joe
        is back within ~6 s), the clone (visible=2) keeps flying in 100-tick steps of simulated
        time until it crosses an edge and goes dormant in the room beyond, stamped with its
        simulated arrival time, or dies. Joe's marker is absent during this, as in the original.
        The original loops until every clone has settled; a cap guards against a stuck one."""
        self.cbm = self.get_collision_bitmap(self.current_room)[0]
        self.cbm_bak = self.cbm_backup[self.current_room]
        clones = []
        for e in list(self.entities):
            if e.mobile and e.alive and e.visible == 1:
                c = copy.copy(e)
                c.visible = 2
                clones.append(c)
                self.make_dormant(e)
            elif e.keeps_slot and e.alive and e.visible == 1:      # AX=3 HIDE keeps the slot
                e.hide(self)
                self.make_dormant(e)
        t = self.tick
        limit = t + 12000
        while clones and t < limit:
            t += 100
            for c in list(clones):
                while c.alive and c.visible == 2 and c.next_time <= t:
                    c.update(self)
                    c.next_time += c.interval
                if not c.alive or c.visible != 2:
                    clones.remove(c)
        for c in clones:                                  # phase 3: still in transit → destroyed
            c.alive = False
        self.entities = [e for e in self.entities if e.alive and e.visible == 1]

    def wake_dormant(self):
        """Main loop 0x071C / room entry 0x0916: a dormant object in Joe's room whose time has
        come is activated (AX=1) and resumes where it was parked."""
        pending, self.dormant = self.dormant, []
        for e in pending:
            if not e.alive or e.room is None:
                continue
            if e.room == self.current_room and e.next_time <= self.tick:
                e.activate(self)
                if self.enhanced and isinstance(e, (Shot, TurretShot)):
                    self.catch_up(e)
                if e.alive and e.visible == 1:
                    self.entities.append(e)
            else:
                self.dormant.append(e)

    def catch_up(self, e):
        """Enhanced mode: a shot parked at a room edge is run through the updates it missed, so
        it reappears where it would be by now, which usually means it has already hit a wall or
        left (the original, 0x06F8, resumes it from the edge up to ~6 s later: Cam found that
        wrong). Run as a transit clone (visible 2) so no stale explosion is shown."""
        e.visible = 2
        n = 0
        while e.alive and e.visible == 2 and e.next_time + e.interval <= self.tick and n < 2000:
            e.update(self)
            e.next_time += e.interval
            n += 1
        if e.visible == 2:
            e.visible = 1

    def purge_dormant(self):
        """Timer tick 0x0A13 (once per second, with the TIME countdown): dormant objects more
        than 0x1B58 (7000) ticks past their time are destroyed (AX=5)."""
        keep = []
        for e in self.dormant:
            if self.tick - e.next_time < 0x1B58:
                keep.append(e)
            else:
                e.destroy(self)
        self.dormant = keep

    def jump_to_room(self, room):
        """Debug helper (G key, [ ], --start): switch rooms without a door and drop Joe on the
        nearest free spot so he does not start inside a wall or a pit."""
        if not 0 <= room < self.num_rooms:
            return False
        for e in self.dormant + self.entities:
            if e.keeps_slot:
                e.destroy(self)
        self.dormant = []
        self.current_room = room
        self.beam_in = self.beam_out = None
        self.player.next_time = self.tick            # no beam-in wait when debugging
        self.death = None
        self.entities = [e for e in self.entities if not isinstance(e, (Shot, TurretShot))]
        self.player.explosions.clear()
        cbm = self.get_collision_bitmap(room)[0]
        px, py = int(self.player.x), int(self.player.y)
        py = max(16, min(py, SCREEN_H - 48))
        best = None
        for radius in range(0, 200, 2):
            for dx in range(-radius, radius + 1, 2):
                for dy in (-radius, radius) if radius else (0,):
                    for cx, cy in ((px + dx, py + dy), (px + dy, py + dx)):
                        if 8 <= cx < SCREEN_W - 8 and 8 <= cy < SCREEN_H - 40 and not joe_hits_bg(cbm, cx, cy):
                            dist = (cx - px) ** 2 + (cy - py) ** 2
                            if best is None or dist < best[0]:
                                best = (dist, cx, cy)
            if best is not None:
                break
        if best is not None:
            self.player.x, self.player.y = float(best[1]), float(best[2])
        self.player.vy = self.player.frac = 0
        self.joe_marked = None
        return True

    def enter_room(self):
        """Called whenever current_room changes. The original (0x0802) destroys every object of
        the old room and re-runs the init handlers of the new room's object list, so enemies and
        generator countdowns start fresh each visit."""
        room = self.current_room
        self.last_room = room
        self.entities = []
        self.joe_marked = None
        self.cbm = self.get_collision_bitmap(room)[0]
        self.cbm_bak = self.cbm_backup[room]
        for obj in self.room_objects.get(room, []):
            t = obj["type"]
            tile = obj["params"][0]
            self.init_room_object(obj)
            if t == 10 and obj.get("disappear", -1) < 0:
                play_sound(SND_HELP)                      # 0x1406: captive init
            if t in (11, 12, 14, 20, 23) and not self.enemies_enabled:
                continue                                  # debug: --no-enemies / E key
            if t in (22, 23):                             # enhanced mode: pack / turret
                var = obj["params"][1 if t == 23 else 2] if len(obj["params"]) > 2 else 0
                if self.enhanced and self.switch_state[var] != 0:
                    self.entities.append((Turret if t == 23 else Pack)(self, obj))
                continue
            if t == 14:
                var_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                if self.switch_state[var_id] != 0:        # 0x232E: skipped if its variable is 0
                    self.entities.append(Sentry(self, obj["x"], obj["y"], var_id))
            elif t == 11:
                self.entities.append(BirdGen(self, tile))
            elif t == 12:
                self.entities.append(BallGen(self, tile))
            elif t == 20:
                self.entities.append(OrbGen(self, tile))
            elif t == 18:
                self.entities.append(SensorSwitch(self, obj))
            elif t == 19:
                self.entities.append(Teleporter(self, obj))
        self.wake_dormant()

    def update_entities(self):
        """Main loop 0x06F8: run every object whose next_time has passed, as often as needed."""
        room = self.current_room
        self.cbm = self.get_collision_bitmap(room)[0]
        self.cbm_bak = self.cbm_backup[room]
        if self.dormant:
            self.wake_dormant()
        for e in list(self.entities):
            n = 0
            while e.alive and e.next_time <= self.tick and n < 8:
                e.update(self)
                e.next_time += e.interval
                n += 1
        self.entities = [e for e in self.entities if e.alive and e.visible == 1]

    def draw_entities(self, surface):
        """Enemy layer (sprite priority 3-5: below Joe). Generator tiles are background."""
        for e in self.entities:
            if isinstance(e, (Generator, SensorSwitch)):
                e.draw_tiles(surface, self.tile_surfs)
        for e in self.entities:
            if not isinstance(e, (Generator, SensorSwitch)):
                e.draw(surface, self.sprites, self.frame_no)

    def joe_check_and_unmark(self, cbm, backup):
        """Start of Joe's update (0x0CCC-0x0CF0). With his own type-14 marker still in place
        from last frame, any byte under his shape that is neither 14 nor a wall (1) means
        something killed him: a field/laser/orb/ring restored the backup (0) or an enemy wrote
        its own type (6). Then erase his marker so movement checks don't see it."""
        px, py = int(self.player.x), int(self.player.y)
        hx, hy = px >> 1, py >> 1
        if self.joe_marked is cbm:
            total, hist = cb_check(cbm, 0, hx, hy, CT_JOE)
            if total and total != hist[CT_WALL]:
                if os.environ.get("JPJ_DEBUG"):
                    print(f"DEATH at ({px},{py}) room {self.current_room}: bytes under Joe by type "
                          f"{ {t: n for t, n in enumerate(hist) if n} }")
                self.start_death()
            cb_restore_if(cbm, backup, 0, hx, hy, CT_JOE)
        self.joe_marked = None

    def joe_mark(self):
        """End of Joe's update (0x0E3B): DRAW_COLLISION(shape 0, type 14) at his position."""
        cbm = self.get_collision_bitmap(self.current_room)[0]
        cb_write(cbm, 0, int(self.player.x) >> 1, int(self.player.y) >> 1, CT_JOE)
        self.joe_marked = cbm

    def shield_save(self):
        """Enhanced mode: True if a death is absorbed, by a shield (consumed, then SHIELD_INVULN
        ticks of invulnerability) or by that invulnerability itself."""
        p = self.player
        if self.tick < p.invuln_until:
            return True
        if p.pack == PACK_SHIELD:
            p.pack = None
            p.invuln_until = self.tick + SHIELD_INVULN
            p.explosions.append(Explosion(int(p.x), int(p.y) - 10))    # the shield shatters
            return True
        return False

    def find_clear_near(self, x, y, radius):
        """The nearest position within `radius` px where Joe's shape is clear, or None."""
        cbm = self.get_collision_bitmap(self.current_room)[0]
        best = None
        for r in range(2, radius + 1, 2):
            for d in range(-r, r + 1, 2):
                for cx, cy in ((x + d, y - r), (x + d, y + r), (x - r, y + d), (x + r, y + d)):
                    if 8 <= cx < SCREEN_W - 8 and 8 <= cy < SCREEN_H - 8 and Player._clear(cbm, cx, cy):
                        dist = (cx - x) ** 2 + (cy - y) ** 2
                        if best is None or dist < best[0]:
                            best = (dist, cx, cy)
            if best is not None:
                return best[1], best[2]
        return None

    def shield_knockback(self, x, y):
        """Enhanced mode: a crush that the shield absorbs throws Joe to the nearest free spot
        (or leaves him where he is until whatever overlaps him has gone). None = no shield."""
        if not self.enhanced or not self.shield_save():
            return None
        return self.find_clear_near(x, y, 40) or (x, y)

    def start_death(self):
        """GAME.EXE 0x0F05: Joe's death sequence. First step after 80 ticks, then every 70."""
        if self.death is not None:
            return
        if self.enhanced and self.shield_save():
            return
        self.death = {"frame": 0, "next": self.tick + 80, "sprite": None, "hidden": False}
        self.player.vy = 0

    def update_death(self):
        d = self.death
        px, py = int(self.player.x), int(self.player.y)
        while d["next"] <= self.tick:
            d["next"] += 70
            d["frame"] += 1
            f = d["frame"]
            if 1 <= f <= 15:
                # Joe tumbles through his own 8 frames; small glow bursts around him
                d["sprite"] = f & 7
                self.player.explosions.append(Explosion(px + random.randrange(29) - 13,
                                                        py + random.randrange(23) - 11))
            elif 16 <= f <= 23:
                # Debris sprites 46-49, each shown twice; wider glow bursts
                d["sprite"] = 46 + (f - 16) // 2
                self.player.explosions.append(Explosion(px + random.randrange(37) - 18,
                                                        py + random.randrange(45) - 22))
            elif f == 25:
                d["hidden"] = True               # FREE_SPRITE of Joe (0x0FCD)
            elif f >= 58:
                self.finish_death()              # [0x305E] = 1: level loop exits (0x0FDB)
                return
        for e in self.player.explosions:
            e.update()
        self.player.explosions[:] = [e for e in self.player.explosions if e.alive]

    def finish_death(self):
        self.death = None
        self.end_level(won=False)

    def end_level(self, won):
        """Level loop exit 0x078B-0x07A8: fade the palette out, then the caller (0x01CB-0x02D5)
        decides. A completed level earns the thumbs-up and the next level, the credits after
        the last one; a lost level simply restarts, after the reaper the first time. There
        are no lives. After the credits the original exits to DOS; here the title comes back."""
        def after_fade():
            if won:
                nxt = self.current_level + 1 if self.current_level + 1 < 3 else None
                if nxt is not None:
                    self.play_cutscene(ANIM_THUMBS_UP, lambda: self.set_level(nxt))
                else:
                    again = self.current_level if self.current_level >= 3 else 0
                    self.play_cutscene(ANIM_THUMBS_UP, lambda: self.play_cutscene(
                        ANIM_CREDITS, lambda: self.play_cutscene(
                            ANIM_TITLE, lambda: self.set_level(again))))
            elif not self.reaper_shown:
                self.reaper_shown = True
                self.play_cutscene(ANIM_REAPER, lambda: self.set_level(self.current_level))
            else:
                self.set_level(self.current_level)
        self.fade = {"t0": self.tick, "dir": -1, "then": after_fade}

    def play_cutscene(self, idx, then):
        """0x2750 entry `idx`; `then` runs when it is over (at once with --no-anims)."""
        if not self.anims_enabled:
            then()
            return
        self.cutscene = Cutscene(idx, self.tick)
        self.cutscene_then = then

    def spawn_timeout_beam(self):
        """0x0A5E: up to five random tiles (column <= 17) whose 3x3 block has no foreground
        tiles and whose centre is clear of everything (shape 16) get a TimeoutBeam."""
        room = self.current_room
        map_data = self.levels[self.current_level]["map"]
        fg = map_data[room * ROOM_BYTES + 640:room * ROOM_BYTES + 960]
        cbm = self.get_collision_bitmap(room)[0]
        for _ in range(5):
            tile = random.randrange(0x118)
            col, row = tile % MAP_COLS, tile // MAP_COLS
            if col > 0x11:
                continue
            if any(fg[(row + dr) * MAP_COLS + col + dc] for dr in range(3) for dc in range(3)):
                continue                                  # [0x5D7 + 2*tile]: foreground map words
            x, y = col * TILE_W + 0x17, row * TILE_H + 0x11
            if cb_check(cbm, 0x10, x >> 1, y >> 1, 0)[0] != 0:
                continue
            self.entities.append(TimeoutBeam(self, tile, x, y))
            return

    def change_room(self, new_room, x, y):
        """ROOM CHANGE 0x0802 for Joe's own transition (0x0E30) — Joe lands at (x, y)."""
        if os.environ.get("JPJ_DEBUG"):
            print(f"TRANSITION: room {self.current_room}→{new_room}  pos ({self.player.x},{self.player.y})→({x},{y})")
        self.carry_mobiles()
        self.cbm_cache.pop(self.current_room, None)       # 0x032A rebuilds a room on entry
        self.cbm_backup.pop(self.current_room, None)
        self.current_room = new_room
        self.player.x, self.player.y = x, y
        self.player.explosions.clear()
        self.enter_room()

    def set_level(self, level):
        if 0 <= level < len(self.levels):
            self.current_level = level
            self.build_assets()
            self.current_room = self.start_room
            # Position Joe at beam-in tile (matching GAME.EXE 0x0C7E)
            bcol = self.beam_tile % MAP_COLS
            brow = self.beam_tile // MAP_COLS
            self.player = Player(bcol * TILE_W + 23, brow * TILE_H + 16)
            self.player.next_time = self.tick
            self.player.time = self.level_timer           # 0x063C: shown once 0x09DE first runs
            self.time_counter = 0
            self.beam_out = None
            self.start_beam_in(self.beam_tile)   # 0x0C5B-0x0C78 / 0x1FBF
            self.level_complete_timer = 0
            self.fade = {"t0": self.tick, "dir": 1, "then": None}   # 0x075E: palette fade-in
            self.cbm_cache = {}
            self.cbm_backup = {}
            self.entities = []
            self.dormant = []
            self.last_room = None
            self.joe_marked = None
            self.death = None

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and self.goto_buf is not None:
                    # G mode: type a room number, Enter jumps, Esc cancels
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.goto_buf:
                            self.jump_to_room(int(self.goto_buf))
                        self.goto_buf = None
                    elif event.key == pygame.K_ESCAPE:
                        self.goto_buf = None
                    elif event.key == pygame.K_BACKSPACE:
                        self.goto_buf = self.goto_buf[:-1]
                    elif event.unicode.isdigit() and len(self.goto_buf) < 2:
                        self.goto_buf += event.unicode
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.set_level(self.current_level)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self.jump_to_room(self.current_room + 1)
                    elif event.key == pygame.K_LEFTBRACKET:
                        self.jump_to_room(self.current_room - 1)
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                        self.set_level(event.key - pygame.K_1)      # 4 = a level loaded with --level
                    elif event.key == pygame.K_g:
                        self.goto_buf = ""
                    elif event.key == pygame.K_e:
                        self.enemies_enabled = not self.enemies_enabled
                        self.last_room = None             # respawn the room's objects
                        print("enemies", "on" if self.enemies_enabled else "off")
                    elif event.key == pygame.K_t:
                        self.set_level(1)
                        self.current_room = 18
                        self.beam_in = None
                    elif event.key == pygame.K_s:
                        n = 0
                        while os.path.exists(os.path.join(BASE, f"screenshot_{n:03d}.png")):
                            n += 1
                        fname = f"screenshot_{n:03d}.png"
                        shot = self.window.convert(24)
                        pygame.image.save(shot, os.path.join(BASE, fname))
                        print(f"Saved {fname}")

            if self.cutscene is not None:
                self.tick += TICKS_PER_FRAME
                self.cutscene.update(self.tick)
                self.cutscene.draw(self.screen)
                pygame.transform.scale(self.screen, (WIN_W, WIN_H), self.window)
                pygame.display.flip()
                if self.cutscene.done:
                    then, self.cutscene = self.cutscene_then, None
                    then()
                continue
            frozen = self.fade is not None and self.fade["dir"] < 0    # 0x079E fade-out
            if frozen:
                self.tick += TICKS_PER_FRAME
            else:
                self.tick += TICKS_PER_FRAME
                self.frame_no += 1
                if self.current_room != self.last_room:
                    self.enter_room()
                # Joe is frozen by the beam-out, and until 0x410 ticks after the beam-in's
                # first frame (0x2006), which is where its frame has reached 1.
                beaming = self.beam_out is not None or (self.beam_in is not None and self.beam_in["frame"] > 1)
                dying = self.death is not None
                keys = pygame.key.get_pressed()
                inp = 0
                if not beaming and not dying:
                    if keys[pygame.K_LEFT]:
                        inp |= INP_LEFT
                    if keys[pygame.K_RIGHT]:
                        inp |= INP_RIGHT
                    if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                        inp |= INP_THRUST
                    if keys[pygame.K_z]:
                        inp |= INP_FIRE
                if dying:
                    self.update_death()
                elif not beaming:
                    self.update_room_objects()
                    # Joe runs every 10 ticks (0x06BB), ~1.94 times per 60 Hz frame
                    while self.player.next_time <= self.tick and self.death is None:
                        self.player.step(self, inp)
                        self.player.next_time += JOE_INTERVAL
                    if self.player.next_time <= self.tick:          # died mid-frame: stay in step
                        self.player.next_time = self.tick + JOE_INTERVAL
                    self.player.update_explosions()
                else:
                    self.update_room_objects()
                    self.player.next_time = self.tick + JOE_INTERVAL
                if self.current_room != self.last_room:
                    self.enter_room()
                self.update_entities()
                # Level completion: start beam-out when all captives rescued
                if self.captive_count <= 0 and self.beam_out is None and self.level_complete_timer == 0:
                    # Convert Joe's position to tile for beam-out (matching GAME.EXE 0x0C27)
                    tile = (int(self.player.y) // TILE_H) * MAP_COLS + (int(self.player.x) // TILE_W)
                    self.beam_out = {"tile": tile, "frame": 0, "next": self.tick}
                    play_sound(SND_TRANSPORTER)       # 0x1F62 via 0x0C27
                    self.level_complete_timer = 1  # flag: beam-out started
                self.time_counter += 1
                if self.time_counter >= FPS:              # 0x09DE every 0x48D = 1165 ticks
                    self.time_counter = 0
                    if self.player.time > 0:
                        self.player.time -= 1
                    else:
                        self.spawn_timeout_beam()         # 0x0A38 AX=0: TIME has run out
                    self.purge_dormant()                  # 0x0A13

            self.draw()
            pygame.display.flip()
            if frozen and self.tick - self.fade["t0"] >= FADE_TICKS:
                then, self.fade = self.fade["then"], None
                then()
        pygame.quit()

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.render_room(self.current_room), (0, 0))
        self.draw_objects(self.screen, self.current_room)
        self.draw_entities(self.screen)
        if True:
            joe_hidden = False
            if self.beam_out and self.beam_out["frame"] >= 12:
                joe_hidden = True
            if self.beam_in and self.beam_in["frame"] > 12:
                joe_hidden = True
            if self.death is not None and self.death["hidden"]:
                joe_hidden = True
            if not joe_hidden:
                if self.death is not None and self.death["sprite"] is not None:
                    sp = self.sprites[self.death["sprite"]]
                    self.screen.blit(sp["surf"], (int(self.player.x) + sp["x_off"],
                                                  int(self.player.y) + sp["y_off"]))
                else:
                    self.player.draw(self.screen, self.sprites, self)
        for e in self.entities:
            if isinstance(e, Bird):
                e.draw_laser(self.screen, self.sprites, self.frame_no)
        self.render_foreground(self.current_room, self.screen)
        # Draw explosions on top of everything (they occur at wall edges)
        for e in self.player.explosions:
            e.draw(self.screen, self.sprites)
        for e in self.entities:
            if isinstance(e, EnemyExplosion):
                e.draw_top(self.screen, self.sprites)

        self.draw_status_bar()
        if self.fade is not None:                         # palette fade (0x2A24 / 0x29F2)
            t = self.tick - self.fade["t0"]
            k = min(1.0, t / FADE_TICKS)
            if self.fade["dir"] < 0:
                k = 1.0 - k
            if k < 1.0:
                self.screen.fill((int(255 * k),) * 3, special_flags=pygame.BLEND_MULT)
            if self.fade["dir"] > 0 and t >= FADE_TICKS:
                self.fade = None
        pygame.transform.scale(self.screen, (WIN_W, WIN_H), self.window)


    def draw_status_bar(self):
        """0x4745: the 40-character line at y=192 from the buffer DS:0x2363, seeded from
        DS:0x0321 with attribute 7 (palette 7, grey); 0x09F7 writes the TIME digits with
        attribute 0x0A (palette 10, green). The debug prompts replace the middle text."""
        bar_y = SCREEN_H
        pygame.draw.rect(self.screen, (0, 0, 0), (0, bar_y, SCREEN_W, STATUS_H))
        pal = self.levels[self.current_level]["pal"]
        time_s = f"{max(0, min(999, self.player.time)):03d}"
        middle = "JET PACK JOE DEMO"
        debug = pack = None
        if self.goto_buf is not None:
            debug = f"GO TO ROOM: {self.goto_buf}_".ljust(17)
        elif not self.enemies_enabled:
            debug = "   NO ENEMIES    "
        elif self.enhanced and self.player.pack in PACK_NAMES:      # enhanced: the pack slot
            pack = f"PACK: {PACK_NAMES[self.player.pack]}".ljust(17)
        line = f"TIME: {time_s}   {debug or pack or middle}   ROOM: {self.current_room:02d}"
        draw_text8(self.screen, 0, bar_y, line, pal[7])
        draw_text8(self.screen, 6 * 8, bar_y, time_s, pal[10])
        if debug:
            draw_text8(self.screen, 12 * 8, bar_y, debug, (255, 255, 0))
        elif pack:
            draw_text8(self.screen, 12 * 8, bar_y, pack, pal[11])


def parse_start_arg(argv):
    """`--start L:R` (level 1-3, room number) → (level_index, room) or None."""
    for i, a in enumerate(argv):
        spec = None
        if a.startswith("--start="):
            spec = a.split("=", 1)[1]
        elif a == "--start" and i + 1 < len(argv):
            spec = argv[i + 1]
        if spec:
            lvl, _, room = spec.partition(":")
            if lvl.isdigit() and room.isdigit() and 1 <= int(lvl) <= 4:
                return int(lvl) - 1, int(room)
            raise SystemExit(f"bad --start {spec!r}: use LEVEL:ROOM, e.g. --start 3:13")
    return None


LEVEL_MAGIC = b"JPL1"


def load_level_file(path):
    """A standalone level: b"JPL1", three little-endian u32 sizes, then the map (MPxx format),
    the level data (LVxx format) and the 768-byte palette, then an optional UTF-8 name."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != LEVEL_MAGIC:
        raise SystemExit(f"{path}: not a Jet Pack Joe level file")
    n_map, n_lv, n_pal = struct.unpack_from('<III', data, 4)
    pos = 16
    m = data[pos:pos + n_map]; pos += n_map
    lv = data[pos:pos + n_lv]; pos += n_lv
    pal_raw = data[pos:pos + n_pal]; pos += n_pal
    name = data[pos:].decode("utf-8", "replace") or os.path.basename(path)
    pal = [(pal_raw[i] * 4, pal_raw[i + 1] * 4, pal_raw[i + 2] * 4) for i in range(0, 768, 3)]
    return {"map": m, "lv": lv, "pal": pal, "name": name}


def parse_level_arg(argv):
    """`--level FILE` → path or None."""
    for i, a in enumerate(argv):
        if a.startswith("--level="):
            return a.split("=", 1)[1]
        if a == "--level" and i + 1 < len(argv):
            return argv[i + 1]
    return None


if __name__ == "__main__":
    game = JetPackJoe()
    print("sound:", game.sound.reason)
    level_path = parse_level_arg(sys.argv)
    if level_path:
        game.levels.append(load_level_file(level_path))      # becomes level 4 (key 4)
        game.set_level(len(game.levels) - 1)
    start = parse_start_arg(sys.argv)
    if start:
        game.set_level(start[0])
        game.jump_to_room(start[1])
    elif not level_path:
        game.play_cutscene(ANIM_TITLE, lambda: game.set_level(0))   # 0x01CB: [cs:8](2)
    game.run()
