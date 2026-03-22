"""Minimal PNG decoder for RGBA images using only stdlib.

Handles 8-bit RGBA non-interlaced PNGs (RainViewer's radar tile format).
"""

import struct
import zlib
from typing import List, Tuple


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode_png(data: bytes) -> Tuple[int, int, List[Tuple[int, int, int, int]]]:
    """Decode a PNG image into width, height, and RGBA pixel list.

    Returns:
        (width, height, pixels) where pixels is a flat list of (R, G, B, A) tuples,
        row-major from top-left.
    """
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("Not a valid PNG file")

    pos = 8
    width = height = 0
    bit_depth = color_type = 0
    idat_chunks = []

    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length  # 4 (length) + 4 (type) + data + 4 (CRC)

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(
                ">IIBB", chunk_data[:10]
            )
            # We only handle 8-bit RGBA
            if bit_depth != 8 or color_type != 6:
                raise ValueError(
                    f"Unsupported PNG format: bit_depth={bit_depth}, color_type={color_type}"
                )
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if not idat_chunks:
        raise ValueError("No IDAT chunks found")

    # Decompress all IDAT data
    raw = zlib.decompress(b"".join(idat_chunks))

    # Each row: 1 filter byte + width * 4 bytes (RGBA)
    stride = width * 4
    pixels = []
    prev_row = bytes(stride)

    offset = 0
    for _ in range(height):
        filter_byte = raw[offset]
        offset += 1
        row_data = bytearray(raw[offset : offset + stride])
        offset += stride

        # Undo PNG filter
        _unfilter_row(filter_byte, row_data, prev_row, 4)

        # Extract RGBA tuples
        for x in range(width):
            base = x * 4
            pixels.append((row_data[base], row_data[base + 1],
                           row_data[base + 2], row_data[base + 3]))

        prev_row = bytes(row_data)

    return (width, height, pixels)


def _unfilter_row(
    filter_type: int,
    row: bytearray,
    prev_row: bytes,
    bpp: int,
) -> None:
    """Apply PNG row unfiltering in-place."""
    if filter_type == 0:  # None
        pass
    elif filter_type == 1:  # Sub
        for i in range(bpp, len(row)):
            row[i] = (row[i] + row[i - bpp]) & 0xFF
    elif filter_type == 2:  # Up
        for i in range(len(row)):
            row[i] = (row[i] + prev_row[i]) & 0xFF
    elif filter_type == 3:  # Average
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            up = prev_row[i]
            row[i] = (row[i] + (left + up) // 2) & 0xFF
    elif filter_type == 4:  # Paeth
        for i in range(len(row)):
            left = row[i - bpp] if i >= bpp else 0
            up = prev_row[i]
            up_left = prev_row[i - bpp] if i >= bpp else 0
            row[i] = (row[i] + _paeth_predictor(left, up, up_left)) & 0xFF


def _paeth_predictor(a: int, b: int, c: int) -> int:
    """Paeth predictor function."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    return c
