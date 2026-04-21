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

import struct, os, pygame

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

    def update(self, cbm):
        if not self.alive:
            return
        self.x += self.direction * 2
        # Check screen bounds
        if self.x < 0 or self.x >= SCREEN_W:
            self.alive = False
            return
        # Check wall collision using half-res bitmap (matching SH00.DAT shape 1: 4×2)
        hx, hy = int(self.x) // 2, int(self.y) // 2
        if 0 <= hx < HALF_W and 0 <= hy < HALF_H and cbm[hy * HALF_W + hx]:
            self.explosions.append(Explosion(self.x, self.y))
            self.alive = False
            return

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

    def update(self, cbm, sprites, pipe_floors=(), pipe_ceilings=()):
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
            s.update(cbm)
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
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
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
        self.build_assets()
        self.current_room = 0
        self.player = Player(160, 120)
        self.time_counter = 0
        self.game_over = False

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
            # Add cage collision walls (shape 13: two 2px walls, 18 rows tall)
            cbm = self.cbm_cache[room_idx][0]
            if room_idx in self.room_objects:
                for obj in self.room_objects[room_idx]:
                    if obj["type"] == 10:
                        hx, hy = obj["x"] // 2, obj["y"] // 2
                        for r in range(18):
                            for c in [1, 2, 21, 22]:  # left wall cols 1-2, right wall cols 21-22
                                bx, by = hx + c, hy + r
                                if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                    cbm[by * HALF_W + bx] = 1
            # Backup bitmap for DRAW_VISUAL erase (matches original 0x4820)
            self.cbm_backup[room_idx] = bytearray(cbm)
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
                if obj["type"] in (1, 2, 3, 4, 5, 9, 10) and "fg_tiles" in obj:
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
                            if ti < len(self.tile_surfs):
                                surface.blit(self.tile_surfs[ti], ((col + dc) * TILE_W, (row + dr) * TILE_H))
                            obj.setdefault("fg_tiles", {})[fg_idx] = 0  # skip in render_foreground
                        else:
                            # Foreground fan: defer to render_foreground (after Joe, with colorkey)
                            obj.setdefault("fg_tiles", {})[fg_idx] = ti
                continue
            elif ot == 8:  # vertical_field — lightning using actual game animation tiles
                # Check switch state — only draw if switch is ON
                switch_id = obj["params"][1] if len(obj["params"]) > 1 else 0
                if self.switch_state[switch_id] == 0:
                    continue  # field is OFF, don't draw lightning
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
                # Write collision for active vertical field
                cbm = self.get_collision_bitmap(room_idx)[0]
                backup = self.cbm_backup.get(room_idx)
                hx = (col * TILE_W) // 2
                # Shape 7: 2w at cols 3-4, alternating rows 0-34
                for r in range(0, 35, 2):
                    by = y_top // 2 + r
                    for c in [3, 4]:
                        bx = hx + c
                        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                            cbm[by * HALF_W + bx] = 1
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
                        bx = x_left // 2 + c
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
                        else:
                            # Animation complete — clear collision walls
                            cbm = self.get_collision_bitmap(room_idx)[0]
                            hx, hy = obj["x"] // 2, obj["y"] // 2
                            for r in range(18):
                                for c in [1, 2, 21, 22]:
                                    bx, by = hx + c, hy + r
                                    if 0 <= bx < HALF_W and 0 <= by < HALF_H:
                                        cbm[by * HALF_W + bx] = 0
                        sp = None
                    else:
                        # Active cage: draw captive + force field, check collision
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
            elif ot == 14:  # sentry — sprites 29-32
                sp = self.sprites[29 + (obj["timer"] // 8) % 4]
            elif ot == 13:  # glow_ball — sprites 35-37
                sp = self.sprites[35 + (obj["timer"] // 8) % 3]
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
                    surface.blit(self.tile_surfs[ti], (px, py))
            active_beam["timer"] += 1
            if active_beam["timer"] >= 4:
                active_beam["timer"] = 0
                if self.beam_out is not None:
                    # Beam-out: frames 0→16 (forward), Joe hidden at frame 12
                    self.beam_out["frame"] += 1
                    if self.beam_out["frame"] > 16:
                        # Beam-out done → teleport Joe → start beam-in
                        bo = self.beam_out
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
                        for other in self.room_objects.get(self.current_room, []):
                            if other["type"] == 19:
                                other["armed"] = False
                        self.beam_out = None
                        self.beam_in = {"tile": dest_tile, "frame": 15, "timer": 0}
                else:
                    # Beam-in: frames 15→0 (reverse)
                    self.beam_in["frame"] -= 1
                    if self.beam_in["frame"] < 0:
                        self.beam_in = None

    def update_objects(self):
        """Update objects that affect gameplay (teleporters). Called during update phase."""
        room_idx = self.current_room
        if room_idx not in self.room_objects:
            return
        px, py = int(self.player.x), int(self.player.y)
        for obj in self.room_objects[room_idx]:
            if obj["type"] == 19:  # teleporter — matching GAME.EXE 0x2219
                x, y = obj["x"], obj["y"]
                # Teleporter center (where trigger is): x+16, y+12
                cx, cy = x + 16, y + 12
                dx, dy = abs(px - cx), abs(py - cy)
                # Inner trigger: Joe center within ~10px of teleporter center
                inner = dx < 10 and dy < 8
                # Outer boundary: Joe within the full teleporter area
                outer_left = abs(px - (x + 2)) < 14
                outer_right = abs(px - (x + 42)) < 14
                outer_y = y - 4 < py < y + 40
                on_boundary = (outer_left or outer_right) and outer_y
                if not inner:
                    obj["armed"] = not on_boundary
                elif not on_boundary and obj.get("armed", True):
                    obj["armed"] = True
                    dest_room = obj["params"][1] if len(obj["params"]) > 1 else 0
                    dest_tile = obj["params"][2] if len(obj["params"]) > 2 else 0
                    # Start beam-out at source, then beam-in at destination
                    src_tile = obj["params"][0]
                    self.beam_out = {"tile": src_tile, "frame": 0, "timer": 0,
                                     "dest_room": dest_room, "dest_tile": dest_tile,
                                     "src_room": room_idx}
                    # Disarm all teleporters in current room
                    for other in self.room_objects.get(room_idx, []):
                        if other["type"] == 19:
                            other["armed"] = False
                    return

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
            self.player = Player(160, 120)
            self.game_over = False
            self.cbm_cache = {}
            self.cbm_backup = {}

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.player = Player(160, 120)
                        self.game_over = False
                    elif event.key == pygame.K_RIGHTBRACKET:
                        if self.current_room + 1 < self.num_rooms:
                            self.current_room += 1
                    elif event.key == pygame.K_LEFTBRACKET:
                        if self.current_room > 0:
                            self.current_room -= 1
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        self.set_level(event.key - pygame.K_1)
                    elif event.key == pygame.K_s:
                        n = 0
                        while os.path.exists(os.path.join(BASE, f"screenshot_{n:03d}.png")):
                            n += 1
                        fname = f"screenshot_{n:03d}.png"
                        shot = self.window.convert(24)
                        pygame.image.save(shot, os.path.join(BASE, fname))
                        print(f"Saved {fname}")

            if not self.game_over:
                beaming = self.beam_out is not None or self.beam_in is not None
                keys = pygame.key.get_pressed()
                if not beaming:
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
                cbm, pipe_floors, pipe_ceilings = self.get_collision_bitmap(self.current_room)
                self.player.update(cbm, self.sprites, pipe_floors, pipe_ceilings)
                self.update_objects()
                self.try_room_transition()
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
        if not self.game_over:
            joe_hidden = False
            if self.beam_out and self.beam_out["frame"] >= 12:
                joe_hidden = True
            if self.beam_in and self.beam_in["frame"] > 12:
                joe_hidden = True
            if not joe_hidden:
                self.player.draw(self.screen, self.sprites)
        self.render_foreground(self.current_room, self.screen)
        # Draw explosions on top of everything (they occur at wall edges)
        if not self.game_over:
            for e in self.player.explosions:
                e.draw(self.screen, self.sprites)

        bar_y = SCREEN_H
        pygame.draw.rect(self.screen, (0, 0, 0), (0, bar_y, SCREEN_W, STATUS_H))
        self.screen.blit(self.font.render(f"TIME: {self.player.time:03d}", False, (0, 255, 0)), (4, bar_y + 3))
        self.screen.blit(self.font.render("JET PACK JOE", False, (0, 255, 0)), (SCREEN_W // 2 - 36, bar_y + 3))
        self.screen.blit(self.font.render(f"ROOM: {self.current_room:02d}", False, (0, 255, 0)), (SCREEN_W - 60, bar_y + 3))

        if self.game_over:
            go = self.font.render("GAME OVER - Press R", False, (255, 0, 0))
            self.screen.blit(go, (SCREEN_W // 2 - go.get_width() // 2, SCREEN_H // 2))

        pygame.transform.scale(self.screen, (WIN_W, WIN_H), self.window)


if __name__ == "__main__":
    game = JetPackJoe()
    game.run()
