#!/usr/bin/env python3
"""Generate a sprite sheet with uniform grid cells, centered sprites, and index labels."""
import os, struct, sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

BASE = os.path.dirname(os.path.abspath(__file__))

def load_raw(fn):
    with open(os.path.join(BASE, fn), 'rb') as f:
        return f.read()

def load_palette(fn):
    raw = load_raw(fn)
    return [(min(255, raw[i*3]*4), min(255, raw[i*3+1]*4), min(255, raw[i*3+2]*4)) for i in range(256)]

def decode_sprites(sp_data, pal):
    first_off = struct.unpack_from('<H', sp_data, 0)[0]
    num = first_off // 2
    offsets = [struct.unpack_from('<H', sp_data, i*2)[0] for i in range(num)]
    sprites = []
    for idx in range(num):
        start = offsets[idx]
        end = offsets[idx+1] if idx+1 < num else len(sp_data)
        if start + 4 > len(sp_data):
            sprites.append({"surf": pygame.Surface((1,1), pygame.SRCALPHA), "w": 1, "h": 1})
            continue
        x_off, y_off, x_end, y_end = struct.unpack_from('4b', sp_data, start)
        w, h = x_end - x_off + 1, y_end - y_off + 1
        surf = pygame.Surface((max(1,w), max(1,h)), pygame.SRCALPHA)
        pos = start + 4
        cur_x, cur_y = 0, 0
        try:
            while pos < end - 1:
                if sp_data[pos] == 0 and sp_data[pos+1] == 0: break
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
                    if sp_data[pos] == 0 and sp_data[pos+1] == 0: pos += 2; break
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
        sprites.append({"surf": surf, "w": max(1,w), "h": max(1,h)})
    return sprites

def main():
    pygame.init()
    screen = pygame.display.set_mode((1, 1))
    pal = load_palette('PL11.DAT')
    sprites = decode_sprites(load_raw('SP00.DAT'), pal)

    # Find max sprite dimensions
    max_w = max(s["w"] for s in sprites)
    max_h = max(s["h"] for s in sprites)
    print(f"{len(sprites)} sprites, largest: {max_w}x{max_h}")

    # Cell size: largest sprite + padding for label + border
    label_h = 18
    pad = 6
    cell_w = max_w + pad * 2
    cell_h = max_h + pad * 2 + label_h

    # Grid layout
    cols = 10
    rows = (len(sprites) + cols - 1) // cols

    sheet_w = cols * cell_w
    sheet_h = rows * cell_h
    sheet = pygame.Surface((sheet_w, sheet_h), depth=24)
    sheet.fill((32, 32, 32))

    font = pygame.font.SysFont("monospace", 14, bold=True)

    for idx, sp in enumerate(sprites):
        col = idx % cols
        row = idx // cols
        cx = col * cell_w
        cy = row * cell_h

        # Cell border
        pygame.draw.rect(sheet, (64, 64, 64), (cx, cy, cell_w, cell_h), 1)

        # Center sprite in cell (below label)
        sx = cx + (cell_w - sp["w"]) // 2
        sy = cy + label_h + (cell_h - label_h - sp["h"]) // 2
        sheet.blit(sp["surf"], (sx, sy))

        # Index label at top of cell
        label = font.render(str(idx), True, (200, 200, 0))
        lx = cx + (cell_w - label.get_width()) // 2
        sheet.blit(label, (lx, cy + 2))

    out = os.path.join(BASE, 'sprite_sheet.png')
    pygame.image.save(sheet, out)
    print(f"Saved: {out} ({sheet_w}x{sheet_h})")
    pygame.quit()

if __name__ == '__main__':
    main()
