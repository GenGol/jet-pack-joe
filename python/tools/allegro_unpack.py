"""Decode Allegro packfiles ("slh!" = LZSS packed, "slh." = unpacked) and list datafile objects."""
import sys, struct, os

N, F, THRESHOLD = 4096, 18, 2

def lzss_decode(data, fill=0):
    out = bytearray()
    buf = bytearray([fill]) * N
    r = N - F
    i = 0
    flags = 0
    while i < len(data):
        flags >>= 1
        if not flags & 0x100:
            flags = data[i] | 0xFF00
            i += 1
        if flags & 1:
            c = data[i]; i += 1
            out.append(c); buf[r] = c; r = (r + 1) & (N - 1)
        else:
            if i + 1 >= len(data):
                break
            a, b = data[i], data[i + 1]; i += 2
            pos = a | ((b & 0xF0) << 4)
            ln = (b & 0x0F) + THRESHOLD
            for k in range(ln + 1):
                c = buf[(pos + k) & (N - 1)]
                out.append(c); buf[r] = c; r = (r + 1) & (N - 1)
    return bytes(out)

def be32(b, o):
    return struct.unpack_from(">I", b, o)[0]

def parse_datafile(b, depth=0, limit=None):
    """Allegro datafile: 'ALL.' count, then per object: props ('prop' id len data)*, then type id, len, data."""
    o = 0
    assert b[:4] == b"ALL.", b[:8]
    count = be32(b, 4); o = 8
    pad = "  " * depth
    print(f"{pad}datafile with {count} objects")
    objs = []
    for n in range(count):
        props = {}
        while b[o:o + 4] == b"prop":
            pid = b[o + 4:o + 8].decode("latin1"); ln = be32(b, o + 8)
            props[pid] = b[o + 12:o + 12 + ln]
            o += 12 + ln
        typ = b[o:o + 4].decode("latin1")
        fsize = be32(b, o + 4)                       # chunk header: packed size, then data size
        dsize = struct.unpack_from(">i", b, o + 8)[0]   # (negative = chunk not packed)
        o += 12
        ln = fsize
        data = b[o:o + ln]; o += ln
        if dsize > 0:                                # a packed chunk inside: decode it
            data = lzss_decode(data)
        name = props.get("NAME", b"").rstrip(b"\0").decode("latin1")
        extra = ""
        if typ == "BMP ":
            bits, w, h = struct.unpack_from(">HHH", data, 0)
            extra = f"{w}x{h} {bits}bpp"
        elif typ == "FILE":
            extra = "(nested)"
        print(f"{pad}[{n}] {typ!r} {name:20s} {ln:7d} bytes {extra}  props={ {k: v[:16] for k, v in props.items() if k != 'NAME'} }")
        objs.append((typ, name, data, props))
        if typ == "BMP " and DUMP:
            bits, w, h = struct.unpack_from(">HHH", data, 0)
            if bits == 8:
                import zlib
                px = data[6:6 + w * h]
                PAL_HOLD["bmps"].append((name, w, h, px))
        elif typ == "PAL " and DUMP:
            PAL_HOLD["pal"] = data
        if typ == "FILE" and depth < 2:
            parse_datafile(data, depth + 1)
    return objs

DUMP = True
PAL_HOLD = {"bmps": [], "pal": None}


def write_png(path, w, h, px, pal):
    import zlib, struct as st
    raw = b"".join(b"\x00" + bytes(px[y * w:(y + 1) * w]) for y in range(h))
    def chunk(t, d):
        return st.pack(">I", len(d)) + t + d + st.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    plte = bytes(min(255, v * 4) for v in pal[:768]) if pal else bytes(i // 3 for i in range(768))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", st.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0)) + chunk(b"PLTE", plte) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        raw = open(path, "rb").read()
        magic = raw[:4]
        if magic == b"slh!":
            body = lzss_decode(raw[4:])
        elif magic == b"slh.":
            body = raw[4:]
        else:
            body = raw
        out = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "unpacked", os.path.basename(path) + ".raw")
        open(out, "wb").write(body)
        print(f"== {path}: magic {magic!r}, packed {len(raw)} -> {len(body)} bytes -> {out}")
        print("   head:", body[:48])
        if body[:4] == b"ALL.":
            try:
                parse_datafile(body)
            except Exception as e:
                print("   parse error:", e)

    pal = PAL_HOLD["pal"]
    outdir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "unpacked")
    for name, w, h, px in PAL_HOLD["bmps"]:
        write_png(os.path.join(outdir, f"bmp_{name or 'x'}.png"), w, h, px, pal)
        print("wrote", f"bmp_{name}.png", w, h)
