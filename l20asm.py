from math import log2, ceil
from sys import argv

mn2hex = {
    "CIR":0, "SIR":1, "LDR":2, "STR":3, "ADD":4, "NND":5, "PSR":6, "SEF":7,
    "CLF":8, "PPR":9, "MOV":10, "JMP":11, "BCS":11, "BVS":11, "BZS":11, "BNS":11}

interrupt_aliases = {"HALT": 0}
conditions = {"NS": 8, "ZS": 4, "CS": 2, "VS": 1, "": 0, "AL":0}
labels = {}

def error(msg:str, problem, line:int, optional:str=""):
    p = str(problem)
    print("Error: "+msg+(" '"+p+"'" if len(p) > 0 else "")+" on line "+str(line+1)+"."+(" "+optional if len(optional) > 0  else ""))
    exit(-1)

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
    except ValueError:
        error("Invalid immediate format", s, line)
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
    if r > 127 or r < 0:
        error("Invalid register", s, line, "Target architecture only has 128, positively indexed registers.")
    return r

def preprocess(instr: str, line:int):
    instr = instr.split(";")[0].strip() #strip comments from program
    if instr != "":
        parts = instr.split()
        try:
            op = mn2hex[parts[0]]
        except KeyError:
            try:
                x = labels[parts[0]]
                error("Duplicate label", parts[0], line)
            except KeyError:
                labels[parts[0]] = line

def convert(instr: str, line:int, show: bool = False) -> tuple[str, str]:
    ins = 0
    instr = instr.split(";")[0].strip() #strip comments from program
    if instr == "":
        return ("", "")
    parts = instr.split(",")
    parts = parts[0].split(" ") + parts[1:]
    startindex = 1
    # try to convert mnemonic to opcode
    try:
        op = mn2hex[parts[0]]
        mn = parts[0]
    except KeyError:
        try:
            op = mn2hex[parts[1]]
            startindex = 2
            mn = parts[1]
        except KeyError:
            print("Unrecognized mnemonic '"+parts[1]+"' on line "+str(line)+".")
            exit(-1)
    c = mn[1:]
    ins = op << 28
    rcount = 0
    rmask = [21, 14, 0]
    for i in range(startindex, len(parts)):
        s = parts[i].strip()
        if op in [0, 1]: #CIR, SIR
            if s[0] == "#":
                code = parseImm(s[1:], line)
                rcount += 1
            else:
                if rcount == 0:
                    try:
                        code = interrupt_aliases[s]
                        rcount += 1
                    except KeyError:
                        error("Unknown interrupt code", s, line)
                elif op == 1 and rcount == 1:
                    if s[0] == "R":
                        r = parseReg(s, line)
                        ins |= r
                    else:
                        error("Unknown operand", s, line)
            ins |= code << 20
        elif op in [2, 3]: #LDR, STR
            try:
                if rcount == 1:
                    s = s[s.index("[")+1:]
                elif rcount == 2:
                    s = s[:s.index("]")]
            except ValueError:
                error("Missing '[' or ']'", "", line)
            r = parseReg(s, line)
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
                if op == 6:
                    ins |= r << 14
                else:
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
                if s[0] == "#":
                    imm = parseImm(s[1:], line)
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
                    sh = s.split(" ")
                    rn = parseReg(sh[0], line)
                    shtype = 0
                    rm = 0
                    if len(sh) == 3:
                        try:
                            shtype = ["LSL", "LSR", "ASR"].index(sh[1])
                        except ValueError:
                            error("Unrecognized shift type", sh[1], line)
                        rm = parseReg(sh[2], line)
                    elif len(sh) != 1:
                        error("Incorrect number of arguments for MOV", "", line)
                    ins |= rn << 14 | shtype << 12 | rm
        elif op in [11]: #JMP, and B<flag>S
            if mn != "JMP":
                try:
                    n = conditions[c]
                    ins |= n << 24
                except KeyError:
                    error("Unrecognized condition", c, line)
            if s[0] == "#":
                d = parseImm(s[1:])
                if d < 0:
                    d = twos(-d, 24)
            else:
                try:
                    l = labels[s]
                except KeyError:
                    error("Undefined label", s, line)
                d = l - line
                if d < 0:
                    d = twos(-d, 24)
                d -= 2
            ins |= d
    return (format(ins, "08x"), instr if show else "")

opts = []
srcname = ""
src = ""
dest = ""
for i in range(1, len(argv)):
    if argv[i][0] == "-":
        opts.append(argv[i][1:])
    elif len(srcname) <= 0:
        srcname = argv[i]
    elif len(dest) <= 0:
        dest = argv[i]
    else:
        print("Unexpected command line argument '"+argv[i]+"'")
        exit(-1)
if srcname == "":
    print("You must specify a source file!")
    exit(-1)
if dest == "":
    dest = ".".join(srcname.split(".")[:-1]) + ".lbin"

try:
    src = open(srcname, "r")
except FileNotFoundError:
    print("Error reading file '"+srcname+"'")
    exit(-1)
dest = open(dest, "w")
dest.write("v2.0 raw\n")
i = 0
pc = 0
while True:
    l = src.readline()
    if not l:
        break
    preprocess(l, i)
    i += 1
src.close()
src = open(srcname, "r")
i = 0
while True:
    l = src.readline()
    if not l:
        break
    t = convert(l, i, True)
    if t[0] != "":
        dest.write(t[0]+" # 0x"+str(format(i, "06x"))+(": "+t[1] if len(t[1]) > 0 else "")+"\n")
    i += 1
src.close()
dest.close()