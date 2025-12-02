#!/usr/bin/env python3
"""Quick test to verify seed reading"""

import sys
sys.path.insert(0, '..')

from memory.process import ProcessAttacher
from memory.reader import MemoryReader
from data.offsets import Offset

def main():
    attacher = ProcessAttacher()
    if not attacher.attach():
        print("Failed to attach to PVZ")
        return
    
    print(f"Attached to PVZ (PID: {attacher.pid})")
    
    reader = MemoryReader(attacher.kernel32, attacher.handle)
    
    if not reader.is_in_game():
        print("Not in game, please start a level first")
        return
    
    board = reader.get_board()
    print(f"Board: 0x{board:08X}")
    
    # Read seed array pointer
    seed_array = reader.read_int(board + Offset.SEED_ARRAY)
    print(f"Seed Array: 0x{seed_array:08X}")
    
    # Read card count from first slot
    card_count = reader.read_int(seed_array + Offset.S_COUNT)
    print(f"Card Count: {card_count}")
    
    print("\n--- Seed Slots ---")
    for i in range(min(10, max(card_count, 1))):
        addr = seed_array + i * Offset.SEED_SIZE
        
        # Read raw values
        s_type = reader.read_int(addr + Offset.S_TYPE)
        s_cd = reader.read_int(addr + Offset.S_RECHARGE_COUNTDOWN)
        s_cd_max = reader.read_int(addr + Offset.S_RECHARGE_TIME)
        s_usable = reader.read_byte(addr + Offset.S_USABLE)
        s_imitator = reader.read_int(addr + Offset.S_IMITATOR_TYPE)
        
        print(f"Slot {i}: type={s_type:3d}, cd={s_cd:5d}/{s_cd_max:5d}, "
              f"usable={s_usable}, imitator={s_imitator}")
        
        # Also try reading at raw offsets for debugging
        print(f"         Raw @ +0x00: {reader.read_int(addr + 0x00)}")
        print(f"         Raw @ +0x24: {reader.read_int(addr + 0x24)}")
        print(f"         Raw @ +0x28: {reader.read_int(addr + 0x28)}")
        print(f"         Raw @ +0x34: {reader.read_int(addr + 0x34)}")
        print(f"         Raw @ +0x5C: {reader.read_int(addr + 0x5C)}")

if __name__ == "__main__":
    main()
