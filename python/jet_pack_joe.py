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
"""

import struct, os, sys, time, random
from array import array
import pygame

BASE = os.path.dirname(os.path.abspath(__file__))

TILE_W, TILE_H = 16, 12
MAP_COLS, MAP_ROWS = 20, 16
ROOM_BYTES = 960
SCREEN_W = MAP_COLS * TILE_W   # 320
SCREEN_H = MAP_ROWS * TILE_H   # 192
STATUS_H = 16
TOTAL_H = SCREEN_H + STATUS_H  # 208
SCALE = 3
WIN_W, WIN_H = SCREEN_W * SCALE, TOTAL_H * SCALE
FPS = 60
GRAVITY = 0.15
THRUST = -0.35
MAX_FALL = 3.0
MAX_FLY = -3.0
MOVE_SPEED = 2.0
SHOT_SPEED = 5
SHOT_LIFE = 40
TIME_LIMIT = 999

# Joe sprite indices: 0-7 (even=left, odd=right)
JOE_FRAMES_L = [0, 2, 4, 6]
JOE_FRAMES_R = [1, 3, 5, 7]


def load_raw(fn):
    with open(os.path.join(BASE, fn), "rb") as f:
        return f.read()


def load_palette(fn):
    raw = load_raw(fn)
    return [(min(255, raw[i*3]*4), min(255, raw[i*3+1]*4), min(255, raw[i*3+2]*4)) for i in range(256)]


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
CRUSH_NUDGES = ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2), (-2, 2), (2, 2), (2, -2), (-2, -2))


def in_room(x, y):
    """ROOM_TRANSITION (0x0521) exit test for moving objects: leaving the 320x192 area."""
    return 0 <= x < SCREEN_W and 0 <= y < SCREEN_H


# ---------------------------------------------------------------------------
# Enemy / generator entities — ports of the GAME.EXE object handlers.
# Each runs on the original tick scheduler: update() is called whenever game.tick has
# passed next_time, then next_time += interval (handlers may also adjust next_time).
# ---------------------------------------------------------------------------
class Entity:
    interval = 20

    def __init__(self, x, y, tick):
        self.x, self.y = int(x), int(y)
        self.next_time = tick
        self.alive = True
        self.sprite_idx = None

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
    It never checks for intrusions, so it cannot be killed. Two glow sprites (50-53) trail it."""
    interval = 27

    def __init__(self, g, x, y):
        super().__init__(x, y, g.tick)
        self.facing = 1    # [DI+0x1C]
        self.vy = 0        # [DI+0x16]
        self.frac = 0      # [DI+0x18]
        self.thrust = 0    # [DI+0x1D]: 0 idle, 2 thrusting (selects glow sprite 50/51 vs 52/53)
        cb_write(g.cbm, 19 + self.facing, self.x >> 1, self.y >> 1, CT_WALL)   # activate (0x23EA)

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
        cb_write(g.cbm, 16, self.x >> 1, self.y >> 1, CT_ENEMY)   # activate (0x1657)

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        hx, hy = x >> 1, y >> 1
        self.retarget -= 1
        if self.retarget == 0:
            self.retarget = 25
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
        total, hist = cb_check(cbm, 16, hx, hy, CT_ENEMY)
        if total:                                        # something intruded → explode (0x176A)
            cb_restore_if(cbm, backup, 16, hx, hy, CT_ENEMY)
            g.entities.append(EnemyExplosion(g, x, y, self.sprite_idx))
            self.alive = False
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
        if not in_room(nx, ny):
            self.alive = False
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
        if not in_room(nx, ny):
            self.alive = False
            return
        total, hist = cb_check(cbm, 22, nx >> 1, ny >> 1, 0)
        if total == 0:
            self.x, self.y = nx, ny
            self.sprite_idx = 51
        else:
            cb_restore(cbm, backup, 22, nx >> 1, ny >> 1)
            g.entities.append(EnemyExplosion(g, x, y, self.sprite_idx))
            self.alive = False


class Bird(Entity):
    """Handler 0x199A (spawned by bird_generator). Red bird (sprites 29-32) rising 1px per
    update. When Joe's marker is found in the 1-wide column above it (shape 15) it fires a
    laser (sprite 25/26 flickering, 89px tall) for 10 updates; the DRAW_VISUAL of that column
    wipes Joe's marker and kills him. Vanishes silently on hitting a ceiling (type 1)."""
    interval = 20

    @staticmethod
    def can_spawn(g, x, y):
        return cb_check(g.cbm, 2, x >> 1, y >> 1, 0)[0] == 0      # init check at 0x19C0

    def __init__(self, g, x, y):
        super().__init__(x, y, g.tick)
        self.sprite_idx = 29     # [DI+0x1C]
        self.frame_acc = 0       # [DI+0x1D]
        self.laser = 0           # [DI+0x16]
        cb_write(g.cbm, 2, self.x >> 1, self.y >> 1, CT_ENEMY)   # activate (0x1A54)

    def update(self, g):
        cbm, backup = g.cbm, g.cbm_bak
        x, y = self.x, self.y
        hx, hy = x >> 1, y >> 1
        if self.laser == 0:
            total, hist = cb_check(cbm, 15, hx, hy, 0)
            if hist[CT_JOE]:
                self.laser = 10
                cb_restore(cbm, backup, 15, hx, hy)
        total, hist = cb_check(cbm, 2, hx, hy, CT_ENEMY)
        if total:                                        # intruded → explode (0x1B42)
            cb_restore_if(cbm, backup, 2, hx, hy, CT_ENEMY)
            g.entities.append(EnemyExplosion(g, x, y, self.sprite_idx))
            self.alive = False
            return
        cb_restore_if(cbm, backup, 2, hx, hy, CT_ENEMY)
        ny = y - 1
        if not in_room(x, ny):
            self.alive = False
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
SOUND_NAMES = ("explosion", "shoot", "help me", "transporter", "thank you")
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
        if not enabled:
            return
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            info = pygame.mixer.get_init()
        except pygame.error:
            info = None
        if not info:
            return
        rate, fmt, nch = info
        data = load_raw("DS00.DAT")
        offs = [struct.unpack_from('<H', data, 2 * i)[0] * 16 for i in range(6)]
        for i in range(5):
            self.sounds.append(self._convert(data[offs[i]:offs[i + 1]], rate, nch))
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


class Shot:
    """Moving projectile matching original GAME.EXE handler 0xFE3.
    Moves ±2px every frame. On wall hit: spawn Explosion, die immediately."""
    def __init__(self, x, y, direction, explosions):
        self.x, self.y = float(x), float(y)
        self.direction = direction
        self.sprite_idx = 23 if direction > 0 else 24
        self.alive = True
        self.explosions = explosions  # shared list to append explosions to

    INTERVAL = 15   # [DI+8] = 0x0F ticks between moves

    def update(self, cbm, backup=None):
        """One render frame: step every 15 ticks (GAME.EXE 0x1084)."""
        if not self.alive:
            return
        self.acc = getattr(self, "acc", 0.0) + TICKS_PER_FRAME
        while self.alive and self.acc >= self.INTERVAL:
            self.acc -= self.INTERVAL
            self.x += self.direction * 2
            if self.x < 0 or self.x >= SCREEN_W:
                self.alive = False
                return
            hx, hy = int(self.x) >> 1, int(self.y) >> 1
            total, hist = cb_check(cbm, 1, hx, hy, 0)
            if total == 0:
                continue
            if hist[CT_JOE] == 0:
                # Hit a wall or enemy: restore backup under the 4x2 shape (this is what wounds
                # a ball/bird — their own bytes get wiped), spawn explosion, die.
                cb_restore(cbm, backup, 1, hx, hy)
                self.explosions.append(Explosion(self.x, self.y))
                self.alive = False
            elif total != hist[CT_JOE]:
                self.alive = False          # Joe plus something else: vanish silently
            # only Joe under the shot: keep flying

    def draw(self, surface, sprites):
        if self.alive and self.sprite_idx < len(sprites):
            sp = sprites[self.sprite_idx]
            surface.blit(sp["surf"], (int(self.x) + sp["x_off"], int(self.y) + sp["y_off"]))


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.direction = 1
        self.thrusting = False
        self.time = TIME_LIMIT
        self.lives = 3
        self.shots = []
        self.explosions = []
        self.fire_cooldown = 0
        self.anim_frame = 0
        self.anim_timer = 0
        self.thrust_timer = 0

    def _get_sprite(self, sprites):
        frames = JOE_FRAMES_R if self.direction > 0 else JOE_FRAMES_L
        return sprites[frames[self.anim_frame]]

    def update(self, cbm, sprites, pipe_floors=(), pipe_ceilings=(), backup=None):
        sp = self._get_sprite(sprites)

        # --- Horizontal movement ---
        old_x = self.x
        self.x += self.vx
        if joe_hits_bg(cbm, self.x, self.y):
            found = False
            for dy in (-2, 2, -4, 4, -6, 6):
                if not joe_hits_bg(cbm, self.x, self.y + dy):
                    self.y += dy
                    found = True
                    break
            if not found:
                self.x = old_x

        # --- Vertical movement ---
        self.vy += GRAVITY
        if self.thrusting:
            self.vy += THRUST
        self.vy = max(MAX_FLY, min(MAX_FALL, self.vy))
        old_y = self.y
        self.y += self.vy
        if joe_hits_bg(cbm, self.x, self.y):
            # Try nudging horizontally to slide into openings
            found = False
            for dx in (-2, 2, -4, 4, -6, 6):
                if not joe_hits_bg(cbm, self.x + dx, self.y):
                    self.x += dx
                    found = True
                    break
            if not found:
                self.y = old_y
                self.vy = 0


        # Pipe floors and ceilings: invisible platforms
        # When falling, check ceilings first (land ON pipe), then floors (land IN pipe)
        if self.vy >= 0:
            feet_y = int(self.y) + 14
            joe_l = int(self.x) - 16
            joe_r = int(self.x) + 15
            landed = False
            # Ceilings act as floors when falling from above
            for x1, x2, ceil_y in pipe_ceilings:
                if joe_r > x1 and joe_l < x2 and old_y + 14 <= ceil_y <= feet_y:
                    self.y = ceil_y - 14
                    self.vy = 0
                    landed = True
                    break
            if not landed:
                # Pipe floors inside pipes
                for x1, x2, floor_y in pipe_floors:
                    if joe_r > x1 and joe_l < x2 and int(self.y) <= floor_y <= feet_y:
                        self.y = floor_y - 14
                        self.vy = 0
                        break

        # Pipe ceilings: invisible barriers at top of pipes
        if self.vy < 0:
            head_y = int(self.y) - 14
            joe_l = int(self.x) - 16
            joe_r = int(self.x) + 15
            for x1, x2, ceil_y in pipe_ceilings:
                if joe_r > x1 and joe_l < x2 and head_y <= ceil_y <= int(self.y):
                    self.y = ceil_y + 14
                    self.vy = 0
                    break

        # No screen clamping — room transitions handle edge-of-screen

        # Animation
        # Animation: frame 0 = static, only cycle when firing
        if self.fire_cooldown > 0:
            self.anim_timer += 1
            if self.anim_timer >= 8:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 4
        else:
            self.anim_frame = 0
            self.anim_timer = 0

        # Thrust flame: grows over time while thrusting or moving
        if self.thrusting or self.vx != 0:
            self.thrust_timer = min(self.thrust_timer + 1, 30)
        else:
            self.thrust_timer = 0

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        for s in self.shots:
            s.update(cbm, backup)
        self.shots = [s for s in self.shots if s.alive]
        for e in self.explosions:
            e.update()
        self.explosions[:] = [e for e in self.explosions if e.alive]

    def fire(self):
        if self.fire_cooldown <= 0:
            gun_x = self.x + (12 if self.direction > 0 else -12)
            gun_y = self.y + 2
            self.shots.append(Shot(gun_x, gun_y, self.direction, self.explosions))
            self.fire_cooldown = 8
            play_sound(SND_SHOOT)                # 0x0EF8

    def draw(self, surface, sprites):
        sp = self._get_sprite(sprites)
        # Draw Joe
        surface.blit(sp["surf"], (int(self.x) + sp["x_off"], int(self.y) + sp["y_off"]))
        # Draw thrust flame on top of Joe
        if self.thrust_timer > 0 and (self.thrusting or self.vx != 0):
            size = 0 if self.thrust_timer < 10 else (1 if self.thrust_timer < 20 else 2)
            if self.vx > 0:
                flame_idx = [11, 15, 19][size]
            elif self.vx < 0:
                flame_idx = [10, 14, 18][size]
            else:
                flame_idx = [9, 13, 17][size] if self.direction > 0 else [8, 12, 16][size]
            if flame_idx < len(sprites):
                fl = sprites[flame_idx]
                surface.blit(fl["surf"], (int(self.x) + fl["x_off"], int(self.y) + fl["y_off"]))
        for s in self.shots:
            s.draw(surface, sprites)
        for e in self.explosions:
            e.draw(surface, sprites)


class JetPackJoe:
    def __init__(self):
        pygame.init()
        self.sound = SoundBank(sound_enabled_from_args(sys.argv))
        self.window = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Jet Pack Joe — Joe Lowe (1990s)")
        self.screen = pygame.Surface((SCREEN_W, TOTAL_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 10)

        self.blk = load_raw("BK00.DAT")
        self.col_data = load_raw("CB00.DAT")
        self.sp_data = load_raw("SP00.DAT")
        self.num_tiles = len(self.blk) // (TILE_W * TILE_H)

        self.levels = [
            {"map": load_raw("MP11.DAT"), "pal": load_palette("PL11.DAT"), "name": "Level 1"},
            {"map": load_raw("MP12.DAT"), "pal": load_palette("PL12.DAT"), "name": "Level 2"},
            {"map": load_raw("MP13.DAT"), "pal": load_palette("PL13.DAT"), "name": "Level 3"},
        ]

        self.current_level = 0
        self.time_counter = 0
        self.tick = 0.0          # object counter (INT 62h DX=0), advanced TICKS_PER_FRAME per frame
        self.frame_no = 0        # render frame number ([0x2361]) — drives sprite flicker
        self.entities = []       # enemies, generators, enemy explosions in the current room
        self.last_room = None
        self.joe_marked = None   # the cbm Joe's type-14 marker is currently stamped in
        self.death = None        # Joe death animation state (GAME.EXE 0x0F05)
        self.cbm = self.cbm_bak = None
        self.goto_buf = None     # digits typed after G (debug "go to room"), None when inactive
        self.enemies_enabled = "--no-enemies" not in sys.argv and os.environ.get("JPJ_ENEMIES", "1") != "0"
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
        lv_files = ["LV11.DAT", "LV12.DAT", "LV13.DAT"]
        lv_data = load_raw(lv_files[self.current_level])
        first_off = struct.unpack_from('<H', lv_data, 0)[0]
        # Room 68's offset + 8 (skip header) = start of trailer data
        trailer_off = struct.unpack_from('<H', lv_data, 68 * 2)[0] + 8
        self.captive_count = struct.unpack_from('<H', lv_data, trailer_off)[0]
        self.beam_tile = struct.unpack_from('<H', lv_data, trailer_off + 6)[0]
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
                    if obj["type"] == 10:
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
                if obj["type"] in (6, 7) and "fg_tile" in obj:
                    fg_overrides[obj["params"][0]] = obj["fg_tile"]
                if obj["type"] in (1, 2, 3, 4, 5, 9, 10, 15, 16) and "fg_tiles" in obj:
                    fg_overrides.update(obj["fg_tiles"])
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
        lv_files = ["LV11.DAT", "LV12.DAT", "LV13.DAT"]
        data = load_raw(lv_files[self.current_level])
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

    OBJ_PARAMS = {0:0,1:1,2:1,3:1,4:1,5:3,6:2,7:2,8:2,9:2,10:3,11:1,12:1,13:2,14:2,15:2,16:2,17:3,18:3,19:3,20:1,21:0,22:0,23:0}

    def load_room_objects(self):
        """Parse objects from LVxx.DAT for each room."""
        lv_files = ["LV11.DAT", "LV12.DAT", "LV13.DAT"]
        data = load_raw(lv_files[self.current_level])
        first_off = struct.unpack_from('<H', data, 0)[0]
        num_entries = first_off // 2
        offsets = [struct.unpack_from('<H', data, i * 2)[0] for i in range(num_entries)]
        self.room_objects = {}
        for room in range(num_entries):
            off = offsets[room]
            pos = off + 8  # skip 8-byte header
            objects = []
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

    def draw_objects(self, surface, room_idx):
        """Draw room objects using their sprites."""
        if room_idx not in self.room_objects:
            return
        for obj in self.room_objects[room_idx]:
            ot = obj["type"]
            obj["timer"] += 1
            x, y = obj["x"], obj["y"]
            sp = None
            if ot in (1, 2, 3, 4):  # fans — 3x3 foreground tile animation
                base_tiles = [200, 200, 440, 440][ot - 1]
                frame_order = [[0,1,2], [0,2,1], [0,1,2], [0,2,1]][ot - 1]
                frame = frame_order[(obj["timer"] // 6) % 3]
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                map_data = self.levels[self.current_level]["map"]
                base = room_idx * ROOM_BYTES
                bg_words = struct.unpack_from('<320H', map_data[base:base + 640])
                # Check if fan is in background layer (draw before Joe) or foreground (after Joe)
                bi0 = row * MAP_COLS + col
                bti0 = bg_words[bi0] & 0x3FF if bg_words[bi0] != 0xFFFF else 0
                fan_in_bg = (200 <= bti0 <= 248) or (440 <= bti0 <= 488)
                for dr in range(3):
                    for dc in range(3):
                        ti = base_tiles + frame * 3 + dc + dr * 20
                        fg_idx = (row + dr) * MAP_COLS + (col + dc)
                        if fan_in_bg:
                            # Background fan: draw opaquely here (before Joe)
                            # Original uses MODIFY_SCREEN_MAP which writes to background
                            # and skips positions where foreground tiles exist
                            if ti < len(self.tile_surfs):
                                surface.blit(self.tile_surfs[ti], ((col + dc) * TILE_W, (row + dr) * TILE_H))
                        else:
                            # Foreground fan: defer to render_foreground (after Joe, with colorkey)
                            obj.setdefault("fg_tiles", {})[fg_idx] = ti
                continue
            elif ot == 8:  # vertical_field — lightning using actual game animation tiles
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                hx = (col * TILE_W) // 2
                if self.switch_state[switch_id] == 0:
                    # Field OFF — erase collision (restore from backup, shape 8: 6w×35h rows 1-35)
                    if obj.get("field_active") and backup:
                        for r in range(1, 36):
                            by = (row * TILE_H) // 2 + r
                            for c in range(1, 7):
                                bx = hx + c
                                if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                    cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                        obj["field_active"] = False
                    continue
                # 4 frames, 6 rows each. Tiles from game data (confirmed via GAME.EXE disassembly)
                frame_tiles = [
                    [81, 101, 121, 141, 161, 181],
                    [82, 102, 122, 142, 162, 182],
                    [83, 103, 123, 143, 163, 183],
                    [80, 100, 120, 140, 160, 180],
                ]
                frame = (obj["timer"] // 3) % 4
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                map_data = self.levels[self.current_level]["map"]
                base = room_idx * ROOM_BYTES
                bg_words = struct.unpack_from('<320H', map_data, base)
                y_top = 0
                for r in range(row - 1, -1, -1):
                    if (bg_words[r * MAP_COLS + col] >> 10) & 0x3F != 0:
                        y_top = (r + 1) * TILE_H
                        break
                y_bot = SCREEN_H
                for r in range(row + 1, MAP_ROWS):
                    if (bg_words[r * MAP_COLS + col] >> 10) & 0x3F != 0:
                        y_bot = r * TILE_H
                        break
                tiles = frame_tiles[frame]
                ty = y_top
                ti_idx = 0
                while ty < y_bot and ti_idx < len(tiles):
                    ti = tiles[ti_idx]
                    if ti < len(self.tile_surfs):
                        ts = self.tile_surfs[ti]
                        ts.set_colorkey((0, 0, 0))
                        surface.blit(ts, (col * TILE_W, ty))
                        ts.set_colorkey(None)
                    ty += TILE_H
                    ti_idx += 1
                # DRAW_VISUAL shape 8 (6w x 35h, cols 1-6, rows 1-35): restore backup first.
                # This wipes Joe's type-14 marker if he touches the field — that is how it kills.
                if backup:
                    for r in range(1, 36):
                        by = y_top // 2 + r
                        for c in range(1, 7):
                            bx = hx + c
                            if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                # Write collision for active vertical field
                # Shape 7: 2w at cols 3-4, alternating rows 0-34
                for r in range(0, 35, 2):
                    by = y_top // 2 + r
                    for c in [3, 4]:
                        bx = hx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 1
                obj["field_active"] = True
                continue
            elif ot == 9:  # horiz_field — horizontal lightning, GAME.EXE 0x131F
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                hy = (row * TILE_H) // 2
                if self.switch_state[switch_id] == 0:
                    # Field OFF — erase collision (restore from backup, shape 12: 48w×4h rows 1-4)
                    if obj.get("field_active"):
                        if backup:
                            for r in range(1, 5):
                                by = hy + r
                                for c in range(48):
                                    bx = (col * TILE_W) // 2 + c
                                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                        cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                        obj["field_active"] = False
                        obj.pop("fg_tiles", None)
                    continue
                # Field ON — draw animation and collision
                frame_tiles = [
                    [64, 65, 66, 67, 68, 69],
                    [104, 105, 106, 107, 108, 109],
                    [84, 85, 86, 87, 88, 89],
                    [124, 125, 126, 127, 128, 129],
                ]
                frame = (obj["timer"] // 3) % 4
                tiles = frame_tiles[frame]
                # MODIFY_FOREGROUND_MAP: 6 tiles at offsets 0-5 from location
                obj["fg_tiles"] = {}
                for i, ti in enumerate(tiles):
                    fg_idx = row * MAP_COLS + col + i
                    if fg_idx < MAP_ROWS * MAP_COLS:
                        obj["fg_tiles"][fg_idx] = ti
                # Erase old collision (shape 12: 48w×4h rows 1-4), then write new (shape 11: 48w×2h rows 2-3)
                if backup:
                    for r in range(1, 5):
                        by = hy + r
                        for c in range(48):
                            bx = (col * TILE_W) // 2 + c
                            if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                for r in [2, 3]:
                    by = hy + r
                    for c in range(48):
                        bx = (col * TILE_W) // 2 + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 1
                obj["field_active"] = True
                continue
            elif ot in (6, 7):  # right_switch / left_switch
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                # Original game uses CHECK_COLLISION with shape 4 (4x2 half-res at +2,+2)
                # Check if Joe's collision shape overlaps the switch shape
                jhx, jhy = self.player.x // 2, self.player.y // 2
                shx, shy = x // 2, y // 2
                # Switch shape: rows +2..+3, cols +2..+5 from switch half-res pos
                touching = False
                for dy, dx_start, count in JOE_COL_SHAPE:
                    jy = jhy + dy
                    if jy < shy + 2 or jy > shy + 3:
                        continue
                    for i in range(count):
                        jx = jhx + dx_start + i
                        if shx + 2 <= jx <= shx + 5:
                            touching = True
                            break
                    if touching:
                        break
                if touching:
                    if not obj.get("touching"):
                        self.switch_state[switch_id] = 0 if self.switch_state[switch_id] else 0xFF
                    obj["touching"] = True
                else:
                    obj["touching"] = False
                # Store the tile override for render_foreground
                # Base tile from original foreground (even=ON, odd=OFF)
                map_data = self.levels[self.current_level]["map"]
                fg_byte = map_data[room_idx * ROOM_BYTES + 640 + obj["params"][0]]
                base_tile = fg_byte & 0xFE  # clear bit 0 to get base
                state_bit = self.switch_state[switch_id] & 1
                obj["fg_tile"] = base_tile + state_bit
                continue
            elif ot == 10:  # cage — captive sprite + force field tile animation
                if len(obj["params"]) >= 3 and obj["params"][2] < len(self.sprites):
                    col = obj["params"][0] % MAP_COLS
                    row = obj["params"][0] // MAP_COLS
                    cx, cy = x + 23, y + 10
                    disappear = obj.get("disappear", -1)
                    if disappear >= 0:
                        # Advance every 3 ticks
                        obj["disappear_tick"] = obj.get("disappear_tick", 0) + 1
                        if obj["disappear_tick"] >= 3:
                            obj["disappear_tick"] = 0
                            obj["disappear"] = disappear + 1
                        # Disappear animation (17 frames from DS:0x3389)
                        CAGE_DISAPPEAR = [
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
                        if disappear < 17:
                            # Draw captive sprite until frame 12
                            if disappear < 12:
                                sp = self.sprites[obj["params"][2]]
                                surface.blit(sp["surf"], (cx + sp["x_off"], cy + sp["y_off"]))
                            # Draw disappear tiles
                            for toff, ti in CAGE_DISAPPEAR[disappear]:
                                dc, dr = toff % 20, toff // 20
                                fg_idx = (row + dr) * MAP_COLS + (col + dc)
                                obj.setdefault("fg_tiles", {})[fg_idx] = ti if ti else 0
                        elif not obj.get("done"):
                            # Animation complete — clear collision walls, decrement captive count (once)
                            obj["done"] = True
                            cbm = self.get_collision_bitmap(room_idx)[0]
                            hx, hy = obj["x"] // 2, obj["y"] // 2
                            for r in range(18):
                                for c in [1, 2, 21, 22]:
                                    bx, by = hx + c, hy + r
                                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                        cbm[by * HALF_W + bx] = 0
                            self.captive_count = max(0, self.captive_count - 1)
                        sp = None
                    else:
                        # Active cage: draw captive + force field, check collision
                        # DRAW_COLLISION shape 13 every update (0x142F): keeps the walls present
                        # even after another object's restore-from-backup passed over them.
                        cbm = self.get_collision_bitmap(room_idx)[0]
                        chx, chy = obj["x"] // 2, obj["y"] // 2
                        for r in range(18):
                            for c in (1, 2, 21, 22):
                                bx, by = chx + c, chy + r
                                if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                    cbm[by * HALF_W + bx] = 1
                        sp = self.sprites[obj["params"][2]]
                        surface.blit(sp["surf"], (cx + sp["x_off"], cy + sp["y_off"]))
                        # Force field tiles (4 frames from DS:0x3AF5)
                        ff_tiles = [232, 233, 252, 253]
                        frame = (obj["timer"] // 4) % 4
                        ti = ff_tiles[frame]
                        for dr in range(3):
                            for dc in range(3):
                                fg_idx = (row + dr) * MAP_COLS + (col + dc)
                                obj.setdefault("fg_tiles", {})[fg_idx] = ti
                        # Check if Joe touches the force field (collision shape overlap)
                        jhx, jhy = self.player.x // 2, self.player.y // 2
                        shx, shy = x // 2, y // 2
                        touching = False
                        for dy, dx_start, count in JOE_COL_SHAPE:
                            jy = jhy + dy
                            if jy < shy or jy > shy + 17:
                                continue
                            for i in range(count):
                                jx = jhx + dx_start + i
                                if shx <= jx <= shx + 23:
                                    touching = True
                                    break
                            if touching:
                                break
                        if touching:
                            obj["disappear"] = 0  # start disappear animation
                            play_sound(SND_THANKS)        # 0x1468
                            play_sound(SND_TRANSPORTER)   # 0x1F62
                        sp = None
            elif ot == 5:  # door — slides up/down based on switch state
                DOOR_FRAMES = [
                    [(0,144),(20,164),(40,164),(60,184)],
                    [(0,145),(20,165),(40,165),(60,185)],
                    [(0,146),(20,166),(40,166),(60,186)],
                    [(0,147),(20,167),(40,167),(60,187)],
                    [(0,144),(20,164),(40,149),(60,187)],
                    [(0,145),(20,165),(40,169),(60,187)],
                    [(0,146),(20,166),(40,189),(60,187)],
                    [(0,147),(20,167),(40,0),(60,187)],
                    [(0,144),(20,149),(40,0),(60,187)],
                    [(0,145),(20,169),(40,0),(60,187)],
                    [(0,146),(20,189),(40,0),(60,187)],
                    [(0,147),(20,0),(40,0),(60,187)],
                    [(0,148),(20,0),(40,0),(60,187)],
                    [(0,168),(20,0),(40,0),(60,187)],
                    [(0,188),(20,0),(40,0),(60,187)],
                ]
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                var_id = obj["params"][2] if len(obj["params"]) > 2 else 0
                old_state = min(14, self.switch_state[var_id])
                # DRAW_VISUAL: erase old collision (restore from backup)
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                hx = (x + 2) // 2
                old_shift = (old_state * 3) // 2
                if backup:
                    for r in range(0, 21, 2):
                        by = (y + 4) // 2 - old_shift + r
                        for c in range(6):
                            bx = hx + c
                            if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                # Update state
                if self.switch_state[switch_id]:
                    if old_state < 14:
                        old_state += 1
                else:
                    if old_state > 0:
                        old_state -= 1
                self.switch_state[var_id] = old_state
                state = old_state
                # DRAW_COLLISION: write new collision (type 1)
                new_shift = (state * 3) // 2
                for r in range(0, 21, 2):
                    by = (y + 4) // 2 - new_shift + r
                    for c in range(6):
                        bx = hx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 1
                # Update foreground tiles
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                for toff, ti in DOOR_FRAMES[state]:
                    dc, dr = toff % 20, toff // 20
                    fg_idx = (row + dr) * MAP_COLS + (col + dc)
                    obj.setdefault("fg_tiles", {})[fg_idx] = ti
                continue
            elif ot == 19:  # teleporter — handled in update_objects
                continue
                continue
            elif ot == 17:  # toggle_switch — matching GAME.EXE 0x213C
                sw1 = obj["params"][1] if len(obj["params"]) > 1 else 0
                sw2 = obj["params"][2] if len(obj["params"]) > 2 else 0
                # CHECK_COLLISION shape 4 overlap (same as regular switch)
                jhx, jhy = int(self.player.x) // 2, int(self.player.y) // 2
                shx, shy = x // 2, y // 2
                touching = False
                for dy, dx_start, count in JOE_COL_SHAPE:
                    jy = jhy + dy
                    if jy < shy + 2 or jy > shy + 3:
                        continue
                    for i in range(count):
                        jx = jhx + dx_start + i
                        if shx + 2 <= jx <= shx + 5:
                            touching = True
                            break
                    if touching:
                        break
                # Edge-triggered: toggle only on first contact
                if touching and not obj.get("touching"):
                    self.switch_state[sw1] = ~self.switch_state[sw1] & 0xFF
                    if sw2 != sw1:
                        self.switch_state[sw2] = ~self.switch_state[sw2] & 0xFF
                obj["touching"] = touching
                # Visual: tile 556 + (sw2 & 1) + 2*(sw1 & 1), written to background
                ti = 556 + (self.switch_state[sw2] & 1) + 2 * (self.switch_state[sw1] & 1)
                loc = obj["params"][0]
                col_t = loc % MAP_COLS
                row_t = loc // MAP_COLS
                surface.blit(self.tile_surfs[ti], (col_t * TILE_W, row_t * TILE_H))
                sp = None
            elif ot in (15, 16):  # plates — oscillating collision walls (GAME.EXE 0x17A0/0x189B)
                is_right = (ot == 16)
                var_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                tile_loc = obj["params"][0]
                base_x = x  # BLOCK_TO_XY result stored at init
                # Position table: 52 entries × 3 words [x_offset, anim_frame, tile_col]
                PLATE_POS = [
                    (0,0,0),(2,1,0),(4,2,0),(6,3,0),(8,4,0),(10,5,0),(12,6,0),(14,7,0),(16,8,0),
                    (18,1,1),(20,2,1),(22,3,1),(24,4,1),(26,5,1),(28,6,1),(30,7,1),(32,8,1),
                    (34,1,2),(36,2,2),(38,3,2),(40,4,2),(42,5,2),(44,6,2),(46,7,2),(48,8,2),
                    (50,1,3),(52,2,3),
                    (50,1,3),(48,0,3),(46,7,2),(44,6,2),(42,5,2),(40,4,2),(38,3,2),(36,9,2),(34,1,2),
                    (32,0,2),(30,7,1),(28,6,1),(26,5,1),(24,4,1),(22,3,1),(20,9,1),(18,1,1),
                    (16,0,1),(14,7,0),(12,6,0),(10,5,0),(8,4,0),(6,3,0),(4,9,0),(2,1,0),
                ]
                LEFT_FRAMES = [
                    [(0,72),(20,72),(40,72),(60,72),(80,72)],
                    [(0,52),(20,51),(40,52),(60,51),(80,52)],
                    [(0,191),(20,190),(40,191),(60,190),(80,191)],
                    [(0,171),(20,170),(40,171),(60,170),(80,171),(1,172),(21,172),(41,172),(61,172),(81,172)],
                    [(0,151),(20,150),(40,151),(60,150),(80,151),(1,152),(21,152),(41,152),(61,152),(81,152)],
                    [(0,131),(20,130),(40,131),(60,130),(80,131),(1,132),(21,132),(41,132),(61,132),(81,132)],
                    [(0,111),(20,110),(40,111),(60,110),(80,111),(1,112),(21,112),(41,112),(61,112),(81,112)],
                    [(0,91),(20,90),(40,91),(60,90),(80,91),(1,92),(21,92),(41,92),(61,92),(81,92)],
                    [(0,0),(20,71),(40,0),(60,71),(80,0),(1,72),(21,72),(41,72),(61,72),(81,72)],
                    [(0,191),(20,190),(40,191),(60,190),(80,191),(1,0),(21,0),(41,0),(61,0),(81,0)],
                ]
                RIGHT_FRAMES = [
                    [(0,191),(20,191),(40,191),(60,191),(80,191)],
                    [(0,52),(20,53),(40,52),(60,53),(80,52)],
                    [(0,72),(20,73),(40,72),(60,73),(80,72)],
                    [(0,92),(20,93),(40,92),(60,93),(80,92),(-1,91),(19,91),(39,91),(59,91),(79,91)],
                    [(0,112),(20,113),(40,112),(60,113),(80,112),(-1,111),(19,111),(39,111),(59,111),(79,111)],
                    [(0,132),(20,133),(40,132),(60,133),(80,132),(-1,131),(19,131),(39,131),(59,131),(79,131)],
                    [(0,152),(20,153),(40,152),(60,153),(80,152),(-1,151),(19,151),(39,151),(59,151),(79,151)],
                    [(0,172),(20,173),(40,172),(60,173),(80,172),(-1,171),(19,171),(39,171),(59,171),(79,171)],
                    [(0,0),(20,71),(40,0),(60,71),(80,0),(-1,191),(19,191),(39,191),(59,191),(79,191)],
                    [(0,72),(20,73),(40,72),(60,73),(80,72),(-1,0),(19,0),(39,0),(59,0),(79,0)],
                ]
                ANIM_FRAMES = RIGHT_FRAMES if is_right else LEFT_FRAMES
                obj["timer"] += 1
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                hy = y // 2
                cur_hx = obj.get("plate_hx", x // 2)
                if obj["timer"] % 4 == 0:
                    # Full update: erase old collision, advance state, write new
                    old_hx = cur_hx
                    if backup:
                        for r in range(0, 30, 2):
                            by = hy + r
                            for c in range(6):
                                bx = old_hx + c
                                if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                    cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]
                    val = (self.switch_state[var_id] + 1) & 0xFF
                    if val >= 52:
                        val = 0
                    self.switch_state[var_id] = val
                    x_off, anim_frame, tile_col = PLATE_POS[val]
                    col = tile_loc % MAP_COLS
                    row = tile_loc // MAP_COLS
                    base_tile = tile_loc + tile_col if not is_right else tile_loc - tile_col
                    for toff, ti in ANIM_FRAMES[anim_frame]:
                        fg_idx = base_tile + toff
                        if 0 <= fg_idx < MAP_COLS * MAP_ROWS:
                            obj.setdefault("fg_tiles", {})[fg_idx] = ti
                    # Trail fill: write tile 71 to fg map at rows 1 and 3 below tile_loc
                    # Left plate fills rightward, right plate fills leftward
                    fg = obj.setdefault("fg_tiles", {})
                    for c in range(tile_col):
                        tc = tile_loc + c if not is_right else tile_loc - c
                        for row_off in (20, 60):
                            idx = tc + row_off
                            if 0 <= idx < MAP_COLS * MAP_ROWS:
                                fg[idx] = 71
                    new_cx = base_x + x_off
                    if is_right:
                        new_cx = base_x - x_off + 4
                    cur_hx = new_cx // 2
                    obj["plate_hx"] = cur_hx
                # Draw plate tiles via fg_overrides in render_foreground (with colorkey)
                sp = None
                continue
            elif ot == 14:  # sentry — a live Sentry entity is spawned in enter_room()
                continue
            elif ot == 18:  # sensor switch — a SensorSwitch entity is spawned in enter_room()
                continue
            elif ot == 13:  # glow_ball — GAME.EXE 0x134D via shared field handler 0x1E3C
                # Not a sprite: a 2x2 foreground tile animation (table DS:0x3BA9) with a hollow
                # ring collision (shape 5 written, shape 6 erased each update). Frame 4 is the
                # dormant look drawn once when the switch turns it off.
                GLOW_FRAMES = ((94, 95, 114, 115), (96, 97, 116, 117), (134, 135, 154, 155),
                               (136, 137, 156, 157), (138, 139, 158, 159))
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                col = obj["params"][0] % MAP_COLS
                row = obj["params"][0] // MAP_COLS
                hx, hy = (col * TILE_W) >> 1, (row * TILE_H) >> 1
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                if self.switch_state[switch_id] == 0:
                    if obj.get("field_active"):
                        obj["field_active"] = False
                        obj["gb_dormant"] = True
                        cb_restore(cbm, backup, 5, hx, hy)
                    frame = 4 if obj.get("gb_dormant") else None
                else:
                    frame = (obj["timer"] // 4) % 4
                    cb_restore(cbm, backup, 6, hx, hy)      # DRAW_VISUAL ring: wipes Joe's marker
                    cb_write(cbm, 5, hx, hy, CT_WALL)       # DRAW_COLLISION
                    obj["field_active"] = True
                if frame is not None:
                    for i, (dc, dr) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                        ti = GLOW_FRAMES[frame][i]
                        if ti < len(self.tile_surfs):
                            ts = self.tile_surfs[ti]
                            ts.set_colorkey((0, 0, 0))
                            surface.blit(ts, ((col + dc) * TILE_W, (row + dr) * TILE_H))
                            ts.set_colorkey(None)
                continue
            if sp:
                surface.blit(sp["surf"], (x + sp["x_off"], y + sp["y_off"]))
        # Beam-out/beam-in animation (cage disappear frames, DS:0x3389)
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
        active_beam = self.beam_out or self.beam_in
        if active_beam is not None:
            f = active_beam["frame"]
            if 0 <= f <= 16:
                tile_loc = active_beam["tile"]
                col = tile_loc % MAP_COLS
                row = tile_loc // MAP_COLS
                for toff, ti in BEAM_FRAMES[f]:
                    if ti == 0:
                        continue
                    dc, dr = toff % 20, toff // 20
                    px = (col + dc) * TILE_W
                    py = (row + dr) * TILE_H
                    ts = self.tile_surfs[ti]
                    ts.set_colorkey((0, 0, 0))
                    surface.blit(ts, (px, py))
            active_beam["timer"] += 1
            if active_beam["timer"] >= 4:
                active_beam["timer"] = 0
                if self.beam_out is not None:
                    # Beam-out: frames 0→16 (forward), Joe hidden at frame 12
                    self.beam_out["frame"] += 1
                    if self.beam_out["frame"] > 16:
                        bo = self.beam_out
                        self.beam_out = None
                        if "dest_room" in bo:
                            # Teleporter beam-out → teleport Joe → start beam-in
                            dest_room = bo["dest_room"]
                            dest_tile = bo["dest_tile"]
                            dcol = dest_tile % MAP_COLS
                            drow = dest_tile // MAP_COLS
                            self.player.x = dcol * TILE_W + 23
                            self.player.y = drow * TILE_H + 16
                            self.player.vx = 0
                            self.player.vy = 0
                            if dest_room != self.current_room:
                                self.current_room = dest_room
                                self.player.shots.clear()
                                self.player.explosions.clear()
                            self.cbm_cache.pop(self.current_room, None)
                            self.cbm_backup.pop(self.current_room, None)
                            self.last_room = None   # force enter_room(): objects re-init
                            self.beam_in = {"tile": dest_tile, "frame": 15, "timer": 0}
                            play_sound(SND_TRANSPORTER)   # 0x2020 (beam-in object init)
                        else:
                            # Level-complete beam-out → advance level
                            if self.current_level < 2:
                                self.set_level(self.current_level + 1)
                            else:
                                self.game_won = True
                else:
                    # Beam-in: frames 15→0 (reverse)
                    self.beam_in["frame"] -= 1
                    if self.beam_in["frame"] < 0:
                        self.beam_in = None

    def start_teleport(self, obj):
        """0x22C5: begin the beam-out at the teleporter; beam_out's completion moves Joe to
        dest_room/dest_tile and starts the beam-in there."""
        dest_room = obj["params"][1] if len(obj["params"]) > 1 else 0
        dest_tile = obj["params"][2] if len(obj["params"]) > 2 else 0
        play_sound(SND_TRANSPORTER)                       # 0x1F62 (beam-out object init)
        self.beam_out = {"tile": obj["params"][0], "frame": 0, "timer": 0,
                         "dest_room": dest_room, "dest_tile": dest_tile,
                         "src_room": self.current_room}

    def update_objects(self):
        """Update objects that affect gameplay (teleporters). Called during update phase."""
        room_idx = self.current_room
        if room_idx not in self.room_objects:
            return
        px, py = int(self.player.x), int(self.player.y)
        for obj in self.room_objects[room_idx]:
            if obj["type"] == 19:  # teleporter — a Teleporter entity (update_entities) fires it
                continue
            elif obj["type"] in (15, 16):  # plates — write collision before player update
                is_right = (obj["type"] == 16)
                var_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                base_x = obj["x"]
                PLATE_POS = [
                    (0,0,0),(2,1,0),(4,2,0),(6,3,0),(8,4,0),(10,5,0),(12,6,0),(14,7,0),(16,8,0),
                    (18,1,1),(20,2,1),(22,3,1),(24,4,1),(26,5,1),(28,6,1),(30,7,1),(32,8,1),
                    (34,1,2),(36,2,2),(38,3,2),(40,4,2),(42,5,2),(44,6,2),(46,7,2),(48,8,2),
                    (50,1,3),(52,2,3),
                    (50,1,3),(48,0,3),(46,7,2),(44,6,2),(42,5,2),(40,4,2),(38,3,2),(36,9,2),(34,1,2),
                    (32,0,2),(30,7,1),(28,6,1),(26,5,1),(24,4,1),(22,3,1),(20,9,1),(18,1,1),
                    (16,0,1),(14,7,0),(12,6,0),(10,5,0),(8,4,0),(6,3,0),(4,9,0),(2,1,0),
                ]
                val = self.switch_state[var_id]
                if val < 52:
                    x_off = PLATE_POS[val][0]
                else:
                    x_off = 0
                new_cx = base_x + x_off if not is_right else base_x - x_off + 4
                cur_hx = new_cx // 2
                hy = obj["y"] // 2
                cbm = self.get_collision_bitmap(room_idx)[0]
                for r in range(0, 30, 2):
                    by = hy + r
                    for c in range(6):
                        bx = cur_hx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 1

    # ------------------------------------------------------------------
    # Room entry, enemy scheduling, Joe's collision marker and death
    # ------------------------------------------------------------------
    def jump_to_room(self, room):
        """Debug helper (G key, [ ], --start): switch rooms without a door and drop Joe on the
        nearest free spot so he does not start inside a wall or a pit."""
        if not 0 <= room < self.num_rooms:
            return False
        self.current_room = room
        self.beam_in = self.beam_out = None
        self.death = None
        self.player.shots.clear()
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
        self.player.vx = self.player.vy = 0.0
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
            if t == 10 and obj.get("disappear", -1) < 0:
                play_sound(SND_HELP)                      # 0x1406: captive init
            if t in (11, 12, 14, 20) and not self.enemies_enabled:
                continue                                  # debug: --no-enemies / E key
            if t == 14:
                var_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                if self.switch_state[var_id] != 0:        # 0x232E: skipped if its variable is 0
                    self.entities.append(Sentry(self, obj["x"], obj["y"]))
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

    def update_entities(self):
        """Main loop 0x06F8: run every object whose next_time has passed, as often as needed."""
        room = self.current_room
        self.cbm = self.get_collision_bitmap(room)[0]
        self.cbm_bak = self.cbm_backup[room]
        for e in list(self.entities):
            n = 0
            while e.alive and e.next_time <= self.tick and n < 8:
                e.update(self)
                e.next_time += e.interval
                n += 1
        self.entities = [e for e in self.entities if e.alive]

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

    def start_death(self):
        """GAME.EXE 0x0F05: Joe's death sequence. First step after 80 ticks, then every 70."""
        if self.death is not None:
            return
        self.death = {"frame": 0, "next": self.tick + 80, "sprite": None, "hidden": False}
        self.player.thrusting = False
        self.player.vx = 0
        self.player.vy = 0
        self.player.thrust_timer = 0

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
        """The demo's caller (0x02C3) simply restarts the level on a lost life."""
        self.death = None
        lives = self.player.lives - 1
        if lives <= 0:
            self.player.lives = 0
            self.game_over = True
            return
        self.set_level(self.current_level)
        self.player.lives = lives

    def try_room_transition(self):
        """Check if player has left the screen and transition rooms.
        Matches original GAME.EXE room transition logic at 0x0721 exactly."""
        cx = self.player.x - 160
        dx = self.player.y - 96
        if self.current_room >= len(self.room_headers):
            return
        hdr = self.room_headers[self.current_room]

        new_room = 0xFF
        if dx < -96:  # top exit
            dx += 192
            new_room = hdr[0]
            if hdr[0] != hdr[1]:
                if cx >= 0:
                    new_room = hdr[1]
                    cx -= 320
                cx += 160
            # if hdr[0]==hdr[1], cx unchanged
        elif dx >= 96:  # bottom exit
            dx -= 192
            new_room = hdr[5]
            if hdr[4] != hdr[5]:
                if cx >= 0:
                    new_room = hdr[4]
                    cx -= 320
                cx += 160
        elif cx < -160:  # left exit
            cx += 320
            new_room = hdr[7]
            if hdr[6] != hdr[7]:
                if dx >= 0:
                    new_room = hdr[6]
                    dx -= 192
                dx += 96
        elif cx >= 160:  # right exit
            cx -= 320
            new_room = hdr[2]
            if hdr[2] != hdr[3]:
                if dx >= 0:
                    new_room = hdr[3]
                    dx -= 192
                dx += 96
        else:
            return

        if new_room == 0xFF:
            self.player.x = max(1, min(SCREEN_W - 1, self.player.x))
            self.player.y = max(1, min(SCREEN_H - 1, self.player.y))
            return

        print(f"TRANSITION: room {self.current_room}→{new_room}  pos ({self.player.x:.0f},{self.player.y:.0f})→({cx+160:.0f},{dx+96:.0f})")
        self.current_room = new_room
        self.player.x = cx + 160
        self.player.y = dx + 96
        self.player.shots.clear()
        self.player.explosions.clear()

    def set_level(self, level):
        if 0 <= level < 3:
            self.current_level = level
            self.build_assets()
            self.current_room = 0
            # Position Joe at beam-in tile (matching GAME.EXE 0x0C7E)
            bcol = self.beam_tile % MAP_COLS
            brow = self.beam_tile // MAP_COLS
            self.player = Player(bcol * TILE_W + 23, brow * TILE_H + 16)
            # Start beam-in animation (matching GAME.EXE 0x0C5B-0x0C78)
            self.beam_in = {"tile": self.beam_tile, "frame": 15, "timer": 0}
            play_sound(SND_TRANSPORTER)          # 0x0AFC
            self.beam_out = None
            self.game_over = False
            self.game_won = False
            self.level_complete_timer = 0
            self.cbm_cache = {}
            self.cbm_backup = {}
            self.entities = []
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
                        self.game_over = False
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self.jump_to_room(self.current_room + 1)
                    elif event.key == pygame.K_LEFTBRACKET:
                        self.jump_to_room(self.current_room - 1)
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        self.set_level(event.key - pygame.K_1)
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

            if not self.game_over and not self.game_won:
                self.tick += TICKS_PER_FRAME
                self.frame_no += 1
                if self.current_room != self.last_room:
                    self.enter_room()
                beaming = self.beam_out is not None or self.beam_in is not None
                dying = self.death is not None
                keys = pygame.key.get_pressed()
                if not beaming and not dying:
                    self.player.vx = 0
                    if keys[pygame.K_LEFT]:
                        self.player.vx = -MOVE_SPEED
                        self.player.direction = -1
                    if keys[pygame.K_RIGHT]:
                        self.player.vx = MOVE_SPEED
                        self.player.direction = 1
                    self.player.thrusting = keys[pygame.K_SPACE] or keys[pygame.K_UP]
                    if keys[pygame.K_z]:
                        self.player.fire()
                if dying:
                    self.update_death()
                elif not beaming:
                    cbm, pipe_floors, pipe_ceilings = self.get_collision_bitmap(self.current_room)
                    backup = self.cbm_backup[self.current_room]
                    self.joe_check_and_unmark(cbm, backup)
                    if self.death is None:
                        self.update_objects()
                        self.player.update(cbm, self.sprites, pipe_floors, pipe_ceilings, backup)
                        # Crush check (0x0CFB-0x0D5B): if something moved into Joe, try the
                        # original's 9 nudge positions; if none is free he dies.
                        px, py = int(self.player.x), int(self.player.y)
                        if joe_hits_bg(cbm, px, py):
                            for ddx, ddy in CRUSH_NUDGES:
                                if not joe_hits_bg(cbm, px + ddx, py + ddy):
                                    self.player.x = px + ddx
                                    self.player.y = py + ddy
                                    break
                            else:
                                if os.environ.get("JPJ_DEBUG"):
                                    print(f"CRUSHED at ({px},{py}) room {self.current_room}")
                                self.start_death()
                else:
                    self.update_objects()
                self.try_room_transition()
                if self.current_room != self.last_room:
                    self.enter_room()
                if not beaming and self.death is None:
                    self.joe_mark()
                self.update_entities()
                # Level completion: start beam-out when all captives rescued
                if self.captive_count <= 0 and self.beam_out is None and self.level_complete_timer == 0:
                    # Convert Joe's position to tile for beam-out (matching GAME.EXE 0x0C27)
                    tile = (int(self.player.y) // TILE_H) * MAP_COLS + (int(self.player.x) // TILE_W)
                    self.beam_out = {"tile": tile, "frame": 0, "timer": 0}
                    play_sound(SND_TRANSPORTER)       # 0x1F62 via 0x0C27
                    self.level_complete_timer = 1  # flag: beam-out started
                if self.player.y > SCREEN_H:
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.game_over = True
                    else:
                        self.player.y = 40
                        self.player.vy = 0
                self.time_counter += 1
                if self.time_counter >= FPS:
                    self.time_counter = 0
                    self.player.time -= 1
                    if self.player.time <= 0:
                        self.game_over = True

            self.draw()
            pygame.display.flip()
        pygame.quit()

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.render_room(self.current_room), (0, 0))
        self.draw_objects(self.screen, self.current_room)
        self.draw_entities(self.screen)
        if not self.game_over:
            joe_hidden = False
            if self.beam_out and self.beam_out["frame"] >= 12:
                joe_hidden = True
            if self.beam_in:
                joe_hidden = True
            if self.death is not None and self.death["hidden"]:
                joe_hidden = True
            if not joe_hidden:
                if self.death is not None and self.death["sprite"] is not None:
                    sp = self.sprites[self.death["sprite"]]
                    self.screen.blit(sp["surf"], (int(self.player.x) + sp["x_off"],
                                                  int(self.player.y) + sp["y_off"]))
                else:
                    self.player.draw(self.screen, self.sprites)
        for e in self.entities:
            if isinstance(e, Bird):
                e.draw_laser(self.screen, self.sprites, self.frame_no)
        self.render_foreground(self.current_room, self.screen)
        # Draw explosions on top of everything (they occur at wall edges)
        if not self.game_over:
            for e in self.player.explosions:
                e.draw(self.screen, self.sprites)
        for e in self.entities:
            if isinstance(e, EnemyExplosion):
                e.draw_top(self.screen, self.sprites)

        bar_y = SCREEN_H
        pygame.draw.rect(self.screen, (0, 0, 0), (0, bar_y, SCREEN_W, STATUS_H))
        self.screen.blit(self.font.render(f"TIME: {self.player.time:03d}", False, (0, 255, 0)), (4, bar_y + 3))
        if self.goto_buf is not None:
            self.screen.blit(self.font.render(f"GO TO ROOM: {self.goto_buf}_  (Enter / Esc)", False, (255, 255, 0)), (SCREEN_W // 2 - 90, bar_y + 3))
        elif not self.enemies_enabled:
            self.screen.blit(self.font.render("NO ENEMIES", False, (255, 255, 0)), (SCREEN_W // 2 - 30, bar_y + 3))
        else:
            self.screen.blit(self.font.render(f"Rescues Remaining: {self.captive_count:02d}", False, (0, 255, 0)), (SCREEN_W // 2 - 66, bar_y + 3))
        self.screen.blit(self.font.render(f"ROOM: {self.current_room:02d}", False, (0, 255, 0)), (SCREEN_W - 60, bar_y + 3))

        if self.game_over:
            go = self.font.render("GAME OVER - Press R", False, (255, 0, 0))
            self.screen.blit(go, (SCREEN_W // 2 - go.get_width() // 2, SCREEN_H // 2))
        elif self.game_won:
            go = self.font.render("YOU WIN!", False, (255, 255, 0))
            self.screen.blit(go, (SCREEN_W // 2 - go.get_width() // 2, SCREEN_H // 2))

        pygame.transform.scale(self.screen, (WIN_W, WIN_H), self.window)


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
            if lvl.isdigit() and room.isdigit() and 1 <= int(lvl) <= 3:
                return int(lvl) - 1, int(room)
            raise SystemExit(f"bad --start {spec!r}: use LEVEL:ROOM, e.g. --start 3:13")
    return None


if __name__ == "__main__":
    game = JetPackJoe()
    start = parse_start_arg(sys.argv)
    if start:
        game.set_level(start[0])
        game.jump_to_room(start[1])
    game.run()
