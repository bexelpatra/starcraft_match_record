"""
Analyze raw command data from a StarCraft Remastered replay to reverse-engineer CMD_SIZES.
This script does NOT modify sc_replay_parser.py.
"""

import struct
import zlib
from collections import defaultdict, Counter
from pathlib import Path

REPLAY_PATH = Path(r"D:\pypy\star_record\replays\samples\2026-02-25@015428_kimsabuho(t)_vs_HM_sSak(t).rep")


def find_zlib_blocks(data):
    blocks = []
    pos = 0
    while pos < len(data) - 6:
        if data[pos:pos+2] == b'\x78\x9c':
            expected = struct.unpack('<I', data[pos-4:pos])[0] if pos >= 4 else 0
            blocks.append({'pos': pos, 'expected_size': expected})
        pos += 1
    return blocks


def decompress_block(data, blocks, index):
    if index >= len(blocks):
        return None
    pos = blocks[index]['pos']
    try:
        return zlib.decompress(data[pos:])
    except:
        if index + 1 < len(blocks):
            end = blocks[index + 1]['pos'] - 4
            try:
                return zlib.decompress(data[pos:end])
            except:
                pass
    return None


def find_map_data_start(data, blocks):
    for i in range(len(blocks)):
        decompressed = decompress_block(data, blocks, i)
        if decompressed and len(decompressed) > 4:
            if decompressed[:4] in [b'VER ', b'TYPE', b'VCOD', b'OWNR']:
                return i
    return len(blocks)


def main():
    with open(REPLAY_PATH, 'rb') as f:
        raw_data = f.read()

    print(f"File size: {len(raw_data):,} bytes")
    print(f"Magic: {raw_data[12:16]}")

    blocks = find_zlib_blocks(raw_data)
    print(f"Found {len(blocks)} zlib blocks")

    map_start = find_map_data_start(raw_data, blocks)
    print(f"Map data starts at block {map_start}")

    # Collect command data from blocks 1 to map_start
    cmd_data = b''
    for i in range(1, map_start):
        block = decompress_block(raw_data, blocks, i)
        if block:
            print(f"  Block {i}: {len(block):,} bytes")
            cmd_data += block

    print(f"\nTotal command data: {len(cmd_data):,} bytes")

    # === PHASE 1: Parse frame/block structure and dump raw blocks ===
    print("\n" + "="*80)
    print("PHASE 1: Frame/Block structure analysis")
    print("="*80)

    pos = 0
    frame_count = 0
    block_sizes = []
    action_id_counts = Counter()
    first_byte_counts = Counter()  # player_id byte
    all_blocks = []  # Store (frame, block_bytes) for later analysis

    errors = 0
    while pos < len(cmd_data) - 5:
        frame = struct.unpack('<I', cmd_data[pos:pos+4])[0]
        block_size = cmd_data[pos+4]

        if frame > 100000:
            pos += 1
            errors += 1
            continue

        if block_size == 0 or pos + 5 + block_size > len(cmd_data):
            pos += 1
            errors += 1
            continue

        cmd_block = cmd_data[pos+5:pos+5+block_size]
        block_sizes.append(block_size)
        all_blocks.append((frame, cmd_block))

        # Count the action_id (second byte in block, after player_id)
        if len(cmd_block) >= 2:
            first_byte_counts[cmd_block[0]] += 1
            action_id_counts[cmd_block[1]] += 1

        pos += 5 + block_size
        frame_count += 1

    print(f"Parsed {frame_count} frame blocks, {errors} alignment errors")
    print(f"Block sizes: min={min(block_sizes)}, max={max(block_sizes)}, avg={sum(block_sizes)/len(block_sizes):.1f}")

    print(f"\nFirst byte (player_id) distribution:")
    for byte_val, count in first_byte_counts.most_common(20):
        print(f"  0x{byte_val:02x} ({byte_val:3d}): {count:6d}")

    print(f"\nSecond byte (action_id) distribution (first cmd in each block):")
    for byte_val, count in action_id_counts.most_common(30):
        print(f"  0x{byte_val:02x} ({byte_val:3d}): {count:6d}")

    # === PHASE 2: Analyze ALL action_id bytes within blocks ===
    print("\n" + "="*80)
    print("PHASE 2: Dump first 50 blocks raw hex for pattern analysis")
    print("="*80)

    for idx, (frame, block) in enumerate(all_blocks[:50]):
        hex_str = ' '.join(f'{b:02x}' for b in block)
        print(f"  Frame {frame:5d} (size={len(block):3d}): {hex_str}")

    # === PHASE 3: Try parsing with current (potentially wrong) CMD_SIZES ===
    print("\n" + "="*80)
    print("PHASE 3: Attempt parsing with CURRENT CMD_SIZES")
    print("="*80)

    CURRENT_CMD_SIZES = {
        0x00: 0, 0x01: 0, 0x02: 0, 0x03: 0,
        0x04: 'select', 0x05: 'select', 0x06: 'select',
        0x07: 7, 0x08: 2, 0x09: 4, 0x0A: 1, 0x0B: 0, 0x0C: 0,
        0x0D: 4, 0x0E: 2, 0x0F: 9, 0x10: 9,
        0x11: 0, 0x12: 0, 0x13: 0, 0x14: 0, 0x15: 0, 0x16: 0, 0x17: 0,
        0x18: 2, 0x19: 2, 0x1A: 0, 0x1B: 0, 0x1C: 2,
        0x1D: 0, 0x1E: 0, 0x1F: 0, 0x20: 0, 0x21: 2, 0x22: 0, 0x23: 0,
        0x24: 0, 0x25: 0, 0x26: 0, 0x27: 4, 0x28: 1, 0x29: 0, 0x2A: 1,
        0x2B: 0, 0x2C: 0, 0x2D: 2, 0x2E: 0, 0x2F: 4,
        0x35: 0, 0x37: 5, 0x3A: 1, 0x48: 1, 0x49: 1, 0x4A: 1, 0x4C: 4,
        0x4D: 0, 0x50: 0, 0x52: 'chat',
        0x54: 9, 0x55: 9, 0x56: 2, 0x57: 'select',
        0x58: 'select_delta', 0x59: 'select_delta', 0x5A: 'chat', 0x5C: 2,
        0x60: 'select', 0x61: 'select', 0x62: 'select',
        0x63: 9, 0x64: 9, 0x65: 9,
    }

    def get_cmd_size(action_id, block, offset, sizes_dict):
        size_info = sizes_dict.get(action_id)
        if size_info is None:
            return None
        if isinstance(size_info, int):
            return size_info
        if size_info == 'select':
            if offset < len(block):
                count = block[offset]
                return 1 + count * 2
            return None
        if size_info == 'select_delta':
            if offset < len(block):
                count = block[offset]
                return 1 + count * 4
            return None
        if size_info == 'chat':
            null_pos = block.find(b'\x00', offset)
            if null_pos >= 0:
                return null_pos - offset + 1
            return len(block) - offset
        return None

    # Count actions with current sizes
    current_action_counts = Counter()
    current_parse_failures = 0
    current_total_cmds = 0

    for frame, block in all_blocks:
        bpos = 0
        while bpos + 1 < len(block):
            player_id = block[bpos]
            action_id = block[bpos + 1]
            cmd_data_start = bpos + 2

            if not (0 <= player_id <= 11):
                break

            cmd_size = get_cmd_size(action_id, block, cmd_data_start, CURRENT_CMD_SIZES)
            if cmd_size is None:
                current_parse_failures += 1
                break

            cmd_end = cmd_data_start + cmd_size
            if cmd_end > len(block):
                current_parse_failures += 1
                break

            current_action_counts[action_id] += 1
            current_total_cmds += 1
            bpos = cmd_end

    print(f"Total commands parsed: {current_total_cmds}")
    print(f"Parse failures (unknown cmd or overflow): {current_parse_failures}")
    print(f"\nAction distribution:")
    for action_id, count in current_action_counts.most_common(30):
        name_map = {
            0x00: 'Keep Alive', 0x04: 'Select', 0x05: 'Shift Select', 0x06: 'Shift Deselect',
            0x07: 'Build', 0x0E: 'Hotkey', 0x0F: 'Right Click', 0x10: 'Targeted Order',
            0x11: 'Cancel Build', 0x12: 'Cancel Morph', 0x13: 'Stop', 0x14: 'Carrier Stop',
            0x18: 'Train', 0x19: 'Cancel Train', 0x1C: 'Unit Morph', 0x1D: 'Unsiege',
            0x1E: 'Siege', 0x1F: 'Train Fighter', 0x20: 'Unload All', 0x21: 'Unload',
            0x23: 'Hold Position', 0x27: 'Lift', 0x28: 'Research', 0x2A: 'Upgrade',
            0x2D: 'Building Morph', 0x2E: 'Stim', 0x2F: 'Sync',
            0x48: 'Latency', 0x52: 'Chat', 0x54: 'Right Click (RM)',
            0x57: 'Select (RM)', 0x5A: 'Chat (RM)', 0x5C: 'Cancel Train (RM)',
            0x60: 'Select (RM2)', 0x17: 'Return Cargo', 0x4A: 'Leave Game',
        }
        name = name_map.get(action_id, f'0x{action_id:02x}')
        print(f"  0x{action_id:02x} {name:30s}: {count:6d}")


    # === PHASE 4: Look for patterns - what follows 0x13 in blocks ===
    print("\n" + "="*80)
    print("PHASE 4: What bytes follow 0x13 (currently Stop, size=0)?")
    print("="*80)

    # After 0x13 with size=0, the next byte should be player_id of next cmd
    # Let's see what byte follows 0x13 in raw blocks
    count_0x13 = 0
    bytes_after_0x13 = Counter()
    sample_0x13_contexts = []

    for frame, block in all_blocks:
        for i in range(len(block) - 1):
            if block[i] == 0x13:
                # What's the byte after?
                if i + 1 < len(block):
                    bytes_after_0x13[block[i+1]] += 1
                # Get surrounding context
                if count_0x13 < 30:
                    start = max(0, i-3)
                    end = min(len(block), i+6)
                    ctx = ' '.join(f'{b:02x}' for b in block[start:end])
                    sample_0x13_contexts.append(f"  block_pos={i}, frame={frame}: ...{ctx}...")
                count_0x13 += 1

    print(f"Total occurrences of byte 0x13 in blocks: {count_0x13}")
    print(f"Bytes immediately after 0x13:")
    for b, c in bytes_after_0x13.most_common(15):
        print(f"  0x{b:02x} ({b:3d}): {c:5d}")
    print(f"\nSample contexts around 0x13:")
    for s in sample_0x13_contexts[:20]:
        print(s)


    # === PHASE 5: What bytes follow 0x1f (currently Train Fighter, size=0)? ===
    print("\n" + "="*80)
    print("PHASE 5: What bytes follow 0x1f (currently Train Fighter, size=0)?")
    print("="*80)

    bytes_after_0x1f = Counter()
    sample_0x1f_contexts = []
    count_0x1f = 0

    for frame, block in all_blocks:
        for i in range(len(block)):
            if block[i] == 0x1f:
                if i + 2 < len(block):
                    two_bytes = struct.unpack('<H', block[i+1:i+3])[0]
                    bytes_after_0x1f[two_bytes] += 1
                if count_0x1f < 30:
                    start = max(0, i-3)
                    end = min(len(block), i+6)
                    ctx = ' '.join(f'{b:02x}' for b in block[start:end])
                    sample_0x1f_contexts.append(f"  block_pos={i}, frame={frame}: ...{ctx}...")
                count_0x1f += 1

    print(f"Total occurrences of byte 0x1f in blocks: {count_0x1f}")
    print(f"Two bytes (as uint16 LE) after 0x1f (if Train, should be unit IDs 0-228):")
    for val, c in bytes_after_0x1f.most_common(20):
        print(f"  {val:5d} (0x{val:04x}): {c:5d}")
    print(f"\nSample contexts around 0x1f:")
    for s in sample_0x1f_contexts[:20]:
        print(s)


    # === PHASE 6: Brute-force: within parsed blocks, count all byte values at position after action_id ===
    print("\n" + "="*80)
    print("PHASE 6: Block size distribution (how big are the blocks?)")
    print("="*80)

    size_counter = Counter(block_sizes)
    print("Block sizes and their frequencies:")
    for sz, cnt in sorted(size_counter.items()):
        print(f"  size={sz:3d}: {cnt:5d}")


if __name__ == '__main__':
    main()
