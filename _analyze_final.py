"""
Final analysis: Build and validate the correct CMD_SIZES mapping
by systematic pattern analysis of all action IDs.
"""

import struct
import zlib
from collections import defaultdict, Counter
from pathlib import Path

REPLAY_PATH = Path(r"D:\pypy\star_record\replays\samples\2026-02-25@015428_kimsabuho(t)_vs_HM_sSak(t).rep")

UNITS = {
    0: 'Marine', 1: 'Ghost', 2: 'Vulture', 3: 'Goliath', 4: 'Goliath Turret',
    5: 'Siege Tank (Tank)', 6: 'Tank Turret', 7: 'SCV', 8: 'Wraith', 9: 'Science Vessel',
    10: 'Dropship', 11: 'Battlecruiser', 12: 'Spider Mine', 13: 'Nuclear Missile',
    14: 'Civilian', 30: 'Siege Tank (Siege)', 32: 'Firebat', 34: 'Medic', 58: 'Valkyrie',
    35: 'Larva', 36: 'Egg', 37: 'Zergling', 38: 'Hydralisk', 39: 'Ultralisk',
    41: 'Drone', 42: 'Overlord', 43: 'Mutalisk', 44: 'Guardian', 45: 'Queen',
    46: 'Defiler', 47: 'Scourge', 60: 'Zealot', 61: 'Dragoon', 62: 'Lurker',
    63: 'Archon', 64: 'Shuttle', 65: 'Scout', 66: 'Arbiter', 67: 'Carrier',
    68: 'Interceptor', 69: 'Dark Templar', 70: 'Dark Archon', 71: 'Probe',
    72: 'Reaver', 73: 'Observer', 74: 'Scarab', 83: 'Corsair', 84: 'High Templar',
    106: 'Command Center', 107: 'Comsat Station', 108: 'Nuclear Silo',
    109: 'Supply Depot', 110: 'Refinery', 111: 'Barracks', 112: 'Academy',
    113: 'Factory', 114: 'Starport', 115: 'Control Tower', 116: 'Science Facility',
    117: 'Covert Ops', 118: 'Physics Lab', 120: 'Machine Shop',
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

TECH_NAMES = {
    0: 'Stim Packs', 1: 'Lockdown', 2: 'EMP Shockwave', 3: 'Spider Mines',
    4: 'Scanner Sweep', 5: 'Tank Siege Mode', 6: 'Defensive Matrix',
    7: 'Irradiate', 8: 'Yamato Gun', 9: 'Cloaking Field', 10: 'Personnel Cloaking',
    11: 'Burrowing', 12: 'Infestation', 13: 'Spawn Broodlings',
    14: 'Dark Swarm', 15: 'Plague', 16: 'Consume', 17: 'Ensnare',
    18: 'Parasite', 19: 'Psionic Storm', 20: 'Hallucination',
    21: 'Recall', 22: 'Stasis Field', 23: 'Archon Warp',
    24: 'Restoration', 25: 'Disruption Web', 27: 'Mind Control',
    30: 'Optical Flare', 31: 'Maelstrom', 32: 'Lurker Aspect',
    34: 'Healing',
}

UPGRADE_NAMES = {
    0: 'Terran Infantry Armor', 1: 'Terran Vehicle Plating',
    2: 'Terran Ship Plating', 3: 'Zerg Carapace',
    4: 'Zerg Flyer Carapace', 5: 'Protoss Ground Armor',
    6: 'Protoss Air Armor', 7: 'Terran Infantry Weapons',
    8: 'Terran Vehicle Weapons', 9: 'Terran Ship Weapons',
    10: 'Zerg Melee Attacks', 11: 'Zerg Missile Attacks',
    12: 'Zerg Flyer Attacks', 13: 'Protoss Ground Weapons',
    14: 'Protoss Air Weapons', 15: 'Protoss Plasma Shields',
    16: 'U-238 Shells', 17: 'Ion Thrusters',
    19: 'Titan Reactor', 22: 'Ocular Implants',
    23: 'Moebius Reactor', 24: 'Apollo Reactor',
    25: 'Colossus Reactor', 27: 'Ventral Sacs',
    28: 'Antennae', 29: 'Pneumatized Carapace', 30: 'Metabolic Boost',
    31: 'Adrenal Glands', 32: 'Muscular Augments', 33: 'Grooved Spines',
    34: 'Gamete Meiosis', 35: 'Metasynaptic Node',
    36: 'Singularity Charge', 37: 'Leg Enhancements',
    38: 'Scarab Damage', 39: 'Reaver Capacity', 40: 'Gravitic Drive',
    41: 'Sensor Array', 42: 'Gravitic Boosters', 43: 'Khaydarin Amulet',
    44: 'Apial Sensors', 45: 'Gravitic Thrusters',
    46: 'Carrier Capacity', 47: 'Khaydarin Core',
    49: 'Argus Jewel', 51: 'Argus Talisman',
    52: 'Caduceus Reactor', 53: 'Chitinous Plating',
    54: 'Anabolic Synthesis', 55: 'Charon Boosters',
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


def main():
    with open(REPLAY_PATH, 'rb') as f:
        raw_data = f.read()

    all_blocks = parse_all_blocks(raw_data)
    print(f"Total frame blocks: {len(all_blocks)}")

    # ================================================================
    # Analysis of each action ID from raw data patterns:
    # ================================================================
    #
    # 0x0c: 7 bytes data. Validated as Build (order + x + y + unit_id). CONFIRMED.
    #   Example: 0c 1e 75 00 0a 00 6d 00 = Build order=30, x=117, y=10, unit=109(Supply Depot)
    #
    # 0x13: 2 bytes data. CONFIRMED as Hotkey (type=0|1, group=0-9).
    #   Examples: 13 00 05, 13 01 01, 13 00 03
    #
    # 0x18: 0 bytes data. Only 2 occurrences. Could be Stop.
    #   Examples appear as sole command: "00 18"
    #
    # 0x1a: 1 byte data (always 00). Could be something with 1 byte.
    #   Wait -- looking at 0x1a samples:
    #   "00 1a 00" (size 3, exactly 1 byte after)
    #   BUT some have more: "01 1a 00 00 60..." - that's 1 byte data + next cmd starts with 00 60
    #   So 0x1a has 0 bytes data? Let me re-check.
    #   Actually "01 1a 00" = player=1, action=0x1a, then data=00 (1 byte)?
    #   Or player=1, action=0x1a, data=empty, then next cmd: player=0, ...?
    #   Block size is 3 in some cases: "00 1a 00" = player(0) + action(0x1a) + 1 byte data.
    #   But in "01 1a 00 00 60...": if 1a has 0 bytes, next would be player=00 action=00 which is KeepAlive(0 bytes), then 60 is next player... nah.
    #   If 1a has 1 byte, then: player=1, action=0x1a, data=00, next: player=0, action=0x60, ...
    #   That makes more sense! 0x1a has 1 byte data.
    #
    # Wait, actually let me look more carefully at the context.
    # "01 1a 00 00 60 1e 01 2f 0e 33 2d 00 00 e4 00 00" (size 16)
    # If 0x1a has 0 bytes: P=1 A=1a | P=0 A=0 (KeepAlive) | next byte 60... but 60 isn't a valid player_id
    # If 0x1a has 1 byte(00): P=1 A=1a D=00 | P=0 A=60 D=... YES, 0x60 is the RightClick(RM)
    # If 0x60 takes 11 bytes: 1e 01 2f 0e 33 2d 00 00 e4 00 00 = 11 bytes. Total = 3 + 13 = 16. EXACT MATCH!
    #
    # So 0x1a has 1 byte data.
    # But wait... "00 1a 00" (size 3) also works with 1 byte data: P=0 A=1a D=00. Total=3. Match.
    #
    # 0x1e: 1 byte data.
    #   "01 1e 00" (size 3): P=1, A=1e, D=00. 3 bytes total. Match.
    #   "01 1e 00 00 60 21 01 f1 0e bc 2c 00 00 e4 00" (size 16-1=15? wait size=16)
    #   Actually the output says "size= 16" but let me recount: 01 1e 00 00 60 21 01 f1 0e bc 2c 00 00 e4 00 = 15 bytes
    #   Hmm, there must be one more byte. Let me check again.
    #   If 0x1e has 1 byte(00): P=1 A=1e D=00 | P=0 A=60 D=... 0x60 with 11 bytes: 21 01 f1 0e bc 2c 00 00 e4 00 XX
    #   16 - 3 - 2 = 11 bytes for 0x60 data. So 0x60 data = 21 01 f1 0e bc 2c 00 00 e4 00 (that's 10 bytes only).
    #   Hmm, 16 bytes total, 3 bytes for first cmd, leaves 13 for second cmd.
    #   P=0 A=60 + 11 bytes = 13. So 0x60 has 11 bytes data. Total = 3 + 13 = 16. EXACT!
    #   Wait but the display showed only 15 hex bytes for that sample. The sample display was truncated.
    #   Let me trust the size field.
    #
    # Actually wait - looking at the output again for 0x1e:
    #   "Frame   174, size= 16: 01 1e 00 00 60 21 01 f1 0e bc 2c 00 00 e4 00"
    #   That's only 15 hex values shown. There must be a 16th byte that got cut off in display.
    #   If 0x1e=1byte and 0x60=11bytes: 3 + 13 = 16. Correct.
    #
    # But WAIT: is 0x1e actually 1 byte? Let me check 0x25 which also shows this pattern:
    #   "00 25 00" (size 3) -> 0x25 has 1 byte data.
    #   "00 25 01" (size 3) -> data byte is 01.
    # So 0x25 has 1 byte data where the byte is 0 or 1. Could be CancelTrain(slot?)
    # Actually in classic BW, CancelTrain has 2 bytes (slot as uint16).
    # But this data only shows 1 byte.
    #
    # Let me reconsider. Maybe 0x1e has 0 bytes and the 00 after it is the next player_id.
    # "01 1e | 00 60 21 01 f1 0e bc 2c 00 00 e4 00 ??" = 2 + (2+11) = 15... doesn't match size 16.
    # "01 1e | 00 60 21 01 f1 0e bc 2c 00 00 e4 00 ?? ??" hmm no.
    # If 0x60 has 13 bytes (not 11)?: 2 + 2 + 13 = 17, doesn't match 16.
    #
    # Let me try another approach: if 0x1e has 1 byte:
    # "01 1e 00 | 00 60 ..." = 3 + 0x60 cmd = 3 + 13 = 16. Works!
    # 0x60 = 11 bytes data (2 header + 11 data = 13 per cmd). 3 + 13 = 16. Perfect.
    #
    # Actually, looking at 0x60 standalone blocks:
    # "01 60 72 0f 2e 01 00 00 00 00 e4 00 00" (size 13) = 2 + 11 = 13. YES. 0x60 = 11 bytes data.
    #
    # So:
    # 0x18: 0 bytes (Stop - only 2 occurrences in a TvT makes sense as rarely used explicitly)
    # 0x1a: Looking again... maybe it's 0 bytes and the next byte is player 0?
    #   "00 1a | 00 ..." hmm but block size is 3, and "00 1a" is only 2 bytes. Need 3.
    #   So either 0x1a has 1 byte, or the block has trailing garbage.
    #   All 0x1a examples: size 3 has "XX 1a 00". If 0x1a = 0 bytes, leftover byte = 00.
    #   But that would mean imperfect parse. Let me test both in the final hypothesis.
    #
    # Actually let me look at 0x25 more carefully. Classic BW mapping:
    # If there's an offset, 0x25 could map to various things.
    # 0x25 data is 1 byte (00 or 01). This looks like it could be Siege/Unsiege (0 bytes in classic)
    # or Unload All (0 bytes in classic), or Cancel Train (2 bytes in classic - but we see 1 byte here).
    #
    # Let me check: in the +5 hypothesis, what would 0x25 be?
    # Classic 0x20 = Unload All -> +5 = 0x25. Unload All has 0 bytes.
    # But 0x25 shows 1 byte. Hmm.
    # Classic 0x1F = Train Fighter -> +5 = 0x24. Train Fighter has 0 bytes.
    # Classic 0x1E = Siege -> +5 = 0x23. Siege has 0 bytes.
    # Classic 0x1D = Unsiege -> +5 = 0x22. Unsiege has 0 bytes.
    #
    # With +5 offset, 0x25 = classic 0x20 = Unload All = 0 bytes.
    # But data shows 1 byte for 0x25. Could Remastered have added an extra byte?
    # Actually, looking at the output for 0x25:
    #   "00 25 00" and "00 25 01"
    # The values 00 and 01 could be: position/mode for unload?
    # OR this could be CancelTrain with 1 byte slot number (instead of 2 bytes).
    #
    # Let me try parsing with my best hypothesis and see what parse rate we get.

    # From the analysis, let me also look at 0x20:
    # "01 20 00 00" (size 4? no, samples show data like "00 00", "fe 00", etc.)
    # Actually the data field shows "00 00", "fe 00", "02 00 01 13 01 06" etc.
    # "01 20 fe 00" (size 4) = 2 header + 2 data = 4. So 0x20 has 2 bytes.
    # "01 20 02 00 01 13 01 06" = P=1 A=20 D=02,00 | P=1 A=13 D=01,06. Total = 4+4 = 8. Check size!
    # Sample says size=6... hmm. Let me look again.
    # Wait the sample shows: "Frame  5500, P1: 00 00" - this is the DATA after P+A, so data = "00 00" = 2 bytes.
    # And "Frame 10225, P1: 02 00 01 13 01 06" - data starts at "02 00 01 13 01 06".
    # If 0x20 = 2 bytes: data = 02 00, next cmd: P=1 A=13 D=01,06. Total = (2+2) + (2+2) = 8. Need to check block size.
    # The original analysis just showed data field, not full block. Let me trust the pattern.
    # 0x20 = 2 bytes data. This maps to CancelTrain (slot as uint16)? In BW, CancelTrain=0x19 has 2 bytes.

    # Let me also look at 0x21:
    # "00 21 00" - 1 byte data (always 00). What could this be?
    # 5 occurrences total. 0x21 with +5 offset = classic 0x1C = Unit Morph (2 bytes).
    # But we only see 1 byte. Hmm.
    # Wait actually let me look at the raw block sizes to verify.
    # "Frame 24155, P1: 00" - data = just "00". Size must be 3 (2 header + 1 byte).
    # If the block is exactly size 3, 0x21 has 1 byte.

    # 0x22: "00 22 00" - same pattern, 1 byte data. 2 occurrences.
    #   With +5 offset: classic 0x1D = Unsiege (0 bytes). But we see 1 byte.

    # Pattern emerging: it seems like Remastered adds an extra byte (padding? flags?) to some commands.
    # Many zero-byte classic commands become 1-byte in Remastered?

    # Let me look at this from a different angle. Check what the screp Go source
    # actually says about sizes.

    # Based on the exhaustive data analysis, here's my EMPIRICAL hypothesis:
    EMPIRICAL_SIZES = {
        0x05: 0,           # KeepAlive (if it appears)
        0x09: 'select',    # Select: count(1) + N*2 unit_ids
        0x0a: 'select',    # Shift Select
        0x0b: 'select',    # Shift Deselect
        0x0c: 7,           # Build: order(1)+x(2)+y(2)+unit(2) - CONFIRMED
        0x0d: 2,           # Vision
        0x0e: 4,           # Alliance
        0x0f: 1,           # Game Speed
        0x10: 0,           # Pause
        0x11: 0,           # Resume
        0x12: 4,           # Cheat
        0x13: 2,           # Hotkey: type(1)+group(1) - CONFIRMED
        0x14: 9,           # Right Click: x(2)+y(2)+unit(2)+unk(2)+action(1)
        0x15: 9,           # Targeted Order
        0x16: 0,           # Cancel Build
        0x17: 0,           # Cancel Morph
        0x18: 0,           # Stop - CONFIRMED (0 bytes, 2 occurrences)
        0x19: 0,           # Carrier Stop
        0x1a: 0,           # Reaver Stop - NEED TO VERIFY
        0x1b: 0,           # Order Nothing
        0x1c: 0,           # Return Cargo
        0x1d: 2,           # Train: unit(2) -- possible but 0x1f seems to be Train
        0x1e: 1,           # Cancel Train: slot(1)?
        0x1f: 2,           # Train/Cloak? - CONFIRMED 2 bytes = unit IDs
        0x20: 2,           # Cancel Train (2 bytes)?
        0x21: 0,           # Unit Morph?
        0x22: 0,           # Unsiege?
        0x23: 0,           # Siege?
        0x24: 0,           # Train Fighter?
        0x25: 1,           # Unload All + 1 byte?
        0x26: 0,           # Unload (1 byte? or 0?)
        0x27: 0,           # Merge Archon
        0x28: 0,           # Hold Position
        0x29: 0,           # Burrow
        0x2a: 0,           # Unburrow
        0x2b: 0,           # Cancel Nuke
        0x2c: 4,           # Lift: x(2)+y(2)
        0x2d: 1,           # Research: tech(1)
        0x2e: 0,           # Cancel Research
        0x2f: 4,           # Upgrade? Actually screp says it's 1 byte. But data shows 4 bytes.
        0x30: 1,           # Cancel Upgrade? Data shows 1 byte
        0x31: 0,           # Cancel Addon
        0x32: 1,           # Building Morph: unit(1)? Data shows 1 byte values like 0x11, 0x08, 0x36
        0x33: 0,           # Stim
        0x34: 4,           # Sync: 4 bytes
        0x57: 'chat',      # Chat (Remaster)
        0x5c: 'select',    # Select (Remaster)
        # Remastered extended commands
        0x60: 11,          # Right Click (Remaster) - CONFIRMED 11 bytes
        0x61: 12,          # Targeted Order (Remaster) - CONFIRMED 12 bytes (14-2=12)
        0x62: 4,           # Select Delta? - 4 bytes data
        0x63: 'select',    # Select (Remaster) - CONFIRMED variable
        0x64: 'select',    # Shift Select (Remaster) - CONFIRMED variable
        0x65: 'select',    # Shift Deselect (Remaster) - CONFIRMED variable
        0x00: 0,           # KeepAlive (classic)
    }

    EMPIRICAL_NAMES = {
        0x00: 'KeepAlive(classic)', 0x05: 'KeepAlive',
        0x09: 'Select', 0x0a: 'ShiftSelect', 0x0b: 'ShiftDeselect',
        0x0c: 'Build', 0x0d: 'Vision', 0x0e: 'Alliance', 0x0f: 'GameSpeed',
        0x10: 'Pause', 0x11: 'Resume', 0x12: 'Cheat', 0x13: 'Hotkey',
        0x14: 'RightClick', 0x15: 'TargetedOrder',
        0x16: 'CancelBuild', 0x17: 'CancelMorph', 0x18: 'Stop',
        0x19: 'CarrierStop', 0x1a: 'ReaverStop', 0x1b: 'OrderNothing',
        0x1c: 'ReturnCargo', 0x1d: 'Train', 0x1e: 'CancelTrain',
        0x1f: 'Train(alt)/Cloak?', 0x20: 'Decloak/CancelTrain?',
        0x21: 'UnitMorph?', 0x22: 'Unsiege', 0x23: 'Siege',
        0x24: 'TrainFighter', 0x25: 'UnloadAll',
        0x26: 'Unload', 0x27: 'MergeArchon', 0x28: 'HoldPosition',
        0x29: 'Burrow', 0x2a: 'Unburrow', 0x2b: 'CancelNuke',
        0x2c: 'Lift', 0x2d: 'Research', 0x2e: 'CancelResearch',
        0x2f: 'Upgrade/Sync?', 0x30: 'CancelUpgrade', 0x31: 'CancelAddon',
        0x32: 'BuildingMorph', 0x33: 'Stim', 0x34: 'Sync',
        0x57: 'Chat(RM)', 0x5c: 'Select(RM)',
        0x60: 'RightClick(RM)', 0x61: 'TargetedOrder(RM)',
        0x62: 'SelectDelta?', 0x63: 'Select(RM2)', 0x64: 'ShiftSelect(RM2)',
        0x65: 'ShiftDeselect(RM2)',
    }

    # Test this hypothesis
    print("\n" + "="*80)
    print("TESTING EMPIRICAL HYPOTHESIS")
    print("="*80)

    action_counts = Counter()
    player_action_counts = {0: Counter(), 1: Counter()}
    parse_failures = 0
    total_cmds = 0
    blocks_fully_parsed = 0
    blocks_partial = 0
    failed_blocks = []

    # Validation data
    hotkey_data = []
    train_data_0x1d = []
    train_data_0x1f = []
    build_data = []
    right_click_60 = []
    targeted_order_61 = []
    upgrade_data = []
    research_data = []
    morph_data = []

    for frame, block in all_blocks:
        bpos = 0
        block_ok = True
        while bpos + 1 < len(block):
            player_id = block[bpos]
            action_id = block[bpos + 1]
            cmd_data_start = bpos + 2

            if not (0 <= player_id <= 11):
                block_ok = False
                break

            cmd_size = get_cmd_size(action_id, block, cmd_data_start, EMPIRICAL_SIZES)
            if cmd_size is None:
                block_ok = False
                parse_failures += 1
                if len(failed_blocks) < 20:
                    remaining = ' '.join(f'{b:02x}' for b in block[bpos:bpos+15])
                    failed_blocks.append(f"Frame {frame}, bpos={bpos}, action=0x{action_id:02x}: {remaining}")
                break

            cmd_end = cmd_data_start + cmd_size
            if cmd_end > len(block):
                block_ok = False
                parse_failures += 1
                if len(failed_blocks) < 20:
                    remaining = ' '.join(f'{b:02x}' for b in block[bpos:bpos+15])
                    failed_blocks.append(f"Frame {frame}, bpos={bpos}, action=0x{action_id:02x}, size={cmd_size}, need={cmd_end}, have={len(block)}: {remaining}")
                break

            payload = block[cmd_data_start:cmd_end]
            action_counts[action_id] += 1
            if player_id in (0, 1):
                player_action_counts[player_id][action_id] += 1
            total_cmds += 1

            # Collect validation data
            if action_id == 0x13 and len(payload) >= 2:
                hotkey_data.append((payload[0], payload[1], player_id))

            if action_id == 0x1d and len(payload) >= 2:
                uid = struct.unpack('<H', payload[0:2])[0]
                train_data_0x1d.append((uid, player_id))

            if action_id == 0x1f and len(payload) >= 2:
                uid = struct.unpack('<H', payload[0:2])[0]
                train_data_0x1f.append((uid, player_id))

            if action_id == 0x0c and len(payload) >= 7:
                order = payload[0]
                x = struct.unpack('<H', payload[1:3])[0]
                y = struct.unpack('<H', payload[3:5])[0]
                uid = struct.unpack('<H', payload[5:7])[0]
                build_data.append((order, x, y, uid, player_id))

            if action_id == 0x60 and len(payload) >= 4:
                x = struct.unpack('<H', payload[0:2])[0]
                y = struct.unpack('<H', payload[2:4])[0]
                right_click_60.append((x, y, player_id, payload))

            if action_id == 0x61 and len(payload) >= 4:
                x = struct.unpack('<H', payload[0:2])[0]
                y = struct.unpack('<H', payload[2:4])[0]
                targeted_order_61.append((x, y, player_id, payload))

            if action_id == 0x2f and len(payload) >= 1:
                upgrade_data.append((payload[0], player_id, payload))

            if action_id == 0x2d and len(payload) >= 1:
                research_data.append((payload[0], player_id))

            if action_id == 0x32 and len(payload) >= 1:
                morph_data.append((payload[0], player_id))

            bpos = cmd_end

        if block_ok and bpos == len(block):
            blocks_fully_parsed += 1
        elif bpos > 0 and not block_ok:
            blocks_partial += 1

    print(f"\nTotal commands parsed: {total_cmds}")
    print(f"Parse failures: {parse_failures}")
    print(f"Blocks fully parsed: {blocks_fully_parsed}/{len(all_blocks)} ({blocks_fully_parsed/len(all_blocks)*100:.1f}%)")
    print(f"Blocks partially parsed: {blocks_partial}")

    if failed_blocks:
        print(f"\nFirst parse failures:")
        for fb in failed_blocks:
            print(f"  {fb}")

    print(f"\nAction distribution:")
    for action_id, count in action_counts.most_common(40):
        name = EMPIRICAL_NAMES.get(action_id, f'Unknown(0x{action_id:02x})')
        p0 = player_action_counts[0].get(action_id, 0)
        p1 = player_action_counts[1].get(action_id, 0)
        print(f"  0x{action_id:02x} {name:35s}: {count:6d}  (P0={p0:5d}, P1={p1:5d})")

    # Hotkey validation
    if hotkey_data:
        valid = sum(1 for t, g, _ in hotkey_data if t in (0, 1) and 0 <= g <= 9)
        print(f"\n--- Hotkey validation: {valid}/{len(hotkey_data)} valid ({valid/len(hotkey_data)*100:.1f}%) ---")
        types = Counter(h[0] for h in hotkey_data)
        groups = Counter(h[1] for h in hotkey_data)
        print(f"  Types: {dict(types.most_common(5))}")
        print(f"  Groups: {dict(sorted(groups.items()))}")

    # Train 0x1f validation
    if train_data_0x1f:
        valid = sum(1 for uid, _ in train_data_0x1f if uid in UNITS)
        print(f"\n--- Train(0x1f) validation: {valid}/{len(train_data_0x1f)} valid ({valid/len(train_data_0x1f)*100:.1f}%) ---")
        unit_counts = Counter()
        for uid, pid in train_data_0x1f:
            unit_counts[UNITS.get(uid, f'Unknown({uid})')] += 1
        for unit, count in unit_counts.most_common(15):
            print(f"  {unit}: {count}")

    # Train 0x1d validation
    if train_data_0x1d:
        valid = sum(1 for uid, _ in train_data_0x1d if uid in UNITS)
        print(f"\n--- Train(0x1d) validation: {valid}/{len(train_data_0x1d)} valid ({valid/len(train_data_0x1d)*100:.1f}%) ---")
        unit_counts = Counter()
        for uid, pid in train_data_0x1d:
            unit_counts[UNITS.get(uid, f'Unknown({uid})')] += 1
        for unit, count in unit_counts.most_common(15):
            print(f"  {unit}: {count}")

    # Build validation
    if build_data:
        valid = sum(1 for _, x, y, uid, _ in build_data if uid in UNITS)
        print(f"\n--- Build validation: {valid}/{len(build_data)} valid ---")
        bld_counts = Counter()
        for _, x, y, uid, pid in build_data:
            bld_counts[UNITS.get(uid, f'Unknown({uid})')] += 1
        for bld, count in bld_counts.most_common(20):
            print(f"  {bld}: {count}")

    # Right Click 0x60 validation
    if right_click_60:
        # Check if x,y values look like map coordinates
        # SC map is typically 128x128 tiles, pixel coords would be up to 128*32=4096
        valid = sum(1 for x, y, _, _ in right_click_60 if 0 < x < 5000 and 0 < y < 5000)
        print(f"\n--- RightClick(0x60) validation: {valid}/{len(right_click_60)} valid coords ---")
        print(f"  Sample coords: {[(x,y) for x,y,_,_ in right_click_60[:10]]}")
        # Show full payloads for a few
        print(f"  Sample payloads:")
        for x, y, pid, payload in right_click_60[:5]:
            hex_p = ' '.join(f'{b:02x}' for b in payload)
            print(f"    P{pid}: x={x}, y={y}, payload={hex_p}")

    # Targeted Order 0x61 validation
    if targeted_order_61:
        valid = sum(1 for x, y, _, _ in targeted_order_61 if 0 < x < 5000 and 0 < y < 5000)
        print(f"\n--- TargetedOrder(0x61) validation: {valid}/{len(targeted_order_61)} valid coords ---")
        print(f"  Sample payloads:")
        for x, y, pid, payload in targeted_order_61[:5]:
            hex_p = ' '.join(f'{b:02x}' for b in payload)
            print(f"    P{pid}: x={x}, y={y}, payload={hex_p}")

    # Upgrade 0x2f validation
    if upgrade_data:
        print(f"\n--- Upgrade(0x2f) data ---")
        print(f"  {len(upgrade_data)} entries")
        for val, pid, payload in upgrade_data[:10]:
            hex_p = ' '.join(f'{b:02x}' for b in payload)
            upgrade_name = UPGRADE_NAMES.get(val, f'Unknown({val})')
            print(f"    P{pid}: first_byte={val}={upgrade_name}, payload={hex_p}")

    # Research 0x2d validation
    if research_data:
        print(f"\n--- Research(0x2d) data ---")
        for val, pid in research_data:
            tech_name = TECH_NAMES.get(val, f'Unknown({val})')
            print(f"    P{pid}: tech={val}={tech_name}")

    # Building Morph 0x32 validation
    if morph_data:
        print(f"\n--- BuildingMorph(0x32) data ---")
        for val, pid in morph_data:
            # Value might be a unit ID byte (not uint16)
            unit_name = UNITS.get(val, f'Unknown({val})')
            print(f"    P{pid}: value={val}=0x{val:02x} ({unit_name})")

    # ================================================================
    # Now let me also check what happens with adjustments to problematic IDs
    # ================================================================

    # Check 0x1a more carefully
    print("\n" + "="*80)
    print("CHECKING: 0x1a sizing (0 vs 1 byte)")
    print("="*80)

    # Try with 0x1a = 0 bytes
    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x1a] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x1a:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x1a = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x26 sizing
    print("\n" + "="*80)
    print("CHECKING: 0x26 sizing (0 vs 1 byte)")
    print("="*80)

    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x26] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x26:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x26 = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x2b sizing
    print("\n" + "="*80)
    print("CHECKING: 0x2b sizing (0 vs 1 byte)")
    print("="*80)

    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x2b] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x2b:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x2b = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x21 sizing
    print("\n" + "="*80)
    print("CHECKING: 0x21 sizing (0 vs 1 byte)")
    print("="*80)

    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x21] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x21:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x21 = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x22 sizing
    print("\nCHECKING: 0x22 sizing (0 vs 1 byte)")
    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x22] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x22:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x22 = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x28 sizing
    print("\nCHECKING: 0x28 sizing (0 vs 1 byte)")
    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x28] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x28:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x28 = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")

    # Check 0x25 sizing
    print("\nCHECKING: 0x25 sizing (0 vs 1 byte)")
    for size_to_try in [0, 1]:
        test_sizes = EMPIRICAL_SIZES.copy()
        test_sizes[0x25] = size_to_try
        success = 0
        fail = 0
        for frame, block in all_blocks:
            if len(block) >= 2 and block[1] == 0x25:
                bpos = 0
                ok = True
                while bpos + 1 < len(block):
                    pid = block[bpos]
                    aid = block[bpos + 1]
                    if not (0 <= pid <= 11):
                        ok = False
                        break
                    cs = get_cmd_size(aid, block, bpos+2, test_sizes)
                    if cs is None:
                        ok = False
                        break
                    ce = bpos + 2 + cs
                    if ce > len(block):
                        ok = False
                        break
                    bpos = ce
                if ok and bpos == len(block):
                    success += 1
                else:
                    fail += 1
        print(f"  0x25 = {size_to_try} byte(s): {success} blocks OK, {fail} blocks failed")


if __name__ == '__main__':
    main()
