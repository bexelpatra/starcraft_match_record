"""
Test the hypothesis that CMD_SIZES should match the screp Go parser's mapping.
Analyze with corrected sizes and validate against expected TvT gameplay.
"""

import struct
import zlib
from collections import defaultdict, Counter
from pathlib import Path

REPLAY_PATH = Path(r"D:\pypy\star_record\replays\samples\2026-02-25@015428_kimsabuho(t)_vs_HM_sSak(t).rep")

# Unit IDs for validation
UNITS = {
    0: 'Marine', 1: 'Ghost', 2: 'Vulture', 3: 'Goliath', 4: 'Goliath Turret',
    5: 'Siege Tank (Tank)', 6: 'Tank Turret', 7: 'SCV', 8: 'Wraith', 9: 'Science Vessel',
    10: 'Dropship', 11: 'Battlecruiser', 12: 'Spider Mine', 13: 'Nuclear Missile',
    14: 'Civilian', 30: 'Siege Tank (Siege)', 32: 'Firebat', 34: 'Medic', 58: 'Valkyrie',
    35: 'Larva', 36: 'Egg', 37: 'Zergling', 38: 'Hydralisk', 39: 'Ultralisk',
    40: 'Broodling', 41: 'Drone', 42: 'Overlord', 43: 'Mutalisk', 44: 'Guardian',
    45: 'Queen', 46: 'Defiler', 47: 'Scourge', 60: 'Zealot', 61: 'Dragoon',
    63: 'Archon', 64: 'Shuttle', 65: 'Scout', 66: 'Arbiter', 67: 'Carrier',
    68: 'Interceptor', 69: 'Dark Templar', 70: 'Dark Archon', 71: 'Probe',
    72: 'Reaver', 73: 'Observer', 74: 'Scarab', 83: 'Corsair', 84: 'High Templar',
    106: 'Command Center', 107: 'Comsat Station', 108: 'Nuclear Silo',
    109: 'Supply Depot', 110: 'Refinery', 111: 'Barracks', 112: 'Academy',
    113: 'Factory', 114: 'Starport', 115: 'Control Tower', 116: 'Science Facility',
    117: 'Covert Ops', 118: 'Physics Lab', 119: 'Starbase', 120: 'Machine Shop',
    122: 'Engineering Bay', 123: 'Armory', 124: 'Missile Turret', 125: 'Bunker',
    131: 'Hatchery', 132: 'Lair', 133: 'Hive', 134: 'Nydus Canal',
    135: 'Hydralisk Den', 136: 'Defiler Mound', 137: 'Greater Spire',
    138: 'Queens Nest', 139: 'Evolution Chamber', 140: 'Ultralisk Cavern',
    141: 'Spire', 142: 'Spawning Pool', 143: 'Creep Colony', 144: 'Spore Colony',
    145: 'Sunken Colony', 146: 'Extractor',
    149: 'Nexus', 150: 'Robotics Facility', 151: 'Pylon', 152: 'Assimilator',
    153: 'Observatory', 154: 'Gateway', 157: 'Photon Cannon',
    159: 'Citadel of Adun', 160: 'Cybernetics Core', 161: 'Templar Archives',
    162: 'Forge', 163: 'Stargate', 165: 'Fleet Beacon', 166: 'Arbiter Tribunal',
    167: 'Robotics Support Bay', 168: 'Shield Battery',
}


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


def parse_all_blocks(raw_data):
    blocks = find_zlib_blocks(raw_data)
    map_start = find_map_data_start(raw_data, blocks)

    cmd_data = b''
    for i in range(1, map_start):
        block = decompress_block(raw_data, blocks, i)
        if block:
            cmd_data += block

    all_blocks = []
    pos = 0
    while pos < len(cmd_data) - 5:
        frame = struct.unpack('<I', cmd_data[pos:pos+4])[0]
        block_size = cmd_data[pos+4]

        if frame > 100000 or block_size == 0 or pos + 5 + block_size > len(cmd_data):
            pos += 1
            continue

        cmd_block = cmd_data[pos+5:pos+5+block_size]
        all_blocks.append((frame, cmd_block))
        pos += 5 + block_size

    return all_blocks


def test_hypothesis(all_blocks, cmd_sizes, hypothesis_name, cmd_names):
    """Test a CMD_SIZES hypothesis and report results."""
    print(f"\n{'='*80}")
    print(f"TESTING: {hypothesis_name}")
    print(f"{'='*80}")

    action_counts = Counter()
    player_action_counts = {0: Counter(), 1: Counter()}
    parse_failures = 0
    total_cmds = 0
    blocks_fully_parsed = 0
    blocks_partially_parsed = 0

    # For validation
    hotkey_data = []  # (type, group)
    train_data = []   # (unit_id, player_id)
    build_data = []   # (order, x, y, unit_id)
    right_click_data = []  # (x, y)
    select_data = []  # (count,)

    for frame, block in all_blocks:
        bpos = 0
        block_parsed_fully = True
        while bpos + 1 < len(block):
            player_id = block[bpos]
            action_id = block[bpos + 1]
            cmd_data_start = bpos + 2

            if not (0 <= player_id <= 11):
                block_parsed_fully = False
                break

            cmd_size = get_cmd_size(action_id, block, cmd_data_start, cmd_sizes)
            if cmd_size is None:
                block_parsed_fully = False
                parse_failures += 1
                break

            cmd_end = cmd_data_start + cmd_size
            if cmd_end > len(block):
                block_parsed_fully = False
                parse_failures += 1
                break

            action_counts[action_id] += 1
            if player_id in (0, 1):
                player_action_counts[player_id][action_id] += 1
            total_cmds += 1

            # Extract validation data
            cmd_payload = block[cmd_data_start:cmd_end]

            # Hotkey validation (whatever maps to hotkey)
            hotkey_id = None
            for aid, name in cmd_names.items():
                if 'Hotkey' in name:
                    hotkey_id = aid
                    break
            if action_id == hotkey_id and len(cmd_payload) >= 2:
                hotkey_data.append((cmd_payload[0], cmd_payload[1]))

            # Train validation
            train_id = None
            for aid, name in cmd_names.items():
                if name == 'Train' and aid < 0x50:
                    train_id = aid
                    break
            if action_id == train_id and len(cmd_payload) >= 2:
                unit_id = struct.unpack('<H', cmd_payload[0:2])[0]
                train_data.append((unit_id, player_id))

            # Build validation
            build_id = None
            for aid, name in cmd_names.items():
                if name == 'Build' and aid < 0x50:
                    build_id = aid
                    break
            if action_id == build_id and len(cmd_payload) >= 7:
                order = cmd_payload[0]
                x = struct.unpack('<H', cmd_payload[1:3])[0]
                y = struct.unpack('<H', cmd_payload[3:5])[0]
                unit_id = struct.unpack('<H', cmd_payload[5:7])[0]
                build_data.append((order, x, y, unit_id))

            # Select validation
            for aid, name in cmd_names.items():
                if 'Select' in name and action_id == aid:
                    if len(cmd_payload) >= 1:
                        select_data.append((cmd_payload[0],))
                    break

            # Right click validation
            for aid, name in cmd_names.items():
                if 'Right Click' in name and action_id == aid:
                    if len(cmd_payload) >= 4:
                        x = struct.unpack('<H', cmd_payload[0:2])[0]
                        y = struct.unpack('<H', cmd_payload[2:4])[0]
                        right_click_data.append((x, y))
                    break

            bpos = cmd_end

        if block_parsed_fully and bpos == len(block):
            blocks_fully_parsed += 1
        elif bpos > 0:
            blocks_partially_parsed += 1

    print(f"\nTotal commands parsed: {total_cmds}")
    print(f"Parse failures: {parse_failures}")
    print(f"Blocks fully parsed: {blocks_fully_parsed}/{len(all_blocks)}")
    print(f"Blocks partially parsed: {blocks_partially_parsed}")
    print(f"Parse rate: {blocks_fully_parsed/len(all_blocks)*100:.1f}%")

    print(f"\nAction distribution (top 30):")
    for action_id, count in action_counts.most_common(30):
        name = cmd_names.get(action_id, f'Unknown (0x{action_id:02x})')
        p0 = player_action_counts[0].get(action_id, 0)
        p1 = player_action_counts[1].get(action_id, 0)
        print(f"  0x{action_id:02x} {name:35s}: {count:6d}  (P0={p0:5d}, P1={p1:5d})")

    # Validate Hotkey data
    if hotkey_data:
        types = Counter(h[0] for h in hotkey_data)
        groups = Counter(h[1] for h in hotkey_data)
        valid_hotkeys = sum(1 for t, g in hotkey_data if t in (0, 1) and 0 <= g <= 9)
        print(f"\nHotkey validation ({len(hotkey_data)} total):")
        print(f"  Valid (type=0|1, group=0-9): {valid_hotkeys}/{len(hotkey_data)} ({valid_hotkeys/len(hotkey_data)*100:.1f}%)")
        print(f"  Types: {dict(types.most_common(10))}")
        print(f"  Groups: {dict(groups.most_common(15))}")
    else:
        print(f"\nHotkey validation: NO HOTKEY COMMANDS FOUND")

    # Validate Train data
    if train_data:
        valid_trains = sum(1 for uid, _ in train_data if uid in UNITS)
        unit_counts = Counter(UNITS.get(uid, f'Unknown({uid})') for uid, _ in train_data)
        print(f"\nTrain validation ({len(train_data)} total):")
        print(f"  Valid unit IDs: {valid_trains}/{len(train_data)} ({valid_trains/len(train_data)*100:.1f}%)")
        print(f"  Unit breakdown:")
        for unit, count in unit_counts.most_common(15):
            print(f"    {unit}: {count}")
    else:
        print(f"\nTrain validation: NO TRAIN COMMANDS FOUND")

    # Validate Build data
    if build_data:
        valid_builds = sum(1 for _, x, y, uid in build_data if uid in UNITS and 0 < x < 10000 and 0 < y < 10000)
        building_counts = Counter(UNITS.get(uid, f'Unknown({uid})') for _, _, _, uid in build_data)
        print(f"\nBuild validation ({len(build_data)} total):")
        print(f"  Valid: {valid_builds}/{len(build_data)}")
        print(f"  Building breakdown:")
        for building, count in building_counts.most_common(15):
            print(f"    {building}: {count}")
    else:
        print(f"\nBuild validation: NO BUILD COMMANDS FOUND")

    # Validate Select data
    if select_data:
        counts = Counter(s[0] for s in select_data)
        print(f"\nSelect validation ({len(select_data)} total):")
        print(f"  Count distribution: {dict(counts.most_common(15))}")
    else:
        print(f"\nSelect validation: NO SELECT COMMANDS FOUND")

    # Right click validation
    if right_click_data:
        valid_rc = sum(1 for x, y in right_click_data if 0 < x < 10000 and 0 < y < 10000)
        print(f"\nRight Click validation ({len(right_click_data)} total):")
        print(f"  Valid coordinates: {valid_rc}/{len(right_click_data)} ({valid_rc/len(right_click_data)*100:.1f}%)")
    else:
        print(f"\nRight Click validation: NO RIGHT CLICK COMMANDS FOUND")

    return total_cmds, parse_failures, blocks_fully_parsed


def main():
    with open(REPLAY_PATH, 'rb') as f:
        raw_data = f.read()

    all_blocks = parse_all_blocks(raw_data)
    print(f"Total frame blocks: {len(all_blocks)}")

    # ========== HYPOTHESIS 1: screp-based mapping ==========
    # Based on screp Go parser, the IDs are shifted relative to the classic BW parser.
    # Key observations from Phase 4/5 data:
    #   0x13 appears with 2 bytes after: (0|1, 0-9) -> Hotkey
    #   0x1f appears with 2 bytes after: valid unit IDs -> Train
    #   0x63 appears with variable data starting with count byte -> Select (Remastered)
    #   0x60 appears with variable data -> Select (Remastered)
    #   0x0c appears frequently -> could be Build (screp: 0x0c = Build)
    #   0x26 appears -> could be Cancel Train or something else

    # From screp source code, the Remastered command IDs are:
    # 0x05=KeepAlive, 0x06=SaveGame, 0x07=LoadGame, 0x08=RestartGame,
    # 0x09=Select, 0x0a=ShiftSelect, 0x0b=ShiftDeselect, 0x0c=Build,
    # 0x0d=Vision, 0x0e=Alliance, 0x0f=GameSpeed, 0x10=Pause, 0x11=Resume,
    # 0x12=Cheat, 0x13=Hotkey, 0x14=RightClick, 0x15=TargetedOrder,
    # 0x16=CancelBuild, 0x17=CancelMorph, 0x18=Stop, 0x19=CarrierStop,
    # 0x1a=ReaverStop, 0x1b=OrderNothing, 0x1c=ReturnCargo, 0x1d=Train,
    # 0x1e=CancelTrain, 0x1f=Cloak... wait that doesn't match.
    #
    # Actually, looking at the data more carefully:
    # 0x1f with unit IDs = TRAIN (size=2)
    # 0x13 with type/group = HOTKEY (size=2)
    # So the mapping is shifted by +5 from the original BW IDs.
    #
    # BW original: 0x0E=Hotkey, 0x18=Train
    # This replay: 0x13=Hotkey, 0x1f=Train (but 0x1f in BW is TrainFighter)
    # Actually, 0x13 = 0x0E + 5, 0x1f =/= 0x18 + 5 = 0x1d
    #
    # Let me look at this differently. Let me check if there's a uniform +5 offset.

    # From data, likely mapping (offset +5 from classic BW):
    # BW 0x00 KeepAlive    -> RM 0x05
    # BW 0x04 Select       -> RM 0x09
    # BW 0x07 Build        -> RM 0x0c
    # BW 0x0E Hotkey       -> RM 0x13
    # BW 0x0F RightClick   -> RM 0x14
    # BW 0x13 Stop         -> RM 0x18
    # BW 0x18 Train        -> RM 0x1d
    # BW 0x1F TrainFighter -> RM 0x24
    #
    # But 0x1f appears with unit IDs! That's not +5 from Train (0x18).
    # Let me check if maybe it's NOT a uniform offset.
    #
    # OK, looking at the raw data more carefully:
    # 0x1f with 2 bytes (unit IDs like 7=SCV, 0=Marine) = this MUST be Train
    # 0x13 with 2 bytes (0|1, 0-9) = this MUST be Hotkey
    # 0x0c with 7 bytes = this MUST be Build
    # 0x63 with variable (count + ids) = Select (Remastered)
    # 0x60 with variable (count + ids) = Select (Remastered2) -- different format?
    #
    # So the observed IDs don't match a simple +5 offset.
    # Let me try building the mapping empirically.

    # First, let's figure out what all the observed action IDs are by checking
    # data patterns after each one.

    print("\n" + "="*80)
    print("PHASE A: Empirical action ID analysis")
    print("For each frequent action_id, what do the data bytes look like?")
    print("="*80)

    # Build a mapping of action_id -> list of (player_id, data_bytes) from raw blocks
    # We'll just look at the FIRST command in each block (no multi-cmd parsing needed)
    action_samples = defaultdict(list)
    for frame, block in all_blocks:
        if len(block) >= 2:
            player_id = block[0]
            action_id = block[1]
            data = block[2:]  # Everything after player_id + action_id (might include next cmd)
            if len(action_samples[action_id]) < 30:
                action_samples[action_id].append((frame, player_id, data))

    for action_id in sorted(action_samples.keys()):
        samples = action_samples[action_id]
        print(f"\n  Action 0x{action_id:02x} ({len(samples)} samples):")
        for frame, pid, data in samples[:8]:
            hex_data = ' '.join(f'{b:02x}' for b in data[:20])
            print(f"    Frame {frame:5d}, P{pid}: {hex_data}")

    # ========== HYPOTHESIS 2: Empirical mapping based on data patterns ==========
    # From the phase A output, we can manually determine sizes.
    # Let me build a hypothesis based on what we've observed:

    # 0x13: always 2 bytes data (type 0|1, group 0-9) = HOTKEY
    # 0x1f: always 2 bytes data (unit_id LE16) = TRAIN
    # 0x60: looks like select - starts with what could be a different format
    #        Let me check: 0x60 data starts with varying bytes...
    # 0x63: looks like count + N*2 unit IDs = SELECT (Remastered)
    # 0x0c: Build (7 bytes: order + x + y + unit_id)
    # 0x26: what is this?
    # 0x2b: what is this?
    # 0x1e: could be CancelTrain (2 bytes: slot)?

    # Let me try a hypothesis with screp-like IDs but adjusted:

    # Based on raw data analysis, here's my best hypothesis:
    HYPOTHESIS_SCREP = {
        # Low IDs (possibly KeepAlive and system commands)
        0x05: 0,           # KeepAlive
        0x06: 0,           # SaveGame
        0x07: 0,           # LoadGame
        0x08: 0,           # RestartGame

        # Select commands
        0x09: 'select',    # Select (1 + N*2)
        0x0a: 'select',    # Shift Select
        0x0b: 'select',    # Shift Deselect

        # Build
        0x0c: 7,           # Build: order(1) + x(2) + y(2) + unit(2)

        # Alliance/Vision
        0x0d: 2,           # Vision
        0x0e: 4,           # Alliance
        0x0f: 1,           # Game Speed

        0x10: 0,           # Pause
        0x11: 0,           # Resume
        0x12: 4,           # Cheat

        # Hotkey
        0x13: 2,           # Hotkey: type(1) + group(1)

        # Right Click
        0x14: 9,           # Right Click: x(2)+y(2)+unit(2)+unknown(2)+action(1)

        # Targeted Order
        0x15: 9,           # Targeted Order

        0x16: 0,           # Cancel Build
        0x17: 0,           # Cancel Morph
        0x18: 0,           # Stop
        0x19: 0,           # Carrier Stop
        0x1a: 0,           # Reaver Stop
        0x1b: 0,           # Order Nothing
        0x1c: 0,           # Return Cargo

        # Train
        0x1d: 2,           # Train: unit(2)

        # Cancel Train
        0x1e: 2,           # Cancel Train: slot(2)

        # Cloak/Decloak
        0x1f: 0,           # Cloak
        0x20: 0,           # Decloak

        # Unit Morph
        0x21: 2,           # Unit Morph: unit(2)

        0x22: 0,           # Unsiege
        0x23: 0,           # Siege
        0x24: 0,           # Train Fighter
        0x25: 0,           # Unload All
        0x26: 2,           # Unload: unit(2)
        0x27: 0,           # Merge Archon
        0x28: 0,           # Hold Position
        0x29: 0,           # Burrow
        0x2a: 0,           # Unburrow
        0x2b: 0,           # Cancel Nuke
        0x2c: 4,           # Lift: x(2)+y(2)
        0x2d: 1,           # Research: tech(1)
        0x2e: 0,           # Cancel Research
        0x2f: 1,           # Upgrade: upgrade(1)
        0x30: 0,           # Cancel Upgrade
        0x31: 0,           # Cancel Addon
        0x32: 2,           # Building Morph: unit(2)
        0x33: 0,           # Stim
        0x34: 4,           # Sync
        0x3a: 0,           # Start Game
        0x3c: 5,           # Change Game Slot
        0x3f: 1,           # Change Race
        0x4d: 1,           # Latency
        0x4e: 1,           # Replay Speed
        0x4f: 1,           # Leave Game
        0x51: 4,           # Minimap Ping
        0x52: 0,           # Merge Dark Archon
        0x55: 0,           # Make Game Public
        0x57: 'chat',      # Chat

        # Remastered commands
        0x59: 9,           # Right Click (Remaster)
        0x5a: 9,           # Targeted Order (Remaster)
        0x5b: 2,           # Unload (Remaster)
        0x5c: 'select',    # Select (Remaster)
        0x5d: 'select_delta',  # Select Delta Add
        0x5e: 'select_delta',  # Select Delta Del
        0x5f: 'chat',      # Chat (Remaster)
        0x61: 2,           # Cancel Train (Remaster)
        0x65: 'select',    # Select (Remaster2)
        0x66: 'select',    # Shift Select (Remaster)
        0x67: 'select',    # Shift Deselect (Remaster)
        0x68: 9,           # Right Click (Remaster2)
        0x69: 9,           # Targeted Order (Remaster2)
        0x6a: 9,           # Target Order Alt (Remaster)

        # Classic IDs that might still appear
        0x00: 0,
    }

    HYPOTHESIS_SCREP_NAMES = {
        0x00: 'KeepAlive(classic)', 0x05: 'KeepAlive', 0x06: 'SaveGame', 0x07: 'LoadGame',
        0x08: 'RestartGame', 0x09: 'Select', 0x0a: 'ShiftSelect', 0x0b: 'ShiftDeselect',
        0x0c: 'Build', 0x0d: 'Vision', 0x0e: 'Alliance', 0x0f: 'GameSpeed',
        0x10: 'Pause', 0x11: 'Resume', 0x12: 'Cheat', 0x13: 'Hotkey',
        0x14: 'RightClick', 0x15: 'TargetedOrder', 0x16: 'CancelBuild', 0x17: 'CancelMorph',
        0x18: 'Stop', 0x19: 'CarrierStop', 0x1a: 'ReaverStop', 0x1b: 'OrderNothing',
        0x1c: 'ReturnCargo', 0x1d: 'Train', 0x1e: 'CancelTrain', 0x1f: 'Cloak',
        0x20: 'Decloak', 0x21: 'UnitMorph', 0x22: 'Unsiege', 0x23: 'Siege',
        0x24: 'TrainFighter', 0x25: 'UnloadAll', 0x26: 'Unload', 0x27: 'MergeArchon',
        0x28: 'HoldPosition', 0x29: 'Burrow', 0x2a: 'Unburrow', 0x2b: 'CancelNuke',
        0x2c: 'Lift', 0x2d: 'Research', 0x2e: 'CancelResearch', 0x2f: 'Upgrade',
        0x30: 'CancelUpgrade', 0x31: 'CancelAddon', 0x32: 'BuildingMorph', 0x33: 'Stim',
        0x34: 'Sync',
        0x3a: 'StartGame', 0x3c: 'ChangeGameSlot', 0x3f: 'ChangeRace',
        0x4d: 'Latency', 0x4e: 'ReplaySpeed', 0x4f: 'LeaveGame', 0x51: 'MinimapPing',
        0x52: 'MergeDarkArchon', 0x55: 'MakeGamePublic', 0x57: 'Chat',
        0x59: 'RightClick(RM)', 0x5a: 'TargetedOrder(RM)', 0x5b: 'Unload(RM)',
        0x5c: 'Select(RM)', 0x5d: 'SelectDeltaAdd', 0x5e: 'SelectDeltaDel',
        0x5f: 'Chat(RM)', 0x61: 'CancelTrain(RM)', 0x65: 'Select(RM2)',
        0x66: 'ShiftSelect(RM)', 0x67: 'ShiftDeselect(RM)',
        0x68: 'RightClick(RM2)', 0x69: 'TargetedOrder(RM2)', 0x6a: 'TargetOrderAlt(RM)',
    }

    test_hypothesis(all_blocks, HYPOTHESIS_SCREP, "Hypothesis: screp +5 offset", HYPOTHESIS_SCREP_NAMES)

    # ========== Wait, let me re-examine. The data clearly shows: ==========
    # 0x1f has 2 bytes data = unit IDs for TRAIN
    # But in the +5 offset, Train would be 0x1d (0x18+5)
    # 0x1f in +5 would be Cloak (0x1a+5), but Cloak has size=0 in classic
    # So 0x1f can't be Cloak if it has 2 bytes of data.
    #
    # This means the offset is NOT a uniform +5 for all commands.
    # Let me look at this differently.
    #
    # Actually, looking at the screp source more carefully, maybe the IDs are:
    # The classic BW format uses one set of IDs.
    # Remastered replays use DIFFERENT IDs that are NOT simply offset.
    #
    # Let me try yet another hypothesis based purely on the data:

    # From data observations:
    # 0x13 = Hotkey (2 bytes: type 0|1, group 0-9) - CONFIRMED by data
    # 0x1f = Train (2 bytes: unit_id LE16) - CONFIRMED by data (SCV=7, Marine=0, etc.)
    # 0x0c = Build (7 bytes: order + x + y + unit) - very likely (241 occurrences, TvT needs buildings)
    # 0x63 = Select variant (variable: count + N*2) - data shows count + unit_ids
    # 0x60 = Select variant (variable) - data looks different, check format
    # 0x61 = ShiftSelect variant (variable)
    # 0x64 = Targeted Order variant (9 bytes)
    # 0x65 = some order (variable?)
    # 0x26 = what? (172 occurrences)
    # 0x2b = what? (103 occurrences)
    # 0x1e = CancelTrain? (73 occurrences)
    # 0x25 = UnloadAll? (71 occurrences)
    # 0x2f = ? (25 occurrences)
    # 0x32 = ? (21 occurrences)
    # 0x1a = ? (10 occurrences)

    # Let me check what 0x1f-0x18=7 difference means.
    # Classic: 0x18=Train -> this replay: 0x1f=Train -> offset = +7
    # Classic: 0x0E=Hotkey -> this replay: 0x13=Hotkey -> offset = +5
    # So different commands have different offsets! Unless...
    #
    # Wait, let me recount. In the classic BW format:
    # 0x00=KeepAlive, 0x01=SaveGame, ... 0x0E=Hotkey ... 0x18=Train
    # Difference: 0x13-0x0E = 5, 0x1f-0x18 = 7
    # These are different offsets. So it's NOT a simple uniform shift.
    #
    # BUT WAIT: what if there are EXTRA commands inserted between?
    # Let me count the classic commands 0x00 through 0x0E:
    # 0x00 KeepAlive, 0x01 SaveGame, 0x02 LoadGame, 0x03 RestartGame,
    # 0x04 Select, 0x05 ShiftSelect, 0x06 ShiftDeselect, 0x07 Build,
    # 0x08 Vision, 0x09 Alliance, 0x0A GameSpeed, 0x0B Pause,
    # 0x0C Resume, 0x0D Cheat, 0x0E Hotkey
    # That's 15 commands (0x00-0x0E).
    #
    # If Remastered adds 5 IDs before KeepAlive, then KeepAlive=0x05, Hotkey=0x13.
    # 0x0E + 5 = 0x13. Check.
    #
    # Now 0x18 Train + 5 = 0x1d. But our data shows Train at 0x1f.
    # 0x1f - 0x18 = 7. That's 2 more than expected.
    #
    # Unless there are 2 extra commands inserted between Hotkey(0x13) and Train.
    # Classic: Hotkey(0x0E), RightClick(0x0F), TargetedOrder(0x10),
    #          CancelBuild(0x11), CancelMorph(0x12), Stop(0x13),
    #          CarrierStop(0x14), ReaverStop(0x15), OrderNothing(0x16),
    #          ReturnCargo(0x17), Train(0x18)
    # That's 10 commands from Hotkey to Train (0x0E to 0x18).
    #
    # Remastered: Hotkey(0x13), ..., Train(0x1f)
    # That's 12 slots (0x13 to 0x1f), meaning 2 extra commands inserted.
    #
    # Hmm, this is getting complicated. Let me take a different approach
    # and just systematically determine each ID from the data.

    # ========== HYPOTHESIS 3: Pure empirical ==========
    # Let me build the mapping purely from data patterns.
    # I'll try parsing with these assignments and see if blocks parse cleanly.

    # Key insight: Look at block boundaries. If we assign correct sizes,
    # ALL blocks should parse completely (bpos == len(block) at end).

    # Let's try iteratively. Start with what we KNOW:
    # 0x13 = 2 bytes (Hotkey)
    # 0x1f = 2 bytes (Train)
    # 0x63 = 'select' (variable: 1 + N*2)
    # 0x60 = needs investigation
    # 0x0c = 7 bytes (Build) - need to verify

    # First, let's check 0x60 format by looking at blocks that start with it
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x60 data format")
    print("="*80)

    for frame, block in all_blocks[:200]:
        if len(block) >= 2 and block[1] == 0x60:
            hex_data = ' '.join(f'{b:02x}' for b in block[:25])
            print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")

    # Check 0x61 format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x61 data format")
    print("="*80)

    count_61 = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x61:
            if count_61 < 30:
                hex_data = ' '.join(f'{b:02x}' for b in block[:25])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_61 += 1

    # Check 0x0c format (should be Build with 7 bytes)
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x0c data format")
    print("="*80)

    count_0c = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x0c:
            if count_0c < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:25])
                # If it's Build with 7 bytes: order(1) + x(2) + y(2) + unit(2)
                if len(block) >= 9:
                    order = block[2]
                    x = struct.unpack('<H', block[3:5])[0]
                    y = struct.unpack('<H', block[5:7])[0]
                    unit_id = struct.unpack('<H', block[7:9])[0]
                    unit_name = UNITS.get(unit_id, f'Unknown({unit_id})')
                    print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
                    print(f"    -> order={order}, x={x}, y={y}, unit={unit_id}={unit_name}")
            count_0c += 1

    # Check 0x26 format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x26 data format")
    print("="*80)

    count_26 = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x26:
            if count_26 < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:15])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_26 += 1

    # Check 0x2b format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x2b data format")
    print("="*80)

    count_2b = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x2b:
            if count_2b < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:15])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_2b += 1

    # Check 0x1e format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x1e data format")
    print("="*80)

    count_1e = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x1e:
            if count_1e < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:15])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_1e += 1

    # Check 0x25 format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x25 data format")
    print("="*80)

    count_25 = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x25:
            if count_25 < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:15])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_25 += 1

    # Check 0x65 format
    print("\n" + "="*80)
    print("DETAILED: Analyzing 0x65 data format")
    print("="*80)

    count_65 = 0
    for frame, block in all_blocks:
        if len(block) >= 2 and block[1] == 0x65:
            if count_65 < 20:
                hex_data = ' '.join(f'{b:02x}' for b in block[:25])
                print(f"  Frame {frame:5d}, size={len(block):3d}: {hex_data}")
            count_65 += 1


if __name__ == '__main__':
    main()
