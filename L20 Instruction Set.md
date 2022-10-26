# L20 Instruction Set Architecture

## Name

L20 stands for "**L**ess than **20**."  
The L20 instruction set has only 19 instructions, where instruction is defined as an opcode and an addressing mode.  

## Instructions

The instructions are as follows;
- CIR imm8
- SIR imm8, rm            
- LDR rd, [rn, rm]
- STR rd, [rn, rm]
- ADD rd, rn, rm
- NND rd, rn, rm
- PSR rn
- SEF imm4
- CLF imm4
- PPR rd
- MOV rd, rn sh[13:12] rm
- B cond4 imm24

Opcodes 0xC-0xF are left unused for future expansion.

## Status Flags

ADD always sets N, Z, C, V
NND always sets N, Z and clears C, V

## Register structure

R0 always 0x00000000
R1 always 0x00000001
R127 always 0xFFFFFFFF
R126 = PC
R125 = SP
special mnemonics
NOP: MOV R0, R0
HLT: INR #0

shifts
0: LSL (<<)
1: LSR (>>)
2: ASR (>>>)
3: imm14 << imm5 (sign-extended)

conditions:
0000: NS
0100: ZS
0010: CS
0001: VS
0000: AL

31 30 29 28|27 26 25 24|23 22 21 20|19 18 17 16|15 14 13 12|11 10 09 08|07 06 05 04|03 02 01 00
| opcode 4| |       Rd 7       | |       Rn 7       | |     control 7    | |       Rm 7       |

## Interrupts

NVIC format
31-30: type (0: halt, 1:jump to handler)
29-24: priority
23-0: handler address