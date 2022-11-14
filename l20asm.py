from math import log2, ceil
from sys import argv
import json

mn2hex = {
    "CIR":0x0, "SIR":0x1, "LDR":0x2, "STR":0x3, 
    "ADD":0x4, "NND":0x5, "PSR":0x6, "SEF":0x7, 
    "CLF":0x8, "PPR":0x9, "MOV":0xa, "B":0xb}

aliases = {"RNEG":"R127", "PC":"R126", "SP":"R125", "LR":"R124",
    "JMP": "B #b0000", "BNS": "B #b1000", "BZS": "B #b0100", "BCS":"B #b0010", "BVS":"B #b0001",
    "HLT": "CIR #0", "NOP": "MOV R0 R0", "IO_block": "#x1000000", "RET": "MOV PC LR",
    "CALL":["PSR LR", "MOV LR PC", "JMP %1", "PPR LR"]
}
def test_alias(line:str) -> tuple[bool, str]:
    if line in aliases:
        if type(aliases[line]) == list:
            return (True, aliases[line].copy())
        return (True, aliases[line])
    else:
        return (False, line)
for k, v in aliases.items():
    if type(v) == list:
        for z in range(len(v)):
            x = v[z].split()
            for y in range(len(x)):
                x[y] = test_alias(x[y])[1]
            v[z] = " ".join(x)
        aliases[k] = v
    else:
        x = v.split()
        for y in range(len(x)):
            x[y] = test_alias(x[y])[1]
        v = " ".join(x)
        aliases[k] = v

labels = {}
data_labels = {}
data = []
grouping = ""
errors = 0
warnings = 0
shtypes = ["LSL", "LSR", "ASR"]

escapes = {
    "'":"'", "\"":"\"", "\\":"\\", "n":"\n", "r":"\r", 
    "t":"\t", "b":"\b", "f":"\f", "0": "\0"}

def readfile(filename: str) -> list[tuple[str, int, str]]:
    try:
        file = open(filename, "r")
    except FileNotFoundError:
        print("Could not find file: '"+filename+"'")
        exit(-1)
    lines = []
    i = 0
    while True:
        l = file.readline()
        if not l:
            break
        lines.append((l, i, filename))
        i += 1
    file.close()
    return lines

def error(msg:str, problem, line:int, optional:str=""):
    p = str(problem)
    print("Error: "+msg+(" '"+p+"'" if len(p) > 0 else "")+" on line "+str(line+1)+"."+(" "+optional if len(optional) > 0  else ""))
    global errors
    errors += 1

def warn(msg:str, problem, line:int, optional:str=""):
    p = str(problem)
    print("Warning: "+msg+(" '"+p+"'" if len(p) > 0 else "")+" on line "+str(line+1)+"."+(" "+optional if len(optional) > 0  else ""))
    global warnings 
    warnings += 1

def twos(i:int, l:int) -> int:
    i = format(i, "0"+str(l)+"b")
    t = ""
    for d in i:
        if d == "0":
            t += "1"
        else:
            t += "0"
    return int(t, 2) + 1

def parseImm(s:str, line:int) -> int:
    neg = False
    if s[0] == "-":
        neg = True
        s = s[1:]
    try: 
        if s[0] == "x" or s[0:2] == "0x":
            imm = int(s[s.index("x")+1:], 16)
        elif s[0] == "b" or s[0:2] == "0b":
            imm = int(s[s.index("b")+1:], 2)
        else:
            imm = int(s, 10)
    except (ValueError, TypeError):
        error("Invalid immediate format", s, line)
        return 0
    if neg:
        imm = -imm
    return imm

def parseReg(s:str, line:int) -> int:
    try:
        if s[1] == "x":
            r = int(s[2:], 16)
        else:
            r = int(s[1:], 10)
    except ValueError:
        error("Invalid register format", s, line, "Expected format RN or RxN for hexadecimal.")
        return 0
    if r > 127 or r < 0:
        error("Invalid register", s, line, "Target architecture only has 128, positively indexed registers.")
    return r

def splitLine(line:str) -> list[str]:
    instr = line.split(";")[0].strip() #strip comments from program
    if instr == "":
        return []
    parts = instr.split()
    return parts     

def process_data_group(g, line:int):
    cg = True
    i = 0
    while i < len(g):
        n = g[i]
        i += 1
        if n[-1] == grouping:
            cg = False
            if len(n) <= 1:
                break
            else:
                n = n[:-1]
        if grouping == "\"":
            if n == "\\":
                n = escapes[g[i]]
                i += 1
            n = ord(n)
            try:
                l = list(data[-1])
                if len(l) < 4:
                    data[-1].append(n)
                else:
                    data.append([n])
            except (TypeError, IndexError):
                data.append([n])
        else:
            if grouping == "]":
                t = 1
                if "*" in n:
                    n = n.split("*")
                    t = parseImm(n[0], line)
                    n = n[1]
                n = parseImm(n, line)
                if n < 0:
                    n = twos(-n, 32)
                for j in range(t):
                    data.append(n)
            elif grouping == "'":
                if n == "\\":
                    n = escapes[g[i]]
                    i += 1
                data.append(ord(n))
    if grouping == "\"" and not cg:
        l = len(data[-1])
        if l == 4:
            data.append(4*[0])
        else:
            data[-1].extend((4 - l)*[0])
    return cg

def preprocess(line: tuple[str, int, str], pc:int) -> tuple[str, int, int]:
    parts = splitLine(line[0])
    if len(parts) > 0:
        global grouping
        if grouping != "":
            if grouping == "]":
                g = parts
            else:
                g = (" ".join(parts))
            grouping = grouping if process_data_group(g, line[1]) else ""
        elif parts[0] == "__DATA":
            if parts[1] in data_labels:
                error("Duplicate data label", parts[1], line[1])
            else:
                data_labels[parts[1]] = len(data)
                if len(parts) < 3:
                    error("Data label has no data", "", line[1])
                else:
                    if parts[2][0] in "\"['":
                        grouping = parts[2][0]
                        if grouping == "[":
                            grouping = "]"
                            g = ([parts[2][1:]] if len(parts[2]) > 1 else []) + parts[3:]
                        else:
                            g = (" ".join(parts[2:]))[1:]
                        grouping = grouping if process_data_group(g, line[1]) else ""
                    else:
                        if len(parts) > 3:
                            error("Data label requires a group for more than one value", "", line[1])
                        else:
                            data.append(parseImm(parts[2], line[1]))
        else:
            #print(line[2]+" ("+str(line[1])+"): "+str(parts))
            for i in range(len(parts)):
                t = test_alias(parts[i])
                parts[i] = t[1]
            if type(parts[0]) == list:
                for p in range(len(parts[0])):
                    l = parts[0][p].split("%")
                    l[0] = l[0].strip()
                    for j in range(1, len(l)):
                        l[j] = parts[int(l[j].strip())]
                    parts[0][p] = " ".join(l)
                parts = parts[0]
                r = []
                for p in parts:
                    if p.split()[0] in mn2hex:
                        pc += 1
                    r.append((p, line[1]))
                return (r, pc, line[1])
            else:
                parts = splitLine(" ".join(parts))
                if parts[0] in mn2hex:
                    pc += 1
                else:
                    if parts[0] in labels:
                        error("Duplicate label", parts[0], line[1])
                    else:
                        if parts[0] not in mn2hex:
                            labels[parts[0]] = pc + 1
                            parts = parts[1:]
                            if len(parts) > 0 and parts[0] in mn2hex:
                                pc += 1
                return (" ".join(parts), pc, line[1])
    return ("", pc, line[1])

def assemble(instr: str, line:int, pc:int, show: bool = False) -> tuple[str, str, int]:
    ins = 0
    op = 0
    parts = splitLine(instr)
    if len(parts) == 0:
        return ("", "", pc)
    startindex = 1
    # try to convert mnemonic to opcode
    try:
        op = mn2hex[parts[0]]
    except KeyError:
        error("Unrecognized mnemonic", parts[1], line)
    ins = op << 28
    rcount = 0
    rmask = [21, 14, 0]
    for i in range(startindex, len(parts)):
        s = parts[i]
        if op in [0, 1]: #CIR, SIR
            code = 0
            if s[0] == "#":
                code = parseImm(s[1:], line)
                rcount += 1
            else:
                if op == 1 and rcount == 1:
                    if s[0] == "R":
                        r = parseReg(s, line)
                        ins |= r
                    else:
                        error("Unknown operand", s, line)
            ins |= code << 20
        elif op in [2, 3]: #LDR, STR
            if rcount == 0:
                r = parseReg(s, line)
            elif rcount == 1:
                s = s.split("[")
                r = parseReg(s[0], line)
                if len(s) > 1:
                    if s[1][-1] != "]":
                        error("Missing", "]", line)
                    rm = parseReg(s[1][:-1], line)
                    ins |= rm
            ins |= r << rmask[rcount]
            rcount += 1
        elif op in [4, 5]: #ADD, NND
            if s[0] == "R":
                r = parseReg(s, line)
                if rcount < 3:
                    ins |= r << rmask[rcount]
                    rcount += 1
                else:
                    error("Too many operands", "", line)
            else:
                error("ADD/NND non-register operand", s, line)
        elif op in [6, 9]: #PSR, PPR
            if rcount == 0:
                r = parseReg(s, line)
                if op == 9 and r == 126:
                    error("Disallowed PPR PC", "", line)
                ins |= r << 21
                rcount += 1
            else:
                error("Incorrect number of arguments", "", line)
        elif op in [7, 8]: #SEF, CLF
            if s[0] == "#":
                f = parseImm(s[1:], line)
                if f > 15:
                    error("Bit flag is too large", "", line)
            else:
                f = 0
                for i in range(len(s)):
                    if s[i] == "N":
                        f |= 8
                    elif s[i] == "Z":
                        f |= 4
                    elif s[i] == "C":
                        f |= 2
                    elif s[i] == "V":
                        f |= 1
                    else:
                        error("Unrecognized bit flag pattern", s, line)
            ins |= f << 24
        elif op == 10: #MOV
            if rcount == 0:
                if s[0] != "R":
                    error("MOV must have a destination specified", "", line)
                r = parseReg(s, line)
                ins |= r << 21
                rcount += 1
            else:
                if s[0] == "#" or (s[0] != "R" and s not in shtypes):
                    imm = 0
                    if s[0] == "#":
                        imm = parseImm(s[1:], line)
                    else:
                        if s in data_labels:
                            imm = data_labels[s]
                        else:
                            error("Unrecognized data label", s, line)
                    neg = imm < 0
                    imm = abs(imm)
                    if imm < 2048:
                        shamt = 0
                    else:
                        shamt = ceil(log2(imm+1)) - 11
                        if shamt > 31 or (imm & ((2 **shamt) -1)) != 0:
                            error("Immediate cannot fit into instruction format", "", line)
                        imm = imm >> shamt
                    if neg:
                        imm = twos(imm, 12)
                    imm = imm & 0xfff
                    ins |= 3 << 12 | shamt << 14 | imm
                else:
                    rn = 0
                    sh = 0
                    rm = 0
                    if rcount == 1:
                        rn = parseReg(s, line)
                        rcount += 1
                    elif rcount == 2:
                        try:
                            sh = shtypes.index(s)
                        except ValueError:
                            error("Unrecognized shift type", s, line)
                        rcount += 1
                    elif rcount == 3:
                        rm = parseReg(s, line)
                        rcount += 1
                    ins |= rn << 14 | sh << 12 | rm
        elif op in [11]: #JMP, and B<flag>S
            c = 0
            if s[0] == "#":
                d = parseImm(s[1:], line)
                if rcount == 0:
                    c = d
                    d = 0
                    rcount += 1
                elif d < 0:
                    d = twos(-d, 24)
                    rcount += 1
            else:
                l = 0
                try:
                    l = labels[s]
                except KeyError:
                    error("Undefined label", s, line)
                d = l - pc - 2
                if d < 0:
                    d = twos(-d, 24)
            ins |= c << 24 | d
    pc += 1
    return (format(ins, "08x"), instr if show else "", pc)

def disassemble(line: str) -> str:
    if line == "v2.0 raw\n":
        return ""
    parts = line.split("#")
    parts = parts[0].strip()
    s = ""
    parts = int(parts, 16)
    op = parts >> 28
    imm4 = (parts >> 24) & 0xF
    imm8 = (parts >> 20) & 0xFF
    imm24 = parts & 0xFFFFFF
    if imm24 & 0x800000:
        imm24 = -twos(imm24, 24)
    rd = (parts >> 21) & 0x7F
    rn = (parts >> 14) & 0x7F
    rm = parts & 0x7F
    sh = (parts >> 12) & 0x3
    imm5 = (parts >> 14) & 0x1F
    imm12 = parts & 0xFFF
    mn = "; ??? "
    if op in mn2hex.values():
        mn = list(mn2hex.keys())[op]
    s += mn + " "
    if op in [0, 1]:
        s += "#"+str(imm8) + str(" R"+str(rm) if op == 1 else "")
    elif op in [2, 3]:
        s += "R"+str(rd)+" R"+str(rn)+"[R"+str(rm)+"]"
    elif op in [4, 5]:
        s += "R"+str(rd)+" R"+str(rn)+" R"+str(rm)
    elif op in [6, 9]:
        s += "R"+str(rd)
    elif op in [7, 8]:
        f = ""
        if imm4 & 0x8:
            f += "N"
        if imm4 & 0x4:
            f += "Z"
        if imm4 & 0x2:
            f += "C"
        if imm4 & 0x1:
            f += "V"
        #s += f
        s += "#b"+format(imm4, "04b")
    elif op == 10:
        s += "R"+str(rd)+" "
        if sh == 3:
            neg = bool(imm12 & 0x800)
            if neg:
                imm12 = twos(imm12, 12)
            s += "#"+("-" if neg else "")+str(imm12 << imm5)
        else:
            s += "R"+str(rn)
            if rm != 0:
                s += " "+shtypes[sh]+" R"+str(rm)
    elif op == 11:
        s += "#b"+format(imm4, "04b")+" #"+str(imm24)
    return s+" ; 0x"+format(parts, "08x")+"\n"

opts = []
src = ""
dest = ""
for i in range(1, len(argv)):
    if argv[i][0] == "-":
        opts.append(argv[i][1:])
    elif len(src) <= 0:
        src = argv[i]
    elif len(dest) <= 0:
        dest = argv[i]
    else:
        print("Unexpected command line argument '"+argv[i]+"'")
        exit(-1)

dis = '-disassemble' in opts

if src == "":
    print("You must specify a source file!")
    exit(-1)
if dest == "":
    dest = ".".join(src.split(".")[:-1]) + (".l20" if dis else ".lbin")

srcname = src
src = readfile(src)
srcpre = []
text_out = []
if dis:
    for l in src:
        d = disassemble(l[0])
        if len(d) > 0:
            text_out.append(d)
else:
    pc = -1
    for i in range(len(src)):
        t = preprocess(src[i], pc)
        pc = t[1]
        if len(t[0]) > 0:
            if type(t[0]) == list:
                srcpre.extend(t[0])
            else:
                srcpre.append((t[0], t[2]))
    src = srcpre
    #print(json.dumps(labels, indent=4))
    #print(json.dumps(data_labels, indent=4))
    #print(data)
    pc = 0
    for i in range(len(src)):

        t = assemble(src[i][0], src[i][1], pc, True)
        if t[0] != "":
            text_out.append(t[0]+" # 0x"+str(format(pc, "06x"))+(": "+t[1] if len(t[1]) > 0 else "")+"\n")
        pc = t[2]

if errors == 0:
    data_out = dest.split(".")
    data_out[-2] += "-data"
    data_out = ".".join(data_out)
    dest = open(dest, "w")
    if dis:
        dest.write("; disassembly of "+str(srcname)+"\n")
    else:
        dest.write("v2.0 raw\n")
    for l in text_out:
        dest.write(l)
    dest.close()
    if len(data) > 0:
        data_out = open(data_out, "w")
        data_out.write("v2.0 raw\n")
        for d in data:
            try:
                l = list(d)
                d = int(l[0]) << 24 | int(l[1]) << 16 | int(l[2]) << 8 | int(l[3])
            except TypeError:
                pass
            data_out.write(format(int(d), "08x")+"\n")
        data_out.close()
else:
    print("errors: "+str(errors))
if warnings > 0:
    print("warnings: "+str(warnings))
