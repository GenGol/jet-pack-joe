# jpjoe-editor-levels

Unpacked from `jpjoe-20261104T072514Z-1-001.zip` (Cam, 2026-11-04). **This is not the 1992
GAME.EXE game.** It is a separate "Jetpack Joe!" written in C with DJGPP and the Allegro
library around 2001-2002 by someone whose home directory was `/home/daniel` (the datafile
properties say `/home/daniel/graphics/joe/...`, dated 12-27-2001 to 1-05-2002). The zip's
files are all dated 2011-11-29.

| file | what it is |
|---|---|
| `joe.exe` | the game, DJGPP/go32 COFF, UPX-packed (unpacks to 596 KB) |
| `editor.exe` | its level editor, same build, mouse driven ("Save As...", "Load File...") |
| `joe.dat` | Allegro datafile: two fonts and three samples, **no graphics** |
| `joe1.lev` .. `joe9.lev` | Allegro packfiles (LZSS "slh!"), 37 501 bytes each unpacked |

The game's strings describe it: "Collect All To Pass The Level", "Collect To Gain Jetpack",
"Don't collect jetpacks if you don't need them", "Try to 'Walk' in the air to reduce fuel
usage", keys Up = jetpack (or jump), Space = jump, J = unstick. Fuel, jumping and a collect-
everything goal: a different design from the 1992 game's rescue-the-captives rooms.

**Missing:** `joe.exe` loads `screen.bmp`, which is not in the zip, and nothing in the zip holds
the tile graphics, so the game cannot be run or its levels drawn as intended from these files.

## Level format (decoded far enough to read the maps)

`python3 python/tools/allegro_unpack.py joeN.lev` writes `unpacked/joeN.lev.raw`.

- 10 rooms x 25 rows x 50 columns x 3 bytes = 37 500 bytes, plus one trailing byte (0 or 9).
- Each tile is `(a, b, c)`: `(a, b)` looks like a column/row into a tile sheet (values up to
  (30, 16), so a sheet of at least 31 x 17 tiles), `c` a tile class. `(0, 0, 9)` is empty.
  `(9, 7, 4)` and `(9, 7, 8)` form the solid borders and walls, `(1, 6, 3)` / `(10, 6, 2)` are
  the sparse pickups (the collectibles and jetpacks of the help text), `(9, 15, c)` with
  c = 1, 2, 5, 6, 7, 8 are special blocks, and level 9 has runs of `(0, 13..15, 19..31)` that
  look like an animated or counting object.
- Levels 1-6 have 2-5 rooms with content; 7-9 are nearly empty (unfinished).

The 1992 game's rooms are 20 x 16 tiles of 16 x 12 px on one screen; these are 50 x 25 and
would need scrolling or a 640 x 400 mode (both exes carry Allegro's "Xtended mode only
supports 640x400" driver text). Nothing here converts to the port's level format without the
missing tile sheet.
