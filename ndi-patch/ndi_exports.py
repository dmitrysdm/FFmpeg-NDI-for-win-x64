#!/usr/bin/env python3
"""Parse a Windows PE DLL's export table (stdlib only) and emit a .def file.

Used by the build workflow to generate a proper GNU import library for the
NDI SDK:  python ndi_exports.py <dll> <out.def>

We parse the PE export directory directly instead of text-scraping
`objdump -p` — that output format has changed across binutils versions and
broke a fragile awk parse.

Usage:  python ndi_exports.py Processing.NDI.Lib.x64.dll ndi-exports.def
"""
import struct
import sys


def parse_exports(dll_path, def_path):
    d = open(dll_path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    assert d[pe : pe + 4] == b"PE\x00\x00", "not a PE file"

    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    opthsz = struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", d, opt)[0]
    # Optional header: data-directory array starts at +96 (PE32) / +112 (PE32+).
    # The 0th data directory is the export directory.
    dd = opt + (112 if magic == 0x20B else 96)
    exp_rva, _ = struct.unpack_from("<II", d, dd)
    if not exp_rva:
        sys.exit("no export directory")

    # Section table: map a virtual address to a file offset.
    sec_off = opt + opthsz
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        vsize, va, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        secs.append((va, vsize, rawptr))

    def va2off(va):
        for s_va, s_vs, ro in secs:
            if s_vs and s_va <= va < s_va + s_vs:
                return ro + (va - s_va)
        return None

    er = va2off(exp_rva)
    if er is None:
        sys.exit(f"export RVA {exp_rva:#x} not mapped")

    # IMAGE_EXPORT_DIRECTORY (NO magic field — first DWORD is Characteristics).
    nfunc = struct.unpack_from("<I", d, er + 20)[0]
    nnames = struct.unpack_from("<I", d, er + 24)[0]
    names_rva = struct.unpack_from("<I", d, er + 32)[0]
    names = va2off(names_rva)
    out = []
    for i in range(nnames):
        rva = struct.unpack_from("<I", d, names + 4 * i)[0]
        o = va2off(rva)
        e = d.index(b"\x00", o)
        out.append(d[o:e].decode("utf-8", "replace"))

    with open(def_path, "w", newline="") as f:
        f.write('LIBRARY "Processing.NDI.Lib.x64.dll"\nEXPORTS\n')
        for s in out:
            f.write("  " + s + "\n")
    print(f"parsed {len(out)} exports from {dll_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <dll> <out.def>")
    parse_exports(sys.argv[1], sys.argv[2])
