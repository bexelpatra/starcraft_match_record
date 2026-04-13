"""
StarCraft Brood War / Remastered Replay Parser
Parses .rep files and extracts all game information
Saves parsed data to JSON and text files
"""

import struct
import zlib
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class SCReplayParser:
    # Constants
    RACES = {
        0: 'Zerg', 1: 'Terran', 2: 'Protoss', 3: 'Invalid',
        4: 'Invalid', 5: 'User Select', 6: 'Random', 7: 'None'
    }

    GAME_TYPES = {
        0x00: 'None', 0x01: 'Custom', 0x02: 'Melee', 0x03: 'Free For All',
        0x04: 'One on One', 0x05: 'Capture The Flag', 0x06: 'Greed',
        0x07: 'Slaughter', 0x08: 'Sudden Death', 0x09: 'Ladder',
        0x0A: 'Use Map Settings', 0x0B: 'Team Melee', 0x0C: 'Team Free For All',
        0x0D: 'Team Capture The Flag', 0x0F: 'Top vs Bottom'
    }

    PLAYER_TYPES = {
        0: 'Inactive', 1: 'Computer', 2: 'Human', 3: 'Rescue Passive',
        4: 'Unused', 5: 'Computer', 6: 'Human (Open)', 7: 'Neutral', 8: 'Closed'
    }

    TILESETS = {
        0: 'Badlands', 1: 'Space Platform', 2: 'Installation', 3: 'Ashworld',
        4: 'Jungle', 5: 'Desert', 6: 'Ice', 7: 'Twilight'
    }

    # Command IDs
    COMMANDS = {
        0x00: 'Keep Alive', 0x01: 'Save Game', 0x02: 'Load Game', 0x03: 'Restart Game',
        0x04: 'Select', 0x05: 'Shift Select', 0x06: 'Shift Deselect', 0x07: 'Build',
        0x08: 'Vision', 0x09: 'Alliance', 0x0A: 'Game Speed', 0x0B: 'Pause',
        0x0C: 'Resume', 0x0D: 'Cheat', 0x0E: 'Hotkey', 0x0F: 'Right Click',
        0x10: 'Targeted Order', 0x11: 'Cancel Build', 0x12: 'Cancel Morph', 0x13: 'Stop',
        0x14: 'Carrier Stop', 0x15: 'Reaver Stop', 0x16: 'Order Nothing', 0x17: 'Return Cargo',
        0x18: 'Train', 0x19: 'Cancel Train', 0x1A: 'Cloak', 0x1B: 'Decloak',
        0x1C: 'Unit Morph', 0x1D: 'Unsiege', 0x1E: 'Siege', 0x1F: 'Train Fighter',
        0x20: 'Unload All', 0x21: 'Unload', 0x22: 'Merge Archon', 0x23: 'Hold Position',
        0x24: 'Burrow', 0x25: 'Unburrow', 0x26: 'Cancel Nuke', 0x27: 'Lift',
        0x28: 'Research', 0x29: 'Cancel Research', 0x2A: 'Upgrade', 0x2B: 'Cancel Upgrade',
        0x2C: 'Cancel Addon', 0x2D: 'Building Morph', 0x2E: 'Stim', 0x2F: 'Sync',
        0x35: 'Start Game', 0x37: 'Change Game Slot', 0x3A: 'Change Race',
        0x48: 'Latency', 0x49: 'Replay Speed', 0x4A: 'Leave Game', 0x4C: 'Minimap Ping',
        0x4D: 'Merge Dark Archon', 0x50: 'Make Game Public', 0x52: 'Chat',
        0x54: 'Right Click (Remaster)', 0x55: 'Targeted Order (Remaster)',
        0x56: 'Unload (Remaster)', 0x57: 'Select (Remaster)',
        0x58: 'Select Delta Add', 0x59: 'Select Delta Del', 0x5A: 'Chat (Remaster)',
        0x5C: 'Cancel Train (Remaster)', 0x60: 'Select (Remaster2)',
        0x61: 'Shift Select (Remaster)', 0x62: 'Shift Deselect (Remaster)',
        0x63: 'Right Click (Remaster2)', 0x64: 'Targeted Order (Remaster2)',
        0x65: 'Target Order Alt (Remaster)',
    }

    # Command sizes (bytes after player_id + action_id header)
    # None = unknown/skip rest of block, 'select' = variable select, 'select_delta' = variable delta
    # 'chat' = null-terminated string
    CMD_SIZES = {
        0x00: 0,   # Keep Alive
        0x01: 0,   # Save Game (actually variable, but rare)
        0x02: 0,   # Load Game
        0x03: 0,   # Restart Game
        0x04: 'select',  # Select: 1 + N*2
        0x05: 'select',  # Shift Select
        0x06: 'select',  # Shift Deselect
        0x07: 7,   # Build: order(1) + x(2) + y(2) + unit(2)
        0x08: 2,   # Vision
        0x09: 4,   # Alliance
        0x0A: 1,   # Game Speed
        0x0B: 0,   # Pause
        0x0C: 0,   # Resume
        0x0D: 4,   # Cheat
        0x0E: 2,   # Hotkey: type(1) + group(1)
        0x0F: 9,   # Right Click: x(2)+y(2)+unit(2)+unknown(2)+action(1)
        0x10: 9,   # Targeted Order
        0x11: 0,   # Cancel Build
        0x12: 0,   # Cancel Morph
        0x13: 0,   # Stop
        0x14: 0,   # Carrier Stop
        0x15: 0,   # Reaver Stop
        0x16: 0,   # Order Nothing
        0x17: 0,   # Return Cargo
        0x18: 2,   # Train: unit(2)
        0x19: 2,   # Cancel Train: slot(2)
        0x1A: 0,   # Cloak
        0x1B: 0,   # Decloak
        0x1C: 2,   # Unit Morph: unit(2)
        0x1D: 0,   # Unsiege
        0x1E: 0,   # Siege
        0x1F: 0,   # Train Fighter
        0x20: 0,   # Unload All
        0x21: 2,   # Unload: unit(2)
        0x22: 0,   # Merge Archon
        0x23: 0,   # Hold Position
        0x24: 0,   # Burrow
        0x25: 0,   # Unburrow
        0x26: 0,   # Cancel Nuke
        0x27: 4,   # Lift: x(2)+y(2)
        0x28: 1,   # Research: tech(1)
        0x29: 0,   # Cancel Research
        0x2A: 1,   # Upgrade: upgrade(1)
        0x2B: 0,   # Cancel Upgrade
        0x2C: 0,   # Cancel Addon
        0x2D: 2,   # Building Morph: unit(2)
        0x2E: 0,   # Stim
        0x2F: 4,   # Sync
        0x35: 0,   # Start Game
        0x37: 5,   # Change Game Slot
        0x3A: 1,   # Change Race
        0x48: 1,   # Latency
        0x49: 1,   # Replay Speed
        0x4A: 1,   # Leave Game: reason(1)
        0x4C: 4,   # Minimap Ping: x(2)+y(2)
        0x4D: 0,   # Merge Dark Archon
        0x50: 0,   # Make Game Public
        0x52: 'chat',  # Chat
        0x54: 9,   # Right Click (Remaster)
        0x55: 9,   # Targeted Order (Remaster)
        0x56: 2,   # Unload (Remaster)
        0x57: 'select',  # Select (Remaster)
        0x58: 'select_delta',  # Select Delta Add
        0x59: 'select_delta',  # Select Delta Del
        0x5A: 'chat',  # Chat (Remaster)
        0x5C: 2,   # Cancel Train (Remaster)
        0x60: 'select',  # Select (Remaster2)
        0x61: 'select',  # Shift Select (Remaster)
        0x62: 'select',  # Shift Deselect (Remaster)
        0x63: 9,   # Right Click (Remaster2)
        0x64: 9,   # Targeted Order (Remaster2)
        0x65: 9,   # Target Order Alt (Remaster)
    }

    # Unit IDs
    UNITS = {
        # Terran Units
        0: 'Marine', 1: 'Ghost', 2: 'Vulture', 3: 'Goliath', 4: 'Goliath Turret',
        5: 'Siege Tank (Tank)', 6: 'Tank Turret', 7: 'SCV', 8: 'Wraith', 9: 'Science Vessel',
        10: 'Dropship', 11: 'Battlecruiser', 12: 'Vulture Spider Mine', 13: 'Nuclear Missile',
        14: 'Civilian', 30: 'Siege Tank (Siege)', 32: 'Firebat', 34: 'Medic', 58: 'Valkyrie',

        # Zerg Units
        35: 'Larva', 36: 'Egg', 37: 'Zergling', 38: 'Hydralisk', 39: 'Ultralisk',
        40: 'Broodling', 41: 'Drone', 42: 'Overlord', 43: 'Mutalisk', 44: 'Guardian',
        45: 'Queen', 46: 'Defiler', 47: 'Scourge', 48: 'Torrasque', 49: 'Infested Terran',
        50: 'Infested Kerrigan', 51: 'Unclean One', 52: 'Hunter Killer', 53: 'Devouring One',
        54: 'Kukulza (Mutalisk)', 55: 'Kukulza (Guardian)', 56: 'Yggdrasill', 57: 'Cocoon',
        59: 'Lurker Egg', 62: 'Lurker', 103: 'Lurker',

        # Protoss Units
        60: 'Zealot', 61: 'Dragoon', 63: 'Archon', 64: 'Shuttle', 65: 'Scout',
        66: 'Arbiter', 67: 'Carrier', 68: 'Interceptor', 69: 'Dark Templar',
        70: 'Dark Archon', 71: 'Probe', 72: 'Reaver', 73: 'Observer', 74: 'Scarab',
        83: 'Corsair', 84: 'High Templar', 85: 'Dark Templar (Hero)',
        86: 'Danimoth', 87: 'Aldaris', 88: 'Artanis',

        # Terran Buildings
        106: 'Command Center', 107: 'Comsat Station', 108: 'Nuclear Silo',
        109: 'Supply Depot', 110: 'Refinery', 111: 'Barracks', 112: 'Academy',
        113: 'Factory', 114: 'Starport', 115: 'Control Tower', 116: 'Science Facility',
        117: 'Covert Ops', 118: 'Physics Lab', 119: 'Starbase', 120: 'Machine Shop',
        121: 'Repair Bay', 122: 'Engineering Bay', 123: 'Armory', 124: 'Missile Turret', 125: 'Bunker',

        # Zerg Buildings
        130: 'Infested CC', 131: 'Hatchery', 132: 'Lair', 133: 'Hive',
        134: 'Nydus Canal', 135: 'Hydralisk Den', 136: 'Defiler Mound',
        137: 'Greater Spire', 138: 'Queens Nest', 139: 'Evolution Chamber',
        140: 'Ultralisk Cavern', 141: 'Spire', 142: 'Spawning Pool',
        143: 'Creep Colony', 144: 'Spore Colony', 145: 'Sunken Colony', 146: 'Extractor',

        # Protoss Buildings
        149: 'Nexus', 150: 'Robotics Facility', 151: 'Pylon', 152: 'Assimilator',
        153: 'Observatory', 154: 'Gateway', 155: 'Gateway', 157: 'Photon Cannon',
        159: 'Citadel of Adun', 160: 'Cybernetics Core', 161: 'Templar Archives',
        162: 'Forge', 163: 'Stargate', 164: 'Stasis Cell', 165: 'Fleet Beacon',
        166: 'Arbiter Tribunal', 167: 'Robotics Support Bay', 168: 'Shield Battery',
    }

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.data = None
        self.zlib_blocks = []
        self.section_data = []

        # Parsed data
        self.header = {}
        self.game_info = {}
        self.players = []
        self.map_data = {}
        self.map_strings = []
        self.map_chunks = {}
        self.commands = []
        self.command_stats = defaultdict(lambda: defaultdict(int))
        self.player_stats = {}
        self.unit_production = defaultdict(lambda: defaultdict(int))
        self.chat_messages = []
        self.winner = None
        self.winner_method = None
        self.is_observer_replay = False

    def parse(self):
        """Parse the replay file"""
        with open(self.filepath, 'rb') as f:
            self.data = f.read()

        # Parse file header
        self._parse_file_header()

        # Find all zlib blocks
        self._find_zlib_blocks()

        # Parse game info (block 0)
        self._parse_game_info()

        # Parse commands
        self._parse_commands()

        # Parse map data
        self._parse_map_data()

        # Calculate statistics
        self._calculate_stats()

        # Determine winner
        self._determine_winner()

        return self

    def parse_header_only(self):
        """플레이어 정보만 빠르게 파싱한다. 게임 시작 직후 overlay용.

        전체 parse()와 달리 첫 번째 zlib 블록만 압축 해제하므로
        파일이 완전히 기록되지 않은 상태에서도 동작한다.

        Returns:
            self (players, game_info['game_type'] 등 부분적으로 채워진 상태)
        """
        try:
            with open(self.filepath, 'rb') as f:
                self.data = f.read()
        except OSError as e:
            raise ValueError(f"파일을 읽을 수 없습니다: {e}") from e

        if len(self.data) < 32:
            raise ValueError("파일이 너무 작습니다 (헤더 불완전)")

        # 파일 헤더 검증 (magic 체크 없이 관대하게)
        try:
            self._parse_file_header()
        except ValueError:
            # magic이 다를 수 있음 (게임 중에는 아직 미완성일 수 있음)
            pass

        # zlib 블록 탐색
        self._find_zlib_blocks()

        if not self.zlib_blocks:
            raise ValueError("zlib 블록을 찾을 수 없습니다 (파일이 아직 기록 중일 수 있음)")

        # 블록 0만 파싱 (game info + player names)
        self._parse_game_info()

        return self

    def _parse_file_header(self):
        """Parse the file header"""
        if len(self.data) < 32:
            raise ValueError("File too small to be a valid replay")

        self.header['crc'] = struct.unpack('<I', self.data[0:4])[0]
        self.header['engine_id'] = struct.unpack('<I', self.data[4:8])[0]
        self.header['section_count'] = struct.unpack('<I', self.data[8:12])[0]
        self.header['magic'] = self.data[12:16].decode('ascii', errors='ignore')

        if self.header['magic'] != 'seRS':
            raise ValueError("Not a valid StarCraft replay file")

        self.header['file_size'] = len(self.data)

    def _find_zlib_blocks(self):
        """Find all zlib compressed blocks"""
        self.zlib_blocks = []
        pos = 0
        while pos < len(self.data) - 6:
            if self.data[pos:pos+2] == b'\x78\x9c':
                expected = struct.unpack('<I', self.data[pos-4:pos])[0] if pos >= 4 else 0
                self.zlib_blocks.append({'pos': pos, 'expected_size': expected})
            pos += 1

        self.header['zlib_blocks'] = len(self.zlib_blocks)

    def _decompress_block(self, index):
        """Decompress a zlib block"""
        if index >= len(self.zlib_blocks):
            return None

        pos = self.zlib_blocks[index]['pos']

        try:
            # Try decompressing until end of file
            return zlib.decompress(self.data[pos:])
        except:
            # Try with explicit boundary
            if index + 1 < len(self.zlib_blocks):
                end = self.zlib_blocks[index + 1]['pos'] - 4
                try:
                    return zlib.decompress(self.data[pos:end])
                except:
                    pass
        return None

    def _parse_game_info(self):
        """Parse game info from block 0"""
        sec0 = self._decompress_block(0)
        if not sec0:
            return

        # Engine type
        self.game_info['engine'] = sec0[0] if len(sec0) > 0 else 0

        # Game frames (stored at offset 1-3)
        if len(sec0) > 3:
            self.game_info['total_frames'] = struct.unpack('<H', sec0[1:3])[0]
            frames = self.game_info['total_frames']
            self.game_info['duration_seconds'] = round(frames / 23.81, 1)
            minutes = int(frames / 23.81 // 60)
            seconds = int(frames / 23.81 % 60)
            self.game_info['duration'] = f"{minutes}m {seconds}s"

        # Map info
        if len(sec0) > 0x38:
            self.game_info['map_width'] = struct.unpack('<H', sec0[0x34:0x36])[0]
            self.game_info['map_height'] = struct.unpack('<H', sec0[0x36:0x38])[0]

            game_type_id = sec0[0x38]
            self.game_info['game_type_id'] = game_type_id
            self.game_info['game_type'] = self.GAME_TYPES.get(game_type_id, f'Unknown ({game_type_id})')

        # Parse players
        self._parse_players(sec0)

    def _parse_players(self, sec0):
        """Parse player information from section 0"""
        name_positions = [
            (0x48, 25),   # Player 1
            (0x118, 25),  # Player 2 (for 1v1)
        ]

        # Also try alternate positions
        alt_positions = [
            (0xF4, 25),   # Player 2 alternate
            (0x1A0, 25),  # Player 3
            (0x24C, 25),  # Player 4
        ]

        for i, (name_offset, max_len) in enumerate(name_positions):
            if name_offset + max_len <= len(sec0):
                name_bytes = sec0[name_offset:name_offset + max_len]
                name_end = name_bytes.find(b'\x00')
                if name_end > 0:
                    name = name_bytes[:name_end].decode('utf-8', errors='ignore')
                    if name and len(name) >= 1:
                        # Detect race from filename or other sources
                        race = self._detect_race(name, i)

                        self.players.append({
                            'id': i,
                            'name': name,
                            'race': race
                        })

        # Try alternate positions if we don't have 2 players
        if len(self.players) < 2:
            for name_offset, max_len in alt_positions:
                if name_offset + max_len <= len(sec0):
                    name_bytes = sec0[name_offset:name_offset + max_len]
                    name_end = name_bytes.find(b'\x00')
                    if name_end > 0:
                        name = name_bytes[:name_end].decode('utf-8', errors='ignore')
                        if name and len(name) >= 1 and not any(p['name'] == name for p in self.players):
                            race = self._detect_race(name, len(self.players))
                            self.players.append({
                                'id': len(self.players),
                                'name': name,
                                'race': race
                            })
                            if len(self.players) >= 2:
                                break

    def _detect_race(self, name, player_id):
        """Detect race from filename or player name"""
        filename = self.filepath.name.lower()

        # Check filename for race indicators
        if f'_{name.lower()}(t)' in filename.lower() or f'({name.lower()})(t)' in filename.lower():
            return 'Terran'
        elif f'_{name.lower()}(z)' in filename.lower() or f'({name.lower()})(z)' in filename.lower():
            return 'Zerg'
        elif f'_{name.lower()}(p)' in filename.lower() or f'({name.lower()})(p)' in filename.lower():
            return 'Protoss'

        # Check for (t), (z), (p) patterns after player names in filename
        parts = filename.split('_vs_')
        if len(parts) == 2:
            if player_id == 0 and '(t)' in parts[0]:
                return 'Terran'
            elif player_id == 0 and '(z)' in parts[0]:
                return 'Zerg'
            elif player_id == 0 and '(p)' in parts[0]:
                return 'Protoss'
            elif player_id == 1 and '(t)' in parts[1]:
                return 'Terran'
            elif player_id == 1 and '(z)' in parts[1]:
                return 'Zerg'
            elif player_id == 1 and '(p)' in parts[1]:
                return 'Protoss'

        return 'Unknown'

    def _find_map_data_start(self):
        """Find where map CHK data starts"""
        for i, block in enumerate(self.zlib_blocks):
            decompressed = self._decompress_block(i)
            if decompressed and len(decompressed) > 4:
                if decompressed[:4] in [b'VER ', b'TYPE', b'VCOD', b'OWNR']:
                    return i
        return len(self.zlib_blocks)

    def _get_cmd_size(self, action_id, block, offset):
        """Get the size of a command's data (after player_id + action_id).
        Returns number of bytes to skip, or None if unknown."""
        size_info = self.CMD_SIZES.get(action_id)

        if size_info is None:
            return None  # Unknown command, can't continue parsing block

        if isinstance(size_info, int):
            return size_info

        if size_info == 'select':
            # 1 byte count + N * 2 bytes unit IDs
            if offset < len(block):
                count = block[offset]
                return 1 + count * 2
            return None

        if size_info == 'select_delta':
            # 1 byte count + N * 4 bytes (unit ID + flags)
            if offset < len(block):
                count = block[offset]
                return 1 + count * 4
            return None

        if size_info == 'chat':
            # Null-terminated string
            null_pos = block.find(b'\x00', offset)
            if null_pos >= 0:
                return null_pos - offset + 1  # include the null byte
            return len(block) - offset  # rest of block if no null found

        return None

    def _parse_commands(self):
        """Parse game commands, iterating through all commands within each frame block"""
        map_start = self._find_map_data_start()

        # Build set of known player IDs
        known_player_ids = {p['id'] for p in self.players}

        # Collect all command data from blocks 1 to map_start
        cmd_data = b''
        for i in range(1, map_start):
            block = self._decompress_block(i)
            if block:
                cmd_data += block

        if not cmd_data:
            return

        pos = 0
        max_frame = 0
        leave_game_player = None
        leave_game_frame = 0
        player_last_action_frame = {}

        while pos < len(cmd_data) - 5:
            frame = struct.unpack('<I', cmd_data[pos:pos+4])[0]

            if frame > 100000:
                pos += 1
                continue

            block_size = cmd_data[pos+4]

            if block_size == 0 or pos + 5 + block_size > len(cmd_data):
                pos += 1
                continue

            cmd_block = cmd_data[pos+5:pos+5+block_size]
            pos += 5 + block_size

            # Iterate through all commands within this block
            bpos = 0
            while bpos + 1 < len(cmd_block):
                player_id = cmd_block[bpos]
                action_id = cmd_block[bpos + 1]
                cmd_data_start = bpos + 2  # data starts after player_id + action_id

                if not (0 <= player_id <= 11):
                    break  # Invalid byte, stop parsing this block

                # Get command data size to know how far to advance
                cmd_size = self._get_cmd_size(action_id, cmd_block, cmd_data_start)

                if cmd_size is None:
                    # Unknown command size - can't reliably parse further
                    break

                cmd_end = cmd_data_start + cmd_size

                # Validate: enough bytes remaining in block
                if cmd_end > len(cmd_block):
                    break

                # Only record commands from known players
                if player_id in known_player_ids:
                    cmd_entry = {
                        'frame': frame,
                        'time_seconds': round(frame / 23.81, 2),
                        'player_id': player_id,
                        'action_id': action_id,
                        'action_name': self.COMMANDS.get(action_id, f'Unknown (0x{action_id:02x})'),
                    }

                    # Extract this command's sub-block for detailed parsing
                    cmd_sub_block = cmd_block[bpos:cmd_end]

                    # Parse chat messages
                    if action_id in (0x52, 0x5A):
                        self._parse_chat_message(cmd_entry, cmd_block, cmd_data_start, frame, player_id)

                    # Parse additional command data
                    self._parse_command_data(cmd_entry, cmd_sub_block)

                    self.commands.append(cmd_entry)
                    self.command_stats[player_id][action_id] += 1

                    if frame > max_frame:
                        max_frame = frame

                    # Track last action frame per player (excluding non-gameplay commands)
                    if action_id not in (0x00, 0x2F, 0x48, 0x49):
                        player_last_action_frame[player_id] = frame

                    # Track Leave Game
                    if action_id == 0x4A:
                        if leave_game_player is None or frame < leave_game_frame:
                            leave_game_frame = frame
                            leave_game_player = player_id

                bpos = cmd_end

        # Update game info with actual max frame
        if max_frame > 0:
            self.game_info['actual_frames'] = max_frame
            self.game_info['actual_duration'] = f"{int(max_frame / 23.81 // 60)}m {int(max_frame / 23.81 % 60)}s"

        # Store leave game info
        if leave_game_player is not None:
            self.game_info['leave_game_player'] = leave_game_player
            self.game_info['leave_game_frame'] = leave_game_frame

        # Store last action frames for winner determination
        self.game_info['player_last_action_frame'] = player_last_action_frame

    def _parse_chat_message(self, cmd_entry, cmd_block, data_start, frame, player_id):
        """Extract chat message text from 0x52/0x5A commands"""
        msg_bytes = cmd_block[data_start:]
        null_pos = msg_bytes.find(b'\x00')
        if null_pos > 0:
            msg_bytes = msg_bytes[:null_pos]
        elif null_pos == 0:
            return  # Empty message

        # Decode: try UTF-8 first, fall back to cp949 (Korean)
        try:
            message = msg_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                message = msg_bytes.decode('cp949')
            except UnicodeDecodeError:
                message = msg_bytes.decode('latin-1')

        if not message.strip():
            return

        player_name = f"Player {player_id}"
        for p in self.players:
            if p['id'] == player_id:
                player_name = p['name']
                break

        time_seconds = round(frame / 23.81, 2)
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)

        self.chat_messages.append({
            'frame': frame,
            'time': f"{minutes}:{seconds:02d}",
            'time_seconds': time_seconds,
            'player_id': player_id,
            'player_name': player_name,
            'message': message,
        })

        cmd_entry['message'] = message

    def _parse_command_data(self, cmd_entry, cmd_block):
        """Parse command-specific data"""
        action_id = cmd_entry['action_id']
        player_id = cmd_entry['player_id']

        # Train/Build/Morph commands
        if action_id in [0x18, 0x1C, 0x2D] and len(cmd_block) >= 4:
            unit_id = struct.unpack('<H', cmd_block[2:4])[0]
            if unit_id in self.UNITS:
                unit_name = self.UNITS[unit_id]
                cmd_entry['unit'] = unit_name
                cmd_entry['unit_id'] = unit_id
                self.unit_production[player_id][unit_name] += 1

        # Build command (building placement) — unit_id must be a building (>=106)
        elif action_id == 0x07 and len(cmd_block) >= 9:
            unit_id = struct.unpack('<H', cmd_block[7:9])[0]
            if unit_id >= 106 and unit_id in self.UNITS:
                unit_name = self.UNITS[unit_id]
                cmd_entry['unit'] = unit_name
                cmd_entry['unit_id'] = unit_id
                self.unit_production[player_id][unit_name] += 1

        # Right click / Move commands
        elif action_id in [0x0F, 0x10, 0x54, 0x55, 0x63, 0x64, 0x65]:
            if len(cmd_block) >= 6:
                x = struct.unpack('<H', cmd_block[2:4])[0]
                y = struct.unpack('<H', cmd_block[4:6])[0]
                cmd_entry['target_x'] = x
                cmd_entry['target_y'] = y

        # Hotkey
        elif action_id == 0x0E and len(cmd_block) >= 4:
            hotkey_type = cmd_block[2]
            hotkey_group = cmd_block[3]
            cmd_entry['hotkey_type'] = 'Assign' if hotkey_type == 0 else 'Select'
            cmd_entry['hotkey_group'] = hotkey_group

    def _parse_map_data(self):
        """Parse map data (CHK format)"""
        map_start = self._find_map_data_start()
        if map_start >= len(self.zlib_blocks):
            return

        chk_data = self._decompress_block(map_start)
        if not chk_data:
            return

        self._parse_chk_data(chk_data)

    def _parse_chk_data(self, chk_data):
        """Parse CHK format map data"""
        offset = 0
        while offset < len(chk_data) - 8:
            chunk_id = chk_data[offset:offset+4]
            chunk_size = struct.unpack('<I', chk_data[offset+4:offset+8])[0]

            if chunk_size > len(chk_data) or chunk_size < 0:
                break

            chunk_data = chk_data[offset+8:offset+8+chunk_size]
            chunk_name = chunk_id.decode('ascii', errors='ignore')

            self.map_chunks[chunk_name] = {'offset': offset, 'size': chunk_size}

            if chunk_id == b'STR ':
                self._parse_str_chunk(chunk_data)
            elif chunk_id == b'SPRP':
                self._parse_sprp_chunk(chunk_data)
            elif chunk_id == b'ERA ':
                self._parse_era_chunk(chunk_data)

            offset += 8 + chunk_size

    def _parse_str_chunk(self, data):
        """Parse string table chunk"""
        if len(data) < 2:
            return

        num_strings = struct.unpack('<H', data[0:2])[0]

        for i in range(min(num_strings, 100)):
            if 2 + i * 2 + 2 > len(data):
                break
            string_offset = struct.unpack('<H', data[2 + i * 2:4 + i * 2])[0]
            if string_offset < len(data):
                end = data.find(b'\x00', string_offset)
                if end > string_offset:
                    try:
                        s = data[string_offset:end].decode('cp949', errors='ignore')
                    except:
                        s = data[string_offset:end].decode('utf-8', errors='ignore')
                    if s.strip():
                        self.map_strings.append({'index': i, 'value': s})

    def _parse_sprp_chunk(self, data):
        """Parse scenario properties chunk"""
        if len(data) >= 4:
            name_idx = struct.unpack('<H', data[0:2])[0]
            for s in self.map_strings:
                if s['index'] == name_idx:
                    self.map_data['map_name'] = s['value']
                    break

    def _parse_era_chunk(self, data):
        """Parse tileset chunk"""
        if len(data) >= 2:
            tileset_id = struct.unpack('<H', data[0:2])[0] & 0x07
            self.map_data['tileset'] = self.TILESETS.get(tileset_id, f'Unknown ({tileset_id})')

    def _calculate_stats(self):
        """Calculate game statistics"""
        if not self.commands:
            return

        game_seconds = self.game_info.get('duration_seconds', 1)
        if game_seconds == 0:
            game_seconds = 1

        for player_id in self.command_stats:
            total_actions = sum(self.command_stats[player_id].values())
            real_actions = total_actions - self.command_stats[player_id].get(0x00, 0)

            apm = (real_actions / game_seconds) * 60

            player_name = f"Player {player_id}"
            for p in self.players:
                if p['id'] == player_id:
                    player_name = p['name']
                    break

            # Get action breakdown
            action_breakdown = {}
            for action_id, count in sorted(self.command_stats[player_id].items(), key=lambda x: -x[1]):
                action_name = self.COMMANDS.get(action_id, f'Unknown (0x{action_id:02x})')
                action_breakdown[action_name] = count

            # Get unit production
            units = dict(sorted(self.unit_production[player_id].items(), key=lambda x: -x[1]))

            self.player_stats[player_id] = {
                'name': player_name,
                'total_actions': total_actions,
                'real_actions': real_actions,
                'apm': round(apm, 1),
                'action_breakdown': action_breakdown,
                'unit_production': units
            }

    def _determine_winner(self):
        """Determine the winner using a fallback chain of methods"""
        if len(self.players) < 2:
            return

        # Method 1: Leave Game (0x4A) - first leaver is the loser
        leave_player = self.game_info.get('leave_game_player')
        if leave_player is not None:
            loser = leave_player
            winner = 1 - loser if loser in [0, 1] else None
            if winner is not None:
                self._set_winner(winner, loser, "Leave Game command")
                return

        # Method 2: Last action comparison
        last_frames = self.game_info.get('player_last_action_frame', {})
        if len(self.players) >= 2:
            p0_id = self.players[0]['id']
            p1_id = self.players[1]['id']
            p0_last = last_frames.get(p0_id, 0)
            p1_last = last_frames.get(p1_id, 0)

            if p0_last > 0 and p1_last > 0:
                diff = abs(p0_last - p1_last)
                max_frame = max(p0_last, p1_last)
                # If one player's last action is significantly later (>5% of game or >500 frames)
                if diff > max(500, max_frame * 0.05):
                    if p0_last > p1_last:
                        self._set_winner(0, 1, "Last action analysis (opponent stopped playing earlier)")
                    else:
                        self._set_winner(1, 0, "Last action analysis (opponent stopped playing earlier)")
                    return

        # Detect likely observer replay:
        # No Leave Game + both players active until nearly the same final frame
        if leave_player is None and len(self.players) >= 2:
            p0_last = last_frames.get(self.players[0]['id'], 0)
            p1_last = last_frames.get(self.players[1]['id'], 0)
            if p0_last > 0 and p1_last > 0:
                diff = abs(p0_last - p1_last)
                max_last = max(p0_last, p1_last)
                # Both active until near the end with small difference
                if diff < max(100, max_last * 0.02):
                    self.is_observer_replay = True
                    self.game_info['observer_replay'] = True

        # No winner determined
        self.game_info['result'] = 'Undetermined'
        self.winner_method = 'Undetermined'

    def _set_winner(self, winner_idx, loser_idx, method):
        """Helper to set winner/loser info"""
        self.winner = winner_idx
        self.winner_method = method
        self.game_info['winner'] = self.players[winner_idx]['name'] if winner_idx < len(self.players) else f"Player {winner_idx}"
        self.game_info['loser'] = self.players[loser_idx]['name'] if loser_idx < len(self.players) else f"Player {loser_idx}"
        self.game_info['result'] = f"{self.game_info['winner']} wins"
        self.game_info['winner_method'] = method

    def to_dict(self):
        """Convert all parsed data to dictionary"""
        return {
            'file_info': {
                'filename': self.filepath.name,
                'filepath': str(self.filepath.absolute()),
                'size_bytes': len(self.data),
                'parsed_at': datetime.now().isoformat()
            },
            'header': self.header,
            'game_info': self.game_info,
            'players': self.players,
            'map_data': self.map_data,
            'map_strings': self.map_strings[:30],
            'map_chunks': list(self.map_chunks.keys()),
            'statistics': {
                'total_commands': len(self.commands),
                'player_stats': self.player_stats
            },
            'observer_replay': self.is_observer_replay,
            'chat_messages': self.chat_messages,
            'commands': self.commands[:500],  # First 500 commands as sample
            'total_commands_count': len(self.commands)
        }

    def save_to_json(self, output_path=None):
        """Save all parsed data to JSON file"""
        if output_path is None:
            output_path = self.filepath.with_suffix('.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return output_path

    def save_commands_to_file(self, output_path=None):
        """Save all commands to a separate file"""
        if output_path is None:
            output_path = self.filepath.with_name(self.filepath.stem + '_commands.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.commands, f, indent=2, ensure_ascii=False)

        return output_path

    def get_summary(self):
        """Get a formatted text summary"""
        lines = []
        lines.append("=" * 70)
        lines.append("       StarCraft Brood War / Remastered Replay Analysis")
        lines.append("=" * 70)
        lines.append("")

        # File Info
        lines.append("[File Information]")
        lines.append(f"  Filename       : {self.filepath.name}")
        lines.append(f"  Size           : {len(self.data):,} bytes")
        lines.append("")

        # Game Info
        lines.append("[Game Information]")
        lines.append(f"  Game Type      : {self.game_info.get('game_type', 'N/A')}")
        lines.append(f"  Map Size       : {self.game_info.get('map_width', '?')}x{self.game_info.get('map_height', '?')}")
        lines.append(f"  Duration       : {self.game_info.get('duration', 'N/A')}")
        lines.append(f"  Total Frames   : {self.game_info.get('total_frames', 0):,}")

        if 'result' in self.game_info:
            lines.append(f"  Result         : {self.game_info['result']}")
        if self.winner_method:
            lines.append(f"  Determined by  : {self.winner_method}")
        if self.is_observer_replay:
            lines.append(f"  Replay Type    : Observer replay (likely)")
        lines.append("")

        # Map Info
        lines.append("[Map Information]")
        if 'map_name' in self.map_data:
            lines.append(f"  Name           : {self.map_data['map_name']}")
        if 'tileset' in self.map_data:
            lines.append(f"  Tileset        : {self.map_data['tileset']}")
        lines.append("")

        # Players
        lines.append("[Players]")
        for p in self.players:
            status = ""
            if self.winner is not None:
                if p['id'] == self.winner:
                    status = " [WINNER]"
                else:
                    status = " [LOSER]"
            lines.append(f"  {p['name']} ({p['race']}){status}")
        lines.append("")

        # Statistics
        lines.append("[Game Statistics]")
        lines.append(f"  Total Commands : {len(self.commands):,}")
        lines.append("")

        for player_id, stats in self.player_stats.items():
            lines.append(f"  {stats['name']}:")
            lines.append(f"    - Total Actions  : {stats['total_actions']:,}")
            lines.append(f"    - APM            : {stats['apm']}")
            lines.append("")
            lines.append(f"    Unit Production:")
            for unit, count in list(stats['unit_production'].items())[:10]:
                lines.append(f"      - {unit}: {count}")
            lines.append("")

        # Chat Log
        lines.append("[Chat Log]")
        if self.chat_messages:
            for msg in self.chat_messages:
                lines.append(f"  [{msg['time']}] {msg['player_name']}: {msg['message']}")
        else:
            lines.append("  (no chat messages)")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def save_summary(self, output_path=None):
        """Save text summary to file"""
        if output_path is None:
            output_path = self.filepath.with_suffix('.txt')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.get_summary())

        return output_path


def main():
    import sys

    if len(sys.argv) < 2:
        filepath = "test.rep"
    else:
        filepath = sys.argv[1]

    try:
        print(f"Parsing {filepath}...")
        print()

        parser = SCReplayParser(filepath)
        parser.parse()

        print(parser.get_summary())

        json_path = parser.save_to_json()
        print(f"JSON data saved to: {json_path}")

        txt_path = parser.save_summary()
        print(f"Summary saved to: {txt_path}")

        commands_path = parser.save_commands_to_file()
        print(f"Commands saved to: {commands_path}")

        print("\nDone!")

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
