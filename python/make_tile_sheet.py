#!/usr/bin/env python3
"""Generate a tile sheet showing all 682 tiles from BK00.DAT with index labels."""
import os, struct
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

BASE = os.path.dirname(os.path.abspath(__file__))

def load_raw(fn):
    with open(os.path.join(BASE, fn), 'rb') as f:
        return f.read()

def main():
    pygame.init()
    pygame.display.set_mode((1, 1))

    pal_raw = load_raw('PL11.DAT')
    pal = [(min(255, pal_raw[i*3]*4), min(255, pal_raw[i*3+1]*4), min(255, pal_raw[i*3+2]*4)) for i in range(256)]

    blk = load_raw('BK00.DAT')
    num_tiles = len(blk) // 192  # 16x12 pixels, 1 byte each
    print(f"{num_tiles} tiles")

    tile_w, tile_h = 16, 12
    scale = 2
    label_h = 16
    pad = 4
    cell_w = tile_w * scale + pad * 2
    cell_h = tile_h * scale + pad * 2 + label_h

    cols = 20
    rows = (num_tiles + cols - 1) // cols

    sheet_w = cols * cell_w
    sheet_h = rows * cell_h
    sheet = pygame.Surface((sheet_w, sheet_h), depth=24)
    sheet.fill((32, 32, 32))

    font = pygame.font.SysFont("monospace", 12, bold=True)

    for idx in range(num_tiles):
        col = idx % cols
        row = idx // cols
        cx = col * cell_w
        cy = row * cell_h

        pygame.draw.rect(sheet, (64, 64, 64), (cx, cy, cell_w, cell_h), 1)

        # Render tile scaled 2x
        tile_surf = pygame.Surface((tile_w, tile_h), depth=24)
        off = idx * 192
        for ty in range(tile_h):
            for tx in range(tile_w):
                ci = blk[off + ty * tile_w + tx]
                tile_surf.set_at((tx, ty), pal[ci])
        scaled = pygame.transform.scale(tile_surf, (tile_w * scale, tile_h * scale))

        sx = cx + pad
        sy = cy + label_h + pad
        sheet.blit(scaled, (sx, sy))

        label = font.render(str(idx), True, (200, 200, 0))
        lx = cx + (cell_w - label.get_width()) // 2
        sheet.blit(label, (lx, cy + 2))

    out = os.path.join(BASE, 'tile_sheet.png')
    pygame.image.save(sheet, out)
    print(f"Saved: {out} ({sheet_w}x{sheet_h})")
    pygame.quit()

if __name__ == '__main__':
    main()
