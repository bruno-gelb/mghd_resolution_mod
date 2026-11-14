"""Light xref: str <text> -> VA + raw-byte refs with local disassembly; dis <va> <n>."""
import sys, struct, capstone, pefile
pe = pefile.PE(sys.argv[1], fast_load=True)
data = pe.__data__
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def off2va(o):
    for s in pe.sections:
        if s.PointerToRawData <= o < s.PointerToRawData + s.SizeOfRawData:
            return base + s.VirtualAddress + o - s.PointerToRawData
def va2off(v):
    return pe.get_offset_from_rva(v - base)
def dis(va, n):
    o = va2off(va)
    for i, ins in enumerate(md.disasm(bytes(data[o:o + n * 8]), va)):
        if i >= n: break
        print(f"  {ins.address:08x}: {ins.mnemonic} {ins.op_str}")
args = sys.argv[2:]
if args[0] == "str":
    t = args[1].encode() + b"\0"
    o = data.find(b"\0" + t) + 1
    va = off2va(o); print(args[1], hex(va))
    pat = struct.pack("<I", va); p = 0
    while (p := data.find(pat, p)) != -1:
        rva = off2va(p); print(" ref at", hex(rva)); dis(rva - 40, 40); p += 1
elif args[0] == "dis":
    dis(int(args[1], 16), int(args[2]))
