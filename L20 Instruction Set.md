# L20 Instruction Set Architecture

## Name

L20 stands for "**L**ess than **20**."  
The L20 instruction set has only 19 instructions, where instruction is defined as an opcode and an addressing mode.  

## Instructions

The instructions are as follows;
- CIR #8
- SIR #8 Rm            
- LDR Rd Rn\[Rm\]
- STR Rd Rn\[Rm\]
- ADD Rd Rn Rm
- NND Rd Rn Rm
- PSR Rd
- SEF #4
- CLF #4
- PPR Rd
- MOV Rd Rn SH[13:12] Rm
- B #4 #24

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
R124 = LR  
special mnemonics
NOP: MOV R0, R0  
HLT: INR #0  

shifts
0: LSL (<<)  
1: LSR (>>)  
2: ASR (>>>)  
3: imm12 << imm5 (sign-extended)  

conditions:  
1000: Negative flag Set  
0100: Zero flag Set  
0010: Carry flag Set  
0001: oVerflow flag Set  
0000: unconditionAL  

31 30 29 28|27 26 25 24|23 22 21 20|19 18 17 16|15 14 13 12|11 10 09 08|07 06 05 04|03 02 01 00  
| opcode 4| |       Rd 7       | |       Rn 7       | |     control 7    | |       Rm 7       |

## Interrupts

NVIC format  
31: type (0: halt, 1:jump to handler)  
30-24: priority  
23-0: handler address

## IO
Any address above 0x00FFFFFF is considered IO.
Addresses:
- 0x01000000: Terminal Write
- 0x01000001: Keyboard Enable
- 0x01000002: Keyboard Read