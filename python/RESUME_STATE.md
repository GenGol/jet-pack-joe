# Jet Pack Joe — Reverse Engineering State Document
# Last updated: 2026-04-20 (session 4)
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
- Display list update: 0x02DC (calls INT 62h DX=4)
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
| 4 | 0x42B3 | Render/update display list |
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

**Decision logic:**
- Joe NOT in trigger → arm (unless on boundary → disarm)
- Joe IN trigger AND NOT on boundary AND armed → TELEPORT
- Joe IN trigger AND on boundary → skip (at edge, not centered)

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

`GAME.EXE N` where N is:
- 0 = No sound (default)
- 1 = Internal PC speaker
- 2 = Covox Speech Thing
- 3 = Sound Master II

No command-line level select exists. Levels play in fixed sequence.

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
