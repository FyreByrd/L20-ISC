# L20-ISC

The **L20** **I**nstruction **S**et **C**omputer is an Instruction Set and accompanying computer that I designed as a project for my Computer Architecture class in school. The official parameters of the project is that the computer have less than 20 instructions, hence the name L20.  

## Files

- L20 Computer.circ:
    - The computer itself as a [Logisim](http://www.cburch.com/logisim/) file.
- l20asm.py:
    - The assembler.
- L20 Instruction Set.md
    - A description of the instruction set.
- l20-vscode-extension
    - A VS Code extension for some syntax highlighting. 
- hello.l20
    - A hello world program
- subleq.l20
    - A program emulating SUBLEQ to demonstrate Turing completeness.

## Usage
run `python3 l20asm.py <source>` in the terminal

arguments:
- 1: source file (required)
- 2: destination file (optional)

Providing the option `--disassemble` will  disassemble the source file.  
If there are `__DATA` tags in the source file, the data will be separated out into a separate file with the same name as the destination file but appended with `-data`.
