#!/usr/bin/env python3

import re
import sys


def imm_to_bin(num: str, bits: int, signed: bool=False) -> str:
    """Convert a number to a binary string

    Args:
        num:    The number to be converted to binary.
                Can be either Hexadecimal, decimal or binary.
        bits:   The number of bits of the binary value returned
        signed: True if the resulting value should be signed

    Returns:
        String representing the number in binary
    """
    # hexadecimal
    if "0x" in num:
        num = int(num, 16)
    # binary
    elif "0b" in num:
        num = int(num, 2)
    # decimal
    else:
        num = int(num)

    # check that the immediate is in range to fit in the bits
    if signed:
        maximum = 2 ** (bits - 1) - 1
        minimum = -1 * maximum - 1
    else:
        maximum = 2 ** bits - 1
        minimum = 0
    if not minimum <= int(num) <= maximum:
        raise ValueError("Immediate {} out of range {} to {}"
                         .format(num, minimum, maximum))

    # convert to binary
    if num < 0:
        bitmask = 2 ** bits - 1
        num = -num
        return bin((bitmask ^ num) + 1)[2:]
    else:
        return bin(num)[2:].zfill(bits)


def convert_pseudoinstructions(code: [str]) -> [str]:
    """Convert .spaces to .fill 0's and movis to lui+llis"""
    newcode = []
    for line in code:
        m = re.match(r"^(\w+:)?(?:\s+)?(\.?\w+)\s?(.*)\s?", line)
        label, operation, args = m[1], m[2], m[3]
        if label is None:
            label = ""
        if operation == ".space":
            newcode.append("{} .fill 0".format(label))
            for i in range(int(args) - 1):
                newcode.append(".fill 0")
        elif operation == "movi":
            regA, imm = args.split(",")
            newcode.append("{} lui {},{}".format(label, regA, int(imm) // 64))
            newcode.append("lli {},{}".format(regA, int(imm) % 64))
        else:
            newcode.append(line)
    return newcode


def assemble_line(line: str) -> str:
    """Convert the assembly instruction to executable machine code

    Args:
        line: The instruction to be assembled

    Returns:
        The machine code value as a binary string
    """
    m = re.match(r"^(\w+:)?(?:\s+)?(\.?\w+)\s?(.*)\s?", line)
    label, operation, args = m[1], m[2], m[3]
    opcode = {"add": "000",
              "addi": "001",
              "nand": "010",
              "lui": "011",
              "sw": "100",
              "lw": "101",
              "beq": "110",
              "jalr": "111"}.get(operation)

    # RRR-type
    if operation in ("add", "nand"):
        regA, regB, regC = (imm_to_bin(n, 3) for n in args.split(","))
        return opcode + regA + regB + "0000" + regC
    # RRI-type
    elif operation in ("addi", "sw", "lw", "beq", "jalr"):
        regA, regB, imm = args.split(",")
        return opcode + imm_to_bin(regA, 3) + imm_to_bin(regB, 3)\
            + imm_to_bin(imm, 7, True)
    # RI-type
    elif operation == "lui":
        regA, imm = args.split(",")
        return opcode + imm_to_bin(regA, 3) + imm_to_bin(imm, 10)

    # pseudo-instructions
    elif operation == "nop":
        return "00000000000000000"

    elif operation == "halt":
        return "111000000" + imm_to_bin("1", 7)

    elif operation == "lli":
        regA, imm = args.split(",")
        return "001" + imm_to_bin(regA, 3) * 2 + "0" + imm_to_bin(imm, 6)

    elif operation == ".fill":
        return imm_to_bin(args, 16, True)


def has_code(line: str) -> bool:
    """
    Return True if there's code on the line
    (so it's not a comment or an empty line).
    """
    return not line.strip().startswith("#") or (line.strip() == "")


def assemble_code(code: [str]) -> [str]:
    """Convert the assembly source code to machine code

    Args:
        code: the source code in RiSC-16 assembly

    Returns:
        RiSC-16 machine code
    """
    # strip empty lines and unnecessary whitespace
    code = (line.strip() for line in code if has_code(line))

    code = convert_pseudoinstructions(code)

    # find the linenumbers for all the labels in the code for branching
    LABELS = dict(map(lambda x: (x[1].partition(":")[0], x[0]),
                      list(filter(lambda x: x[1].partition(" ")[0].endswith(":"),
                                  enumerate(code)))))

    machinecode = []
    for line in code:
        try:
            print("assembling '{}'".format(line))
            machinecode.append(assemble_line(line))
            print(machinecode[-1])
        except Exception as e:
            print("Error on line '{}': {}".format(line, e))
            return

    return machinecode


def main():
    if len(sys.argv) <= 1:
        print("Missing arguments")
        return

    with open(sys.argv[1]) as f:
        code = f.read().splitlines()

    try:
        outfile = sys.argv[2]
    except IndexError:
        outfile = sys.argv[1].partition(".")[0]

    with open(outfile, "w") as f:
        f.write("\n".join(assemble_code(code)))


if __name__ == "__main__":
    main()
