#!/usr/bin/python3
import sys
import argparse
import os

POLYNOMIAL = 0x1021  # X^16 + X^12 + X^5 + 1
INITIAL_STATE = 0xFFFF

parser = argparse.ArgumentParser(description="Calculate and optionally patch ROM checksum and signature.")
parser.add_argument("input_file", help="Input ROM file")
parser.add_argument("-w", "--write", action="store_true", help="Enable writing changes to the ROM file (otherwise, only a dry run is performed)")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debugging output")
args = parser.parse_args()

if not os.path.exists(args.input_file):
    print(f"Error: File '{args.input_file}' does not exist.")
    sys.exit(1)

with open(args.input_file, "rb") as file:
    rom_data = bytearray(file.read())

# Create a copy of the ROM data for processing
data_copy = rom_data.copy()

# Extract the expected signature values from the first two bytes
SIGNATURE_LO = rom_data[0]
SIGNATURE_HI = rom_data[1]

# Extract the current value at position 3 (checksum byte)
current_cchksm_byte = rom_data[2]

# Skip the first three bytes for the checksum calculation (to patch byte 3 later)
start_index_checksum = 3
rom_data_for_checksum = data_copy[start_index_checksum:]

# Perform reverse summation checksum calculation (simulate 6502 ADC behavior)
checksum = 0
carry = 0
if args.verbose:
    print("Debugging Checksum Calculation:")
for index, byte in enumerate(reversed(rom_data_for_checksum)):
    result = checksum + byte + carry
    carry = result >> 8  # Extract carry (overflow)
    checksum = result & 0xFF  # Keep checksum within 8 bits
    if args.verbose:
        print(f"Step {index + 1}: Byte=0x{byte:02X}, Intermediate Checksum=0x{checksum:02X}, Carry={carry}")

# Calculate the cchksm byte for position 3
cchksm_byte = (256 - checksum) & 0xFF
if args.verbose:
    print(f"CCHKSUM Byte to Add to Position 3: 0x{cchksm_byte:02X}")

# Update the checksum byte in the ROM copy
if current_cchksm_byte != cchksm_byte:
    print(f"The CCHKSUM byte needs to be updated: from 0x{current_cchksm_byte:02X} to 0x{cchksm_byte:02X}.")
    data_copy[2] = cchksm_byte
else:
    print("The CCHKSUM byte already contains the correct value.")

# Recalculate the signature after updating the checksum byte
signature = INITIAL_STATE
if args.verbose:
    print("Debugging Signature Calculation:")
for byte_index, byte in enumerate(data_copy[2:]):
    signature ^= (byte << 8)  # XOR the byte with the high byte of the signature
    for _ in range(8):
        if signature & 0x8000:  # If the MSB is set
            signature = (signature << 1) ^ POLYNOMIAL
        else:
            signature <<= 1
        signature &= 0xFFFF
    if args.verbose:
        print(f"Step {byte_index + 1}: Byte=0x{byte:02X}, Intermediate Signature=0x{signature:04X}")

# Extract the recalculated signature bytes
recalculated_lo = signature & 0xFF
recalculated_hi = (signature >> 8) & 0xFF

# Handle signature byte updates in the copy
if recalculated_lo != data_copy[0] or recalculated_hi != data_copy[1]:
    print(f"The signature bytes needs to be updated: LO from 0x{data_copy[0]:02X} to 0x{recalculated_lo:02X}, HI from 0x{data_copy[1]:02X} to 0x{recalculated_hi:02X}.")
    data_copy[0] = recalculated_lo
    data_copy[1] = recalculated_hi
else:
    print("The signature bytes are already correct.")

# Write updates to the ROM file if requested
if args.write:
    with open(args.input_file, "wb") as file:
        file.write(data_copy)
    print(f"ROM file '{args.input_file}' has been updated.")
elif current_cchksm_byte != cchksm_byte or recalculated_lo != SIGNATURE_LO or recalculated_hi != SIGNATURE_HI:
    print("Dry Run: Changes would be needed but not written to the ROM file.")
else:
    print("Dry Run: No changes needed to the ROM file.")

# Display summary
print("\n=== Summary ===")
print(f"Current Signature Bytes: LO=0x{SIGNATURE_LO:02X}, HI=0x{SIGNATURE_HI:02X}")
print(f"Recalculated Signature Bytes: LO=0x{recalculated_lo:02X}, HI=0x{recalculated_hi:02X}")
print(f"Current CCHKSUM Byte: 0x{current_cchksm_byte:02X}")
print(f"Recalculated CCHKSUM Byte: 0x{cchksm_byte:02X}")

