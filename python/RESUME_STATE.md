# Jet Pack Joe — Reverse Engineering State Document
# Last updated: 2026-04-21 (session 5)
# Purpose: Resume point for continuing the Python recreation

## PROJECT LOCATION
- Base directory: /Users/dev/Downloads/Joe/
- Python code: /Users/dev/Downloads/Joe/python/
- Original assets: /Users/dev/Downloads/Joe/DRAW/
- Original game: /Users/dev/Downloads/Joe/GAME.EXE + JET.RSC

## COMPLETED WORK

### Games fully recreated in Python:
1. python/missile_command.py — Missile Command (from MIS/MIS.ASM)
2. python/light_cycles.py — Light Cycles / Tron (from MIS/LC.ASM)
3. python/jet_pack_joe.py — Jet Pack Joe (IN PROGRESS — map + sprites working)

### Documentation:
- DOCUMENTATION.md — Full analysis of all source code and data formats
- RESUME_STATE.md — This file

### Dependencies:
- pygame-ce 2.5.7 installed via: pip3 install --break-system-packages pygame-ce
- dosbox-x installed via: brew install dosbox-x

## DECOMPRESSED GAME DATA (from JET.RSC via UNCRAM.EXE in dosbox-x)
All in /Users/dev/Downloads/Joe/python/:
- BK00.DAT — 130944 bytes — Tile pixel data (shared across levels)
- MP11.DAT — 65280 bytes — Level 1 map (compressed map from RSC, NOT same as DRAW/DATA.MAP)
- MP12.DAT — 65280 bytes — Level 2 map
- MP13.DAT — 65280 bytes — Level 3 map
- PL11.DAT — 768 bytes — Level 1 palette
- PL12.DAT — 768 bytes — Level 2 palette
- PL13.DAT — 768 bytes — Level 3 palette
- PL00.DAT — 768 bytes — Default palette
- SP00.DAT — 23997 bytes — Sprite data
- LV11.DAT — 514 bytes — Level 1 room/object definitions
- LV12.DAT — 1334 bytes — Level 2 room/object definitions
- LV13.DAT — 1684 bytes — Level 3 room/object definitions
- CB00.DAT — 3072 bytes — Collision data
- SH00.DAT — 1527 bytes — Collision sprite shapes (258 entries, scan pattern format)
- DS00.DAT — 38928 bytes — Display set (fade tables, palette effects)

### CRITICAL: DRAW/DATA.MAP ≠ MP11.DAT
- DATA.MAP is the EDITOR's working copy (different tile indices, 29321 bytes differ)
- MP11.DAT is the ACTUAL game level 1 map from the RSC archive
- DATA.BLK and BK00.DAT differ by only 116 bytes (nearly identical tile data)
- DATA.PAL was modified in 2000 (8 years after game), PL11.DAT is the correct game palette

### How decompression was done:
```bash
# Extract CRM files from RSC (python script parses TOC: 4-byte name + 4-byte offset)
# Copy UNCRAM.EXE from DRAW/ to work directory
# Run in dosbox-x:
dosbox-x -c "MOUNT C /tmp/doswork" -c "C:" -c "UNCRAM.BAT" -c "EXIT"
# UNCRAM.BAT contains: UNCRAM XX.CRM XX.DAT for each file
```

## TILE FORMAT (FULLY DECODED ✓)
- BK00.DAT: 682 tiles, 192 bytes each (130944 / 192 = 682)
- Each tile: 16 pixels wide × 12 pixels tall
- Stored as LINEAR 8-bit palette-indexed pixels (NOT Mode X planar)
- Row-major: 16 bytes per row, 12 rows per tile
- Max tile index used in MP11.DAT: 681 (fits exactly in 682 tiles)
- Previous assumption of 16×8 (1023 tiles) was WRONG
- BLOCK_TO_XY's "row * 12" is the actual tile height, not a gap between 8px tiles

### Complete Tile Catalogue (682 tiles)

**Reference images:** python/tile_sheet.png (20-column grid, index labels, 2× scale)

**Usage summary:**
- 682 total tiles, 278 used in maps, 404 unused
- 225 background-only, 53 foreground-only, 0 in both layers
- 122 tiles carry collision flags
- Level 1 exclusive: 22 tiles, Level 2 exclusive: 29, Level 3 exclusive: 27

#### Tiles 0–9: UI / Editor Artifacts
| Tile | Description |
|------|-------------|
| 0 | Blue circle on black — likely editor cursor/marker (not used in maps) |
| 1–3 | Solid black (palette index 16) — filler/padding |
| 4, 6–7 | Pink/magenta half-tiles — editor palette swatches |
| 5, 8 | Grey gradient tiles — editor test patterns |
| 9 | Pink/magenta half-tile variant |
| 10 | Solid black (palette index 16) |

#### Tiles 11–70: Unused
Not referenced in any level map. Likely reserved slots or editor workspace.

#### Tiles 71: Energy Field Collision Marker
Written to collision/screen map by vertical_field handler. Not visually rendered directly.

#### Tiles 80–83, 100–103, 120–123, 140–143, 160–163, 180–183: Vertical Lightning Field Animation
6 rows × 4 frames = 24 tiles. Used by vertical_field (object type 8).
- Row 0 (80–83): Top of field — white/blue zigzag sparks
- Row 1 (100–103): Upper-middle
- Row 2 (120–123): Middle
- Row 3 (140–143): Lower-middle
- Row 4 (160–163): Lower
- Row 5 (180–183): Bottom of field
- Frame cycle: 0→1→2→3→repeat
- Drawn with colorkey (black=transparent) over background

#### Tiles 138–139, 158–159: Pipe Corner Overlays (L3 only)
Grey pipe corner pieces, foreground-only. 72% black (mostly transparent). Used in Level 3 rooms 3, 12, 19, 20.

#### Tiles 174–176, 194–196: Nuclear Symbol / Red Warning Tiles (Foreground)
- 175, 195: Contain bright red (252,0,0) — nuclear/hazard warning symbol pieces
- 174, 176, 194, 196: Blue-grey surround pieces
- Used in cage rooms across all 3 levels (L1: rooms 4,9,13; L2: 11 rooms; L3: 11 rooms)

#### Tiles 177–179, 197–199: Green Warning Tiles (Foreground, L3)
- 178, 198: Contain bright green (0,252,0) — green variant of warning symbol
- Used in Level 3 rooms 4–18 (11 rooms each)

#### Tiles 187–188: Pipe Junction Overlays (Foreground)
Grey pipe junction pieces, 66% black. Used in rooms with doors (L1: 4,8,9; L2: 8 rooms; L3: 2 rooms).

#### Tiles 192–193, 211–212: Pipe End Caps (Foreground)
Grey pipe termination pieces. Used sparingly (L1: room 8; L2: room 19).

#### Tiles 200–205, 220–225, 240–245: Pipe Interior Overlays (Foreground, L2)
Three rows of pipe interior detail tiles:
- 200–202, 220–222, 240–242: Grey/pink pipe cross-sections (L2 rooms 20,22,23)
- 203–205, 223–225, 243–245: Grey/pink pipe variants (L2 room 20)
- Mix of grey (156,156,156) and pink/magenta (196,88,164) colors

#### Tiles 206–208, 226–228, 246–248: Shaft Interior Overlays (Foreground)
Shaft wall detail tiles, widely used across all levels:
- Grey variants (206–208, 246–248): grey (156,156,156) pipe walls
- Pink variants (226–228): magenta (196,88,164) pipe walls
- Used in 9–13 rooms per level

#### Tile 210: Pipe/Shaft T-Junction Overlay (Foreground)
Grey junction piece. Used in L1 room 0; L2: 7 rooms; L3: 3 rooms.

#### Tile 230: Left Switch ON State (Foreground)
#### Tile 231: Left Switch OFF State (Foreground)
Grey switch tiles. Toggled by left_switch (object type 7). Used in L1: rooms 4,8,9; L2: 6 rooms; L3: room 11.

#### Tile 250: Right Switch ON State (Foreground)
#### Tile 251: Right Switch OFF State (Foreground)
Grey switch tiles. Toggled by right_switch (object type 6). Used in L1: rooms 0,9; L2: 8 rooms; L3: room 4.

#### Tile 254: Blue Dither / Screen-Door Transparency (Foreground)
50% blue (0,0,168) / 50% black checkerboard pattern. Creates a screen-door transparency effect when drawn over background. Most-used foreground tile (340 uses). Used in rooms with cages and special areas.

#### Tiles 260–268: Pipe/Shaft Structure Tiles (Background, Grey/Brown/Pink)
Core structural tiles for the pipe and shaft system:
| Tile | Color | Flags | Role |
|------|-------|-------|------|
| 260 | Grey | 1,8,9,18 | Pipe corner (top-left junction) |
| 261 | Grey | 1,9 | Pipe ceiling |
| 262 | Grey | 1,8,9,19 | Pipe corner (top-right junction) |
| 263 | Brown | 1,10 | Shaft left wall (brown/orange) |
| 264 | Brown | 1,11 | Shaft right wall (brown/orange) |
| 265 | Brown | 1 | Solid brown wall |
| 266 | Pink | 1,18 | Pipe corner (pink variant, left) |
| 267 | Pink | 1 | Solid pink wall |
| 268 | Pink | 1,11 | Shaft right wall (pink variant) |

#### Tile 269: Grey Shaft Double-Wall
Grey (156,156,156). Flags 1,10,11. Shaft with both left and right wall collision. 329 uses.

#### Tile 270: Dark Grey Fill — MOST USED TILE
Dark grey (52,52,52). 40,041 uses across all levels. The primary "empty but not black" background fill. Carries many collision flags depending on context (1,16,34,35,42,50,51,53,60,61).

#### Tiles 271–275, 291–295, 311–313: Decorative Wall Details
Brown/tan textured wall pieces with mixed colors. Low usage (1–48 uses). Used in specific rooms for visual detail (cave walls, rocky surfaces).

#### Tiles 280–288: Solid Wall Tiles (Grey/Brown/Pink)
Core solid wall tiles, heavily used:
| Tile | Color | Uses | Role |
|------|-------|------|------|
| 280 | Grey | 193 | Solid grey wall (top edge) |
| 281 | Grey | 439 | Solid grey wall (flat) — 2nd most used structural |
| 282 | Grey | 207 | Solid grey wall (bottom edge) |
| 283 | Brown | 130 | Brown wall with left shaft edge |
| 284 | Brown | 360 | Brown wall (both shaft edges) |
| 285 | Brown | 136 | Solid brown wall |
| 286 | Pink | 158 | Pink wall (top edge) |
| 287 | Pink | 410 | Solid pink wall — most used pink tile |
| 288 | Pink | 175 | Pink wall (bottom edge) |

#### Tiles 289–290: Brown Wall Variants
Textured brown walls. Used in specific rooms (L1: rooms 4–13; L2: rooms 4,5).

#### Tiles 300–308: Pipe Structure Tiles (Dark Variants)
Same layout as 260–268 but with darker shading (shadow side):
| Tile | Color | Flags | Role |
|------|-------|-------|------|
| 300 | Dark grey | 1,8,9,26 | Pipe corner (bottom-left, shadowed) |
| 301 | Dark grey | 1,8 | Pipe floor (shadowed) |
| 302 | Dark grey | 1,8,9,27 | Pipe corner (bottom-right, shadowed) |
| 303 | Dark brown | 1 | Solid dark brown wall |
| 304 | Dark brown | 1,10,11 | Dark brown shaft (both walls) |
| 305 | Dark brown | 1 | Solid dark brown wall |
| 306 | Dark pink | 1,8 | Dark pink pipe floor |
| 307 | Dark pink | 1,8,10,11 | Dark pink pipe+shaft combo |
| 308 | Dark pink | 1,29 | Dark pink wall (special flag 29) |

#### Tile 309: Solid Pink Fill
Pink (152,72,128). 6,010 uses. Second most-used tile overall. Primary pink area fill.

#### Tile 310: Dark Purple Fill
Purple (56,24,88). 1,157 uses. Purple area fill with many collision flag variants.

#### Tiles 320–322, 333: Platform/Ledge Tiles
| Tile | Flags | Role |
|------|-------|------|
| 320 | 1,50 | Platform edge (diagonal collision) |
| 321 | 1,17,50,51,58,59 | Platform surface (many collision variants) |
| 322 | 51 | Platform underside (passable from below) |
| 333 | 17,50,51 | Platform variant |

#### Tiles 327, 330, 346–350: Cave/Cavern Detail Tiles
Used in cave rooms (L1: rooms 6–8; L2: rooms 3–5). Include diagonal slopes (flags 17, 35).

#### Tiles 340–342: Structural Fill Tiles
| Tile | Uses | Flags | Role |
|------|------|-------|------|
| 340 | 189 | 1,34,42,50 | Structural fill with multiple collision types |
| 341 | 573 | 17 flags | Multi-purpose structural tile (most collision flag variants) |
| 342 | 21 | 50 | Diagonal platform piece |

#### Tiles 352–354: Transition/Border Tiles
Used at room boundaries and area transitions. 352 has flags 1,42,60.

#### Tiles 360–362: Floor/Ceiling Tiles
| Tile | Flags | Role |
|------|-------|------|
| 360 | 1 | Floor tile |
| 361 | 17 | Sloped floor |
| 362 | 17 | Sloped floor variant |

#### Tiles 372–374: Decorative Arch/Opening Tiles
No collision flags. Used around doorways and openings.

#### Tiles 380–381: Thick Wall Tiles
Solid walls with flag 1. Used in specific rooms.

#### Tiles 386–391: Pipe System Tiles (Horizontal)
Horizontal pipe sections:
| Tile | Flags | Role |
|------|-------|------|
| 386 | 1,9 | Horizontal pipe (grey top) |
| 387 | 1,9 | Horizontal pipe (grey variant) |
| 388 | 1,9 | Horizontal pipe (grey bottom) |
| 389 | 1,10 | Pipe with left wall |
| 390 | 1 | Solid pipe fill |
| 391 | 1,11 | Pipe with right wall |

#### Tiles 392–397, 412–417: Decorative/Background Tiles
- 392–395, 412–415: Low-usage decorative elements (arches, details)
- 396: Grey structural (160 uses, L1+L2 only)
- 397: Grey background (200 uses, no collision)
- 416: Background fill (111 uses)
- 417: Grey fill (1,682 uses, flags 1,16,34,35,56,57) — L1+L2 only

#### Tiles 400–401, 420–422: Room-Specific Decorations
Used in specific rooms for visual detail (L1: rooms 6,12–14; L2: rooms 6,15,26).

#### Tiles 406–411: Pipe System Tiles (Dark Horizontal Variants)
Dark-shaded versions of 386–391:
| Tile | Flags | Role |
|------|-------|------|
| 406 | 1 | Dark horizontal pipe top |
| 407 | 1 | Dark horizontal pipe variant |
| 408 | 1,8 | Dark horizontal pipe bottom |
| 409 | 1,10 | Dark pipe with left wall |
| 410 | 1 | Dark solid pipe fill |
| 411 | 1,11 | Dark pipe with right wall |

#### Tiles 426–437: Additional Pipe/Wall Tiles
More pipe and wall variants for visual variety:
- 426–428: Pipe sections (flags 1,8)
- 429–431: Shaft sections (flags 1,10,11)
- 432–435: Decorative details
- 436: Structural (153 uses, L1+L2)
- 437: Background (114 uses)

#### Tiles 446–448, 466–468: Arch/Opening Detail Tiles
Decorative arch pieces. No collision. Used in L1 rooms 1,3,10,14; L2 rooms 12,26; L3 widely.

#### Tile 450: Floor Tile
Solid floor with flag 1. Used in 18 rooms across all levels.

#### Tiles 456–457: Structural Tiles (L1+L2)
- 456: Wall (100 uses, flag 1)
- 457: Fill (517 uses, flags 1,17,34,58,59)

#### Tiles 470+: Level 2 & 3 Specific Tiles
Higher-numbered tiles are increasingly level-specific:
- 470–500s: Level 2/3 cave and structure tiles (brown, dark tones)
- 500–530s: Level 2/3 specific structures (teal/cyan colors for L2/L3 palette)
- 540–600s: Level 3 specific tiles (red/dark themes)
- 593: Dark fill (1,686 uses — L2+L3 primary fill, like 270 for L1)
- 573: Dark structural (743 uses, L2+L3)
- 578: Structural (332 uses)
- 597: Structural (217 uses)
- 600–681: Level 3 specific decorative and structural tiles (red/dark palette)
- 640–641, 660–661, 680–681: Yellow diagonal stripe tiles (hazard markings)

## PALETTE FORMAT (FULLY DECODED ✓)
- 768 bytes = 256 colors × 3 (R, G, B)
- VGA 6-bit DAC values (0-63), multiply by 4 for 8-bit RGB
- Each level has its own palette (PL11, PL12, PL13)

## MAP FORMAT (FULLY DECODED ✓)

### EXPAND_MAP routine (at ~0x0548 in GAME.EXE):
```asm
IMUL SI, AX, 0x03C0    ; SI = room_number * 960 (source offset)
MOV DI, 0x0357          ; destination in SCREEN_MAP
MOV CX, 0x0140          ; 320 iterations

; Loop 1: process 320 tile WORDS
LODSW                   ; read 16-bit tile word from map
MOV DL, AH              ; extract high byte
SHR DL, 2               ; shift right 2 = flags for collision map
MOV ES:[BX], DL         ; store to collision map
INC BX
AND AX, 0x03FF          ; mask to 10-bit tile index
STOSW                   ; store to screen map
LOOP                    ; repeat 320 times

; Loop 2: process 320 tile BYTES
SUB AH, AH              ; clear high byte
MOV CX, 0x0140          ; 320 iterations
LODSB                   ; read 8-bit tile byte (foreground/overlay)
STOSW                   ; store as 16-bit word (zero-extended)
LOOP                    ; repeat 320 times
```

### Per room: 960 bytes total
- First 640 bytes = 320 × 16-bit tile words (background layer)
- Next 320 bytes = 320 × 8-bit tile indices (foreground/overlay layer)
- 65280 / 960 = 68 rooms per level

### Tile word format:
- Bits 0-9: tile index (0-681) into BK00.DAT
- Bits 10-15: flags (shifted right 2 and stored to collision map)
- 0xFFFF = empty tile

### Grid layout: 20 columns × 16 rows, row-major order
- Tiles are 16×12 pixels
- 20 cols × 16px = 320px wide
- 16 rows × 12px = 192px tall
- Each room is a single screen (NOT paired rooms)
- 192px game area + status bar at bottom
- Foreground layer: tile index 0 and 255 are empty/transparent
- Visually confirmed against 9 dosbox screenshots of rooms 0-4

### BLOCK_TO_XY (at ~0x05EA):
```asm
MOV CX, 20         ; divide by 20
DIV CX              ; AX = row = index/20, DX = col = index%20
IMUL DX, AX, 12     ; DX = row * 12 (tile height = 12px)
SHL CX, 4           ; CX = col * 16 (tile width = 16px)
SUB CX, 0xA0        ; CX -= 160 (center X)
SUB DX, 0x60        ; DX -= 96 (center Y)
```

## SPRITE FORMAT (FULLY DECODED ✓)

### Overview:
- SP00.DAT: 23997 bytes, 102 sprites
- 16-bit offset table at start: 102 entries (204 bytes)
- Vertical column RLE encoding, designed for Mode X rendering

### 4-byte header per sprite (all signed bytes):
- x_off: left edge relative to sprite origin
- y_off: top edge relative to sprite origin
- x_end: right edge relative to sprite origin
- y_end: bottom edge relative to sprite origin
- Width = x_end - x_off + 1
- Height = y_end - y_off + 1

### Body encoding (reverse-engineered from DRAW_SPRITE at 0x3236 in GAME.EXE):
Sprites are drawn as VERTICAL COLUMNS, not horizontal rows.
This is because Mode X uses MOVSB + ADD DI,79 to draw pixels going down.

```
Format:
  Repeat until 0x0000 word found:
    delta_x (signed byte) — cumulative X cursor adjustment
    delta_y (signed byte) — cumulative Y cursor adjustment
    
    First column in segment:
      draw_count (unsigned byte)
      pixels[draw_count] — drawn vertically starting at (cur_x, cur_y)
    
    Subsequent columns (repeat until 0x0000 word):
      skip_h (unsigned byte) — horizontal pixel skip (advances X)
      row_offset (signed byte) — CUMULATIVE vertical offset adjustment
      draw_count (unsigned byte) — number of pixels to draw vertically
      pixels[draw_count] — pixel data (palette indices)
    
    Segment terminated by 0x0000 (two zero bytes)
  
  Sprite terminated by 0x0000 (two zero bytes)
```

### Key details:
- delta_x/delta_y are CUMULATIVE (ADD [BP-4],AX / ADD [BP-6],AX in ASM)
- row_offset is also CUMULATIVE on the base Y position (ADD BX, offset*80)
- skip_h advances horizontally through Mode X planes (1 skip = 1 pixel right)
- Pixel ranges exactly match header bounds when decoded correctly
- Transparent pixels are simply not drawn (no explicit transparency marker)

### Complete Sprite Catalogue (102 entries):

**Reference images:** python/sprite_sheet.png (10-column grid, index labels)

#### Player — Jet Pack Joe (sprites 0–7)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 0 | 32×29 | (-16,-14)→(+15,+14) | Joe facing left, frame 0 (gun arm extended left) |
| 1 | 32×29 | (-13,-14)→(+18,+14) | Joe facing right, frame 0 (gun arm extended right) |
| 2 | 32×29 | (-16,-14)→(+15,+14) | Joe facing left, frame 1 (gun arm raised) |
| 3 | 32×29 | (-13,-14)→(+18,+14) | Joe facing right, frame 1 (gun arm raised) |
| 4 | 30×29 | (-14,-14)→(+15,+14) | Joe facing left, frame 2 (arms closer, narrower) |
| 5 | 30×29 | (-13,-14)→(+16,+14) | Joe facing right, frame 2 |
| 6 | 30×29 | (-14,-14)→(+15,+14) | Joe facing left, frame 3 |
| 7 | 30×29 | (-13,-14)→(+16,+14) | Joe facing right, frame 3 |
- Even indices = facing left, odd = facing right
- Frames 0-3 have gun arm, frames 4-7 are narrower (no gun extended)
- Origin centered on Joe's body; gun barrel extends beyond collision shape
- 20-21 unique colors (purple suit, skin tones, brown boots, blue jetpack)

#### Jetpack Flames (sprites 8–19)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 8 | 8×5 | (+1,+10)→(+8,+14) | Small vertical flame, right-facing Joe (below-right) |
| 9 | 8×5 | (-6,+10)→(+1,+14) | Small vertical flame, left-facing Joe (below-left) |
| 10 | 7×7 | (+4,+7)→(+10,+13) | Small diagonal flame, moving left (down-right) |
| 11 | 7×7 | (-8,+7)→(-2,+13) | Small diagonal flame, moving right (down-left) |
| 12 | 8×7 | (+1,+10)→(+8,+16) | Medium vertical flame, right-facing |
| 13 | 8×7 | (-6,+10)→(+1,+16) | Medium vertical flame, left-facing |
| 14 | 9×10 | (+4,+7)→(+12,+16) | Medium diagonal flame, moving left |
| 15 | 9×10 | (-10,+7)→(-2,+16) | Medium diagonal flame, moving right |
| 16 | 8×10 | (+1,+10)→(+8,+19) | Large vertical flame, right-facing |
| 17 | 8×10 | (-6,+10)→(+1,+19) | Large vertical flame, left-facing |
| 18 | 12×12 | (+4,+7)→(+15,+18) | Large diagonal flame, moving left |
| 19 | 12×12 | (-13,+7)→(-2,+18) | Large diagonal flame, moving right |
- All 4 colors (blue/white flame gradient)
- Origin offsets position flames relative to Joe's center
- Flame on opposite side of facing direction (jetpack is on Joe's back)
- Growth sequence: small (thrust_timer 0-9), medium (10-19), large (20+)
- Vertical flames for thrust up; diagonal for horizontal movement

#### Empty/Unused Slots (sprites 20–22, 27–28)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 20 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |
| 21 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |
| 22 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |
| 27 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |
| 28 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |

#### Projectiles / Indicators (sprites 23–26)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 23 | 10×5 | (-4,-1)→(+5,+3) | Small arrow/projectile pointing right (9 colors) |
| 24 | 10×5 | (-5,-1)→(+4,+3) | Small arrow/projectile pointing left (9 colors) |
| 25 | 3×89 | (0,-95)→(+2,-7) | Red vertical laser beam (tall, 3 colors) |
| 26 | 3×89 | (0,-95)→(+2,-7) | Green vertical laser beam (tall, 3 colors) |
- Laser beams are 89px tall, drawn from far above origin (y_off=-95)
- Used for vertical energy field/laser hazards

#### Red Sentry / UFO (sprites 29–33)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 29 | 21×11 | (-9,-6)→(+11,+4) | Sentry frame 0 — widest, wings fully extended |
| 30 | 19×11 | (-8,-6)→(+10,+4) | Sentry frame 1 — wings slightly retracted |
| 31 | 15×11 | (-6,-6)→(+8,+4) | Sentry frame 2 — wings most retracted (narrowest) |
| 32 | 19×11 | (-8,-6)→(+10,+4) | Sentry frame 3 — wings extending again |
| 33 | 9×7 | (-4,-3)→(+4,+3) | Sentry bullet/projectile (1 color — solid white circle outline) |
- 9 colors (red body, dark red shading, white highlights)
- Animation cycle: 29→30→31→32→(repeat) — wing flapping
- Sentries patrol and shoot (object type 14)

#### Energy Orbs / Glow Balls (sprites 34–38)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 34 | 13×11 | (-6,-5)→(+6,+5) | Blue orb with white ring outline (7 colors) |
| 35 | 15×13 | (-7,-6)→(+7,+6) | Blue glow ball, medium (6 colors, blue/cyan/white) |
| 36 | 19×17 | (-9,-8)→(+9,+8) | Blue glow ball, large (6 colors) |
| 37 | 19×18 | (-9,-9)→(+9,+8) | White cluster — 4 small circles (4 colors) |
| 38 | 20×21 | (-9,-10)→(+10,+10) | Bubble cluster — scattered circles (4 colors) |
- 34: orb_generator projectile outline
- 35-36: glow_ball entity (object type 13), size variants
- 37-38: dissipating/exploding ball effect

#### Birds (sprites 39–41)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 39 | 33×21 | (-14,-10)→(+18,+10) | Bird frame 0 — wings up (pink/magenta, 22 colors) |
| 40 | 21×21 | (-10,-10)→(+10,+10) | Bird frame 1 — wings mid/folded (21 colors) |
| 41 | 33×21 | (-18,-10)→(+14,+10) | Bird frame 2 — wings down (21 colors, mirrored from 39) |
- Colorful pink/magenta/cyan bird enemy
- Animation cycle: 39→40→41→(repeat) — wing flapping
- Spawned by bird_generator (object type 11)
- Width varies 21-33px as wings extend/retract

#### Explosion / Electric Effects (sprites 42–45)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 42 | 24×21 | (-11,-10)→(+12,+10) | Electric zap frame 0 — white/blue sparks (11 colors) |
| 43 | 22×18 | (-11,-9)→(+10,+8) | Electric zap frame 1 — smaller sparks |
| 44 | 22×19 | (-11,-9)→(+10,+9) | Electric zap frame 2 — blue/white bolts |
| 45 | 27×21 | (-13,-10)→(+13,+10) | Electric zap frame 3 — large blue circle with sparks |
- Used for energy field kill effect / electrocution death
- 11 colors (white, blue, cyan electric palette)

#### Death / Explosion Sequence (sprites 46–49)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 46 | 32×34 | (-15,-16)→(+16,+17) | Death frame 0 — Joe breaking apart (20 colors) |
| 47 | 45×43 | (-22,-21)→(+22,+21) | Death frame 1 — debris spreading (8 colors, grey) |
| 48 | 65×55 | (-30,-27)→(+34,+27) | Death frame 2 — debris scattered wide (8 colors) |
| 49 | 77×65 | (-37,-31)→(+39,+33) | Death frame 3 — debris fully dispersed (5 colors, fading) |
- Progressive explosion: starts with recognizable Joe pieces, ends as scattered dots
- Each frame larger than the last (32px → 77px wide)
- Frame 46 has Joe's colors; 47-49 fade to grey/white debris

#### Small Glow Effects (sprites 50–53)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 50 | 9×7 | (-4,-3)→(+4,+3) | Tiny glow ball (6 colors, blue/white) |
| 51 | 11×9 | (-5,-4)→(+5,+4) | Small glow ball (8 colors) |
| 52 | 13×11 | (-6,-5)→(+6,+5) | Medium glow ball (8 colors) |
| 53 | 17×13 | (-8,-6)→(+8,+6) | Large glow ball (8 colors) |
- Growing glow ball animation sequence (50→51→52→53)
- Used for ball_generator (object type 12) projectiles
- Blue/cyan/white gradient

#### Empty Slots (sprites 54–57)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 54 | 1×1 | (0,0)→(0,0) | Empty (0 pixels) |
| 55 | 1×1 | (0,0)→(0,0) | Empty — reserved for toggle switch (tile-based, not sprite) |
| 56 | 1×1 | (0,0)→(0,0) | Empty — reserved for toggle switch |
| 57 | 1×1 | (0,0)→(0,0) | Empty — reserved for toggle switch |
- Note: toggle switches use foreground tile replacement (tiles 230/231, 250/251), not sprites

#### Captive Characters (sprites 58–63)
| Idx | Size | Origin | Description |
|-----|------|--------|-------------|
| 58 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — blue/teal outfit (26 colors) |
| 59 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — pink/magenta outfit (31 colors) |
| 60 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — red/orange outfit (33 colors) |
| 61 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — green outfit (33 colors) |
| 62 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — teal/green outfit (31 colors) |
| 63 | 34×35 | (-16,-7)→(+17,+27) | Captive kid — yellow/orange outfit (28 colors) |
- All same dimensions, different color palettes for each kid
- Origin y_off=-7 means sprite extends 27px below origin (standing on ground)
- Used by cage object (type 10), param[2] selects which sprite
- Arms raised in celebration pose

#### Empty Slots (sprites 64–101)
| Idx | Description |
|-----|-------------|
| 64–101 | All empty (1×1, 0 pixels, 7 bytes each) |
- 38 unused sprite slots
- Total of 102 entries in offset table; only 54 contain actual sprite data

### DRAW_SPRITE routine location in GAME.EXE:
- Function entry: 0x3236 (PUSH BP; MOV BP,SP)
- PUSHA at 0x323C
- Header reading at 0x3252: four LODSB+CBW+ADD sequences
- Clipping checks: 0x3262-0x32A3
- Unclipped draw loop: 0x32D6-0x3302
- Clipped draw loop: 0x3305-0x338D
- Function end: 0x3390 (POPA; RET)

## COLLISION FORMAT
- **Primary collision**: tile word flags (bits 10-15), extracted by EXPAND_MAP as (AH >> 2)
  - Value 0 = passable, non-zero = type-dependent
  - This is the ONLY source used for collision checks
- CB00.DAT: NOT used for collision (decorative tiles have false positives)

### Collision Flag Values:
| Flag | Type | Current Python Collision |
|------|------|------------------------|
| 0 | Passable (air) | Not in bitmap |
| 1 | Solid wall/floor | Full tile pixel collision |
| 8 | Pipe bottom wall | **PASSABLE** (foreground only) |
| 9 | Pipe ceiling/floor | Full tile pixel collision (solid) |
| 10 | Shaft left wall | **PASSABLE** (foreground only) |
| 11 | Shaft right wall | **PASSABLE** (foreground only) |
| 16-17 | Unknown | Full tile pixel collision |
| 18-19 | Shaft bottom | **PASSABLE** |
| 20-21 | Shaft opening | **PASSABLE** |
| 34-35 | Energy field | Full tile pixel collision |
| Others | Unknown | Full tile pixel collision |

### Pixel-Perfect Collision System (current implementation):
- 320×192 collision bitmap built from tile pixels where flags != 0 and not in passable set
- Joe's full 32×29 sprite mask checked against bitmap
- Nudge system: on collision, tries ±2,±4,±6 pixel offsets on the other axis
- Room transitions use LV11.DAT 8-byte headers matching original GAME.EXE at 0x0721

### PIPE/SHAFT COLLISION SYSTEM — WORKING (CB00.DAT breakthrough):
**Key breakthrough**: CB00.DAT (3072 bytes) IS the collision tile shapes — 64 shapes × 48 bytes (8×6 half-res pixels). Each collision flag value (0-63) indexes directly into this data. Discovered by disassembling 0x3080 (collision buffer builder) and 0x397A (file loader).

**How collision works now (matching original GAME.EXE):**
1. Collision bitmap is 160×96 (half-res), not 320×192
2. For each tile with flags≠0, copy the 8×6 shape from CB00.DAT[flag*48] into the bitmap
3. Sprite collision checks divide coordinates by 2 (matching original SAR CX,1 / SAR DX,1)
4. Shaped collision tiles naturally handle pipes: flag 8 = bottom row only, flag 10 = left 2 cols only, etc.

**CB00.DAT collision shapes (key values):**
| Flag | Shape | Description |
|------|-------|-------------|
| 0 | empty | Passable |
| 1 | full 8×6 | Solid wall |
| 2 | full top, tapered bottom | Rounded bottom |
| 3 | tapered top, full bottom | Rounded top |
| 8 | bottom row only | Pipe floor |
| 9 | top row only | Pipe ceiling |
| 10 | left 2 cols | Shaft left wall |
| 11 | right 2 cols | Shaft right wall |
| 18 | top-left 2px | Shaft junction corner |
| 19 | top-right 2px | Shaft junction corner |
| 20 | top row + left 2 cols | Shaft opening left |
| 21 | top row + right 2 cols | Shaft opening right |
| 42/43 | diagonal slopes | Staircase walls |
| 50/51 | diagonal slopes | Staircase walls (opposite) |

**Invisible pipe barriers (still needed for gameplay):**
- Pipe floor (flags=8): invisible platform at tile bottom - 4px
- Pipe ceiling (flags=9): invisible barrier at tile top + floor when falling from above

**Rendering layers (draw order):**
1. Background tiles (render_room, cached)
2. Joe sprite (player.draw)
3. Foreground pass (render_foreground):
   - Pipe/shaft bg tiles (flags 8/9/10/11/18/19/20/21) drawn opaque over Joe
   - Interior tiles between pipe rows drawn opaque (skip if foreground tile exists)
   - Foreground layer tiles drawn with colorkey (black=transparent)
   - Tile 254 (blue dither) creates screen-door transparency effect

**SH00.DAT** (1527 bytes): loaded at ES:0x9D40 — **COLLISION SPRITE SHAPES (FULLY DECODED ✓)**

The original game does NOT use visual sprite pixels for collision. Instead, SH00.DAT contains
pre-built scan patterns that define each sprite's collision shape as a series of horizontal
line segments in the half-res (192×96) collision bitmap.

**How it was decoded:**
1. Disassembled CHECK_COLLISION at 0x043C in GAME.EXE
2. Traced into subroutine 0x2F11 which reads SH00.DAT scan patterns
3. Found the collision bitmap is 192 bytes wide (not 160) with 32 columns of left padding
4. Decoded the scan pattern format: repeated (delta:signed_word, count:byte), terminated by count=0
5. The delta is a flat byte offset in the 192-wide bitmap; decompose with `row = round(delta / 192)`

**SH00.DAT format:**
- 258-entry offset table (516 bytes) at start — one entry per collision sprite
- Each collision sprite: sequence of (delta:int16, count:uint8) scan segments
  - delta = signed byte offset relative to current position in 192-wide collision bitmap
  - count = number of consecutive bytes to scan horizontally (0 = end of shape)
  - The scan checks each byte against the collision bitmap; any non-zero = collision hit
- Terminated by a segment with count=0

**Collision bitmap layout (original game):**
- 192 columns × 96 rows = 18432 bytes (stride 0xC0)
- Game area occupies columns 32–191 (160 pixels), with 32 columns of left padding
- Player position in bitmap: `DI = half_y * 192 + (half_x + 32)`
- Our Python version uses 160×96 (no padding), so we apply shape offsets directly to `half_x, half_y`

**CHECK_COLLISION (0x043C) calling convention:**
- AX = collision sprite index (into SH00.DAT offset table)
- BL = collision type filter (0x0E for Joe's first check, 0 for nudge checks)
- CX = player X (centered coords, -160 to +160)
- DX = player Y (centered coords, -96 to +96)
- Internally: adds 160 to CX, 96 to DX, then SAR 1 (divide by 2 = half-res)
- Returns: ZF=1 if no collision, ZF=0 if collision; AL = collision type hit

**Joe's collision shape (SH00.DAT entry 0) — IMPLEMENTED ✓:**
```
Rows -7 to +7, Cols -6 to +7 (half-res, relative to player origin)
14 wide × 15 tall half-res pixels = ~28×30 full-res pixels

    ....######....
    ..##########..
    .############.
    .############.
    ##############
    ##############
    ##############
    ######O#######   ← O = player origin
    ##############
    ##############
    ##############
    ##############
    ##############
    ##############
    ##############
```
- Rounded top (narrower at rows -7 and -6), flat bottom
- ~4px narrower than visual sprite on each side — gun barrel excluded
- Same shape regardless of facing direction (AX=0 always for Joe)

**Joe's collision handler (0x0CCC) — nudge system:**
```
1. Check collision at (JET_X, JET_Y) with AX=0, BL=0x0E
2. If hit, check if it's a special type (energy field etc.)
3. Call DRAW_COLLISION (0x048C → 0x2FCB) to write Joe's shape to bitmap
4. Re-check with BL=0 (any collision):
   - Try (X, Y) — original position
   - Try (X-2|1, Y) — nudge left
   - Try (X+1, Y) — nudge right
   - Try (X, Y-2|1) — nudge up
   - Try (X, Y+1) — nudge down
   - Try (X-2|1, Y+1) — nudge left+down
   - Try (X+1, Y+1) — nudge right+down
   - Try (X+1, Y-2) — nudge right+up
   - Try (X-2, Y-2) — nudge left+up
5. If any nudge succeeds, update JET_X/JET_Y to the nudged position
```

**How to use SH00.DAT for other sprites:**
The 258-entry offset table covers all game entities. To decode any collision shape:
```python
import struct
STRIDE = 192
sh_data = open('SH00.DAT', 'rb').read()
off = struct.unpack_from('<H', sh_data, sprite_idx * 2)[0]
pos, di_rel, scans = off, 0, []
while pos + 2 < len(sh_data):
    delta = struct.unpack_from('<h', sh_data, pos)[0]; pos += 2
    count = sh_data[pos]; pos += 1
    if count == 0: break
    di_rel += delta
    row = round(di_rel / STRIDE)
    col = di_rel - row * STRIDE
    scans.append((row, col, count))
    di_rel += count
# scans = list of (row_offset, col_offset, width) in half-res pixels
```
This will be needed for: sentries (type 14), birds (type 11), balls (type 12),
orbs (type 20), and any other entity that needs collision detection.
The sprite index passed to CHECK_COLLISION can be found by tracing each
object handler's call to 0x043C and reading the AX value.

**Animation:** Joe stays on frame 0 (static) unless firing (cycles frames 0-3). Jetpack flame implemented:
- Flame sprites are separate overlays drawn on top of Joe
- **Thrust up**: sprites 9/8→13/12→17/16 (small→large, swapped for facing — jetpack is on opposite side)
- **Moving left**: sprites 10→14→18 (diagonal down-right, growing)
- **Moving right**: sprites 11→15→19 (diagonal down-left, growing)
- Flame grows over time (thrust_timer: 0-9=small, 10-19=medium, 20+=large)
- Flame shows when thrusting OR moving horizontally
- Flame resets immediately when stopping

**Sprite catalogue:** See "Complete Sprite Catalogue (102 entries)" in SPRITE FORMAT section above.

## OBJECT/ENTITY SYSTEM (FULLY DECODED from user's document)

### Object Type Table:
| ID | Name | Parameters |
|----|------|-----------|
| 0 | null_routine | (none) |
| 1 | fan_1 | location |
| 2 | fan_2 | location |
| 3 | fan_3 | location |
| 4 | fan_4 | location |
| 5 | door | location, switch, variable |
| 6 | right_switch | location, switch |
| 7 | left_switch | location, switch |
| 8 | vertical_field | location, switch |
| 9 | horiz_field | location, switch |
| 10 | cage | location, switch, sprite |
| 11 | bird_generator | location |
| 12 | ball_generator | location |
| 13 | glow_ball | location, switch |
| 14 | sentry | location, variable |
| 15 | left_plate | location, variable |
| 16 | right_plate | location, variable |
| 17 | toggle_switch | location, switch, switch |
| 18 | sensor_switch | location, switch, switch |
| 19 | teleporter | location, room, dest_location |
| 20 | orb_generator | location |
| 21 | null_routine | (none) |
| 22 | null_routine | (none) |
| 23 | null_routine | (none) |

### Level Data Format (LV11.DAT etc.):
- Offset table: N 16-bit word offsets (N = first_offset / 2)
- Each room entry:
  - 8-byte header: room connectivity (neighbor room IDs, 0xFF = no exit)
  - Object list: sequence of (object_type_word, param1_word, param2_word, ...) 
  - Terminated by 0xFFFF
- Level 1 has 17 active rooms (0-16), rooms 17-68 point to shared empty data

### Room connectivity (Level 1):
Room 0 → Room 1 → Room 2 → Room 3 → Room 4 → Room 5 ↔ Room 6 → Room 7 → Room 8 → Room 9 → Room 10 → Room 11 → Room 12 → Room 13 ↔ Room 14 ↔ Room 15

### Parsed objects (Level 1):
- Room 0: left_switch@163, vertical_field@116
- Room 1: fan_3@148
- Room 2: fan_1@123
- Room 3: fan_4@168
- Room 4: fan_2@246, fan_2@256, fan_2@76, right_switch@153, door@26, cage@21
- Room 5: ball_generator@64, ball_generator@236
- Room 8: fan_1@134, right_switch@216, bird_generator@270, door@42
- Room 9: left_switch@204, right_switch@77, cage@54, door@51, door@22, fan_1@153
- Room 13: fan_1@72, cage@61, cage@224

## GAME.EXE SYMBOL TABLE (key symbols)
Located in debug section starting around 0x10A8E:
- GAME.ASM: main entry, memory init, archive loading
- PLAY.ASM: game loop, player control, room management
- ANIM.ASM: cutscene animations (thumbs up, death, title, credits)
- ARC.ASM: RSC archive file handling
- UNCRAM.ASM: CRAM decompression
- SPRITE.ASM: sprite rendering with clipping (DRAW_SPRITE at 0x3236)
- CHAR.ASM: text/character rendering
- LOAD.ASM: tile/collision/sprite loading
- CRMLD.ASM: compressed file reading
- TIMER.ASM: timer interrupt handling
- MODE.ASM / DRIVER.ASM: Mode X video driver (JAM driver)
- Sound drivers: pulse width (speaker), speech thing (Covox), sound master

### Key GAME.EXE addresses:
- DRAW_SPRITE: 0x3236 (sprite rendering with clipping)
- EXPAND_MAP: ~0x0548 (map decompression to screen map)
- BLOCK_TO_XY: ~0x05EA (tile index to pixel coordinates)
- SET_SPRITE_WINDOW: referenced in symbol table
- GET_SPRITE_LIMITS: referenced in symbol table
- JAM driver: ~0x4574 (Mode X tile renderer)

## CRAM COMPRESSION (NOT DECODED)
- Custom LZ77 sliding-window compression by Joe Lowe
- 5 code types: LITERAL, SAME_LOOK, ONE_MATCH, SHORT_CODE, LONG_CODE
- Workaround: use dosbox-x + UNCRAM.EXE to decompress files
- CRAM.EXE and UNCRAM.EXE are in DRAW/ directory

## DOSBOX SCREENSHOTS (reference images)
9 screenshots taken from GAME.EXE running in dosbox-x, located in /Users/dev/Downloads/Joe/:
- Screenshot...11.44.21 AM.png — Room 0 (Joe center, left_switch, vertical_field, red arrow)
- Screenshot...11.45.01 AM.png — Room 1 (fan_3, red arrow, pipes)
- Screenshot...11.45.19 AM.png — Room 2 (fan_1, down arrow, yellow mesh, checkerboard)
- Screenshot...11.45.47 AM.png — Room 3 shot 1 (fan_4, vertical pipe, Joe on platform)
- Screenshot...11.46.14 AM.png — Room 3 shot 2 (Joe in pipe top-right)
- Screenshot...11.47.58 AM.png — Room 4 shot 1 (cage with captive, nuclear symbol, fans, Joe entering)
- Screenshot...11.48.14 AM.png — Room 4 shot 2 (Joe in fan)
- Screenshot...11.48.33 AM.png — Room 4 shot 3 (Joe standing, toggle switch visible - DOWN position, dark bolt)
- Screenshot...11.48.55 AM.png — Room 4 shot 4 (toggle switch now UP position, white bolt)

## CURRENT STATE OF jet_pack_joe.py

### Working:
- Tile rendering with correct 16×12 pixel tiles, 20×16 grid, 192px game area ✓
- All 3 levels load and render correctly ✓
- Sprite decoding from SP00.DAT (all 102 sprites) ✓
- Joe rendered with real sprites (8 animation frames, left/right facing) ✓
- Projectile sprites (real sprite graphics) ✓
- Basic player movement (left/right, jetpack thrust, gravity) ✓
- **Collision bitmap** using 160×96 half-res bitmap from CB00.DAT collision shapes ✓
- **Joe collision shape** from SH00.DAT entry 0 (14×15 half-res rounded rect, gun excluded) ✓
- Collision flags: CB00.DAT provides shaped collision per flag value (0-63) ✓
- Pipe/shaft system: shaped collision tiles + invisible floor/ceiling barriers ✓
- Foreground rendering: pipe tiles drawn over Joe, dither tile 254 transparency ✓
- Jetpack flame animation: directional flames (up/left/right), growing over time ✓
- **Room transitions** matching original GAME.EXE (0x0721) with LV11.DAT headers ✓
  - 4 directions × 2 halves = 8 exits per room
  - Position wrapping and half-screen remapping
  - Debug [ ] keys still work for manual room browsing
- Level switching with 1/2/3 keys ✓
- Status bar (TIME, JET PACK JOE, ROOM number) ✓
- Timer countdown ✓
- Lives system ✓
- Window scale 3× (960×624) ✓
- Nudge system for sliding into tight passages (±2,±4,±6 pixels) ✓
- **Switch detection** using SH00.DAT collision shape overlap (entry 4) ✓
- **Object positions** using tile top-left matching BLOCK_TO_XY ✓
- **Fan animations (types 1-4)** — 3×3 tile replacement, 3 frames ✓
  - fan_3/fan_4 (brown): bg layer fans, drawn before Joe (opaque)
  - fan_1/fan_2 (pink/grey): fg layer fans, drawn after Joe (colorkey)
- **Door (type 5)** — sliding vertical barrier, 15-state tile animation ✓
  - Controlled by switch_state[switch_id], position in switch_state[var_id]
  - Dynamic collision wall moves with door (SH00.DAT shape 3) ✓
  - Collision uses backup bitmap erase/write (matching original DRAW_VISUAL/DRAW_COLLISION)
- **Switch state initialization** from level data trailer ✓
  - All states start 0xFF, then specific IDs set to 0 from switch-off list
  - Level 1: switches 17,18,20,21,22,23,25,26 start OFF

### NOT YET IMPLEMENTED:
0. **Collision sprites (SH00.DAT)** — Joe's collision shape DONE ✓, enemy shapes still needed
   - SH00.DAT fully decoded: 258-entry offset table, scan pattern format documented above
   - Joe uses entry 0 (14×15 half-res rounded rectangle, gun barrel excluded)
   - Switch uses entry 4 (4×2 half-res at offset +2,+2)
   - Enemy collision shapes need to be decoded per-entity (trace each handler's AX value)
1. **Object/entity system** — IN PROGRESS
   - LV11.DAT parsing done, objects loaded per room, switch_state[256] array added
   - **Switch system (types 6/7) — WORKING ✓:**
     - Detection uses CHECK_COLLISION with SH00.DAT shape 4 (matching original 0x043C)
     - Toggle: Joe's collision shape overlaps switch shape → flips switch_state[switch_id]
     - Visual: overrides foreground tile (base from original fg data, +0=ON, +1=OFF)
     - Tiles: 230/231 (left), 250/251 (right) — base determined from fg map data
   - **Vertical field (type 8) — WORKING ✓:**
     - Checks switch_state[switch_id] — draws only when ON (non-zero)
     - 4-frame tile animation: tiles 80-83, 100-103, 120-123, 140-143, 160-163, 180-183
     - Drawn with colorkey at field's column between solid walls
   - **Fan system (types 1-4) — WORKING ✓:**
     - 3×3 tile replacement animation via MODIFY_FOREGROUND_MAP (0x04B4)
     - fan_1/fan_2: tiles 200-248 (pink/grey), foreground layer, colorkey over Joe
     - fan_3/fan_4: tiles 440-488 (brown), background layer, opaque before Joe
     - fan_1/fan_3: forward rotation (frames 0→1→2)
     - fan_2/fan_4: reverse rotation (frames 0→2→1)
     - Animation tables decoded from DS:0x3257/0x325D/0x3263/0x3269
   - **Cage (type 10) — FULLY WORKING ✓:**
     - Captive sprite with +23,+10 offset (from 0x13ED)
     - Force field tile animation: tiles 232,233,252,253 cycling 4 frames (DS:0x3AF5)
     - Collision walls from SH00.DAT shape 13: two 2px-wide walls, 18 rows tall
     - Joe touches cage → disappear animation starts (17 frames from DS:0x3389)
     - Disappear uses tiles 213-219, 234-239 (shrink, flash, dissolve)
     - Frame 12: captive sprite removed; Frame 16: all tiles cleared
   - **Other objects**: sentry (14), glow_ball (13) — basic sprite rendering only
   - **Projectile system — WORKING ✓ (session 4):**
     - Moving projectile (Shot class): sprite 23/24, moves ±2px/frame
     - Wall-hit explosion (Explosion class): sprites 33→38, FRAME_HOLD=4
     - No pause on wall hit — projectile dies, explosion spawns at hit position
     - Explosions drawn after foreground layer (visible on top of walls)
     - Shared explosions list uses slice assignment to preserve Shot references
     - Fire cooldown: 8 frames between shots
     - Gun offset: ±12 X, +2 Y from player position
   - **Teleporter (type 19) — WORKING ✓ (session 4):**
     - Distance-based trigger detection, armed flag prevents re-trigger
     - Beam-out animation (forward 0→16) then beam-in (reverse 15→0)
     - Player frozen and hidden during beam animations
     - Cross-room and same-room teleport with bounce-back prevention
   - **Toggle switch (type 17) — WORKING ✓ (session 4):**
     - Bitwise NOT toggle, two switch IDs, edge-triggered
     - Background tiles 556-559 (4 visual states)
   - **Not yet implemented**: generators (11/12/20),
     sensor_switch (18), plates (15/16)
   - **Not yet implemented gameplay**: field killing Joe, enemy AI,
     muzzle flash animation (cosmetic, low priority)

## SESSION 3 FIXES (2026-04-19)

### Fix 1: Sprite sheet colors
- `make_sprite_sheet.py` was saving with alpha channel (pygame-ce SRCALPHA quirk)
- Fix: use `depth=24` for the sheet surface to force RGB-only PNG output

### Fix 2: Tile sheet created
- `make_tile_sheet.py` generates all 682 tiles at 2× scale with index labels
- Uses `depth=24` to avoid same alpha issue

### Fix 3: Foreground rendering bug (Joe hidden in room 8)
- `render_foreground` had a "pipe interior" heuristic that drew background tiles
  opaquely over Joe for any tile between pipe-flagged rows in the same column
- In room 8, columns 10-11 had pipe flags at rows 0-1 and 14-15, causing 24
  solid tiles to be drawn over Joe across almost the entire room height
- Fix: removed the entire pipe interior detection block. Only actual foreground
  layer bytes (the 320-byte section) should be drawn over Joe.

### Fix 4: Switch detection (rooms 8 & 9 unreachable)
- Old code used `abs(px - x - 8) < 12` pixel radius check
- Original game uses CHECK_COLLISION (0x043C) with SH00.DAT shape entry 4
  (4×2 half-res hitbox at offset +2,+2 from switch position)
- Fix: replaced radius check with collision shape overlap between Joe's shape
  (entry 0, 14×15) and the switch shape (entry 4, 4×2)
- This is more generous and matches the original game's detection range

### Fix 5: Object positions (switches still unreachable after fix 4)
- Object pixel positions were calculated as tile CENTER: `(col*16+8, row*12+6)`
- Original game's BLOCK_TO_XY returns tile TOP-LEFT: `(col*16, row*12)`
- The 8px/6px offset shifted every object's hitbox, making switches unreachable
- Fix: changed to `(col*16, row*12)` matching the original

### Fix 6: Fan animations (types 1-4)
- Decoded fan handlers from GAME.EXE: all call shared handler at 0x1D40
- Update (AX=2) increments frame counter, calls MODIFY_FOREGROUND_MAP (0x04B4)
- Animation tables at DS:0x3257/0x325D/0x3263/0x3269, 3 frames each
- Each frame replaces a 3×3 tile grid in the foreground map
- Key discovery from JAM driver renderer (0x4828 second pass):
  - Foreground tiles REPLACE background tiles (not overlay)
  - fg == 0 or 0xFF → draw bg tile only
  - fg == 0xFE (254) → dither blend
  - Any other fg → draw fg tile INSTEAD of bg
- Two fan rendering modes based on map data:
  - fan_3/fan_4: fan tiles in BACKGROUND map (fg bytes = 0) → draw opaquely
    before Joe in draw_objects, mark positions to skip in render_foreground
  - fan_1/fan_2: fan tiles in FOREGROUND map (bg = tile 341) → store animated
    tiles as fg_overrides, render_foreground draws them after Joe with colorkey
    so fan housing covers Joe but dark interior shows Joe through

### Fix 7: Cage captive sprite positioning
- Captive characters in cages were drawn at tile top-left (0,5) instead of centered
- Traced cage handler init at 0x13E4 in GAME.EXE: `ADD CX, 23; ADD DX, 10`
- The cage handler adds +23px X and +10px Y offset to center the sprite in the cage area
- Fix: apply the same offset when drawing cage sprites
- Room 4 cage: sprite now at (23,15) instead of (0,5) — matches dosbox screenshot

### Fix 8: Cage force field animation
**Discovery process:**

The dosbox screenshot showed a colorful sparkle/dot pattern surrounding the captive character
in the cage. Initial attempts to find this data included:

1. **Searching DS00.DAT** (38928 bytes, "display set") — Found only palette fade tables,
   not sprite data. The first 6 words are section offsets to fade/palette effect data.

2. **Tracing the JAM driver INT 62h handler** — The cage init calls `INT 62h` with
   `AX=0x7D, DX=0x0B` to allocate a display object. The handler is in the JAM driver
   code segment (around 0x4574+). The driver manages Mode X rendering, double-buffering,
   and a display list of sprites/objects.

3. **Analyzing the display object lifecycle:**
   - Init allocates display object: `INT 62h DX=0x0B, AX=0x7D`
   - Result + `[DS:0x3065]` (display set base) stored at `[DI+4]`
   - `ALLOC_SPRITE` (0x0378) places captive sprite at slot 7 with +23,+10 offset
   - Init calls `0x02DC` which triggers `INT 62h DX=4` (render/update display list)
   - Update cycles `[DI+4]` by adding 0x0302 (770 bytes) per frame
   - Frame counter at `[DI+0x1C]` cycles 0-3 via `INC; AND 3`

4. **Red herring: display object frame cycling** — The `ADD [DI+4], 0x0302` appeared to
   cycle through pre-rendered frames in the JAM driver's display buffer. This led to
   searching for 770-byte sprite frames in DS00.DAT and the EXE, which found nothing.

5. **Breakthrough: reading the FULL update handler** — After the frame cycling code at
   0x146F-0x147E, the update continues at 0x147F with:
   ```asm
   MOV CX, [DI+0x0A]    ; tile position (from level data)
   MOV BX, 0x3AF5        ; animation table address in DS!
   CALL 0x04B4           ; MODIFY_FOREGROUND_MAP
   ```
   This is the SAME tile replacement mechanism used by fans and vertical fields!

**Force field animation table (DS:0x3AF5):**
```
Frame offsets: [0x3AFD, 0x3B23, 0x3B49, 0x3B6F]

Frame 0: 9 tiles, all set to tile 232
Frame 1: 9 tiles, all set to tile 233
Frame 2: 9 tiles, all set to tile 252
Frame 3: 9 tiles, all set to tile 253

Tile positions (3×3 grid): 0,1,2 / 20,21,22 / 40,41,42
(same layout as fans — offsets 0-2 = row 0, +20 = row 1, +40 = row 2)
```

Each frame fills the entire 3×3 grid with a SINGLE tile index. The tiles themselves
(232, 233, 252, 253 in BK00.DAT) contain the sparkle dot patterns in different
positions, creating the animation effect when cycled.

**Tiles used:**
- Tile 232: Sparkle pattern variant A (colored dots on black)
- Tile 233: Sparkle pattern variant B
- Tile 252: Sparkle pattern variant C
- Tile 253: Sparkle pattern variant D

These tiles are drawn with colorkey (black = transparent) over the captive sprite,
so the sparkle dots appear on top of the character while the character shows through
the black areas.

**Key lesson:** The force field is NOT a special JAM driver effect or procedurally
generated pattern. It's a standard tile replacement animation using MODIFY_FOREGROUND_MAP,
identical in mechanism to fans and vertical fields. The `ADD [DI+4], 0x0302` and
`INT 62h DX=4` calls are for the JAM driver's display list management (the captive
sprite rendering), while the visual force field effect is entirely tile-based.

### Fix 9: Cage collision walls and disappear animation

**Collision system (from GAME.EXE cage update at 0x142F):**

The cage creates invisible walls using the collision bitmap system:
1. `DRAW_COLLISION` (0x045A) with AX=0x0D (shape 13), BL=1 — writes cage walls to bitmap
2. `CHECK_COLLISION` (0x043C) with AX=0x0E (shape 14), BL=0 — checks if Joe overlaps edges

**SH00.DAT shape 13 (cage walls — written to collision bitmap):**
```
Two 2-pixel-wide vertical walls, 18 rows tall (half-res):
Left wall at cols 1-2, Right wall at cols 21-22
##..................##
##..................##
(repeated 18 rows)
```

**SH00.DAT shape 14 (cage edge detection — checked against Joe):**
```
Two 1-pixel-wide edge columns, 18 rows tall (half-res):
#......................#
#......................#
(repeated 18 rows)
```

Shape 13 blocks Joe from entering the cage. Shape 14 detects when Joe touches the
cage edge, triggering the disappear sequence.

**Disappear sequence (from cage update at 0x1452):**

When CHECK_COLLISION detects Joe touching the cage edge:
1. `switch_state[switch_id] = 0` — turns off the cage's switch
2. Spawns a new disappear animation object via handler at 0x1F18
3. The cage object deactivates next frame (switch is OFF → `MOV [DI], 0`)

**Disappear animation handler (0x1F18):**

A separate object that runs the 17-frame dissolve animation:
- Init (AX=0 at 0x1F35): allocates object slot, inherits sprite handle and tile
  position from the cage, sets update handler to self (0x1F18), frame counter = 0
- Update (AX=2 at 0x1F87): advances frame counter each tick

**Disappear animation frames (DS:0x3389, 17 frames via MODIFY_FOREGROUND_MAP):**
```
Frame  0: center column = tile 213, sides = 0 (empty)
Frame  1: center column = tile 214, sides = 0
Frame  2: center column = tile 215, sides = 0
Frame  3: center = 214, sides = 234/235 (flash expands outward)
Frame  4: all = 215/216 (alternating flash)
Frame  5: all = 214/215
Frame  6: all = 215/216 (flash cycle continues)
Frame  7: all = 214/215
Frame  8: all = 215/216
Frame  9: all = 214/215
Frame 10: all = tile 217 (solid fade)
Frame 11: all = tile 218 (darker fade)
Frame 12: top = 236, mid = 218, bot = 237 (dissolve pattern)
          ← FREE_SPRITE (0x03B1) removes captive character sprite
Frame 13: top = 238, mid = 218, bot = 239 (dissolve continues)
Frame 14: mid = 218, top/bot = 0 (clearing)
Frame 15: mid = 219, top/bot = 0 (final fade)
Frame 16: all = 0 (cage completely gone)
```

At frame 17: object deactivates, decrements captive count at DS:0x305F.
If captive count reaches 0, sets level complete flag at DS:0x23BA.

**JAM Driver Architecture (partial, discovered during investigation):**

The JAM driver is a custom Mode X VGA rendering engine embedded in GAME.EXE:

- **Entry point:** INT 62h handler, dispatches on DX register
- **Functions identified:**
  - DX=0x03: VSync wait / timing
  - DX=0x04: Render/update display list
  - DX=0x0B: Allocate display object (AX = size/type parameter)
- **Display list:** Array of sprite entries in driver memory, each with position,
  sprite index, and visibility flag
- **Double buffering:** Two video pages toggled via `XOR SI, 1` at 0x47A8
- **Tile renderer (0x4798):** Two-pass system:
  - Pass 1: Draw background tiles from screen_map, mark changed positions
  - Pass 2: For each position, check foreground_map:
    - fg == 0 or 0xFF → draw background tile
    - fg == 0xFE (254) → draw dither blend (special handling)
    - Any other fg → draw foreground tile REPLACING background
- **Screen map:** DS:0x0357 (320 words, background tile indices)
- **Foreground map:** DS:0x05D7 (320 words, overlay tile indices)
  - Contiguous with screen map: 0x0357 + 0x280 = 0x05D7
- **Display set (DS00.DAT):** Loaded into driver memory, contains palette fade
  tables and effect data. Base address stored at DS:0x3065.
- **Sprite rendering:** Sprites from SP00.DAT are placed in the display list
  via ALLOC_SPRITE (0x0378), which converts centered coords to screen coords
  (`ADD CX, 160; ADD DX, 96`) then calls the driver at 0x4625.

### Fix 10: Door implementation (type 5)

**Door mechanism (from GAME.EXE update at 0x1CCF):**

Doors are vertical sliding barriers controlled by switches. Each door has 3 params:
- param[0]: tile location
- param[1]: switch_id (which switch controls this door)
- param[2]: variable_id (switch_state index holding door position 0-14)

**Init (0x1C73):**
- Position: BLOCK_TO_XY(location) + (2, 4) pixel offset
- Reads switch_id → [DI+0x1E], variable_id → [DI+0x1F]
- Calls update immediately to set initial visual state

**Update (0x1CCF):**
1. Read switch_state[variable_id], clamp to 0-14
2. DRAW_VISUAL (0x0473) with shape 3 at Y - 3*state (old position)
3. Check switch_state[switch_id]:
   - ON (≠0): increment variable toward 14 (door opens, slides UP)
   - OFF (=0): decrement variable toward 0 (door closes, slides DOWN)
4. DRAW_COLLISION (0x045A) with shape 3, BL=1 at Y - 3*new_state (collision wall)
5. MODIFY_FOREGROUND_MAP (0x04B4) with animation table DS:0x3599

**SH00.DAT shape 3 (door collision):**
```
6 wide × 21 tall half-res, alternating filled/empty rows:
######
......
######
(repeated 11 filled rows with gaps)
```

**Door animation table (DS:0x3599, 15 states):**
- State 0 (closed): tiles 144, 164, 184 (full door column)
- States 1-3: door sliding up (tiles 145-147, 165-167, 185-187)
- States 4-6: top section clearing (tiles 149, 169, 189 = partial)
- States 7-10: middle section clearing
- States 11-14: door almost/fully open (tile 187/188 base remains)
- Each state replaces a 1×4 tile column (offsets 0, 20, 40, 60)

**Room 4 door:** location=26 (tile 6,1), switch_id=17, variable_id=18

### Fix 11: Switch state initialization from level data

**Discovery:** Room 4's door started open instead of closed because all switch states
were initialized to 0xFF. The original game has a switch-off list in the level data.

**GAME.EXE initialization sequence (0x0622-0x0665):**
1. Fill switch_state[0-255] with 0xFF (REP STOSW at 0x062C)
2. Set read pointer to room 68's data (MOV AX, 0x44; CALL 0x04F8)
3. Read 4 header words from the trailer:
   - Word 0: captive count (4 for Level 1) → [DS:0x305F]
   - Word 1: timer value (150) → [DS:0x23DA]
   - Word 2: start room (0) → [DS:0x23DC] and [DS:0x23BB]
   - Word 3: value (128) → [DS:0x23BF]
4. Loop: READ_WORD; if 0xFFFF → done; else set switch_state[word] = 0

**Level data trailer location:**
- The offset table has 70 entries (rooms 0-67 + 2 extra)
- Entry 68 (index 68) points to the trailer data area
- Trailer starts at offsets[68] + 8 (skip 8-byte room header)
- For LV11.DAT: offsets[68] = 480, trailer at 488

**Level 1 switch-off list:** [17, 18, 20, 21, 22, 23, 25, 26]
- switch_state[17] = 0: Room 4 door switch OFF (door closed) ✓
- switch_state[18] = 0: Room 4 door position = 0 (fully closed) ✓
- switch_state[20-26] = 0: Other door/switch states for rooms 8, 9, etc.
- switch_state[16] stays 0xFF: Room 0 vertical field ON ✓
- switch_state[19] stays 0xFF: Room 4 cage active ✓

### Fix 12: Cage collision wall removal after disappear animation

When the cage disappear animation completes (frame 17), the collision walls
(SH00.DAT shape 13) were not being cleared from the collision bitmap, preventing
Joe from entering the cage area after the force field was deactivated.

Fix: at frame 17, clear the collision bitmap at the cage wall positions
(cols 1-2 and 21-22, 18 rows tall, relative to cage half-res position).

### Key addresses discovered this session:
- MODIFY_FOREGROUND_MAP: 0x04B4 — writes tile values to foreground map at DS:0x05D7
- MODIFY_SCREEN_MAP: 0x04D2 — writes to screen map at DS:0x0357 (skips if fg exists)
- Shared fan handler: 0x1D40 — dispatches init/update for all fan types
- Fan animation tables: DS:0x3257 (fan_1), 0x325D (fan_2), 0x3263 (fan_3), 0x3269 (fan_4)
- JAM driver tile renderer: 0x4798 (second pass at 0x4828 handles fg tile selection)
- Switch CHECK_COLLISION call: 0x1BF9 with AX=4 (shape), BX=1 (filter), CX/DX=position
- Cage handler: 0x1364 (init at 0x1393, update at 0x140F)
- Cage sprite offset: 0x13ED (ADD CX, 23; ADD DX, 10)
- Cage force field animation table: DS:0x3AF5 (4 frames: tiles 232, 233, 252, 253)
- Cage force field MODIFY_FOREGROUND_MAP call: 0x1485
- ALLOC_SPRITE: 0x0378 (converts centered→screen coords, calls JAM driver at 0x4625)
- PLAY_SOUND: 0x02DC (AX = sound id 0-4, looks up DS00.DAT table, calls INT 62h DX=4)
- JAM driver INT 62h entry: ~0x4599 (saves registers, dispatches on DX)
- JAM driver double-buffer toggle: 0x47A8 (XOR SI, 1)
- Cage collision walls: SH00.DAT shape 13 (two 2px walls, 18 rows) written to collision bitmap
- Cage disappear animation table: DS:0x3389 (17 frames, tiles 213-219, 234-239)
- Cage disappear handler: 0x1F18 (spawned as new object when Joe touches cage)
- FREE_SPRITE: 0x03B1 (called at disappear frame 12 to remove captive sprite)
- Captive count: DS:0x305F (decremented on cage clear), level complete flag: DS:0x23BA
- Display set base: DS:0x3065 (set at runtime when DS00.DAT is loaded)
- Door handler: 0x1C51 (init at 0x1C73, update at 0x1CCF)
- Door position offset: 0x1CA1 (ADD CX, 2; ADD DX, 4)
- Door animation table: DS:0x3599 (15 states, 1×4 tile column)
- Door collision: SH00.DAT shape 3 (6w×21h alternating rows)
- Switch state fill: 0x0622 (REP STOSW fills 256 bytes with 0xFF)
- Switch-off list reader: 0x0654 (loop reads IDs from level trailer, sets to 0)
- Level trailer: room 68 data (offsets[68] + 8 + 4 header words)
- Room read pointer setup: 0x04F8 (sets DS:0x3061/0x3063 for READ_WORD)

### Fix 13: Projectile and wall-hit explosion (CORRECTED — session 4, 2026-04-20)

**Previous implementation was WRONG.** The old code combined the muzzle flash animation
and the moving projectile into a single Shot class, used the wrong sprites for wall hits
(42-45 zap instead of 33-38 glow), and paused on wall collision. All of this was incorrect.

**Fully reverse-engineered from GAME.EXE — three independent systems:**

#### System 1: Moving Projectile (handler 0xFE3)

Created when fire button is pressed. This is the arrow that flies across the screen.

**Creation (at 0x0EAA-0x0EF5):**
- Fire button check: `TEST [BP-2], 0x10`
- Cooldown: `[0x3065] - [0x23CF] >= 0xC8` (200 counter ticks between shots)
- Direction: `BL = [0x23CD]` (0=left, 1=right)
- Gun position: `CX = [0x23C1] - 12 + direction*24`, `DX = [0x23C3] + 2`
  - Left (dir=0): gun_x - 12
  - Right (dir=1): gun_x + 12
  - Y offset: +2
- `BX = direction` (0 or 1 after SHR BX,4)
- `CALL 0xFE3` with AX=0 (init)

**Init (AX=0 at 0x1005):**
```
[DI+0x0A] = CX (start X position)
[DI+0x0C] = DX (start Y position)
[DI+0x1C] = BL + 0x17 (sprite index: 23=left arrow, 24=right arrow)
[DI+0x10] = BL*4 - 2 (movement delta: -2=left, +2=right)
[DI+0x00] = 3 (active state)
[DI+0x04] = [0x3065] (display set base — used for timing)
[DI+0x08] = 0x0F (15 — tick interval for object update scheduling)
[DI+0x06] = 0x0FE3 (self handler address)
```

**Update (AX=2 at 0x1084):**
```
CX = [DI+0x0A] + [DI+0x10]    ; X += movement (±2 per update)
[DI+0x0A] = CX                 ; store new X
DX = [DI+0x0C]                 ; Y (unchanged)
CALL 0x521 (ROOM_TRANSITION)   ; check if left the room
  If room changed → deactivate (projectile disappears)
CALL 0x43C (CHECK_COLLISION)   ; AX=1 (shape 1), BL=0 (any type)
  If NO collision → SET_SPRITE_POSITION, continue
  If collision:
    If [0x3175]==0 (solid wall):
      CALL 0x1103 with AX=0    ; spawn explosion at (CX, DX)
      FREE_SPRITE, deactivate  ; projectile dies IMMEDIATELY
    Else: FREE_SPRITE, deactivate
```

**Key behavior:**
- Moves ±2 pixels per object update (NOT per render frame — see timing below)
- `[DI+8] = 0x0F (15)` → updates every 15 counter ticks
- At ~1165 Hz counter rate, 15 ticks ≈ every render frame (20 ticks/frame)
- So effectively moves ~2px per render frame
- On wall hit: spawns ONE explosion, dies immediately — **NO PAUSE**
- On room exit: just dies, no explosion
- Collision shape: SH00.DAT entry 1 (4×2 half-res = 8×4 full-res rectangle)

#### System 2: Wall-Hit Explosion (handler 0x1103)

Spawned at the projectile's position when it hits a wall. Static expanding glow effect.

**Init (AX=0 at 0x1120):**
```
[DI+0x0A] = CX (X position — from projectile hit point)
[DI+0x0C] = DX (Y position)
[DI+0x1C] = 0x21 (33 — starting sprite index)
[DI+0x04] = [0x3065] + BX (display set base + offset)
[DI+0x08] = 0x47 (71 — tick interval ← THIS IS THE KEY TIMING VALUE)
[DI+0x06] = 0x1103 (self handler)
```

**Update (AX=2 at 0x1192):**
```
AL = [DI+0x1C]                 ; current sprite index
CMP AL, 0x27 (39)              ; past last sprite?
  If yes → FREE_SPRITE, deactivate
  Else → SET_SPRITE_POSITION(handle, X, Y, sprite=AL)
         INC [DI+0x1C]         ; advance to next sprite
```

**Sprite sequence:** 33 → 34 → 35 → 36 → 37 → 38 → (39 = die)
- 33: Small white circle outline (9×7)
- 34: Blue orb with white ring (13×11)
- 35: Blue glow ball, medium (15×13)
- 36: Blue glow ball, large (19×17)
- 37: White cluster — 4 small circles (19×18)
- 38: Bubble cluster — scattered circles (20×21)

**Timing:** `[DI+8] = 0x47 (71)` tick interval. Each sprite shows for 71 counter
ticks. At ~1165 Hz counter rate with ~20 ticks per render frame, each sprite
shows for 71/20 ≈ 3.5 render frames. Total: 6 sprites × 3.5 = ~21 render frames
= **~0.36 seconds** at 58fps.

**Python implementation:** `FRAME_HOLD = 4` at 60fps → 6 × 4 / 60 = 0.4 seconds.

#### System 3: Muzzle Flash / Fire Animation (0x0F05-0x0FE0)

Runs independently at the gun position. NOT related to wall hits.
This creates the sparkle/zap effect around Joe's gun barrel while firing.

**Tick counter:** `[0x23C7]` counts down from 7 (reset to 7 each step)
**Frame counter:** `[0x23D4]` (JET_FIRE_FRAME) increments each step

**Frame behavior:**
- Frames 1-16: SET_SPRITE_POSITION for gun sprite at gun position
  - Spawn 0x1103 trail object at gun_pos + random scatter
  - Small scatter: Y = random(23)-11, X = random(29)-13
- Frames 17-24: Gun sprite changes to zap sprites 42-45
  - Sprite = (frame-8)/2 + 42 → cycles through 42,42,43,43,44,44,45,45
  - Spawn 0x1103 trail at gun_pos + larger scatter
  - Large scatter: Y = random(45)-22, X = random(37)-18
- Frame 25: FREE gun sprite (firing animation ends)
- Frame 58: Set completion flag [0x305E] = 1

**Random numbers:** `INT 62h DX=0x0B` with AX=N returns random value in [0, N).
Handler at 0x3AB8 — linear congruential generator.

**NOT YET IMPLEMENTED in Python.** The muzzle flash is cosmetic and lower priority.

#### Our Python Implementation (session 4):

```python
class Explosion:
    # Static position, cycles sprites 33→38, FRAME_HOLD=4
    # Spawned by Shot on wall collision

class Shot:
    # Moves ±2px per frame, sprite 23 (right) or 24 (left)
    # On wall hit: append Explosion to shared list, die immediately
    # On screen exit: die
    # Shares explosions list with Player via reference

class Player:
    # self.explosions = [] — shared with Shot objects
    # self.shots filtered with list replacement
    # self.explosions filtered with slice assignment (explosions[:] = ...)
    #   ← CRITICAL: must use slice assignment, not replacement,
    #      because Shot objects hold a reference to this list
```

**Bug found and fixed:** List comprehension `self.explosions = [...]` creates a NEW
list object, breaking the reference held by Shot objects. Explosions appended by shots
went into the orphaned old list. Fix: use `self.explosions[:] = [...]` (slice assignment)
to modify the list in-place.

## SESSION 4: GAME TIMING SYSTEM (2026-04-20)

### Global Counter System

The game has TWO counters, both incremented by the timer interrupt handler at 0x441E:

| Counter | Address | INT 62h | Incremented by | Purpose |
|---------|---------|---------|----------------|---------|
| Frame counter | CS:0x3AFE | DX=3 | +1 per 0x441E call | Render frame timing |
| Object counter | CS:0x3AFC | DX=0 | +[CS:0x3B00] per call | Object update scheduling |

`[CS:0x3B00]` is set to 1 by `INT 62h DX=8` (enable) or 0 by `DX=7` (disable).
When enabled, both counters increment at the same rate.

### Timer Interrupt Rate

The PIT (Programmable Interval Timer) rate depends on the sound driver:

| Driver | PIT Divisor | PIT Rate | Handler | Divider | Counter Rate |
|--------|-------------|----------|---------|---------|-------------|
| 0: None | 65536 (default) | 18.2 Hz | 0x4450 | ×64 loop | 1165.2 Hz |
| 1: Speaker | 1024 | 1165.2 Hz | 0x4462 | ×1 | 1165.2 Hz |
| 2: Covox | 64 | 18643.5 Hz | 0x44BF | ÷16 | 1165.2 Hz |
| 3: Sound Master | 128 | 9321.7 Hz | 0x44EC | ÷8 | 1165.2 Hz |

**All drivers produce the same counter rate: ~1165 Hz** (1193182 / 1024).

The no-sound handler (0x4450) compensates by calling 0x441E in a loop 64 times
per PIT interrupt: `MOV CX, 0x40; CALL 0x441E; LOOP`.

### Render Frame Timing (0x03BA)

```asm
0x03C9: MOV DX, 3; INT 62h        ; AX = frame counter [CS:0x3AFE]
0x03CE: SUB AX, [0x235F]          ; delta = current - last_frame_time
0x03D2: CMP AX, 0x14 (20)         ; wait for 20 counter ticks
0x03D5: JC 0x03C9                 ; loop if < 20
0x03D7: CALL 0x4798               ; render tiles
0x03DA: MOV DX, 3; INT 62h        ; get counter again
0x03DF: MOV [0x235F], AX          ; save as last_frame_time
0x03E2: INC [0x2361]              ; increment render frame number
```

**Render frame rate:** 1165.2 / 20 = **58.26 fps**

### Object Update Scheduling (0x06F8-0x0749)

The main game loop iterates all 100 object slots (0x64 = 100, each 0x20 = 32 bytes):

```asm
0x06F5: [0x3065] = INT 62h DX=0   ; refresh object counter
0x06F8: SI = 100, DI = 0x23DE     ; 100 objects starting at DS:0x23DE
; For each object:
0x0700: CMP [DI], 0               ; skip if inactive
0x070B: AX = [0x3065]             ; current counter value
0x070E: SUB AX, [DI+4]           ; AX = counter - object_next_time
0x0711: CMP AX, 0                 ; is it time?
0x0714: JL skip                   ; not yet → skip this object
; ... activate if needed (AX=1) ...
0x0738: MOV AX, 2; CALL [DI+6]   ; call update handler
0x073F: AX = [DI+8]              ; get tick interval
0x0742: ADD [DI+4], AX           ; next_time += interval
```

**Object slot layout (32 bytes each):**

| Offset | Size | Name | Description |
|--------|------|------|-------------|
| 0x00 | byte | state | 0=inactive, 1=pending, 3=active |
| 0x01 | byte | visible | 0=hidden, 1=visible |
| 0x02 | byte | room | Room number this object belongs to |
| 0x03 | byte | sound_id | Sound slot (0xFF = none) |
| 0x04 | word | next_time | Counter value for next update |
| 0x06 | word | handler | Handler function address |
| 0x08 | word | interval | Counter ticks between updates |
| 0x0A | word | x | X position (centered coords) |
| 0x0C | word | y | Y position (centered coords) |
| 0x0E | word | sprite_handle | Sprite display handle |
| 0x10 | word | param1 | Handler-specific (e.g., movement delta) |
| 0x12-0x1F | varies | params | Handler-specific data |
| 0x1C | byte | sprite_idx | Current sprite index (for animation) |
| 0x1E | byte | switch_id | Switch state index |
| 0x1F | byte | var_id | Variable state index |

### Tick Interval Values (from [DI+8])

| Value | Hex | Ticks/frame | Seconds/update | Used by |
|-------|-----|-------------|----------------|---------|
| 15 | 0x0F | ~0.75 | 0.013s | Moving projectile (0xFE3) |
| 71 | 0x47 | ~3.55 | 0.061s | Explosion/trail (0x1103), display set objects |
| 129 | 0x81 | ~6.45 | 0.111s | Timer/slow objects |

**Formula:** `frames_per_update = interval / 20` (since render loop consumes ~20 ticks).
**Python FRAME_HOLD:** `round(interval / 20)` for objects that animate per-update.

### Converting Original Timing to Python (60fps)

For any object with `[DI+8] = N`:
- Original updates per second: 1165.2 / N
- Original render frames between updates: N / 20
- Python FRAME_HOLD at 60fps: `round(N / 20)`

| [DI+8] | Updates/sec | Frames between | Python FRAME_HOLD |
|--------|-------------|----------------|-------------------|
| 15 | 77.7 | 0.75 | 1 (every frame) |
| 71 | 16.4 | 3.55 | 4 |
| 129 | 9.0 | 6.45 | 6 |

### Key Timing Addresses

| Address | Type | Description |
|---------|------|-------------|
| CS:0x3AFC | word | Object counter (INT 62h DX=0 reads, DX=9 writes) |
| CS:0x3AFE | word | Frame counter (INT 62h DX=3 reads) |
| CS:0x3B00 | word | Counter increment (0 or 1, set by DX=7/DX=8) |
| CS:0x3B06 | dword | Saved INT 8 vector (original timer handler) |
| CS:0x3B16 | byte | Timer interrupt divider (counts down) |
| CS:0x3B17 | byte | Sub-divider for original INT 8 chain (counts from 2) |
| CS:0x3B18 | byte | Sub-divider for palette update (counts from 0x20=32) |
| DS:0x235F | word | Last render frame counter value |
| DS:0x2361 | word | Render frame number (incremented per render) |
| DS:0x3065 | word | Cached object counter (refreshed each game loop) |
| DS:0x23C7 | word | Fire animation tick counter (counts down from 7) |
| DS:0x23CF | word | Fire cooldown timestamp |

### INT 62h Function Table (dispatch at 0x3A76 via jump table at DS:0x4778)

| DX | Handler | Description |
|----|---------|-------------|
| 0 | 0x41BC | Read object counter [CS:0x3AFC] → AX |
| 1 | 0x3967 | Read input state |
| 2 | 0x3A51 | Unknown |
| 3 | 0x41C6 | Read frame counter [CS:0x3AFE] → AX |
| 4 | 0x42B3 | START_SOUND: ES:SI = sample, CX = 256-byte blocks → least-busy mixer channel (see Sound section) |
| 5 | 0x3A8C | NOP (RET) |
| 7 | 0x41D3 | Disable counter: [CS:0x3B00] = 0 |
| 8 | 0x41CB | Enable counter: [CS:0x3B00] = 1 |
| 9 | 0x41C1 | Write object counter: [CS:0x3AFC] = AX |
| 0xA | 0x3A8D | Seed random number generator |
| 0xB | 0x3AB8 | Random number: returns AX = random [0, AX) |

### Session 4 Key Addresses

| Address | Description |
|---------|-------------|
| 0x03BA | RENDER_FRAME — copies maps, waits 20 ticks, renders tiles |
| 0x0EAA | Fire button handler — creates moving projectile |
| 0x0EDD | Gun position offset: ADD DX,2; SUB CX,12; direction*24 |
| 0x0F05 | Fire animation handler (muzzle flash, independent of projectile) |
| 0x0FE3 | Moving projectile handler (arrow sprite, ±2px movement) |
| 0x1005 | Projectile init (sprite=BL+23, movement=BL*4-2) |
| 0x1084 | Projectile update (move, check room transition, check collision) |
| 0x1103 | Explosion/trail handler (sprites 33→38, [DI+8]=71) |
| 0x11BA | Secondary trail handler (with extra sprite handle at [DI+0x14]) |
| 0x3A76 | INT 62h handler entry (STI, dispatch via [DS:BP+0x4778]) |
| 0x3AB8 | Random number generator (linear congruential, AX=range) |
| 0x441E | Timer tick handler (increments both counters) |
| 0x4450 | No-sound timer ISR (calls 0x441E × 64 per PIT interrupt) |
| 0x4462 | Speaker timer ISR (calls 0x441E × 1) |
| 0x44BF | Covox timer ISR (divider 16, calls 0x441E) |
| 0x44EC | Sound Master timer ISR (divider 8, calls 0x441E) |

## REVERSE ENGINEERING METHODOLOGY

### Step 1: Find the Data Segment (DS)
The EXE has a 512-byte (0x200) MZ header. Code starts at file offset 0x200.
- Entry point at CS:IP = 0:0x20 (file offset 0x220)
- First instructions: `MOV AX, 0x49E; MOV DS, AX` → **DS = 0x049E**
- To convert DS:offset to file offset: `file_off = 0x200 + 0x49E * 16 + offset`
- Example: DS:0x2F1 → file offset 0x200 + 0x49E0 + 0x2F1 = **0x4ED1**

### Step 2: Read the Object Handler Function Table
- Table at DS:0x2F1 (file offset 0x4ED1), 24 entries × 2 bytes
- Index = object_type × 2
- Each entry is a CODE address (add 0x200 for file offset)
- **Confirmed table:**
  | Type | Handler | Description |
  |------|---------|-------------|
  | 0 | 0x043B | null |
  | 1 | 0x1289 | fan_1 |
  | 2 | 0x12A8 | fan_2 |
  | 3 | 0x12C7 | fan_3 |
  | 4 | 0x12E6 | fan_4 |
  | 5 | 0x1C51 | door |
  | 6 | 0x1305 | right_switch |
  | 7 | 0x1312 | left_switch |
  | 8 | 0x1336 | vertical_field |
  | 9 | 0x131F | horiz_field |
  | 10 | 0x1364 | cage |
  | 11 | 0x1488 | bird_generator |
  | 12 | 0x14F5 | ball_generator |
  | 13 | 0x134D | glow_ball |
  | 14 | 0x22EF | sentry |
  | 15 | 0x17A0 | left_plate |
  | 16 | 0x189B | right_plate |
  | 17 | 0x213C | toggle_switch |
  | 18 | 0x2061 | sensor_switch |
  | 19 | 0x2219 | teleporter |
  | 20 | 0x2526 | orb_generator |

### Step 3: Trace a Handler
1. Disassemble at `0x200 + handler_address`
2. Handlers dispatch on AX: 0=init, 1=activate, 2=update, 3=deactivate, etc.
3. Init code (AX=0) typically:
   - Calls 0x513 (READ_WORD) to read params from level data
   - Calls 0x3EA (BLOCK_TO_XY) to convert tile index to pixel coords
   - Sets [di+6] to the UPDATE handler address
   - Allocates sprite slot via 0x378 (ALLOC_SPRITE)
4. Update code (AX=2) typically:
   - Calls 0x4B4 (MODIFY_FOREGROUND_MAP) for tile-based animation
   - Calls 0x45A (DRAW_COLLISION) for collision
   - Calls 0x473 (DRAW_VISUAL) for sprite rendering

### Step 4: Read Runtime Data Tables
- Convert DS:address to file offset: `0x200 + 0x49E * 16 + address`
- Animation tables have offset pointers to frame data
- Frame data format: count(word), then count × (tile_offset(word), tile_value(word))
- tile_offset is relative to the object's position in the 20-column grid (×20 = next row)

### Step 5: Identify Tiles/Sprites
- Render candidate tiles from BK00.DAT to verify visual match
- Check palette colors to confirm (white=index 31/39, blue=240-247, red=208-215)
- Compare with dosbox screenshots at pixel level using PIL

### Key Addresses (code addresses, add 0x200 for file offset):
- 0x0020: Entry point (sets DS=0x49E)
- 0x02F1: Object handler function table (in DS)
- 0x0378: ALLOC_SPRITE
- 0x03B1: FREE_SPRITE
- 0x03EA: BLOCK_TO_XY
- 0x043C: CHECK_COLLISION
- 0x045A: DRAW_COLLISION
- 0x0473: DRAW_VISUAL
- 0x04B4: MODIFY_FOREGROUND_MAP (tile replacement animation)
- 0x04D2: MODIFY_SCREEN_MAP
- 0x0513: READ_WORD (from level data stream)
- 0x0521: ROOM_TRANSITION
- 0x059A: SET_SPRITE (assign sprite to slot)
- 0x3067: Switch state array (in DS)
- 0x3B95: Vertical field animation data (in DS)
- 0x3BA9: Horizontal field animation data (in DS)

### Vertical Field (type 8) — FULLY DECODED:
- Handler: 0x1336 → reads params, calls 0x1E3C with SI=0x3B95 (animation table)
- 0x1E3C: dispatches init/update. Init at 0x1E5E, update at 0x1EB5
- Update calls 0x4B4 to replace foreground tiles with lightning animation frames
- **4 animation frames**, each replacing 6 tile rows:
  - Frame 0: tiles 81, 101, 121, 141, 161, 181
  - Frame 1: tiles 82, 102, 122, 142, 162, 182
  - Frame 2: tiles 83, 103, 123, 143, 163, 183
  - Frame 3: tiles 80, 100, 120, 140, 160, 180
- Tiles drawn with colorkey (black=transparent) at the field's column position
- Tile 71 (0x47) written to collision/screen map for collision detection
   - **Object handler function table**: at DS:0x2F1, indexed by type*2
   - Fans, switches, doors, cages, enemies: handlers not yet analyzed
   - Objects are visual only — no interaction/gameplay logic yet
   - Object locations are decoded but not rendered or interactive
   - Fans should use sprite animation
   - Switches should toggle state (sprites 55-57)
   - Cages hold captive characters (sprites 75-81)
   - Doors block/unblock passages
2. **Enemies** — sentries (sprites 28-33), birds (sprites 39-41), balls
   - bird_generator, ball_generator, orb_generator spawn enemies
   - Sentries patrol and shoot
4. **Collision refinement** — use all 3 CB00.DAT sub-maps and tile word flags
   - Current collision is basic (block 0 only)
   - Need top/middle/bottom zone collision for slopes/partial blocks
5. **Teleporters** — object type 19, transport between rooms
6. **Energy fields** — vertical_field and horiz_field (sprites with lightning effect)
7. **Proper status bar** — match original green digital font from CHAR.ASM
8. **Sound effects** — .V8 audio samples exist in DRAW/ directory
9. **Cutscene animations** — title, death, thumbs up, credits (ANIM.ASM)
10. **Enemy collision shapes** — SH00.DAT decoded for Joe (entry 0), need to trace other entries for sentries/birds/balls
11. **Display set effects** — DS00.DAT (38928 bytes), fade tables and palette effects

## SESSION 4 CONTINUED: DOOR COLLISION SYSTEM (2026-04-20)

### Fix 14: Door blocking Joe's movement (collision wall moves with door)

**Problem:** Doors had visual tile animation but no working collision. Joe could walk
through closed doors. The old code attempted collision with a type-2 marker system
that tried to avoid clearing wall tiles, but it was fragile and incorrect.

**Solution:** Reverse-engineered the exact DRAW_COLLISION and DRAW_VISUAL functions
from GAME.EXE and implemented the backup bitmap mechanism.

### Collision Bitmap Architecture (from GAME.EXE)

The original game maintains TWO copies of the collision bitmap:

| Bitmap | Offset in ES | Size | Purpose |
|--------|-------------|------|---------|
| Active | ES:0x0000 | 192×96 = 18432 bytes | Current collision state, modified by objects |
| Backup | ES:0x4820 | 192×96 = 18432 bytes | Original tile collision, never modified |

The backup is created at room load by copying the active bitmap (0x2E80).
Objects that need to write/erase collision (doors, cages) use these two functions:

#### DRAW_COLLISION (0x045A → 0x2ED8) — Write collision to bitmap

Called by door handler to place the door's collision wall.

```
Entry: AX = SH00.DAT shape index
       BL = collision type value to write (1 for solid)
       CX = object X (centered coords, -160 to +160)
       DX = object Y (centered coords, -96 to +96)

0x045A wrapper:
  CX += 160 (0xA0)     ; convert to screen coords
  DX += 96 (0x60)
  SAR CX, 1            ; convert to half-res
  SAR DX, 1

0x2ED8 core:
  SI = SH00.DAT offset table[AX * 2] + 0x9D40  ; shape data pointer
  CX += 32 (0x20)      ; add left padding (192-wide bitmap has 32 cols padding)
  DI = DX * 192 + CX   ; starting position in bitmap

  Loop:
    LODSW → delta       ; signed 16-bit offset
    DI += delta          ; advance position
    LODSB → count        ; number of bytes to write
    if count == 0: break ; end of shape
    if DI > 0x47FF: DI += count; continue  ; bounds check
    REP STOSB (AL=BL)   ; fill count bytes with collision type
```

#### DRAW_VISUAL (0x0473 → 0x2F8A) — Erase collision from bitmap

Called by door handler to remove the old collision wall before writing the new one.
**Restores from the backup bitmap** — this is the key insight.

```
Entry: Same as DRAW_COLLISION (AX=shape, CX=X, DX=Y)

0x2F8A core:
  Same coordinate setup as DRAW_COLLISION.

  Loop:
    LODSW → delta
    DI += delta
    LODSB → count
    if count == 0: break
    if DI > 0x47FF: DI += count; continue
    Copy count bytes from [DI + 0x4820] to [DI]  ; restore from backup!
```

This is why the erase never damages wall tiles — it restores whatever was originally
there (walls stay as walls, empty stays as empty).

#### Our Python Implementation

```python
# In get_collision_bitmap(): after building cbm, save backup
self.cbm_backup[room_idx] = bytearray(cbm)

# In door update (draw_objects):
# Step 1: DRAW_VISUAL — erase old collision (restore from backup)
for r in range(0, 21, 2):  # shape 3: alternating rows
    by = (y + 4) // 2 - old_shift + r
    for c in range(6):
        bx = hx + c
        cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]  # restore

# Step 2: Update state (increment/decrement based on switch)

# Step 3: DRAW_COLLISION — write new collision (type 1)
for r in range(0, 21, 2):
    by = (y + 4) // 2 - new_shift + r
    for c in range(6):
        bx = hx + c
        cbm[by * HALF_W + bx] = 1  # solid
```

**Critical difference from old code:** The old code used collision type 2 as a marker
and tried to skip type 1 (walls) during clearing. This was fragile — if a door
collision overlapped a wall tile, the wall would be permanently damaged. The backup
approach is robust: it always restores the correct original value.

### Door Handler (0x1C51) — Complete Disassembly

**Init (AX=0 at 0x1C73):**
```
[DI+0x08] = 0x59 (89) — tick interval (89/20 ≈ 4.5 frames between updates)
[DI+0x04] = random(INT 62h DX=0xB) + [0x3065] — next update time
[DI+0x06] = 0x1C51 — self handler
[DI+0x0A] = READ_WORD — tile location (for MODIFY_FOREGROUND_MAP)
BLOCK_TO_XY(location) → CX, DX
CX += 2, DX += 4 — door position offset
[DI+0x10] = CX — door X (centered coords)
[DI+0x12] = DX — door Y (centered coords)
[DI+0x1E] = READ_WORD — switch_id (which switch controls this door)
[DI+0x1F] = READ_WORD — var_id (switch_state index holding door position 0-14)
Immediately calls self with AX=2 (first update to set initial collision)
```

**Update (AX=2 at 0x1CCF):**
```
1. BL = var_id, AL = switch_state[var_id], clamp to 0-14
2. CX = door_X, DX = door_Y - old_state * 3
   CALL DRAW_VISUAL(shape=3) — erase old collision
3. Check switch_state[switch_id]:
   - If ON (≠0) and state < 14: increment state (door opens, slides UP)
   - If OFF (=0) and state > 0: decrement state (door closes, slides DOWN)
4. CX = door_X, DX = door_Y - new_state * 3
   CALL DRAW_COLLISION(shape=3, type=1) — write new collision
5. CALL MODIFY_FOREGROUND_MAP(location, table=0x3599) — update tiles
```

**Y position formula:** `door_Y - state * 3` (full-res centered coords)
- State 0 (closed): collision at door_Y (bottom position)
- State 14 (open): collision at door_Y - 42 (shifted 42px up, above the passage)
- In half-res: shift = `(state * 3) // 2` pixels

### SH00.DAT Shape 3 (Door Collision)

```
6 wide × 21 tall (half-res), alternating filled/empty rows:
Row  0: ######
Row  1: ......
Row  2: ######
Row  3: ......
Row  4: ######
...
Row 18: ######
Row 19: ......
Row 20: ######

11 filled rows at even positions (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20)
Each row is 6 bytes wide
```

The alternating pattern creates a "venetian blind" collision that still blocks
Joe's 14×15 half-res collision shape (Joe can't fit through the 1-pixel gaps).

### Door Timing

- `[DI+8] = 0x59 (89)` tick interval
- At 1165 Hz counter rate: 89/1165 = 0.076 seconds between state changes
- 15 states (0-14) × 0.076 = **1.15 seconds** to fully open/close
- Python: door updates every `draw_objects` call (once per frame at 60fps)
  - State changes once per call, so 15/60 = 0.25 seconds
  - This is faster than original but acceptable since the door is visually smooth
  - To match exactly: only change state every ~5 frames (89/20 ≈ 4.5)

### Door Instances (Level 1)

| Room | Location | Tile | switch_id | var_id | Controls |
|------|----------|------|-----------|--------|----------|
| 4 | 26 | (6,1) | 17 | 18 | Right switch in room 4 |
| 8 | 42 | (2,2) | 20 | 21 | Right switch in room 8 |
| 9 | 51 | (11,2) | 22 | 23 | Left switch in room 9 |
| 9 | 22 | (2,1) | 25 | 26 | Right switch in room 9 |

All start closed (switch_state[var_id] = 0 from level trailer switch-off list).

### Collision Bitmap Coordinate Systems

This is a common source of bugs. There are THREE coordinate systems:

| System | Range | Used by | Conversion |
|--------|-------|---------|------------|
| Centered | X: -160..+160, Y: -96..+96 | GAME.EXE internally, object positions | +160, +96 → screen |
| Screen | X: 0..319, Y: 0..191 | Python obj["x"]/obj["y"], rendering | ÷2 → half-res |
| Half-res | X: 0..159, Y: 0..95 | Collision bitmap (160×96) | Direct index |

**GAME.EXE collision functions** (0x045A, 0x0473, 0x048C) convert centered → half-res:
```
CX += 160    ; centered → screen
DX += 96
SAR CX, 1    ; screen → half-res
SAR DX, 1
; Then internally: CX += 32 (192-wide bitmap padding)
; DI = DX * 192 + CX
```

**Our Python** uses screen coords directly:
```python
hx = (screen_x + offset_x) // 2   # screen → half-res
hy = (screen_y + offset_y) // 2
idx = hy * HALF_W + hx             # HALF_W = 160 (no padding)
```

**No padding in Python:** The original uses a 192-wide bitmap with 32 columns of
left padding. Our Python uses 160-wide with no padding. This means we DON'T add
the +32 offset. The SH00.DAT scan deltas are designed for stride 192, but since
we decode them into (row, col) tuples, the stride difference doesn't matter.

### Pattern for Future Object Collision (template)

Any object that needs dynamic collision (enemies, plates, etc.) should follow this pattern:

```python
# 1. Ensure cbm_backup exists (created in get_collision_bitmap)
backup = self.cbm_backup.get(room_idx)

# 2. Decode the SH00.DAT shape once (can cache)
# Shape N scans: list of (row_offset, col_offset, width)

# 3. ERASE old collision (restore from backup)
for row_off, col_off, width in shape_scans:
    by = base_hy - old_shift + row_off
    for c in range(width):
        bx = base_hx + col_off + c
        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
            cbm[by * HALF_W + bx] = backup[by * HALF_W + bx]

# 4. WRITE new collision
for row_off, col_off, width in shape_scans:
    by = base_hy - new_shift + row_off
    for c in range(width):
        bx = base_hx + col_off + c
        if 0 <= bx < HALF_W and 0 <= by < HALF_H:
            cbm[by * HALF_W + bx] = collision_type  # usually 1
```

### Debugging Collision Issues

**Print the collision bitmap around an object:**
```python
cbm = self.get_collision_bitmap(room_idx)[0]
hx, hy = obj["x"] // 2, obj["y"] // 2
for row in range(hy - 5, hy + 25):
    line = f'Row {row:3d}: '
    for col in range(hx - 2, hx + 10):
        if 0 <= col < HALF_W and 0 <= row < HALF_H:
            v = cbm[row * HALF_W + col]
            line += str(v) if v else '.'
        else:
            line += '?'
    print(line)
```

**Verify backup exists:**
```python
backup = self.cbm_backup.get(room_idx)
assert backup is not None, f"No backup for room {room_idx}"
assert len(backup) == HALF_W * HALF_H
```

**Common bugs:**
1. **Forgetting to erase before write** → collision accumulates, passage never opens
2. **Using wrong coordinate system** → collision appears in wrong place
3. **List replacement vs slice assignment** → shared references break (see Shot/Explosion bug)
4. **Not clamping state** → array index out of bounds
5. **Modifying backup** → erase restores wrong values (backup must be immutable after creation)

## SESSION 4 CONTINUED: TELEPORTER, TOGGLE SWITCH, BEAM ANIMATIONS (2026-04-21)

### Fix 15: Teleporter (type 19) — GAME.EXE 0x2219

**Only exists in Level 3** (rooms 4, 5, 7, 8, 10, 13-18). Most teleport within the
same room (maze puzzles), some go between rooms.

**Parameters:** location, dest_room, dest_tile

**Init (0x2241):**
```
[DI+0x08] = 0x3E (62) — tick interval
[DI+0x10] = CX, [DI+0x12] = DX — position (BLOCK_TO_XY)
[DI+0x16] = dest_room
[DI+0x18] = dest_tile
[DI+0x1D] = 1 — armed flag
```

**Update (0x2290) — Two collision checks:**
1. `CHECK_COLLISION(shape=13, X=tele_x, Y=tele_y)` — outer boundary (cage walls)
2. `CHECK_COLLISION(shape=4, X=tele_x+16, Y=tele_y+12)` — inner trigger

**Decision logic** (corrected 2026-11-01 — [DI+0x1D] is a BLOCKED flag, set to 1 at init):
- Joe NOT in trigger → blocked = 1 if clear of the side columns, 0 if on them
- Joe IN trigger AND NOT on the side columns AND blocked == 0 → TELEPORT, blocked = 1
- Joe IN trigger AND on the side columns → skip
So Joe must cross a side column (shape 13 = the cage-wall columns at x+2..5 / x+42..45) and
then be within ~5 px of the centre at a 62-tick check. Materialising at the centre (beam-in)
or dropping onto it from above never fires: that is the original's bounce-back guard, no
"disarm on arrival" hack is needed. The earlier Python version had the sense inverted (it
fired only after leaving upward and coming back down), which Cam hit in L3 R13.

**Teleport action (0x22C5):**
```
[0x23BA] = 1 (room change flag)
[0x23BB] = dest_room
[0x23BF] = dest_tile
INC [0x305F]
ADD [0x23D2], 0x3E8
```

**Main loop handles room change in two phases:**
1. `[0x23BA] == 1`: Spawn beam-OUT (0x1F18) at source, increment to 2
2. `[0x23BA] == 2`: Load dest room, spawn beam-IN (0x1FBF) at destination

**Python implementation:**
- Simplified trigger: distance-based (`dx < 10, dy < 8` from teleporter center)
- Boundary check: Joe near left/right walls of teleporter area
- On teleport: start beam-out → when done, move Joe → start beam-in
- `return` from update_objects to stop processing after teleport
- Disarm ALL teleporters in destination room to prevent bounce-back
- Player frozen during beam animations

**Bounce-back bug (found and fixed):**
When teleporting within the same room, the destination teleporter would immediately
fire and send Joe back. Fix: disarm all teleporters in the destination room after
teleporting, and `return` from the object loop.

**Teleporter has no visual of its own** — the green border tiles (177-179, 197-199)
are static foreground tiles placed in the map data.

### Fix 16: Beam-Out and Beam-In Animations

Both use the **cage disappear animation table** at DS:0x3389 (17 frames, tiles 213-219, 234-239).

**Beam-out (0x1F18):** Plays frames 0→16 (forward = dissolve away)
- Frame 12: Joe's sprite is freed (Joe disappears)
- Frame 17: deactivate, DEC captive count, INC [0x23B9]
- `[DI+0x08] = 0x46 (70)` tick interval → FRAME_HOLD = 4

**Beam-in (0x1FBF):** Plays frames 15→0 (reverse = materialize)
- Frame 12: Joe appears (CALL 0x0C7E positions Joe)
- Frame 0xFF (after 0): final cleanup tile, deactivate
- `[DI+0x08] = 0x46 (70)` tick interval → FRAME_HOLD = 4

**Python implementation:**
- `self.beam_out` dict: tracks source tile, frame (0→16), timer
- `self.beam_in` dict: tracks dest tile, frame (15→0), timer
- Sequence: beam_out completes → teleport Joe → beam_in starts
- Joe hidden during beam-out frame >= 12 and beam-in frame > 12
- Player input frozen during both animations
- BEAM_FRAMES table: same 17 entries as CAGE_DISAPPEAR

### Fix 17: Toggle Switch (type 17) — GAME.EXE 0x213C

**Parameters:** location, switch_id_1, switch_id_2

**Init (0x215E):**
```
[DI+0x08] = 0x80 (128) — tick interval
[DI+0x1E] = switch_id_1
[DI+0x1F] = switch_id_2
Immediately calls update (AX=2)
```

**Update (0x21B4):**
```
1. CHECK_COLLISION(shape=4, filter=1, X, Y) — same trigger as regular switch
2. If touching AND was NOT touching last frame (edge-triggered):
     NOT switch_state[switch_id_1]    ← bitwise toggle (0↔0xFF)
     If switch_id_2 != switch_id_1:
       NOT switch_state[switch_id_2]  ← toggle second switch too
3. Save touch state for next frame
4. Visual tile = 556 + (sw2 & 1) + 2*(sw1 & 1)
   Tiles 556-559 represent 4 visual states
   Written to SCREEN MAP (background), not foreground
```

**Key differences from regular switch (types 6/7):**
- **Bitwise NOT toggle** instead of set ON/OFF
- **Two switch IDs** — can control two switches simultaneously
- **Background tile** (556-559) instead of foreground tile (230/231, 250/251)
- **Edge-triggered** — only toggles on first contact, not while standing on it

**Python implementation:**
- Same shape 4 overlap check as regular switches
- `~self.switch_state[sw1] & 0xFF` for bitwise NOT toggle
- Draws tile directly to surface (no cache invalidation needed)
- `obj["touching"]` tracks edge detection

### Level Walkthroughs

#### Level 1 — 4 captives
```
START → R0 → R1 → R2 → R3 → R4★ (door:sw17) → R5 → R6 → R7 → R8 (door:sw20)
                                                                      ↓
R15 ← R14 ← R13★★ ← R12 ← R11 ← R10 ← R9★ (doors:sw28,sw30) ← R8
```
- R4 cage: hit r_switch at R4(13,7) to open door
- R9 cage: r_switch at R10(13,6) opens left door, r_switch at R11(18,5) opens right door
- R13: 2 cages, no doors blocking

#### Level 2 — 11 captives
```
R0 → R13★ → R12★ → R11★ → R10 → R9 → R8★     (right path, 4 cages)
R0 → R14 → R15 → R16★ → R17 → R18★ → R19 → R20★ → R21★  (down path, 4 cages)
R0 → R26★ → R25 → R24★                          (left path, 2 cages)
R0 → R1 → R2 → R3 → R4 → R5★                   (up path, 1 cage)
```
Key switches:
- R13 door (sw33): l_switch at R13(1,2)
- R9 doors: sw28 at R10(13,6), sw30 at R11(18,5)
- R7 door (sw22): r_switch at R6(17,10)
- R15 door (sw37): l_switch at R14(9,8)
- R16 top door (sw38): l_switch at R14(13,13)
- R16 bottom door (sw29): l_switch at R11(11,4)
- R17 h_field (sw36): l_switch at R14(9,6)
- R21 door (sw50): l_switch at R21(6,2) or R22(7,7)
- R25 doors: sw52 at R24(4,5), sw53 at R24(4,7)

#### Level 3 — 15 captives
```
R0 → R1★ → R2★ → R3 → R4(tele) → R5(tele maze) → R6★★(toggle,fields)
                                                      ↓
R0 ← R8★ ← (tele) ← R7★★(tele) ← R13★(sensor doors) ← R12★★ ← R11 → R21★
     ↓
     R9★ → R10(toggle,door,tele) → R3
     ↓
     R14(tele) → R15★(tele maze) → R16★★ → R17(tele) ↔ R18 → R1/R2
```
Cages: R1, R2, R6×2, R7×2, R8, R9, R12×2, R13, R15, R16×2, R21

Key mechanics:
- R4, R5, R15: Teleporter mazes
- R6: 4 toggle switches (all sw6) control h_fields blocking cages
- R10: 2 toggle switches (sw15) control door; h_field at sw200 is PERMANENT (no switch)
- R13: 3 sensor switches (sw22,23,24) control 3 doors — walk past to open
- R7→R8: teleporter chain

### Fix 18: Horizontal Field (type 9) — GAME.EXE 0x131F

**Uses the same shared handler (0x1E3C) as vertical_field (type 8) and glow_ball (type 13).**

**Parameters:** location, switch_id

**Caller setup (0x131F):**
```
READ_WORD → BX = location
READ_WORD → CX = switch_id
DX = 0x0B (11) — collision shape index
SI = 0x3B9F — animation table
CALL 0x1E3C (shared field handler)
```

**Shared handler init (0x1E5E):**
```
[DI+0x08] = 0x4F (79) — tick interval
[DI+0x16] = DX (collision shape: 11 for horiz, 7 for vert)
[DI+0x18] = SI (animation table address)
[DI+0x1E] = switch_id
[DI+0x1D] = 0 (field active flag)
```

**Shared handler update (0x1EB5):**
```
If switch_state[switch_id] == 0 (field OFF):
  If was active: clear tiles (frame 4), erase collision (DRAW_VISUAL shape+1)
  Return
If field ON:
  DRAW_VISUAL(shape+1, X, Y) — erase old collision (shape 12 for horiz)
  Increment frame counter, frame = counter & 3
  MODIFY_FOREGROUND_MAP(frame, table) — draw animation tiles
  DRAW_COLLISION(shape, type=1, X, Y) — write collision (shape 11 for horiz)
  Set active flag
```

**Horizontal field animation table (DS:0x3B9F):**

| Frame | Tiles (6 in a row, offsets 0-5) |
|-------|-------------------------------|
| 0 | 64, 65, 66, 67, 68, 69 |
| 1 | 104, 105, 106, 107, 108, 109 |
| 2 | 84, 85, 86, 87, 88, 89 |
| 3 | 124, 125, 126, 127, 128, 129 |
| 4 (clear) | 0, 0, 0, 0, 0, 0 |

**Collision shapes:**

| Shape | Size | Purpose |
|-------|------|---------|
| 11 (write) | 48w × 2h, rows 2-3 | Horizontal collision bar |
| 12 (erase) | 48w × 4h, rows 1-4 | Slightly larger for clean erase |

**Comparison: all three field types using shared handler 0x1E3C:**

| Type | Handler | Shape (write/erase) | Anim Table | Tile Layout |
|------|---------|---------------------|------------|-------------|
| 8 v_field | 0x1336 | 7/8 (2w×35h / 6w×35h) | DS:0x3B95 | 6 tiles vertical (col) |
| 9 h_field | 0x131F | 11/12 (48w×2h / 48w×4h) | DS:0x3B9F | 6 tiles horizontal (row) |
| 13 glow_ball | 0x134D | 5/6 | DS:0x3BA9 | (different layout) |

**Also fixed:** Added collision bitmap writing for vertical_field (shape 7: 2w at cols 3-4,
alternating rows), which was previously visual-only with no collision.

### Permanent Hazards (no switch to disable)

| Level | Room | Type | Switch ID | Notes |
|-------|------|------|-----------|-------|
| 3 | R10 | h_field | sw200 | No switch exists — permanent barrier |

### Sound Driver Selection (command line)

`GAME.EXE N` where N is (from the usage text in the binary):
- 0 = No sound, no timer speedup (18.2 Hz PIT, counter loop ×64)
- 1 = No sound (fast timer)
- 2 = Internal PC speaker (default)
- 3 = Covox Speech Thing
- 4 = Covox Sound Master II
(No Sound Blaster support exists in the code.)

No command-line level select exists. Levels play in fixed sequence.

### Fix 19: Background Fan Overwriting Foreground Field Tiles

**Bug:** In L3 R6, the right horizontal field lightning was invisible because the
brown fan (type 3) at (13,7) was overwriting the h_field's foreground tiles.

**Root cause:** Two different map modification functions exist in the original:

#### MODIFY_FOREGROUND_MAP (0x04B4) — writes to foreground map at DS:0x5D7
```
Used by: fields (8/9), cages (10), doors (5), beam animations
Unconditionally writes tile values to the foreground map.
```

#### MODIFY_SCREEN_MAP (0x04D2) — writes to background map at DS:0x357
```
Used by: fan_3/fan_4 (background fans)
CONDITIONALLY writes: checks [BX+DI+0x280] (foreground map at same position)
If foreground tile != 0xFF → SKIP the write (don't overwrite foreground content)
If foreground tile == 0xFF → write to background map
```

**This is the key architectural insight:** The original game has a layering system where
foreground tiles take priority. Background fans (fan_3/fan_4) use MODIFY_SCREEN_MAP
which respects existing foreground content. Fields use MODIFY_FOREGROUND_MAP which
writes to the foreground layer directly.

#### Fan handler architecture (two separate handlers):

| Fan Types | Handler | Map Function | Layer |
|-----------|---------|-------------|-------|
| fan_1, fan_2 | 0x1D40 | 0x04B4 (MODIFY_FOREGROUND_MAP) | Foreground |
| fan_3, fan_4 | 0x1DBE | 0x04D2 (MODIFY_SCREEN_MAP) | Background |

**Fix:** Removed `fg_tiles[idx] = 0` from background fan code. Background fans now
only draw to the surface directly and don't touch fg_tiles, so foreground content
(like h_field lightning) renders on top correctly.

**Rule for future objects:** Any object that writes to the background layer should
NOT set fg_tiles. Only objects that write to the foreground layer should use fg_tiles.
Check which MODIFY function the original handler calls:
- Calls 0x04B4 → use fg_tiles (foreground)
- Calls 0x04D2 → draw to surface directly (background)

### Fix 20: Vertical Field Collision Not Erased When Switch Turns It Off

**Bug:** In L1 R0, after hitting the left switch to turn off the vertical lightning
field, Joe was still blocked by invisible collision at the field's position.

**Root cause:** The vertical field code had no OFF path for collision. When
`switch_state == 0`, it did `continue` immediately — skipping collision erase.
The collision bytes written when the field was ON stayed in the bitmap permanently.

**Original behavior (from shared handler 0x1E3C update at 0x1EB5):**
```
If switch_state == 0 (field OFF):
  If field was active ([DI+0x1D] != 0):
    MODIFY_FOREGROUND_MAP(frame=4, table) — clear animation tiles (all tile 0)
    DRAW_VISUAL(shape, X, Y) — erase collision from bitmap (restore from backup)
    [DI+0x1D] = 0 — mark inactive
```

**Fix:** Added the OFF path matching the original:
- Track `obj["field_active"]` flag (matches `[DI+0x1D]`)
- When field turns OFF and was active: restore collision bitmap from backup
  using shape 8 (6w×35h, rows 1-35) for vertical field
- Same pattern already implemented correctly for horizontal field

**Pattern for all field types (v_field, h_field):**
```python
if switch_state == 0:  # OFF
    if obj.get("field_active") and backup:
        # Restore collision from backup at erase shape positions
        obj["field_active"] = False
    continue
# ON path: draw animation, write collision
obj["field_active"] = True
```

### Key Addresses (session 4 continued)

| Address | Description |
|---------|-------------|
| 0x213C | Toggle switch handler |
| 0x2219 | Teleporter handler |
| 0x1F18 | Beam-out handler (cage disappear forward, frames 0→16) |
| 0x1FBF | Beam-in handler (cage disappear reverse, frames 15→0) |
| 0x0C7E | Position Joe at coords (sets gun position, resets fire state) |
| 0x0BBF | Teleport room change path (bounds check, beam-out, state advance) |
| 0x0C62 | Teleport arrival path (load room, beam-in) |
| DS:0x23BA | Room change flag (0=none, 1=teleport pending, 2=beam-out done) |
| DS:0x23BB | Destination room number |
| DS:0x23BF | Destination tile location |
| DS:0x23B9 | Beam completion counter |
| DS:0x3389 | Cage disappear / beam animation table (17 frames) |

## FILES TO CLEAN UP
- test_sprites.png, test_all_sprites.png may exist in python/ directory
- verify_joe.png may exist in python/ directory
- /tmp/doswork/ and /tmp/dosjet/ have working copies
- explosion_sprite_33-38.png in python/ directory

## SESSION 5: CAPTIVE COUNT, LEVEL COMPLETION, BEAM ANIMATIONS (2026-04-21)

### CRITICAL RENDERING RULES (lessons learned across all sessions)

These rules MUST be followed for any future tile/sprite rendering to avoid visual bugs:

#### Rule 1: Foreground tiles drawn with colorkey (black = transparent)
Any tile drawn OVER the background (foreground layer, beam animations, force fields,
fan overlays) MUST use `set_colorkey((0, 0, 0))` so black pixels are transparent and
the background shows through. Without this, you get black rectangles covering the
background tiles.

**Applies to:**
- Beam animation tiles (213-219, 234-239) — sparkle/flash effects
- Force field tiles (232, 233, 252, 253) — cage sparkle dots
- Vertical field tiles (80-83, 100-103, etc.) — lightning animation
- Horizontal field tiles (64-69, 84-89, etc.) — lightning animation
- Foreground fan tiles (fan_1/fan_2) — fan housing over Joe
- Tile 254 — blue dither screen-door transparency
- Any tile drawn in `render_foreground` or `draw_objects` overlay passes

**Does NOT apply to:**
- Background tiles in `render_room` — drawn opaque, fill the entire screen
- Background fan tiles (fan_3/fan_4) — drawn opaque to surface directly

#### Rule 2: Tile value 0 in animation tables means "empty/clear"
When an animation table entry has tile index 0, it means "don't draw anything here"
(the background shows through). Skip these entries (`if ti == 0: continue`).
Do NOT draw tile 0 — it's the editor cursor marker, not a game tile.

#### Rule 3: Foreground vs background layer — check which MODIFY function the handler calls
- Handler calls `MODIFY_FOREGROUND_MAP` (0x04B4) → use `fg_tiles` dict, draw with colorkey
- Handler calls `MODIFY_SCREEN_MAP` (0x04D2) → draw to surface directly, opaque
- Background fans (fan_3/fan_4) use 0x04D2 — do NOT set fg_tiles
- Foreground fans (fan_1/fan_2), fields, cages, doors, beams use 0x04B4 — use fg_tiles

#### Rule 4: Player physics must be frozen during beam animations
When `beam_in` or `beam_out` is active:
- Do NOT call `player.update()` — gravity will pull Joe down during the animation
- Do NOT process player input (movement, thrust, fire)
- Joe's position must remain exactly where it was set
- Joe's sprite must be hidden (not drawn)

**Bug history:** Session 5 — Joe fell to the floor during beam-in because `player.update()`
was still running. The `beaming` flag correctly froze input but not the physics update.

#### Rule 5: Joe visibility during beam animations
- **Beam-out** (dissolve away): Joe hidden when `frame >= 12` (disappears partway through)
- **Beam-in** (materialize): Joe hidden for the ENTIRE animation (`beam_in is not None`)
  - The flash/sparkle plays its full course, THEN Joe appears when animation completes
  - This differs from beam-out where Joe is visible for the first 12 frames

**Bug history:** Session 5 — Originally used `frame > 12` for beam-in (same as teleporter),
which made Joe appear almost immediately (after only 3 frames of a 16-frame animation).
For level-start beam-in, Joe must be hidden until the animation is completely done.

### Fix 21: Captive Count Display in Status Bar

**Change:** Replaced static "JET PACK JOE" text in the center of the status bar with
`Rescues Remaining: XX` showing the live captive count.

**Original game behavior (from GAME.EXE):**
- Status bar string at DS:0x0321: `TIME: 000   JET PACK JOE DEMO   ROOM: 00`
- 40 characters, rendered to text buffer at DS:0x2363 with attribute bytes
- TIME uses attribute 0x0A (bright green), ROOM uses 0x07 (white)
- The middle "JET PACK JOE DEMO" is STATIC — set once at init, never updated
- Captive count at DS:0x305F is only used for the level-complete check, never displayed
- This is a user-requested enhancement, not matching the original

**Implementation:**
```python
self.screen.blit(self.font.render(
    f"Rescues Remaining: {self.captive_count:02d}", False, (0, 255, 0)),
    (SCREEN_W // 2 - 66, bar_y + 3))
```

### Fix 22: Captive Count Decrement — One-Shot Bug

**Bug:** After freeing the first captive, the count dropped from 4 to 0 instead of 3.

**Root cause:** The cage disappear animation's `else` branch (frame >= 17) ran EVERY FRAME
after the animation completed, not just once. The `disappear` counter kept incrementing
past 17, and the decrement fired repeatedly.

**Fix:** Added `obj["done"]` flag so the collision cleanup and decrement only fire once:
```python
elif not obj.get("done"):
    obj["done"] = True
    # ... clear collision walls ...
    self.captive_count = max(0, self.captive_count - 1)
```

**Pattern for future one-shot completion handlers:**
Any code that runs "when animation completes" must guard against repeated execution.
The animation frame counter continues incrementing — the completion branch runs every
frame after the threshold. Always use a `done` flag or deactivate the object.

### Fix 23: Level Completion — Advance to Next Level

**Original GAME.EXE level completion flow (traced from disassembly):**

```
1. Last cage disappear (frame 17):
   DEC WORD [305F]              ; captive_count--
   If count == 0:
     MOV BYTE [23BA], 01        ; set level complete flag

2. Main loop (0x0B40) checks [23BA]:
   == 0: normal gameplay
   == 1: level complete → move Joe toward center (±140x, ±75y)
   > 1:  beam-out in progress

3. Once Joe centered (0x0BBF):
   Check all objects inactive
   Spawn beam-out at Joe's position (CALL 1F18)
   INC [23BA] → state 2

4. Beam-out completes:
   DEC [305F] (goes to -1)
   INC [23B9] (beam done signal)

5. Main loop sees [23BA]>1 and [23B9]!=0:
   Since [305F] <= 0 → set [305E] = 1 (level done)

6. Main loop sees [305E]==1:
   Return with carry clear → caller advances level
```

**Python implementation (simplified):**
- When `captive_count` reaches 0: start beam-out at Joe's tile position
- Beam-out dict has NO `dest_room` key (distinguishes from teleporter beam-out)
- When beam-out completes: check `"dest_room" in bo`
  - Present → teleporter path (move Joe, start beam-in)
  - Absent → level-complete path (`set_level(current_level + 1)` or `game_won = True`)
- Level 2 (index 2) is the last level → shows "YOU WIN!"

### Fix 24: Beam-In Animation at Level Start

**Original GAME.EXE behavior (0x0C5B-0x0C78):**
```
0x05D7: MOV BYTE [23B8], 01     ; set 'arrived' flag at level init
...
0x0C5B: CMP BYTE [23B8], 01     ; check arrived flag in main loop
0x0C60: JNZ 0C7D                ; not set → skip
0x0C6E: MOV CX, [23BF]          ; beam tile from trailer word 3
0x0C72: MOV AX, 0000             ; init
0x0C75: CALL 1FBF                ; spawn beam-in animation
0x0C78: MOV BYTE [23B8], 00      ; clear flag
```

**Beam tile positions (from level data trailer word 3):**

| Level | Trailer Word 3 | Tile | Col | Row | Pixel (x, y) |
|-------|---------------|------|-----|-----|---------------|
| 1 | 128 | 128 | 8 | 6 | (128, 72) → player (151, 88) |
| 2 | 57 | 57 | 17 | 2 | (272, 24) → player (295, 40) |
| 3 | 70 | 70 | 10 | 3 | (160, 36) → player (183, 52) |

Player position = `(col * 16 + 23, row * 12 + 16)` matching GAME.EXE 0x0C7E offset.

**Python implementation:**
```python
# In build_assets():
self.beam_tile = struct.unpack_from('<H', lv_data, trailer_off + 6)[0]

# In set_level():
bcol = self.beam_tile % MAP_COLS
brow = self.beam_tile // MAP_COLS
self.player = Player(bcol * TILE_W + 23, brow * TILE_H + 16)
self.beam_in = {"tile": self.beam_tile, "frame": 15, "timer": 0}
```

### Fix 25: Beam-Out Animation at Level Complete

**Original GAME.EXE behavior (0x0C27-0x0C4F):**
```
0x0C27: MOV CX, AX              ; CX = Joe's tile position
0x0C29: MOV AX, 0000             ; init
0x0C2C: MOV BX, [23C9]           ; Joe's sprite handle
0x0C30: CALL 1F18                ; spawn beam-out
0x0C4F: INC BYTE [23BA]          ; state 1→2 (beam in progress)
```

**Python implementation:**
```python
# When captive_count reaches 0:
tile = (int(self.player.y) // TILE_H) * MAP_COLS + (int(self.player.x) // TILE_W)
self.beam_out = {"tile": tile, "frame": 0, "timer": 0}  # no dest_room = level complete

# On beam-out completion (in draw_objects):
if "dest_room" in bo:
    # Teleporter path
else:
    # Level-complete path
    if self.current_level < 2:
        self.set_level(self.current_level + 1)
    else:
        self.game_won = True
```

### Fix 26: Beam Animation Tile Rendering — Colorkey Fix

**Bug:** Beam animation showed black rectangles instead of background tiles showing through.

**Root cause:** Beam animation tiles (213-219, 234-239) have colored sparkle dots on a
BLACK background. They were drawn opaquely, covering the background with black.

**Fix:** Set colorkey on beam tiles before blitting:
```python
ts = self.tile_surfs[ti]
ts.set_colorkey((0, 0, 0))
surface.blit(ts, (px, py))
```

This is the same pattern used by foreground tiles, force field tiles, and vertical/horizontal
field tiles. **ALL overlay tiles must use colorkey.** See Rule 1 in CRITICAL RENDERING RULES.

### Fix 27: Player Physics Frozen During Beam Animations

**Bug:** Joe fell to the floor during beam-in animation because gravity was still applied.

**Root cause:** The `beaming` flag froze player INPUT but `player.update()` still ran,
applying gravity every frame. By the time the beam-in finished, Joe had fallen from the
beam tile position to the ground.

**Fix:** Skip `player.update()` when beaming:
```python
if not beaming:
    cbm, pipe_floors, pipe_ceilings = self.get_collision_bitmap(self.current_room)
    self.player.update(cbm, self.sprites, pipe_floors, pipe_ceilings)
```

### Level Data Trailer Format (complete, all 4 words now used)

| Offset | Size | Field | L1 Value | L2 Value | L3 Value | Address |
|--------|------|-------|----------|----------|----------|---------|
| +0 | word | captive_count | 4 | 11 | 15 | DS:0x305F |
| +2 | word | timer_value | 150 | 400 | 400 | DS:0x23DA |
| +4 | word | start_room | 0 | 0 | 0 | DS:0x23DC |
| +6 | word | beam_tile | 128 | 57 | 70 | DS:0x23BF |

### Session 5 Key Addresses

| Address | Description |
|---------|-------------|
| 0x0309 | INT_TO_DEC — converts AX to 5-digit ASCII at [DI] |
| 0x032A | Update ROOM display (calls INT_TO_DEC, writes to text buffer) |
| 0x0321 | Status bar string (DS, 40 chars): "TIME: 000   JET PACK JOE DEMO   ROOM: 00" |
| 0x2363 | Status bar text buffer (DS, 40 words: char+attr pairs) |
| 0x236F | Text buffer position 6 (TIME hundreds digit) |
| 0x23AF | Text buffer position 38 (ROOM tens digit) |
| 0x09EE | TIME display update (reads [23DA], calls INT_TO_DEC, attr=0x0A green) |
| 0x0B40 | Main loop [23BA] dispatch (0=normal, 1=level complete, >1=beam) |
| 0x0BBF | Level complete path — check Joe centered, spawn beam-out |
| 0x0C27 | Beam-out spawn for level complete (at Joe's position) |
| 0x0C5B | Beam-in check — [23B8]==1 triggers beam-in at [23BF] tile |
| 0x0C62 | Beam-in spawn (load dest room, CALL 1FBF at [23BF] tile) |
| DS:0x23B8 | Arrived flag (1=spawn beam-in, 0=done) |
| DS:0x23BF | Beam tile location (trailer word 3) |
| DS:0x305E | Level done flag (1=exit game loop with carry clear) |
| DS:0x305F | Captive count (word, DEC on cage clear, level complete when 0) |

### Current State Summary (end of session 5)

**Working:**
- Everything from sessions 1-4 ✓
- Captive count display ("Rescues Remaining: XX") in status bar ✓
- Captive count decrement on cage clear (one-shot, with done flag) ✓
- Level completion: beam-out → advance to next level ✓
- Beam-in at level start: flash animation → Joe appears ✓
- Beam-out at level complete: Joe dissolves → next level loads ✓
- Beam tiles rendered with colorkey (background shows through) ✓
- Player physics frozen during all beam animations ✓
- Joe hidden during entire beam-in (appears only after animation completes) ✓
- Joe hidden from frame 12 during beam-out (disappears partway through) ✓
- Game win state after completing level 3 ✓

**Not yet implemented:**
- Enemy AI: sentries (type 14), bird generators (11), ball generators (12), orb generators (20)
- Sensor switch (type 18), plates (15/16)
- Energy fields killing Joe on contact
- Muzzle flash animation (cosmetic)
- Proper status bar font (CHAR.ASM green digital font)
- Sound effects, cutscene animations
- Death animation (sprites 46-49)
- Enemy collision shapes from SH00.DAT

### Fix 28: Plates (types 15/16) — IN PROGRESS

**Status:** Animation and collision working. Death on crush NOT yet implemented.

**Original GAME.EXE handlers:** left_plate at 0x17A0, right_plate at 0x189B

**Plate mechanics (from disassembly):**
- Plates are moving collision walls that oscillate back and forth horizontally
- `switch_state[var_id]` cycles 0→51 (52 values), wrapping via byte INC + CMP 52
- Position table at DS:0x39BD: 52 entries × 6 bytes [x_offset, anim_frame, tile_col]
  - Values 0-26: plate moves outward (x_offset 0→52)
  - Values 27-51: plate moves back (x_offset 50→2)
- `[DI+08] = 0x000A` (tick interval = 10, very fast)
- `[DI+1D]` = frame counter, starts at 3. TEST with 3 → full update every 4th call
- Non-update frames: DRAW_COLLISION(shape=18, type=1) at current position (refresh)
- Full update: erase old collision, advance state, update tiles, write new collision

**Collision shape 18:** 6w × 30h half-res, alternating filled/empty rows (like door shape 3 but taller). Only the 6-pixel leading edge has collision — the horizontal pipe trail is visual only.

**Left vs Right plate differences:**
- Left plate: `CX = tile_loc + tile_col` (tiles extend rightward)
  - Collision: `base_x + x_off`
  - Trail fill: tile_loc, tile_loc+1, ..., tile_loc+tile_col-1 (rightward)
  - Animation table at DS:0x3995
- Right plate: `CX = tile_loc - tile_col` (tiles extend leftward)
  - Collision: `base_x - x_off + 4`
  - Trail fill: tile_loc, tile_loc-1, ..., tile_loc-tile_col+1 (leftward)
  - Animation table at DS:0x39A9

**Animation frames:** 10 frames (0-9) per plate type. Each frame replaces a 1×5 or 2×5 tile column. Frames 0, 8, 9 handle column transitions (tile 0 entries clear trailing positions). Tiles used: 51-53, 71-73, 91-93, 111-113, 131-133, 151-153, 171-173, 190-191.

**Trail fill (0x1870-0x1882 / 0x196B-0x197D):**
Writes tile 71 to foreground map at rows 1 and 3 below tile_loc for each column the plate has passed through. This creates the horizontal pipe bars extending behind the moving plate edge. Tile 71 is visual only — no collision.

**Tile offset format:** Animation frame tile offsets are FLAT MAP ARRAY OFFSETS added directly to the base tile position (`fg_idx = base_tile + toff`). NOT decomposed into (col, row) pairs. Example: offset 19 from position 111 = position 130 = (col=10, row=6), which is one row down, one column left.

**Collision timing (critical):**
- Collision is written in `update_objects()` BEFORE `player.update()` so the bitmap is current when the player checks it
- `draw_objects()` handles the erase/advance/rewrite cycle for moving the collision position
- The erase in `draw_objects` removes the old position AFTER the player has already been checked
- This avoids the bug where collision was written after player update (player never saw it)

**Rendering:**
- Plate tiles go through `render_foreground` with colorkey (black = transparent)
- Types 15/16 added to the `fg_overrides` collection list
- `fg_tiles` dict accumulates (NOT cleared each frame) — animation frames self-clean via tile 0 entries
- Tile 71 trail entries persist in fg_tiles as the plate extends

**Byte overflow handling:**
`(switch_state[var_id] + 1) & 0xFF` then `if val >= 52: val = 0`. This matches the original's `INC AL; CMP AL, 34h; JC skip; SUB AL,AL`. Starting from 0xFF: `(255+1) & 0xFF = 0`, which is correct.

**Plates found in:**
| Level | Room | Type | Tile Loc | Var ID |
|-------|------|------|----------|--------|
| 2 | 18 | left_plate | 104 (col=4,row=5) | 44 |
| 2 | 18 | right_plate | 111 (col=11,row=5) | 45 |
| 3 | 2 | left_plate | 43 (col=3,row=2) | 2 |
| 3 | 2 | right_plate | 51 (col=11,row=2) | 3 |
| 3 | 19 | left_plate | 108 (col=8,row=5) | 42 |
| 3 | 19 | right_plate | 115 (col=15,row=5) | 43 |
| 3 | 20 | left_plate | 108 (col=8,row=5) | 32 |
| 3 | 20 | right_plate | 115 (col=15,row=5) | 33 |

**Still TODO for plates:**
- Death when plates crush Joe (plates close on him)
- Need to trace the original's crush detection — likely CHECK_COLLISION with Joe's shape against the plate, or detecting when both plates overlap Joe's position
- Death animation (sprites 46-49) not yet implemented globally

**Bugs found and fixed during implementation:**
1. fg_overrides collection list missing types 15/16 → tiles not rendered
2. Tile offsets decomposed as (col,row) instead of flat map offsets → wrong positions
3. Opaque rendering caused black rectangles → need colorkey for transparency
4. fg_tiles cleared every frame → pipe trail disappeared as plate moved
5. Collision written in draw_objects (after player update) → player never saw it
6. Leftover duplicate code and missing sentry sprite line after refactor

**Key addresses (plates):**
| Address | Description |
|---------|-------------|
| 0x17A0 | left_plate handler |
| 0x189B | right_plate handler |
| 0x17C2 | left_plate init |
| 0x1811 | left_plate update |
| 0x18BD | right_plate init |
| 0x190C | right_plate update |
| DS:0x3995 | Left plate animation table (10 frame pointers) |
| DS:0x39A9 | Right plate animation table (10 frame pointers) |
| DS:0x39BD | Plate position table (52 entries × 6 bytes) |
| Shape 18 | Plate collision: 6w × 30h half-res, alternating rows |

### Debug Key Added
- **T key**: Jump to Level 2 Room 18 (plate test room)
## SESSION 6: ENEMY AI — SENTRY, BALLS, ORBS, BIRDS, GLOW BALL, DEATH (2026-10-13)

### Tools used (so this is not forgotten again)
- **ndisasm** (Homebrew `nasm` package) for static disassembly. Code address N lives at file
  offset N + 0x200 (MZ header). Helper used this session:
  `ndisasm -b 16 -o 0x22EF -e 0x24EF GAME.EXE` → disassembles from code address 0x22EF.
  Data segment: DS = 0x049E → file offset of DS:X = 0x200 + 0x49E0 + X.
- **DOSBox-X** (`brew install dosbox-x`) runs GAME.EXE and UNCRAM.EXE and has a built-in
  debugger for breakpoints/stepping/memory dumps.

### THE COLLISION ENGINE, FINALLY UNDERSTOOD (this unlocked all enemy behaviour)

The collision bitmap bytes are **typed**, and CHECK_COLLISION is a histogram, not a boolean.

**CHECK_COLLISION core (0x2F11):** with filter BL, scans the shape and counts every byte
that is **not equal to BL**, bucketed by byte value into DS:0x3167..0x3176 (16 counters).
Returns AX = total, ZF=1 if total == 0.
- `[0x3168]` = count of type-1 bytes (walls)      `[0x3175]` = count of type-14 bytes (Joe)
- BL=0  → "is anything solid here" (movement checks)
- BL=own_type → "has anything intruded on my own footprint" (Joe uses 14, balls/birds use 6)

**Collision byte types:**
| Type | Written by |
|------|-----------|
| 1 | walls (tiles), doors, fields, cages, plates, **sentry** |
| 6 | balls and birds (DRAW_COLLISION with BL=6) |
| 14 | **Joe** — DRAW_COLLISION(shape 0, BL=0x0E) at the END of every Joe update (0x0E3B) |

**The four bitmap primitives (all take AX=shape, CX/DX=centered coords):**
| Wrapper | Core | Effect |
|---------|------|--------|
| 0x043C | 0x2F11 | CHECK (histogram, see above) |
| 0x045A | 0x2ED8 | DRAW_COLLISION: fill shape with type BL |
| 0x0473 | 0x2F8A | DRAW_VISUAL: restore shape area from backup bitmap (ES:0x4820) |
| 0x048C | 0x2FCB | conditional erase: restore from backup only where byte == BL |

**How Joe dies (0x0CCC-0x0CE9):** at the start of his update his own marker is still in the
bitmap from last time. `CHECK(shape 0, BL=14)` counts everything that is not 14. If the total
is non-zero and differs from the wall count → `JMP 0x0F05` (death). So **any byte under Joe
that is neither 14 nor 1 kills him** — including **0**. A 0 appears whenever another object
did a DRAW_VISUAL (backup restore) over Joe. That is the kill mechanism for:
- vertical/horizontal fields (erase shape 8/12 every update), glow balls (erase shape 6)
- the bird's laser (DRAW_VISUAL shape 15 — the 1-wide column above the bird)
- the orb (DRAW_VISUAL shape 22 at its hit point) and the ball's ring (DRAW_VISUAL shape 17)
- type 6 bytes (ball/bird body overlapping Joe) kill directly.
Then Joe erases his marker (0x048C BL=14), moves, and the **9-position nudge** (0x0CFB-0x0D5B)
runs; if all 9 are blocked → `JMP 0x0F05` as well (**crush death**: plates, doors, sentry).

**How shots kill (0x10A5-0x10F9):** CHECK(shape 1, BL=0). If the hit contains no Joe bytes:
DRAW_VISUAL(shape 1) — restores the backup under the 4×2 shape, which **wipes a ball's or
bird's type-6 bytes**; the enemy's next own-footprint check (BL=6) sees the 0s and explodes.
Then the wall-hit explosion (0x1103) spawns and the shot dies. Hits with only Joe → keep
flying; Joe plus something else → vanish silently. **Sentries never do an own-footprint
check, so they are invulnerable** (a shot just explodes against them).

**0x0F05 is NOT a muzzle flash — it is Joe's death animation.** Earlier notes were wrong.
`[0x23D4]` is the death frame (-1 = alive), `[0x23C7]` the countdown (8 Joe-updates to the
first step, 7 after; Joe updates every 10 ticks → 70 ticks ≈ 3.5 frames per step):
- frames 1-15: Joe's sprite = frame & 7 (tumbles through his 8 frames); spawn 0x1103 glow at
  Joe + (random(29)-13, random(23)-11)
- frames 16-23: sprite 46 + (frame-16)/2 (debris 46,46,47,47,48,48,49,49); glow at
  Joe + (random(37)-18, random(45)-22)
- frame 25: FREE Joe's sprite (hidden); frame 58: [0x305E]=1 → level loop exits. The demo's
  caller (0x02C3) just restarts the level.

### Timing model (main loop 0x06A4-0x0788, corrected)
The loop runs Joe (every 10 ticks), the timer (1165 ticks), the state machine (129 ticks) and
every object (its [DI+8]) **repeatedly without rendering while anything is due** (`OR BP,BP`
at 0x074B); it renders (0x03BA, ≥20 ticks apart) only when nothing ran. So objects really run
at their own tick rate — an interval of 9 means ~2.2 updates per render frame, not 1.
Python: `self.tick += TICKS_PER_FRAME (1165.2/60)` per frame; each entity runs
`while next_time <= tick: update(); next_time += interval` (handlers may adjust next_time).

### Object handler reference (all decoded this session)

**Object slot fields reused by enemies:** [0x0A/0x0C] x/y, [0x0E] sprite handle, [0x10/0x12]
|dx|/|dy| or home pos, [0x16/0x18] step signs or vy/frac, [0x1A] bresenham error or 3rd sprite,
[0x1C] sprite/frame, [0x1D] frame accumulator / thrust flag, [0x1E] retarget counter / dir,
[0x1F] step phase. Dispatch: AX=0 init, 1 activate (alloc sprites, write collision), 2 update,
3 hide (free sprites, erase collision), 4 clone-for-room-change (0x09A6), 5 destroy.

#### Sentry — type 14, handler 0x22EF — sprites **39/40/41** (pink UFO), NOT a bird
- Init: position = BLOCK_TO_XY(location); var_id → if switch_state[var]==0 skip spawn;
  interval 0x1B (27). Activate: 3 sprites (body 39+dir, glow 50/51(+2 when thrusting) at
  (x, y+10), glow 52/53 at (x − (17·dir − 17), y − 2)), handles sorted so the body is on top.
- Update: DRAW_VISUAL(shape 19+dir); dir = 1 if |x − JoeX + 8| < 16 else (2 if x < JoeX
  else 0); x += dir − 1; CHECK(19+dir, BL=0): clear → facing = dir; hit only Joe → still
  move; else revert. Vertical = Joe's physics: vy += 41, −82 if y ≥ JoeY (thrust), clamp
  ±1000, thousandths accumulator → ±1 px; CHECK(19+facing): blocked by non-Joe → revert,
  vy = 0. DRAW_COLLISION(19+facing, type 1). Sprites 50..53 flicker with [0x2361]&1.
- Kills Joe by ramming (writes type 1 over him → nudges fail → crush) and by its own
  DRAW_VISUAL wiping his marker. Shapes 19/21 are 17×11 half-res, 20 is 11×11.
- Instances: L3 R11 @225 (var 34), L3 R13 @98 (var 43). Vars not in L3's switch-off list.

#### Ball generator — type 12, 0x14F5 — and Ball — 0x15A2 — sprites **42-45** (electric)
- Generator: pos = tile + (15,11); interval 0x101 (257); countdown random(4)+4.
  Update: countdown−1; at 3/2/1 → MODIFY_SCREEN_MAP frames 1/2/3 of table DS:0x31BF
  (2×2 tiles 506-507/526-527, 508-509/528-529, 546-547/566-567, 548-549/568-569); at 0 →
  if CHECK(shape 16) clear: spawn ball, countdown = 8, frame 0; if blocked: retry next update.
- Ball init: CHECK(shape 2) must be clear; interval 0x10; retarget=1. Activate: sprite 42+frame,
  DRAW_COLLISION(16, type 6).
- Ball update: every 25 updates re-aim: |dx|,|dy|,signs toward Joe. CHECK(16, BL=6) non-zero
  → explode (0x11BA with its sprite handle). Erase own (0x048C BL=6). Bresenham step
  (err ≤ 0: x += sx, err += |dy|, every other step next_time −= 7; else y += sy,
  err −= |dx|, next_time += 3, every other −= 7). ROOM_TRANSITION → hide. CHECK(16, BL=0)
  blocked → revert + retarget. DRAW_VISUAL(**shape 17**, the 11×9 ring) then
  DRAW_COLLISION(16, 6). Frame acc += 22/256 → sprite 42 + (frame & 3).
- The ring restore kills Joe on touch and pops neighbouring balls.
- Instances: L1 R5 ×2; L2 R0, R19 ×2; L3 R3 ×4, R9 ×2, R12.

#### Orb generator — type 20, 0x2526 — and Orb — 0x25C1 — sprites 50 (spawn) / 51 (flight)
- Generator: pos = tile + (15,11); interval 0x2B (43); countdown random(14)+4. Update:
  countdown−1 → MODIFY_SCREEN_MAP frame = countdown value from the 18-entry table DS:0x3233
  (2×2 tiles 622..633/642..653 pulsing); at 0 → spawn orb, countdown = 18, frame 0.
- Orb init: CHECK(shape 2) clear; first update after 50 ticks, then interval 9; aimed ONCE at
  Joe (|dx|,|dy|,signs). Update: bresenham step (x steps: every other next_time −= 3; y steps:
  next_time += 1, every other −= 3), ROOM_TRANSITION → hide, CHECK(**shape 22**, 5×3, BL=0):
  clear → move, sprite 51; hit → DRAW_VISUAL(22) at the hit point (kills Joe), explode
  (0x11BA), die. Writes no collision of its own.
- Instances: L2 R1; L3 R14, R16, R17, R21.

#### Bird generator — type 11, 0x1488 — and Bird — 0x199A — sprites **29-32** (red bird)
- Generator: pos = tile + (15,11); interval 0x5E7 (1511 ≈ 1.3 s), first spawn after
  random(1511) ticks; no tile animation. Spawns via 0x199A AX=0 (CHECK(shape 2) must be clear).
- Bird: interval 0x14 (20), rises 1 px per update, sprite 29→32 (acc += 0x2A/256), collision
  shape 2 type 6. Laser: when idle, CHECK(**shape 15** — a 1-wide, 43-row-tall dashed column
  above it, rows −46..−4) and if `[0x3175]` (Joe bytes) ≠ 0: laser = 10 updates,
  DRAW_VISUAL(15) (kills Joe), allocate sprite **25** (red beam, 89 px tall) shown as
  25/26 (red/green) alternating per render frame. Own-footprint CHECK(2, BL=6) non-zero →
  explode (0x11BA). Moving into a type-1 byte (ceiling) → vanish silently (hide + destroy).
- Instances: L1 R8; L2 R19 (R68 is the trailer, ignore).

#### Glow ball — type 13, 0x134D — NOT a sprite
Uses the shared field handler 0x1E3C with DX=5 (collision shape), SI=DS:0x3BA9 (table).
Table has 5 frames of 2×2 foreground tiles (offsets 0,1,20,21):
0: 94,95,114,115  1: 96,97,116,117  2: 134,135,154,155  3: 136,137,156,157
4 (dormant, drawn once when the switch turns it off): 138,139,158,159.
ON: DRAW_VISUAL(shape 6, 16×12 hollow ring) then DRAW_COLLISION(shape 5, 14×10 hollow ring,
type 1), frame = counter & 3, interval 0x4F. OFF: frame 4 + DRAW_VISUAL(shape 5).
Shared handler detail: the OFF path erases with `[DI+0x16]` (the write shape), the ON path
erases with `[DI+0x16]+1`. Instances: L3 R3 ×5 (sw16, OFF at start), R12 ×2 (sw18),
R19 ×2 (sw30/31), R20 (sw200).

#### Enemy explosion — 0x11BA
Same as 0x1103 (sprites 33→38, interval 0x47) but inherits the dead enemy's sprite handle in
[DI+0x14] and frees it when the explosion reaches sprite 37 — the enemy's last frame stays
visible under the first four explosion frames.

#### Room change (0x0802) and objects
Every object of the old room gets AX=3 (hide) or AX=4 (clone, simulated for 0xD48 ticks,
then hide+destroy); the new room's object list is re-initialised from scratch (0x0961). So
enemies and generator countdowns restart on every room entry. Sentry AX=5 restores
switch_state[var]=0xFF so it respawns next visit.

### Sprite catalogue corrections
| Sprites | Earlier notes said | Actually |
|---------|-------------------|----------|
| 29-32 | red sentry/UFO | **red bird** (bird generator), 33 = explosion start |
| 39-41 | pink bird | **sentry** (type 14): 39 moving left, 40 hovering, 41 moving right |
| 42-45 | electric zap / death | **ball** (ball generator) animation |
| 46-49 | death debris | confirmed: Joe's death frames 16-23 |
| 50-53 | glow balls | sentry thruster glows (50/51 idle, 52/53 thrusting/trail), orb 50/51 |
| 25/26 | laser beams | bird laser, red/green alternating |

### Python implementation (jet_pack_joe.py)
- `cb_check / cb_write / cb_restore / cb_restore_if` — the four primitives, on the 160×96
  bitmap (no 32-col padding; out-of-range bytes are skipped in every primitive, which is
  equivalent because the original writes and reads its padding alike). `sh_shape(idx)`
  decodes any SH00.DAT entry on demand.
- Joe: `joe_check_and_unmark()` at the start of the frame (death rule + marker erase),
  `joe_mark()` after movement/room transition, crush check with `CRUSH_NUDGES`.
  `self.joe_marked is cbm` guards against a rebuilt bitmap being read as a kill.
- Entities (`Sentry, Ball, Orb, Bird, BallGen, OrbGen, BirdGen, EnemyExplosion`) live in
  `self.entities`, created by `enter_room()` (called whenever `current_room` changes),
  scheduled by `update_entities()` on `self.tick`, drawn by `draw_entities()` under Joe,
  lasers with Joe, explosions above the foreground.
- `Shot` now steps every 15 ticks and uses the shape-1 histogram rule; it restores the backup
  under its hit (which is what kills balls/birds). `Player.update` takes `backup`.
- Vertical field ON path now erases shape 8 before writing shape 7 (h_field already did), so
  fields kill. Glow ball replaced the sprite stub with the tile/ring implementation.
- Death: `start_death / update_death / finish_death` (restart level, lives −1, game over at 0).
- `JPJ_DEBUG=1` prints the byte-type histogram on every death and crush.
- Draw order: background → draw_objects → generator tiles → enemies → Joe → lasers →
  foreground → explosions.

### Verified headlessly (SDL dummy driver, scripted keys)
Balls spawn with generator tile animation, home on Joe and kill on contact ({0: n} under Joe);
birds rise, fire the laser when Joe is above and kill; orbs fly straight at Joe and kill;
the sentry chases and crushes; the vertical field kills on touch ({0: 11}); a shot pops a ball
(explosion with ghost sprite); the death animation runs 58 steps, restarts the level and
decrements lives; normal level start and walking unaffected; 600 busy frames in 0.18 s.

### Still not implemented (re-verified against the binary 2026-11-01, see Session 7)
- ~~Sensor switch (type 18)~~ — implemented 2026-11-01 as `SensorSwitch` (see below).
- Plate crush death: VERIFIED in L2 R18 — Joe hovering between the plates (y 60-119) is crushed;
  standing on the floor below them he is not, which is correct.
- ~~Exact Joe physics~~ — ported 2026-11-03 (see "Joe's exact physics" below).
- ~~Status-bar font and colours, cutscenes~~ — done 2026-11-03 (see "Cutscenes, status bar, level flow").

### Headless test suite (added 2026-11-01)

The session-scratchpad harness from Session 6 was lost when that session ended, so it now lives in
the project:

- `python/tests/harness.py` — `Driver` runs the real `JetPackJoe.run()` loop under SDL's dummy
  video driver with scripted keys (`goto(level, room)`, `place(x, y)` finds the nearest free spot
  in the collision bitmap, `run(frames, keys, until)`, `dump_room()`, `save(png)`), plus
  `enemy_rooms(game)` listing every room with enemy/generator objects.
- `python/tests/test_enemies.py` — nine regression tests: safe level start, ball/sentry/bird kill
  Joe, orbs spawn, a shot pops a ball into an EnemyExplosion, death restarts the level with one
  fewer life, game over on the last life, and a 40-frame smoke run of every enemy room.

Run with `python3 python/tests/test_enemies.py` (about 2 s, no pytest needed; pytest also works).
Pass a test name to run one; set `JPJ_DEBUG=1` for tracebacks and death histograms.


## SESSION 7: SOUND (2026-11-01)

### What the original does
- Sound is **sampled**, not tones. `DRAW/LIST` names the five effects: 0 expl2.v8 (missile
  explosion), 1 swoosh1.v8 (missile shoot), 2 outta.v8 ("help me"), 3 zirble2.v8 (transporter),
  4 thanks1.v8 ("thank you"). The .V8 files are raw unsigned 8-bit PCM.
- **DS00.DAT** (38928 bytes, in JET.RSC) is the in-game sound bank: six words of paragraph
  offsets (×16 = byte offset; the 6th is the end), then each sample converted to 6-bit
  (`v8 >> 2`, silence 0x20) and padded to a multiple of 256 bytes. Lengths: 7424 / 5888 /
  11520 / 9728 / 4352 bytes.
- **PLAY_SOUND 0x02DC**: AX = id; table segment at DS:[0x349]; ES = seg + start paragraph,
  CX = (end − start) / 16 = number of 256-byte blocks; INT 62h DX=4.
- **START_SOUND 0x42B3** (INT 62h DX=4; the old notes called it "display list"): four channel
  records at CS:0x3B1C, 8 bytes each (ptr off/seg, blocks left, start frame). The channel with
  the fewest blocks left is taken, finished or not.
- **SOUND_MIXER 0x4308**: called from the counter tick 0x441E every 32 ticks (1165.2/32 =
  36.4 Hz). Copies 256 bytes of channel 0 (or the 0x20 silence buffer at CS:0x40BC) into one
  of two 0x110-byte buffers, adds channels 1-3 (as 128 words; 4 × 63 < 256 so no carries),
  then translates each byte through a table: Covox 0x3EB6 (`(sum−0x80)*4+0x80`, floor 1,
  ceiling 0xFE), speaker 0x3FB6 (`sum−0x60`, 1..0x40). Linear only for ±31 around 0x80, so a
  single full-scale voice fills the range and overlaps clip.
- **ISRs**: speaker 0x4487 (PIT ch0 divisor 64 = 18643 Hz; PIT ch2 mode 0 pulse width = sample;
  pointer advances on alternate interrupts via `rol [0x3B19]=0x55`, so 9321.7 Hz effective);
  Speech Thing 0x44EC (divisor 128, LPT1 data port) and Sound Master 0x4524 (port 0x22F) at
  one sample per interrupt = **1193182/128 = 9321.7 Hz**. All drivers tick the counter at
  1165.2 Hz. Sound init 0x41DB, stop-all 0x42EA.
- **Who plays what** (callers of 0x02DC):
  | Site | Sound | Event |
  |---|---|---|
  | 0x0EF8 | 1 shoot | fire button |
  | 0x1151 | 0 explosion | shot explosion init (0x1103) — also every death-animation burst |
  | 0x120A | 0 explosion | enemy explosion init (0x11BA) |
  | 0x1406 | 2 help me | captive init (room entry with an unrescued cage) |
  | 0x1468 | 4 thank you | Joe touches the captive |
  | 0x0AFC | 3 transporter | Joe beam-in object init (level start) |
  | 0x1F62 | 3 transporter | beam-out object init (cage clear, level end, teleport out) |
  | 0x2020 | 3 transporter | beam-in object init (teleport arrival) |
  The object slot byte +3 ("sound_id") is only written by the slot allocator; no handler uses it.

### Python implementation (jet_pack_joe.py)
- `SoundBank` decodes DS00.DAT into five `pygame.mixer.Sound`s (6-bit → 16-bit, ±31 → full
  scale, zero-order-hold resample from 9321.7 Hz to the mixer rate), runs 4 channels and
  steals the one with the least time left, like 0x42B3. `play_sound(id)` is the PLAY_SOUND
  wrapper; `SoundBank.history` records the last 64 ids for tests.
- Hooks: `Player.fire` → 1; `Explosion.__init__` and `EnemyExplosion.__init__` → 0 (so the
  death animation rumbles like the original); `enter_room` → 2 per unrescued cage; cage rescue
  → 4 then 3; every beam_in/beam_out creation → 3.
- Off switch mirrors the original: `python3 jet_pack_joe.py 0` (or `1`) = no sound, or
  `JPJ_SOUND=0`. Default is sound on.
- Tests: `python3 python/tests/test_sound.py` (bank loads, durations, each trigger).


### Session 7 verification pass (2026-11-01)

Cam asked for every claim in the "what remains" list to be verified against GAME.EXE rather
than the notes. Results:

| Claim | Verdict | Evidence |
|---|---|---|
| Sensor switch is the only unimplemented object type | TRUE | level data uses types 1-20; Python handles all but 18 |
| Plate crush works in L2 R18 | TRUE | crushed at (126,65) between plates at hx 52-57 / 70-75 |
| Joe updates every 10 ticks, same constants as sentry | TRUE | 0x06BB / 0x0D7F sub 0x52, 0x0DBF add 0x29, clamp 0x3E8 |
| Sound = PC speaker tones, no asset files | FALSE | five samples in DS00.DAT, 4-channel mixer (Session 7 sound) |
| Status bar uses a "green digital font from CHAR.ASM" | HALF | font is a bold 8x8 in GAME.EXE at CS:0x31EC (128 glyph pointers, 8 bytes/glyph, drawn by 0x350C in Mode X); labels and ROOM digits are attr 7 = palette 7 grey (42,42,42); only the TIME digits are attr 0x0A = palette 10 green (21,63,21) (0x09F7). Confirmed by dosbox_room_4_door_closed.png. Original string: `TIME: 000   JET PACK JOE DEMO   ROOM: 00`; the Python's "Rescues Remaining" (Fix 21) is an invention. |
| JET.EXE holds the title/menu/intro | FALSE | JET.EXE == J1.EXE, a 7 KB launcher (memory/VGA/CPU checks, sound-driver arg, archive loader). All animation code is GAME.EXE's ANIM.ASM (RUN_ANIM etc. in the symbol table). |
| Cutscenes exist | TRUE (extracted and decoded 2026-11-03, see below) | anim table DS:0x3D12 → 4 entries {resource, palette, length}: FA00/PL00/140, FA01/PL00/200, FA02/PL01/3000, FA03/PL01/6000. JET.RSC TOC: jp00 bk00 cb00 ds00 fa00-fa03 pl00 pl01 sh00 sp00 lv/mp/pl 11-13; **jp00, fa00-fa03 and pl01 were never UNCRAMed**. |
| When cutscenes play | PARTLY | 0x2750 (anim runner, AX<4) is called once with AX=1 at 0x02CD: after the FIRST time the level runner 0x05D1 returns with captives left (i.e. first death), then [0x2EE]=1 and the level restarts. Entry 0x01AD: `[cs:8](2) ; [cs:C](0) ; [cs:8](0) ; [cs:C](1) ; [cs:8](0) ; [cs:C](2) ; [cs:8](0) ; [cs:8](3) ; INT 61h` — [cs:C] is play-level(n) (0x0210 stores AX at [0x2BC], level table DS:0x2BE = pl/mp/lv 11-13); [cs:8] with 2 / 0 / 0 / 0 / 3 fits title / thumbs-up after each level / credits, but CS:0-F are loader-patched far pointers so this is inferred, not read. |
| Muzzle flash exists | FALSE | fire handler 0x0EAA only creates the projectile (0xFE3) and plays sound 1; 0x0F05 is the death animation. |
| Levels play in fixed sequence 1→2→3 | TRUE | entry sequence above; after level 3 the program exits to the launcher ("We hope you've enjoyed the game."). |


### Sensor switch (type 18) implemented (2026-11-01)

`SensorSwitch(Entity)` in jet_pack_joe.py, spawned by `enter_room`, drawn as a background tile
by `draw_entities`. From handler 0x2061:
- init (0x2083): interval 0x80 ticks, first update after random(0x80), params = tile, sw1, sw2
  ([DI+0x1E], [DI+0x1F]); the update runs once immediately (0x20CB).
- update (0x20D9): CHECK shape 4 (rows 2-3, cols 2-5 of the object position) with BL=1; if any
  Joe byte → `switch_state[sw1] = switch_state[sw2]`. Tile written to the background screen map
  (0x2137): 0x116 (278) + 1 if sw1 var set + 0x14 (20) if sw2 var set + (touching ? (0x14 if sw1
  var set else 0x28) : 0). So: 278/279/298/299 idle, 318 touched-both-clear, 319 touched-both-set.
- The only instance is L3 R13: three pads at tiles 248/251/254 (x 128/176/224, y 144) with
  sw1 = 22/23/24 and sw2 = 41 (always 0). The doors in the room are [225, 22, 25], [228, 23, 26],
  [231, 24, 27] at x 80/128/176, open at start (vars 22-24 = 255). Stepping on a pad copies 0
  into its sw1 and **closes the door to the pad's left**, i.e. the one Joe just came through.
- Tests: `python3 python/tests/test_switches.py` (spawn/tiles, variable copy + door closes +
  tile returns, pad drawn on screen). All three suites pass (9 + 7 + 3).


### Debug navigation (2026-11-01)
- **G** then a room number then **Enter** jumps to that room in the current level (Esc cancels;
  the status bar shows the digits). **[** and **]** step rooms. **1/2/3** pick a level.
- `python3 jet_pack_joe.py --start 3:13` launches straight into level 3 room 13 (the sound
  driver number, if given, goes first: `python3 jet_pack_joe.py 0 --start 3:13`).
- All of these go through `JetPackJoe.jump_to_room`, which drops Joe on the nearest free spot
  so he never starts inside a wall; `tests/test_goto.py` checks every room of every level.
- `--no-enemies` (or `JPJ_ENEMIES=0`) stops the sentry and the ball/orb/bird generators from
  spawning; **E** toggles it in play and respawns the room. Hazards (glow balls, fields, plates)
  are unaffected. The status bar shows "NO ENEMIES" while it is off.


### Fix: cleared cage walls came back (2026-11-01)
Cam could not walk through a rescued cage in L3 R13. Cause: `get_collision_bitmap` took the
backup bitmap *after* adding the cage walls, so every restore-from-backup (Joe's own unmark,
sentry/shot erases) re-created the walls after the rescue had cleared them. The original's
backup (ES:0x4820) is the bare tile collision taken before any object writes, and the captive
handler re-DRAW_COLLISIONs shape 13 every update (0x142F). Now: backup is copied before the cage
walls are added, and the active cage rewrites its four wall columns every frame; after the
disappear animation they are cleared once and stay gone. Tests: `tests/test_cage.py`.


### Teleporter re-ported as an entity (2026-11-01)
`Teleporter(Entity)` (interval 0x3E, first check after random(0x3E)) runs in `update_entities`
with Joe's marker present and uses `cb_check` on shapes 13 and 4 exactly like 0x2290; firing
calls `JetPackJoe.start_teleport(obj)` (the old beam-out creation). The distance-box trigger,
the `armed` keys and the arrival disarm loop are gone. Tests: `tests/test_teleport.py`
(walk-in from each side fires, drop onto the centre does not, no bounce-back after arrival,
return trip after stepping off through a side). Harness note: `Driver.run(n)` now runs
exactly n frames (it used to run n+1).

- Follow-up (same day): leaving L3 R13 by teleporter and coming back re-created the rescued
  cage's walls, because the room reload rebuilds the collision bitmap and stamped walls for
  every type-10 object. `get_collision_bitmap` now skips cages whose rescue has started
  (`disappear >= 0`), matching the original where a rescued captive's init sees its variable
  cleared and stays inactive. Test: round trip through the teleporter in `tests/test_cage.py`.


### Enemies follow Joe between rooms (2026-11-02)

Cam remembered balls from L1 R5 following him into R6 "if they were close enough". The old
notes ("room change destroys all objects") were only half right. Decoded from 0x0802/0x0521:

- Slot state 3 = **mobile** object: shots (0x1021), balls (0x15DD), birds (0x19D9), orbs
  (0x263C). Slot byte +1 (visible): 1 live, 2 transit clone, 0 dormant.
- **0x0521** (callers: Joe 0xE2B, shot 0x1095, ball 0x1716, bird 0x1ACC, orb 0x26EE) maps a
  position outside the 320x192 room to (neighbour room, wrapped position) via the room's exit
  table. A mobile object that leaves on its own takes the new room byte and jumps to its HIDE
  path (visible=0): it waits, dormant, at the edge of the neighbouring room.
- **Room change 0x0802** (Joe's edge transition 0xE30, teleport arrival 0xC6B):
  1. every visible object of the old room: state 3 → AX=4 CLONE (0x09A6: copy the slot, clone
     visible=2, original visible=0 — its collision bytes are left in place); others → AX=3 HIDE
     (most non-mobile handlers set state 0 there, i.e. destroy themselves);
  2. loop: [0x3065] += 100 ticks; run every due visible=2 clone (AX=2) in the OLD room's bitmap,
     with Joe's marker absent; clones never retarget (`cmp [DI+1],1` at 0x1666) so they keep
     their last heading; one that crosses an edge becomes dormant in the room beyond, stamped
     with the simulated time; one that explodes leaves no explosion (0x1770 checks visible==1 and
     room==current). The loop exits only when no clone ran in a pass (the 0xD48 "deadline" at
     0x08A1 is checked only then), so a stuck clone would hang the original; the port caps the
     simulation at 12000 ticks and discards leftovers;
  3. remaining visible=2 → hide + destroy; 4. load the new room (0x032A rebuilds the bitmap);
  5. activate (AX=1) every slot whose room == new room and whose next_time has passed — dormant
     crossers appear at the edge when their simulated arrival time comes (a near ball right
     behind Joe, a far one seconds later), and if Joe returns to the old room quickly its
     dormant originals wake where they were; 6. init the new room's object list.
- **Sweep 0x0A13** (once per second with the TIME counter): dormant objects whose next_time is
  more than 0x1B58 (7000) ticks in the past are destroyed.
- Sentries are not mobile: destroyed on exit, re-created on entry (unchanged).

Python: `Entity.visible/room/mobile`, `Entity.cross()`, `Ball/Bird/Orb.activate()`,
`JetPackJoe.exit_room()` (0x0521 for any object), `carry_mobiles()` (phases 1-3, called before
`current_room` changes in `try_room_transition` and on teleport arrival), `make_dormant()`,
`wake_dormant()` (phase 5 + the sweep, run each frame), `self.dormant`. The old room's cached
collision bitmap is dropped on exit, like the original's rebuild on entry. Shots still die at
the edge (not ported). Tests: `tests/test_follow.py`.


### Joe's exact physics and shots crossing rooms (2026-11-03)

`Player.step(g, inp)` is 0x0CCC-0x0F04 line for line, run every **10 ticks** from the frame loop
(`while player.next_time <= tick`), input as the INT 62h DX=1 bit mask (1 thrust, 2 right,
8 left, 0x10 fire):
1. 0x0CCC death check + lift marker (`joe_check_and_unmark`); 0x0CFB the nine unstick positions
   `(x,y) (c1,y) (c3,y) (x,r1) (x,r3) (c1,r3) (c3,r3) (c3,r1) (c1,r1)` with c1=(x-2)|1, c3=c1+3
   (same for rows) → none free = crush death; position stored (0x0D5E).
2. vy -= 82 if thrust; x ± 1 if right/left (both cancel); if blocked, try y'=(y-2)|1 then y'+3,
   else undo the step (0x0D95).
3. vy += 41, clamp ±1000 (thousandths px/update → at most 1 px per update = 116.5 px/s);
   frac += vy with carry/borrow into y (0x0DD8).
4. If blocked at the new y: try x'=(x-2)|1, then x'' = x+2 with y made even, else y = the stored
   y and vy = 0 (0x0DF5).
5. ROOM_TRANSITION 0x0521 → `change_room` (0x0802: carry mobiles, rebuild bitmap, land at the
   wrapped position; no neighbour → clamp). Store, DRAW_COLLISION shape 0 type 14 (`joe_mark`).
6. Sprites (0x0E43): body = dir + 2·moving + 4·(fired within 0x28 ticks); the second sprite
   (flame) = 8 + (body & 3) + 4·(counter bit 6) + 4·thrust — **always drawn**, it flickers even
   when Joe stands still (sprites 8-11/12-15), bigger while thrusting (12-15/16-19).
7. Fire (0x0EAA): fires on a fresh press, then every 0xC8 ticks while held; shot at
   (x - 12 + 24·dir, y + 2), sprite 23+dir, speed dir·4-2.
Verified: walk 117 px/s (116.5), fall capped at 1 px/update, gravity ramp. The Python-only
"pipe floor/ceiling" barriers and the ±6 px nudges are gone (the original only has the bitmap).

**Shots** are now `Shot(Entity)` with `mobile=True` (slot state 3), updated by the entity
scheduler at 15 ticks: on crossing an edge (0x1095) they park dormant in the next room and
resume if Joe follows within ~6 s, exactly like balls; on a room change they are cloned and
carried like the other mobiles. Explosions only when live and in Joe's room (0x10D2).
Tests: `tests/test_joe.py`.


### Standalone test level (2026-11-03)

`python/tools/build_test_level.py` writes `python/TESTLEVEL.JPL`, an eight-room level with every
object type, built from tile stamps copied out of MP11/12/13 so each object has its real
surroundings (door rails, cage/teleporter frames, generator bases, emitters). Load it with
`python3 jet_pack_joe.py --level TESTLEVEL.JPL` (it becomes level 4: key **4**, `--start 4:N`).
File format: `JPL1`, u32 map/lv/pal sizes, MPxx map, LVxx level data (70 entries, trailer in
entry 68), 768-byte palette (PL11), name. Loader: `load_level_file`, `--level FILE`.

Rooms: 0 fans 1-4 + wall-switch door + toggle-pad door (beam-in here); 1 vertical field gate
(pillar col 8, field fills the gap rows 11-14) + left switch, horizontal field gate (slab row 9
over an exit chamber, field across the hole cols 16-18) + right switch, three glow balls on the
ceiling + toggle pad in the chamber; 2 two cages (the
level's captives) + a plate pair; 3 ball/bird/orb generators; 4 sentry + two doors whose
sensor pads close the door behind you; 7 enhanced mode: twin-shot pack, floor turret, shield
pack (between rooms 4 and 5, added 2026-11-03); 5 three teleporters (one to room 6, a same-room
pair); 6 teleporter back. Exits run left/right along the floor. Variables that start OFF (trailer
off-list): 10, 11, 31, 32 (room 0 doors), 18, 19 (plates), 23 (sensor source), 33, 34.
Layout lessons: wall switches trigger through shape 4 at rows +2..3 of their tile and their
tile carries half a wall (CB00 shape 35/34), so at walking height they must sit at row 13;
in the real levels they are placed at flying height. Joe's collision shape is 28x30 px, so
any pocket he must stand or rise in needs two free tiles (the first room 1 trapped him between
the left exit and a block one tile in: Cam reported "after entering room 1 I can't go anywhere",
2026-11-03). Door pillars reach the ceiling, otherwise a door is just flown over. A left switch
(type 7) is pressed from its right, a right switch from its left: the trigger is the tile's
middle (half-res +2..5, +2..3) behind the half wall. Tests: `tests/test_level_file.py` (loads,
every room runs, flood-fill reachability of every room in each switch state so gates provably
block and open, scripted walkthroughs of rooms 0 and 1 with hops and hovering).

### Cutscenes, status bar, level flow and time-out (2026-11-03)

Cam asked to finish the fidelity gaps. Everything below was read from GAME.EXE and checked
against the extracted data; the Python now does the same.

**Resources.** `jp00 fa00-fa03 pl00 pl01` were pulled out of JET.RSC and UNCRAMed (the
`python/*.DAT` copies: FA00 99451, FA01 88075, FA02 64016, FA03 64018, PL01 768 bytes).
JP00 is *code*: a 31 KB older build (Aug 1992) of the game whose offsets 0/4/8/C are
`call X; retf` stubs — the far pointers GAME.EXE's entry calls through `[cs:8]`/`[cs:C]`.
JP00:0x2436 is the same anim runner as GAME.EXE 0x2750 (table at 0x3A62 there), so the
entry sequence `[cs:8](2) [cs:C](0) [cs:8](0) [cs:C](1) [cs:8](0) [cs:C](2) [cs:8](0)
[cs:8](3)` is confirmed: **title, level 1, thumbs-up, level 2, thumbs-up, level 3,
thumbs-up, credits, exit**. Not kept in the repo (it is code, not data).

**FA format (0x285D).** 64000-byte linear 320x200 base image, then delta frames. Op byte:
bits 7-6 op, bit 5 "count continues in the next byte" (count = low5<<8 | next), bits 4-0
count-1. Ops: 0 skip, 1 literal bytes follow, 2 repeat the previous screen byte, 3 copy
from the base image. `FF FF` ends a frame, a second `FF FF` ends the file. The stream
pointer is a far pointer normalised every 32 KB (0x28CF/0x28F0) — linear in Python.
Decoded: FA00 = Joe thumbs-up, 15 frames; FA01 = the Grim Reaper, eyes light up, 14 frames;
FA02 = "Jet Pack Joe Demo / Version 1.0" title card, 2 identical frames; FA03 = Development
Team credits (Joe Lowe, Nathan Lowe, Mark Loertscher, Jerry Hayward), 2 frames.

**Runner (0x2750, AX = table index DS:0x3D12 {resource, palette, delay}).** Saves the Mode X
page (A800, 32 KB), copies the base image to A000 linear, applies frame 1, fades the palette
in (0x2A24: scale 0..256 step 8, one vsync per step = 33 vsyncs), then loops: wait `delay`
object-counter ticks (1165.2 Hz: 140 / 200 / 3000 / 6000), wait vsync, apply the next frame,
stop when the following word is FFFF; fades out (0x29F2) and restores the page. No key
check — not skippable. Totals: title ≈ 0.47 + 2.6 + 0.47 s, credits ≈ 6 s, thumbs ≈ 2.6 s.

**Level loop exit (0x078B).** `[0x305E]=1` ends the loop (death end 0x0FDB, or beam-out);
carry = captives remain ([0x305F] != 0). Palette fade-out 0x29F2 either way; the level's
first frame fades the palette in (0x075E). Caller 0x02BE: carry → if `[0x2EE]` already set,
restart the level at once; else play anim 1 (reaper), set `[0x2EE]`, reload the level.
**There are no lives** — the demo restarts the level for ever. The Python's 3 lives, GAME
OVER and YOU WIN were inventions and are gone. After the credits the original exits to DOS
("We hope you've enjoyed the game." comes from the launcher); the Python shows the title
again and restarts level 1 (a loaded `--level` file restarts itself).

**Level trailer (entry 68, read by 0x0633-0x0654):** captive count → [0x305F]; **timer+1 →
[0x23DA]** (L1 150, L2 400, L3 400 seconds — the Python's TIME_LIMIT=999 was wrong); start
room → [0x23DC]; beam tile → [0x23BF]; then the switch-off list.

**TIME (0x09DE every 0x48D = 1165 ticks).** If [0x23DA] is 0 → call 0x0A38 AX=0; else
decrement, convert, and write the three digits into the status buffer with attribute 0x0A.
**0x0A5E (time has run out):** up to 5 tries: random tile < 0x118 with column <= 17 whose
3x3 block has no foreground tile (DS:0x5D7 is the expanded *foreground* map, one word per
tile — see the object scheduler notes) and whose centre
(tile x+0x17, y+0x11) is clear under shape 0x10; allocate a slot: handler 0x0A38, interval
0x46, counter [DI+0x1C]=15, sound 3. Update draws beam frame `counter` (table DS:0x3389, the
same 3x3 frames as cage disappear / beam-in), spawns a **Ball** (0x15A2 AX=0) at the centre
when the counter is 12, and at 0xFF draws frame 16 (blank) and frees itself. So a ball
beams in every second once TIME hits 000. Python: `TimeoutBeam`, `spawn_timeout_beam`.

**Status bar (0x4745).** 40 words (char, attr) at DS:0x2363, seeded from DS:0x0321
`TIME: 000   JET PACK JOE DEMO   ROOM: 00` with attribute 7 at level start (0x05FD); changed
cells are redrawn at x = col*8, **y = 0xC0 = 192**, through 0x350C using the 8x8 font at
CS:0x31EC (128 pointers, 8 bytes per glyph, **bit 0 is the left pixel**). Attribute 7 =
palette 7 (42,42,42 → grey), TIME digits attribute 0x0A = palette 10 (21,63,21 green; PL12 has
0,63,0). The screen is therefore 200 lines: 192 of play + 8 of bar (the Python used 16).
Python: `STATUS_FONT` (chars 32-127 copied from the binary), `draw_text8`, `draw_status_bar`;
the debug prompts (G room entry, NO ENEMIES) replace the middle 17 characters in yellow.

**Python flow.** `play_cutscene(idx, then)` / `Cutscene` (frozen game underneath, 8-bit
frames with the palette scaled for the fades), `end_level(won)` (fade-out, then thumbs-up →
next level or credits → title → level 1; or reaper once → restart), `fade` state for the
level palette fades. `--no-anims` / `JPJ_ANIMS=0` skips every cutscene (the harness default).
A plain launch opens with the title; `--start` and `--level` launches skip it.
Tests: `tests/test_cutscenes.py` (decoder frame counts, timing, reaper once, thumbs-up →
level 2, level 3 → credits → title → level 1, time-out balls) and `tests/test_status_bar.py`
(200-line screen, string/colours, font bytes vs GAME.EXE, debug prompt). 58 tests pass.

### Room objects on the original tick scheduler (2026-11-03)

Cam asked for the last structural gap: doors, fans, switches, fields, cages, plates, pads and
glow balls stepped once per rendered frame. Now every room object is initialised like its
handler's AX=0 path and stepped by `update_room_objects` (0x06F8) when its time is due;
`draw_objects`/`render_foreground` only show the state the last update wrote.

**EXPAND_MAP 0x032A** lays a room out as: DS:0x357 = 320 background tile words, **DS:0x5D7 =
320 foreground words** (from the 320 fg bytes), DS:0xD57 = 320 collision bytes (word >> 10).
So **0x4B4 writes the foreground map** (table entry: count, then (offset, tile) pairs, a tile
of 0 clears the cell) and **0x4D2 writes the background map, skipping cells whose foreground
word is 0xFF**. The Python's earlier comments had the two swapped; nothing drawn changed
except that vertical fields, glow balls and beams are now foreground overrides (over Joe) and
fans of types 1-2 are foreground while 3-4 are background (0x1D40 → 0x4B4, 0x1DBE → 0x4D2).

| Object | Handler | Interval [DI+8] | First update | Per update |
|---|---|---|---|---|
| Fans 1-4 | 0x1289.. → 0x1D40/0x1DBE | random(0x64)+0x4B = 75..174, per fan | +random(interval) | frame = (frame+1) % 3, 3x3 tiles |
| Door 5 | 0x1C51 | 0x59 = 89 | +random(89) | erase shape 3 at old height, state ±1 (0..14), write shape 3, frame table 0x3599 |
| Switches 6/7 | 0x1305/0x1312 → 0x1B84 | 0x80 = 128 | +random(128) | CHECK shape 4 BL=1; Joe newly present → var 0↔0xFF; fg tile 0xE6/0xFA + (var&1) |
| Fields 8/9, glow 13 | 0x1336/0x131F/0x134D → 0x1E3C | 0x4F = 79 | +random(79) | var off: DRAW_VISUAL once, frame 4 (glow); on: DRAW_VISUAL shape+1 (wipes Joe's marker = the kill), frame = (frame+1)&3 to fg, DRAW_COLLISION shape (7 / 11 / 5) |
| Cage 10 | 0x1364 | 0x7D = 125 | +random(125) | var 0 → free slot, erase shape 13; else write shape 13, **CHECK shape 14 BL=0** (the two columns just OUTSIDE the walls: Joe presses against the cage from outside), hit → var = 0, beam 0x1F18 at the cage, sounds 3+4, next_time += 0x302; frame = (frame+1)&3 force-field tiles 0x3AF5 |
| Beam 0x1F18 (cage, beam-out) | — | 0x46 = 70 | now | frames 0..16 of DS:0x3389; frees the sprite at 12; at the 18th update frees itself and `dec [0x305F]`, 0 → [0x23BA]=1 (level complete) |
| Beam-in 0x1FBF | — | 0x46 | +0x1F4 (500) | frames 15..0 then blank; Joe created at 12 (0xC7E); Joe's first update at +0x410 after the first frame (0x2006) |
| Plates 15/16 | 0x17A0/0x189B | 0xA = 10 | now | counter++; 3 of 4 updates just rewrite shape 18; the 4th erases it, var = (var+1) % 52, table 0x39BF (x, frame, col), frames 0x3995/0x39A9 + trail tile 0x47 in fg rows +1/+3, write shape 18 at the new x |
| Toggle 17 | 0x213C | 0x80 | +random(128) | CHECK shape 4 BL=1; newly present → NOT var1 (and var2); bg tile 0x22C + (var2&1) + 2*(var1&1) |
| Time-out beam 0x0A38 | — | 0x46 | now | (see above) |

Consequences: a door now takes 14 × 89 = 1246 ticks ≈ 1.07 s (was 0.25 s); plates cycle in
52 × 40 = 2080 ticks ≈ 1.8 s (was 3.5 s); fields flicker at 14.7 fps; the beam-in waits 0.43 s
after the room loads and Joe can move from its second-to-last frame; the cage walls vanish
770 ticks after the touch while the beam is still playing, and the captive is counted 1190
ticks after it. Joe is 28 px wide, so the cage's shape-14 columns mean a rescue is Joe
flying/walking into the side of the cage, not standing inside it (the old Python tested a
box overlap). The debug jump (`jump_to_room`) resets Joe's next_time so tests and the G key
are not held by the beam-in wait.

Tests: `tests/test_scheduler.py` (intervals, door 14 × 0x59, fan cadence, plate 40-tick
steps, cage beam cadence and late captive count, beam-in delay and Joe release). The cage
tests' helper `touch_cage` hovers beside a cage at wall height and pushes into it; door
waits in the switch/level tests were lengthened to the real opening time. 64 tests pass.

### Enhanced mode: packs, shield, twin shot, turret (2026-11-03)

Cam asked to make the game better on the enemy/weapon/pack side and chose the starting set
from my list: a pack pickup with two packs (twin shot, shield) and one new enemy (the turret).
None of this is in GAME.EXE. It reaches the game only through two new level-object types, and
`tests/test_enhanced.py::test_original_levels_contain_no_enhanced_objects` checks that no room
of levels 1-3 contains either, so the faithful port plays exactly as before. `--classic` (or
`JPJ_CLASSIC=1`) ignores both types in custom levels too (`JetPackJoe.enhanced`).

- **Type 22 pack** `(tile, kind, var)`: entity `Pack`, interval 0x20, CHECK shape 4 (the
  middle of its tile) for Joe's marker. Present while `switch_state[var] != 0`; taking it
  clears the var, so it does not return on re-entry. One pack at a time (`Player.pack`), lost
  with the Player object on death or level change. kind 1 **TWIN SHOT**: `Player.fire` adds a
  second shot 8 px behind the first on the same path (a stacked pair, 8 px higher, first flew
  over the one-tile turret and then did not match the gun's muzzle animation, so Cam chose the
  same-path version; the 8 px gap is 60 ticks, more than the turret's 32-tick update, so a
  volley counts as two hits, and a test waits for that update before asserting). kind 2 **SHIELD**: `JetPackJoe.shield_save`
  absorbs one death from any cause (`start_death`) and then grants `SHIELD_INVULN` = 1750
  ticks of invulnerability; a crush (`Player._unstick` failing) goes through
  `shield_knockback`, which moves Joe to the nearest clear spot within 40 px or leaves him
  until the overlap clears. Joe flickers while invulnerable; a cyan ring shows the shield.
- **Type 23 turret** `(tile, var, sides)`: entity `Turret`, 16x18 px standing on the bottom of
  its tile (6 px poke above it), collision `SH_TURRET` = a synthetic 8x9 half-res rectangle
  injected into `_SH_CACHE` at index 1000 (SH00.DAT has 258 shapes; shape 2 is a bird-shaped
  diamond, not a block) as type 6 (touching it kills), interval 0x20. It went one tile → two
  tiles (Cam: "make the turret taller" when the stacked twin shot flew over it) → 18 px (Cam:
  "too tall now"). `TURRET_WARMUP` = 2000 ticks after room entry before it may fire, because
  Cam died every time he entered the room with `--start` (Joe lands in its row). Present while `var != 0`; `--no-enemies` / E hides it.
  It fires `TurretShot` (2 px per 12 ticks along its row, no collision bytes of its own) when
  Joe is within `TURRET_RANGE_Y` = 14 px of its row, at least 16 px away horizontally, on an
  allowed side (0 left, 1 right, 2 either) and no wall byte lies on the row between them;
  `TURRET_COOLDOWN` = 1400 ticks between shots, first one no sooner than `TURRET_WARMUP`
  after entry; it never fires while Joe is dead or beaming.
  The bullet kills the original way: `cb_restore` under shape 1 wipes Joe's marker and
  0x0CCC's check finds the hole. A hit is anything but Joe's marker intruding on the turret's
  own bytes (a shot's erase); `TURRET_HP` = 3 hits → `EnemyExplosion`, bytes restored. Like
  the original enemies it comes back when the room is re-entered.
- Graphics are small palette-index pixel maps (`ART`, `build_art` per level palette, EGA
  colours 0-15 are the same in PL11/12/13): two packs, turret (flipped for left, white when
  hit), muzzle flash, bullet. Sounds: `SND_PICKUP` (three rising square-wave notes) and
  `SND_TURRET` (decaying noise) are synthesized into the mixer's 6-bit format and appended to
  the bank as ids 5 and 6; the DS00.DAT samples are untouched.
- Status bar: with a pack held the middle text becomes `PACK: TWIN SHOT` / `PACK: SHIELD` in
  palette 11 (cyan); debug prompts still take precedence.
- Parsing fix found on the way: in LV11 the unused rooms 16-67 share the trailer's entry
  offset, so `load_room_objects` used to give them junk objects of whatever types the trailer
  words happened to spell (4, 17, now 22). Entries at or past 68 and entries aliasing the
  trailer offset now get an empty list.
- Test level room 7 (between 4 and 5): twin-shot pack at col 3, turret on the floor at col 10
  firing both ways (vars 24/25/26, all default ON), shield pack at col 16. Joe either flies
  over the turret or shoots it three times.
- Tests: `tests/test_enhanced.py` (10: originals untouched, room contents, classic flag,
  pickup remembered across re-entry, twin shot count, shield absorbs one ball death then
  breaks, turret fires in-row and its bullet kills, no fire out of row, three hits destroy it,
  status bar slot). `test_level_file.py` covers room 7's reachability; `test_sound.py` expects
  seven samples. 74 tests pass.

Ideas not built yet (from the same list): bounce/charge/homing shots, bombs, afterburner,
hover, phase, cage remote, freeze, time cell; crawler, seeker, splitter, armoured, thief,
jailer, bosses; generators that react to the timer or can be destroyed; score.

### Shots parked in the next room (2026-11-03)

Cam: a shot fired into the next room still appeared there ~10 s later. Verified in GAME.EXE
that this is the original's behaviour: the shot handler's ROOM_TRANSITION call (0x1095, carry
set) stores the new room and wrapped position and jumps to its HIDE path (dormant); the main
loop 0x06F8 activates (AX=1) any dormant slot in Joe's room whose next_time has passed, so it
resumes from the edge; and the once-per-second TIME tick 0x0A13 destroys (AX=5) dormant
slots with counter - next_time ≥ 0x1B58 (7000 ticks), so the window is 6-7 s (10 s is
probably frame-rate drift: game time advances per rendered frame). Changes:
- The stale sweep now runs from the per-second tick (`purge_dormant`), as in the original,
  instead of every frame in `wake_dormant`.
- Enhanced mode (`JetPackJoe.enhanced`): `catch_up` runs a woken shot through the updates it
  missed, as a transit clone so no stale explosion shows; it ends up where it would be, which
  after a second or two means gone. `--classic` keeps the original's resume-from-the-edge.
- Tests: `test_enhanced.py::test_parked_shot_is_caught_up_when_joe_follows` and
  `test_classic_mode_resumes_the_parked_shot_like_the_original`; `test_follow.py`'s sweep
  test now checks the once-per-second granularity.

### Charge shot, destructible generators, splitter ball (2026-11-03, enhanced only)

Cam picked these from the ideas list: "the charge shot plus destructible generators, since it
gives the packs a real purpose ... after that the splitter ball, which reuses the ball handler".
- **Charge pack** (`PACK_CHARGE = 3`, pack kind 3, status bar "PACK: CHARGE SHOT"). Pressing fire
  still fires the ordinary shot at once; holding it no longer auto-repeats (classic keeps the
  0xC8-tick repeat) but charges (`Player.charging` = tick of the press); letting go after
  `CHARGE_TICKS` (1400, ~1.2 s) fires a `ChargedShot` (`Player.fire_charged`, SND_CHARGE = 7, a
  synthesized falling tone). While charging a glow grows at the muzzle and flares white when full.
- **ChargedShot**: 10x8 bolt (`SH_CHARGE` 1001, art "bolt"/"bolt_hot"), mobile, 2 px per 12 ticks.
  Before its collision check it tests rectangle overlap with every live `Generator` (2x2 tile
  block, `Generator.rect()`) and `Turret` (16x18): a generator is wrecked, a turret dies outright
  (`Turret.die`). Then `cb_check(SH_CHARGE)`: type-6 bytes are restored from the backup (the ball,
  bird or orb explodes on its own next self-check) and it flies on; a sentry's wall bytes kill the
  sentry; only a real wall stops it, with the wall explosion. Generators are NOT in the collision
  bitmap (their tiles have no collision), hence the geometric test.
- **Wrecked generators**: `Generator.wreck(g)` adds `(room, tile)` to `JetPackJoe.destroyed`,
  plays an `EnemyExplosion` over the block and spawns a `DeadGenerator` (rubble art "wreck",
  32x24, generated by `wreck_rows()`), which `enter_room` spawns in place of the generator on
  every later visit. `set_level` clears `destroyed` only when the level index changes, so a
  death (level restart) keeps the wrecks; a new level starts clean.
- **Ball handler parametrised**: `Ball.SHAPE/RING/SPAWN_SHAPE` (16/17/2) replace the literals,
  `can_spawn` is a classmethod, `BallGen.BALL/REFILL` pick the ball class. No behaviour change for
  the originals (`test_enemies` unchanged).
- **BigBall(Ball)**: `SH_BIGBALL` 1002 (shape 16 at 1.5x: 119 cells, 26x22 px) and `SH_BIGRING`
  1003 from `shape_ring()`, which reproduces shape 17 exactly from shape 16 (asserted in a test).
  Interval 24 (slower). Sprite drawn at 1.5x (cached scaled surfaces). `explode` runs the ball's
  and then, if it was live in Joe's room, spawns two `Ball`s at x ± 14 where `Ball.can_spawn`.
- **SplitterGen(BallGen)**: object type 24 `(tile)`, `OBJ_PARAMS[24] = 1`, BALL = BigBall,
  REFILL = 12, same tile animation. Gated by `enhanced` and `enemies_enabled`.
- Test level: room 3 gains the charge pack (type 22 kind 3, var 27) at tile (6,13) and a splitter
  generator at (9,4). Tests: eight new ones in `test_enhanced.py` (hold/no-repeat, wreck persists
  through re-entry and set_level, ordinary shots don't wreck, pierce, turret dies, big ball splits,
  splitter spawns, classic unaffected). Suite: 90 pass.
- A charged shot that pops a big ball also wipes the two small balls it splits into (they
  spawn in the bolt's path): an ordinary shot splits it, a charged shot ends it (tested).
- Gotcha for tests: `SplitterGen` *is* a `BallGen` (`isinstance`), filter with `type(e) is`.

### Turret bullets kill sentries (2026-11-03, enhanced only)

Cam: "I would like the turret bullet to kill the sentry if it is in the path of the bullet."
The sentry's footprint is written as CT_WALL (0x23EA), identical to the room's walls, so the
bullet cannot tell it from a wall through the collision bitmap. `TurretShot.update` therefore
checks, when its shape-1 cells hit CT_WALL, whether a live, visible `Sentry` in the room has a
footprint cell (`Sentry.cells()`, shape 19 + facing at its position) in common with the
bullet's cells, and calls `Sentry.kill(g)`: hide (restore its footprint), alive = False, and
an `EnemyExplosion` over sprite 39 + facing (which plays SND_EXPLOSION). The variable stays 0,
so the sentry does not come back when Joe re-enters the room; a sentry killed this way is gone
for the level. Joe's own shots still cannot hurt it (faithful to GAME.EXE: the sentry never
checks for intrusions). Tests: `test_turret_bullet_kills_a_sentry_in_its_path`,
`test_turret_bullet_still_kills_joe_when_a_sentry_is_elsewhere`. 81 tests pass.

### Sentry keeps its slot; turret bullets cross rooms (2026-11-03)

Cam asked whether the sentry in test-level room 4 should follow him out, and then noticed it
reset to its tile when he stepped out and straight back. Decoded from the handler 0x22EF:
- Init 0x2317: `call 0x7be` (slot), reads the tile and the variable; if `[var+0x3067]` is 0 the
  init bails out (0x2374), else it **clears the variable** (0x2335), stores the id in [DI+0x1F],
  sets slot state **2** (0x2343, not 3: it is never cloned), interval 0x1B, handler 0x22EF,
  facing 1, then runs AX=1.
- No `call 0x521` anywhere in 0x22EF-0x2525: the sentry never leaves its room.
- AX=3 HIDE (0x237B, run by the room change for every non-mobile object): frees its three
  sprites, DRAW_VISUAL shape 0x13 at its position, visible = 0 — **the slot stays** (state 2).
  So the main loop (0x06F8: state ≠ 0, Joe's room, next_time passed, visible ≠ 1 → AX=1) wakes
  it where it was when Joe comes back, and the per-second sweep 0x0A13 destroys it after
  0x1B58 ticks.
- AX=5 DESTROY (0x23A0): `[var+0x3067] = 0xFF`, state 0 — the variable comes back, so the next
  visit after the sweep spawns a fresh sentry at its tile. The clearing at init is what stops a
  second sentry spawning while the first waits dormant.
- AX=1 ACTIVATE (0x23B0): allocates sprites 0x32/0x32/0x27 (sorted), DRAW_COLLISION shape
  0x13 + facing as type 1, visible = 1.
Port: `Entity.keeps_slot` (+ `hide`/`destroy` hooks); `carry_mobiles` hides keeps_slot
objects into `dormant` instead of dropping them; `purge_dormant` calls `destroy`; `Sentry`
takes its variable, clears it on spawn, restores it on destroy, and `jump_to_room` (debug)
destroys any sentry it drops so the variable is not lost. On wake the port catches up at most
8 updates per frame where the original runs the whole backlog in one burst.

Turret bullets (`TurretShot`) are now `mobile` like Joe's shots: they cross edges via
`cross`, are cloned on a room change and follow Joe (Cam: "the turret bullet doesn't seem to
follow me into the next room"); the catch-up on wake applies to them too. Tests:
`test_enhanced.py::test_turret_bullet_follows_joe_into_the_next_room` and
`test_sentry_waits_where_it_was_and_respawns_after_the_sweep`. 79 tests pass.
