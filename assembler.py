import re
import sys
from pathlib import Path

# Predefined Hack symbols
PREDEFINED_SYMBOLS = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576,
    **{f"R{i}": i for i in range(16)},
}

# C-instruction lookup tables
COMP_TABLE = {
    "0":   "0101010",
    "1":   "0111111",
    "-1":  "0111010",
    "D":   "0001100",
    "A":   "0110000",
    "M":   "1110000",
    "!D":  "0001101",
    "!A":  "0110001",
    "!M":  "1110001",
    "-D":  "0001111",
    "-A":  "0110011",
    "-M":  "1110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "M+1": "1110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "M-1": "1110010",
    "D+A": "0000010",
    "D+M": "1000010",
    "D-A": "0010011",
    "D-M": "1010011",
    "A-D": "0000111",
    "M-D": "1000111",
    "D&A": "0000000",
    "D&M": "1000000",
    "D|A": "0010101",
    "D|M": "1010101",
    \









    
}

DEST_TABLE = {
    None:  "000",
    "M":   "001",
    "D":   "010",
    "MD":  "011",
    "A":   "100",
    "AM":  "101",
    "AD":  "110",
    "AMD": "111",
}

JUMP_TABLE = {
    None:  "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

SYMBOL_PATTERN = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


class AssemblerError(Exception):
    def __init__(self, line_num: int, message: str):
        super().__init__(f"Line {line_num}: {message}")


def clean_line(raw: str) -> str:
    """Remove // comments and all whitespace."""
    no_comment = raw.split("//", 1)[0]
    return "".join(no_comment.split())


def first_pass(lines: list[str], symbol_table: dict[str, int]) -> list[tuple[int, str]]:
    """
    Strip comments/blank lines, record (LABEL) ROM addresses,
    and return [(original_line_num, instruction), ...].
    """
    instructions: list[tuple[int, str]] = []
    rom_address = 0

    for line_num, raw in enumerate(lines, start=1):
        cleaned = clean_line(raw)
        if not cleaned:
            continue

        if cleaned.startswith("(") and cleaned.endswith(")"):
            label = cleaned[1:-1]
            if not SYMBOL_PATTERN.match(label):
                raise AssemblerError(line_num, f"invalid label name '({label})'")
            if label in symbol_table:
                raise AssemblerError(line_num, f"duplicate label '({label})'")
            symbol_table[label] = rom_address
        elif cleaned.startswith("(") or cleaned.endswith(")"):
            raise AssemblerError(line_num, "malformed label declaration")
        else:
            instructions.append((line_num, cleaned))
            rom_address += 1

    return instructions


def translate_a_instruction(line_num: int, instr: str, symbol_table: dict[str, int], next_var_addr: int) -> tuple[str, int]:
    """Translate @value or @symbol into a 16-bit binary string."""
    target = instr[1:]
    if not target:
        raise AssemblerError(line_num, "missing address or symbol after '@'")

    if target.isdigit():
        value = int(target)
        if value < 0 or value > 32767:
            raise AssemblerError(line_num, f"A-instruction constant out of range (0..32767): {value}")
    else:
        if not SYMBOL_PATTERN.match(target):
            raise AssemblerError(line_num, f"invalid symbol name '{target}'")
        if target not in symbol_table:
            symbol_table[target] = next_var_addr
            next_var_addr += 1
        value = symbol_table[target]

    return f"0{value:015b}", next_var_addr


def translate_c_instruction(line_num: int, instr: str) -> str:
    """Translate dest=comp;jump into a 16-bit binary string."""
    dest_part = None
    jump_part = None
    comp_part = instr

    if "=" in comp_part:
        parts = comp_part.split("=")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise AssemblerError(line_num, "invalid assignment syntax in C-instruction")
        dest_part, comp_part = parts

    if ";" in comp_part:
        parts = comp_part.split(";")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise AssemblerError(line_num, "invalid jump syntax in C-instruction")
        comp_part, jump_part = parts

    if dest_part not in DEST_TABLE:
        raise AssemblerError(line_num, f"invalid destination '{dest_part}'")
    if comp_part not in COMP_TABLE:
        raise AssemblerError(line_num, f"invalid computation '{comp_part}'")
    if jump_part not in JUMP_TABLE:
        raise AssemblerError(line_num, f"invalid jump '{jump_part}'")

    return f"111{COMP_TABLE[comp_part]}{DEST_TABLE[dest_part]}{JUMP_TABLE[jump_part]}"


def second_pass(instructions: list[tuple[int, str]], symbol_table: dict[str, int]) -> list[str]:
    """Translate cleaned instructions into 16-bit binary lines."""
    machine_code: list[str] = []
    next_var_addr = 16

    for line_num, instr in instructions:
        if instr.startswith("@"):
            binary, next_var_addr = translate_a_instruction(line_num, instr, symbol_table, next_var_addr)
        else:
            binary = translate_c_instruction(line_num, instr)
        machine_code.append(binary)

    return machine_code


def assemble_file(asm_path: Path) -> None:
    lines = asm_path.read_text(encoding="utf-8").splitlines()
    symbol_table = dict(PREDEFINED_SYMBOLS)

    instructions = first_pass(lines, symbol_table)
    machine_code = second_pass(instructions, symbol_table)

    hack_path = asm_path.with_suffix(".hack")
    hack_path.write_text("\n".join(machine_code) + "\n", encoding="utf-8")
    print(f"Assembled {asm_path.name} -> {hack_path.name} ({len(machine_code)} instructions)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <Program.asm>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found '{input_path}'")
        sys.exit(1)

    try:
        assemble_file(input_path)
    except AssemblerError as err:
        print(err)
        sys.exit(1)