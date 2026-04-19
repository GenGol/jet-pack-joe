# Joe Lowe's DOS Assembly Game Collection — Documentation

**Author:** Joe Lowe  
**Era:** Early 1990s (1991–1993)  
**Platform:** IBM PC / DOS, VGA graphics  
**Assembler:** Turbo Assembler (TASM) 1.0 by Borland  
**Language:** x86 Assembly (8086/80186/80286)

---

## Overview

This project contains **three complete games** and a collection of **utility/tool programs**, all written in x86 assembly language targeting DOS with VGA graphics. The games are:

1. **Missile Command** (`MIS/`) — A clone of the classic Atari arcade game
2. **Light Cycles** (`MIS/LC.ASM`) — A two-player Tron-style light cycle game
3. **JET** (the main game, `NEWER/` + root) — A side-scrolling action game with sprites, tile maps, and level data

Additionally, there are several **development tools and utilities**:

4. **VGA Mode Explorer** (`MODE/MODE.ASM`) — A VGA register editor/viewer
5. **Big Mode Graphics Engine** (`NEWER/BIGMODE.ASM`) — A custom 320×240 VGA mode with 512-pixel-wide virtual screen
6. **Multi-Edit Automation** (`NEWER/MES.ASM`) — A script-driven keystroke injector for automating the Multi-Edit text editor
7. **Keyboard Buffer Extender** (`NEWER/KEY.ASM`, `NEWER/KEYX.ASM`) — DOS device drivers to extend the keyboard buffer

---

## Directory Structure

```
Joe/
├── GAME.EXE              # Main game executable (JET)
├── JET.EXE               # JET game launcher
├── JET.RSC               # JET resource file (sprites, maps, palettes — 171KB)
├── JET_LEVEL1.RSC         # Level 1 resource pack
├── LIST.BAT              # Lists contents of c:\joe\lib
│
├── NEWER/                # Latest source code (primary development directory)
│   ├── BIGMODE.ASM       # VGA 320×240 mode-X graphics engine
│   ├── BIG.ASM           # Test program for BIGMODE
│   ├── RAND.ASM          # Random number generator
│   ├── MES.ASM           # Multi-Edit automation/scripting tool
│   ├── KEY.ASM           # Keyboard buffer extender (device driver, enhanced)
│   ├── KEYX.ASM          # Keyboard buffer extender (device driver, simple)
│   ├── CMDLN.ASM         # Command-line argument parser
│   ├── STRING.ASM        # String utility library
│   ├── MAKEFILE           # Build file for BIG.EXE (Turbo Assembler + Linker)
│   ├── M.BAT            # Runs "make big.exe"
│   ├── STATUS.ME         # Multi-Edit session state file
│   ├── JET.RSC / JET_NEWER.RSC  # Game resource files
│   └── SBINFO.ZIP        # Sound Blaster documentation
│
├── MIS/                  # Missile Command + Light Cycles
│   ├── MIS.ASM           # Missile Command — main game
│   ├── STARTS.ASM        # Missile Command — task startup routines (included by MIS.ASM)
│   ├── MAINT.ASM         # Missile Command — game object update/maintenance (included by MIS.ASM)
│   ├── MOUSE.ASM         # Missile Command — mouse/cursor handling (included by MIS.ASM)
│   ├── SHAPES.ASM        # Missile Command — city and missile sprite data (included by MIS.ASM)
│   ├── LC.ASM            # Light Cycles — complete Tron-style game
│   ├── EGRAPH.LIB        # External graphics library (binary, no source)
│   ├── LISTFILE.LST      # Library symbol listing for EGRAPH.LIB
│   ├── TEMP/             # Working copy (duplicate)
│   └── BACKUP/           # Backup copy (duplicate)
│
├── MODE/                 # VGA register exploration tool
│   └── MODE.ASM          # Interactive VGA register viewer/editor
│
└── DRAW/                 # Game asset files (art, levels, tools)
    ├── *.SCR             # Raw 320×200 screen images (64000 bytes each)
    ├── *.SPR             # Sprite data files
    ├── *.PAL             # 256-color palette files (768 bytes = 256 × RGB)
    ├── *.BLK             # Tile/block data (130KB)
    ├── *.MAP             # Level map data (65KB)
    ├── *.LEV             # Level configuration data
    ├── *.COL             # Collision data
    ├── *.SHD             # Shadow data
    ├── *.ANM             # Animation sequences
    ├── *.V8              # Sound samples (8-bit, various)
    ├── *.CRM             # Compressed resource files (made by CRAM.EXE)
    ├── EDIT.EXE          # Level/sprite editor
    ├── CRAM.EXE          # Resource compression tool
    ├── UNCRAM.EXE        # Resource decompression tool
    ├── BLD.EXE           # Resource builder
    ├── BLDARC.EXE        # Archive builder
    ├── SAMP.EXE          # Sound sample player
    ├── NED.EXE           # Another editor (possibly "New Editor")
    ├── LEV.EXE           # Level tool
    ├── CONV.EXE          # Format converter
    └── LIST              # Sound effect file listing
```

---

## Detailed Source Code Analysis

### 1. Missile Command (`MIS/MIS.ASM` + includes)

A faithful recreation of the classic Atari Missile Command arcade game.

**Architecture:** Large memory model, 80286 instructions, uses external `EGRAPH.LIB` graphics library.

**Video Mode:** VGA 640×480 16-color (mode 12h)

**Game Features:**
- Mouse-controlled crosshair targeting
- Two missile launch bases (left at x=205, right at x=434)
- 6 cities to defend, drawn with detailed 8×8 pixel art
- 20 progressive difficulty waves with configurable warhead counts, speeds, and timing
- Warhead splitting at a configurable altitude ("split deck")
- Expanding/contracting explosion clouds (circle-based)
- Score tracking with bonus city awards
- Sound effects via PC speaker (tones, clicks)
- Task-based game loop (cooperative multitasking scheduler)

**Task System:**
The game uses a sophisticated cooperative task scheduler with up to 64 tasks, each having 32 bytes of state:
- `time` — next execution time
- `skip` — ticks between executions  
- `kind` — task type identifier
- `address` — procedure to call
- Fields 8–30 vary by task type (position, velocity, color, etc.)

**Task Types:**
| Kind | Name | Purpose |
|------|------|---------|
| 0 | input | Player input handling (mouse + keyboard) |
| 0 | wavehandle | Spawns warheads according to wave script |
| 1 | upmissile | Player missile moving upward |
| 1 | warhead | Enemy warhead moving downward |
| 1 | tracer | Trail eraser following missile path |
| 4 | cloud | Expanding/contracting explosion circle |
| 5 | wartrace | Warhead trail eraser |
| 7 | sound | PC speaker sound effect |

**Wave Data Format:**
Each wave is defined as: `warhead_speed, delay, count, delay, count, ... 0, -1`
- First word: warhead movement speed
- Pairs of (delay_ticks, warhead_count) define spawn timing
- `0, -1` marks end of wave

**Key Procedures (MIS.ASM):**
- `main` → `init` → `body` → `game` → `wave` → `setup`/`timeloop`/`finish`
- `input` — reads mouse motion and button state, fires missiles
- `doscreen` — draws ground, cities, launch bases
- `upscore` — updates and redraws score display
- `drawcity` — draws a city from 8 component character blocks
- `bonuscity` — awards bonus cities at score thresholds

**Key Procedures (STARTS.ASM):**
- `startupmiss` — creates a player missile task
- `startwarhead` — creates an enemy warhead task  
- `startcloud` — creates an explosion cloud task
- `starttracer` — creates a trail-erasing task
- `startsound` — creates a sound effect task
- `nukecity` — destroys a city with 3 explosion clouds
- `endtask` — removes a task by swapping with last task

**Key Procedures (MAINT.ASM):**
- `cloud` — expands then contracts a circle
- `upmissile` — Bresenham line-drawing for upward missiles
- `warhead` — Bresenham line-drawing for downward warheads, with splitting and collision detection
- `wartrace` — erases warhead trails
- `tracer` — erases missile trails
- `sound` — toggles PC speaker for sound effects

**Key Procedures (MOUSE.ASM):**
- `mothand` — reads mouse motion counters, updates cursor position
- `getbuttons` — reads mouse buttons + keyboard shift keys
- `mouseon`/`mouseoff` — draws/erases crosshair cursor
- `crosson` — draws an X at the target point

**External Library (EGRAPH.LIB) — Missing Source:**
From `LISTFILE.LST`, the library provides:
| Module | Symbols | Purpose |
|--------|---------|---------|
| CHAR | `DRAWCHAR`, `STRING`, `INTTODEC`, `LOAD8X8`, `CHAR` | Text/character rendering |
| CIRC | `CIRCLE`, `ACIRCLE`, `OCIRCLE`, `XCIRCLE` | Circle drawing (normal, AND, OR, XOR) |
| CLRSCR | `CLEARSCREEN` | Screen clearing |
| GET | `GET` | Read pixel color |
| PLOT | `PLOT` | Write pixel |
| LINE | `LINE`, `ALINE`, `OLINE`, `XLINE` | Line drawing (normal, AND, OR, XOR) |
| RAND | `RANDOM`, `SEEDRAND` | Random numbers |
| TIMER | `TIMER`, `TIMERON`, `TIMEROFF` | Timer tick counter |

---

### 2. Light Cycles (`MIS/LC.ASM`)

A two-player Tron light cycle game.

**Video Mode:** VGA 640×480 16-color (mode 12h)

**Gameplay:**
- Player 1: Z (turn left), X (turn right) — starts green (color 10)
- Player 2: Arrow keys (left/right) — starts red (color 12)
- Each player leaves a colored trail
- Collision with any non-black pixel = death
- Explosion animation on death (expanding circles)
- "Play again?" prompt after each round

**Key Procedures:**
- `setup` — clears screen, draws border, places players
- `mainloop` — reads keyboard, moves both players each tick, checks collisions
- `explode` — draws expanding circles at crash sites in 3 phases (color → trail → erase)
- `delay` — timer-based wait

**Uses same EGRAPH.LIB** as Missile Command.

---

### 3. JET Game (Main Game — `NEWER/` + root directory)

The main game project. While the core game engine source is not present in the ASM files (it was likely compiled separately or is in the .EXE/.RSC files), the supporting infrastructure is here:

**Resource Files:**
- `JET.RSC` / `JET_LEVEL1.RSC` — 171KB resource archives containing:
  - Sprite data (`DATA.SPR`, `SPRITES1.SPR`)
  - Tile blocks (`DATA.BLK` — 130KB, likely 16×16 tiles)
  - Level maps (`DATA.MAP` — 65KB)
  - Palettes (`DATA.PAL` — 768 bytes)
  - Level config (`DATA.LEV`)
  - Collision data (`DATA.COL`)
  - Shadow data (`DATA.SHD`)
- Sound effects (`.V8` files): explosions, missile sounds, "help me", transporter, "thank you"
- Screen images: intro screens, sprite sheets, palette editor screens
- Animations: door open/close sequences

**The DRAW/ directory** contains the complete asset pipeline:
- `EDIT.EXE` — Level/sprite editor (36KB)
- `CRAM.EXE` — Compresses data files into `.CRM` archives
- `UNCRAM.EXE` — Decompresses `.CRM` files
- `BLD.EXE` / `BLDARC.EXE` — Resource builders
- Batch files automate compression: `CPAL.BAT`, `CMAP.BAT`, `CBLK.BAT`, `CLEV.BAT`

---

### 4. Big Mode VGA Engine (`NEWER/BIGMODE.ASM`)

A custom VGA graphics mode providing **320×240 resolution with a 512-pixel-wide virtual screen** using VGA Mode X techniques.

**How it works:**
1. Sets standard mode 13h to initialize the palette
2. Switches to mode 12h (640×480 16-color) via BIOS
3. Reprograms VGA registers to get 256-color mode with:
   - 2-scanline-high pixels (max scan line = 1)
   - 256-color graphics mode bit set
   - 128 bytes per row (512 pixels / 4 planes)
   - Extended vertical retrace for flicker-free palette loading

**Key Features:**
- **Planar pixel addressing** — 4 VGA planes, pixel X maps to plane (X mod 4), offset (X/4 + Y×128)
- **Hardware scrolling** — `move_window` sets CRTC start address and pixel panning registers
- **Interrupt-driven retrace sync** — Hooks INT 08h (timer), calibrates to vertical retrace timing
- **Palette animation** — Loads palette data during vertical retrace via `set_palette`
- **Drawing primitives** — `plot_pixel`, `circle`, `elipse`, `clear_video`

**Procedures:**
| Procedure | Purpose |
|-----------|---------|
| `_InitBigMode` / `init_big_mode` | Enter 320×240×256 mode |
| `_TermBigMode` / `term_big_mode` | Restore original video mode |
| `move_window` | Set display scroll position |
| `clear_video` | Fill all video memory |
| `plot_pixel` | Plot single pixel (planar) |
| `offset_mask` | Calculate video offset and plane mask |
| `circle` | Draw circle (optimized, direct video writes) |
| `elipse` | Draw ellipse |
| `set_palette` | Queue palette load for next retrace |
| `get_palette` | Read current palette |
| `init_retrace` | Install retrace interrupt handler |
| `term_retrace` | Remove retrace interrupt handler |
| `handler_08h` | Timer ISR — syncs to retrace, loads palette, scrolls |

---

### 5. VGA Mode Explorer (`MODE/MODE.ASM`)

An interactive tool for examining and modifying VGA register values in real-time.

**Displays 43 VGA registers across 4 groups:**
1. Miscellaneous Output Register (1 register)
2. Sequencer Registers 1–4 (4 registers)
3. CRTC Registers 0–18h (25 registers)
4. Graphics Controller Registers 0–8 (9 registers)
5. Attribute Controller Registers 10h–13h (4 registers)

**Shows three columns:** reference mode 0 values, reference mode 1 values, and current modifiable values.

**Controls:**
- Arrow keys: navigate registers
- 0–9, A–F: enter hex values
- E/D: increment/decrement current register
- Enter: apply changes / switch modes
- Esc: exit

---

### 6. Utility Libraries

**RAND.ASM** — Linear congruential random number generator
- `seed_rand(ax)` — seed with value or system timer if ax=0
- `random(ax)` — returns random number in range [0, ax)
- Uses 32-bit multiply with evolving multiplier

**STRING.ASM** — String manipulation library
- `string_end` — find end of string, return length
- `string_copy` — copy string
- `string_cut` — copy N characters
- `string_paste` — paste string into another
- `string_out` — write string to stdout
- `int_to_string` — convert integer to 5-digit ASCII
- `string_to_int` — convert ASCII digits to integer

**CMDLN.ASM** — Command-line argument parser
- `cmd_arg` — parses next whitespace-delimited argument from PSP command tail

**KEY.ASM** — Enhanced keyboard buffer extender (DOS device driver)
- Extends keyboard buffer to 128 entries
- Intercepts INT 16h function 3 (blocks typematic rate changes)
- Accelerates key repeat to maximum speed
- Credited to "George Tzeng"

**KEYX.ASM** — Simple keyboard buffer extender (DOS device driver)
- Extends keyboard buffer to 129 entries
- Simpler version without INT 16h interception
- Also credited to "George Tzeng"

**MES.ASM** — Multi-Edit automation tool
- Spawns Multi-Edit (`c:\me\me.exe`) as a child process
- Hooks INT 08h timer to inject scripted keystrokes
- Script language supports: wait for DOS idle, wait for empty keyboard buffer, set timer speed, push/pop BIOS timer, push keystrokes
- Used to automate editor configuration (setting colors, tab width, etc.)

---

## The Missing Graphics Library (EGRAPH.LIB)

The binary `EGRAPH.LIB` is present but its **source code is missing**. Based on the symbol listing and usage patterns, it provides:

1. **Pixel operations** — `PLOT` (write pixel), `GET` (read pixel) for VGA mode 12h (640×480, 16-color, planar)
2. **Line drawing** — `LINE` (normal), `ALINE` (AND), `OLINE` (OR), `XLINE` (XOR) — likely Bresenham's algorithm
3. **Circle drawing** — `CIRCLE`, `ACIRCLE`, `OCIRCLE`, `XCIRCLE` — with boolean operations
4. **Screen clearing** — `CLEARSCREEN` with color and count parameters
5. **Character rendering** — `LOAD8X8` (load BIOS 8×8 font), `DRAWCHAR` (draw character), `STRING` (draw string), `CHAR`
6. **Number conversion** — `INTTODEC` (integer to decimal string)
7. **Timer** — `TIMERON`/`TIMEROFF` (install/remove timer ISR), `TIMER` (tick counter variable)
8. **Random numbers** — `RANDOM`, `SEEDRAND`

The calling conventions (from usage in MIS.ASM and LC.ASM):
- `plot(ax=color, cx=x, dx=y)` — plot pixel
- `get(cx=x, dx=y)` → `ax=color` — read pixel
- `line(ax=color, cx=x1, dx=y1, si=x2, di=y2)` — draw line
- `circle(ax=color, bx=radius, cx=x, dx=y)` — draw circle
- `clearscreen(ax=color, cx=count, di=start_offset)` — clear screen
- `drawchar(ax=color, bx=height, cx=x, dx=y, si=sprite_ptr)` — draw character/sprite
- `string(ax=color, bx=ptr_to_string, cx=x, dx=y)` — draw text string
- `inttodec(ax=value, bx=buffer_ptr)` — convert int to decimal string

---

## Build System

**Assembler:** Turbo Assembler (TASM) 1.0  
**Linker:** Turbo Link (TLINK)

**Missile Command build:**
```
tasm /ml mis.asm        (includes starts.asm, maint.asm, mouse.asm, shapes.asm)
tlink mis,,,egraph.lib
```

**Light Cycles build:**
```
tasm /ml lc.asm
tlink lc,,,egraph.lib
```

**Big Mode test build (from MAKEFILE):**
```
ta rand          → rand.obj
ta bigmode       → bigmode.obj  
ta big           → big.obj
tl big+bigmode+rand → big.exe
```

**Asset pipeline:**
```
cram data.pal pl11.crm     # Compress palette
cram data.map mp11.crm     # Compress map
cram data.blk bk00.crm     # Compress tile blocks
cram data.lev lv11.crm     # Compress level data
```

---

## Technical Notes

- All games target **real-mode DOS** with direct hardware access (VGA registers, PIC, PIT, PC speaker)
- The Missile Command game uses **VGA mode 12h** (640×480, 16 colors, 4 bit planes)
- The JET game engine uses a **custom Mode X variant** (320×240, 256 colors, planar)
- Mouse input uses **INT 33h** (Microsoft mouse driver)
- Sound is **PC speaker only** (no Sound Blaster support in the code, though SBINFO.ZIP suggests it was planned)
- The `.SCR` files are raw 320×200 framebuffer dumps (64000 bytes = 320 × 200)
- The `.V8` files appear to be 8-bit unsigned PCM audio samples
- The `.CRM` files are compressed using the custom CRAM tool


---

## JET PACK JOE — Reverse-Engineered Data Formats

The main game's binary data was reverse-engineered from the raw asset files and confirmed
by disassembling GAME.EXE routines (EXPAND_MAP, BLOCK_TO_XY, DRAW_SPRITE).

**Tile Format (`BK00.DAT` / `DATA.BLK`):**
- 682 tiles, 192 bytes each (16 pixels wide × 12 pixels tall)
- Stored as linear 8-bit palette-indexed pixels (1 byte per pixel)
- Row-major order: 16 bytes per row, 12 rows per tile
- Max tile index used in level 1 map: 681 (fits exactly)
- Note: earlier analysis incorrectly assumed 16×8 tiles (1023 tiles at 128 bytes).
  The BLOCK_TO_XY routine's `IMUL DX, AX, 12` gives the actual tile height of 12px.

**Map Format (`MP11.DAT` etc. / `DATA.MAP`):**
- 68 rooms per level, 960 bytes per room (65280 / 960 = 68)
- Each room = 320 background tile words (640 bytes) + 320 foreground tile bytes (320 bytes)
- Grid: 20 columns × 16 rows, row-major order
- Visible area: 320×192 pixels (20×16px wide, 16×12px tall) + status bar below
- Each room is a single screen (not paired/stacked rooms)
- Tile word encoding:
  - Bits 0–9: tile index into BK00.DAT (0–681)
  - Bits 10–15: collision/property flags (shifted right 2 in EXPAND_MAP)
  - 0xFFFF = empty/transparent tile
- Foreground layer: tile index 0 and 255 = empty/transparent
- Confirmed visually against dosbox screenshots of rooms 0–4

**Collision Format (`CB00.DAT` / `DATA.COL`):**
- 3072 bytes = 3 × 1024 entries
- 3 sub-maps per tile index (likely top/middle/bottom collision zones)
- Values: 0=passable, 1=solid, 3=special

**Palette Format (`PL11.DAT` etc. / `DATA.PAL`):**
- 768 bytes = 256 colors × 3 (R, G, B)
- VGA 6-bit DAC format (values 0–63, multiply by 4 for 8-bit RGB)
- Each level has its own palette (PL11, PL12, PL13)
- Note: DRAW/DATA.PAL was modified in 2000 and is NOT the correct game palette

**Level Format (`LV11.DAT` etc. / `DATA.LEV`):**
- Offset table: N 16-bit word offsets (N = first_offset / 2)
- Each room entry:
  - 8-byte header: room connectivity (neighbor room IDs, 0xFF = no exit)
  - Object list: sequence of (object_type_word, param1_word, param2_word, ...)
  - Terminated by 0xFFFF
- Level 1 has 17 active rooms (0–16), rooms 17–68 point to shared empty data

**Sprite Format (`SP00.DAT` / `DATA.SPR`):**
- 102 sprites with 16-bit offset table (204 bytes)
- 4-byte header per sprite (all signed bytes): x_off, y_off, x_end, y_end
  - Width = x_end - x_off + 1, Height = y_end - y_off + 1
- Body: vertical column RLE, designed for VGA Mode X rendering
- Decoded from DRAW_SPRITE routine at 0x3236 in GAME.EXE:
  ```
  Repeat until 0x0000 word:
    delta_x (signed byte) — cumulative X adjustment
    delta_y (signed byte) — cumulative Y adjustment
    First column: [draw_count] [pixels...]
    Subsequent: [skip_h] [row_offset_signed] [draw_count] [pixels...]
    Segment end: 0x0000 (two zero bytes)
  ```
- Pixels drawn vertically (MOVSB + ADD DI,79 in Mode X = one pixel per row)
- skip_h advances horizontally (through Mode X planes)
- delta_x, delta_y, and row_offset are all CUMULATIVE
- Sprite catalogue:
  - 0–7: Jet Pack Joe (8 frames, even=left, odd=right, ~32×29 px)
  - 8–19: Projectiles (various sizes/angles)
  - 24–25: Laser beams (red/green vertical)
  - 28–33: Red sentry/UFO (6 animation frames)
  - 35–38: Glow balls (blue/white energy)
  - 39–41: Birds (pink/magenta, 3 frames)
  - 42–48: Explosion/death effects
  - 55–57: Toggle switch states
  - 75–81: Captive characters (kids in different colored outfits)

**RSC Archive Format:**
- Table of contents: 4-byte ASCII name + 4-byte little-endian offset, repeated
- Terminated by null name entry
- All entries are CRAM-compressed (custom LZ77 variant)
- Contains 3 complete levels (lv11/mp11/pl11, lv12/mp12/pl12, lv13/mp13/pl13)

**CRAM Compression:**
- Custom LZ77 sliding-window compression by Joe Lowe
- 5 code types: LITERAL, SAME_LOOK, ONE_MATCH, SHORT_CODE, LONG_CODE
- Used for all RSC archive entries
- Source not available; CRAM.EXE and UNCRAM.EXE tools provided

**Game Objects (from GAME.EXE symbol table):**
- Player: INIT_JET, JET_X, JET_Y, JET_MOMENTUM, JET_DIRECTION, JET_FIRE_FRAME
- Enemies: RED_BIRD, BLUE_BALL, GLOW_BALL, ORB_GENERATOR, BIRD_GENERATOR, BALL_GENERATOR
- Environment: DOOR, TELEPORTER, BEAM_IN, BEAM_OUT, SENSOR_SWITCH, TOGGLE_SWITCH
- Hazards: HORIZ_FIELD, VERTICAL_FIELD, LEFT_PLATE, RIGHT_PLATE, EXPLOSION1, EXPLOSION2
- Animations: THUMBS_UP_ANIM, DEATH_ANIM, TITLE_ANIM, CREDITS_ANIM
- Sound: Internal speaker, Covox Speech Thing, Covox Sound Master II drivers
