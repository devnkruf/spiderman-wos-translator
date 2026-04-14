#!/usr/bin/env python3
"""
Simple PCPACK compressor using LZO.
"""

import struct
import sys
import lzo

NCH_BLOCK_SIZE = 0x80000  # 512KB


def compress_to_pcpack(input_path, output_path):
    """Compress a decompressed archive into PCPACK format."""
    
    print(f"Reading {input_path}...")
    with open(input_path, 'rb') as f:
        data = f.read()
    
    print(f"Input size: {len(data)} bytes")
    
    # Compress using LZO1X
    print("Compressing with LZO1X...")
    compressed = lzo.compress(data, 9, False, algorithm="LZO1X")
    
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(compressed)/len(data)*100:.1f}%")
    
    # Build NCH block(s)
    # Calculate how many blocks we need
    header_size = 32
    max_compressed_per_block = NCH_BLOCK_SIZE - header_size
    
    # For simplicity, we'll put all compressed data in sequence
    # The game seems to expect the full compressed stream to be contiguous
    decompressed_size = len(data)
    compressed_size = len(compressed)
    
    # Header fields
    compressed_end = header_size + compressed_size
    
    header = struct.pack("<4s7I",
        b"NCH\x00",           # Magic
        compressed_size,       # Compressed size
        0,                     # CRC (unused)
        decompressed_size,     # Decompressed size
        0,                     # Unknown
        0,                     # CRC2 (unused)
        compressed_end,        # End of compressed data
        1                      # Compression flag (1 = LZO)
    )
    
    # Build output
    output = bytearray(header)
    output.extend(compressed)
    
    # Pad to exact original size (241664 bytes) with 0xA1
    TARGET_SIZE = 241664  # Original GLOBALTEXT_ENGLISH.PCPACK size
    if len(output) < TARGET_SIZE:
        padding = TARGET_SIZE - len(output)
        output.extend(b'\xA1' * padding)
    
    print(f"Output size: {len(output)} bytes")
    
    # Write output
    print(f"Writing {output_path}...")
    with open(output_path, 'wb') as f:
        f.write(output)
    
    print("Done!")
    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: python compress_pcpack.py <input_archive> <output.PCPACK>")
        print()
        print("Compresses a decompressed archive into PCPACK format using LZO.")
        print("Run with MSYS2 Python: C:\\msys64\\mingw64\\bin\\python.exe compress_pcpack.py")
        sys.exit(1)
    
    compress_to_pcpack(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
