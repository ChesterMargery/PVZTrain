#!/usr/bin/env python3
"""Test planting with proper PlantCard function"""

import sys
sys.path.insert(0, '..')

from memory.process import ProcessAttacher
from memory.reader import MemoryReader
from memory.injector import AsmInjector
from data.offsets import Offset

def main():
    attacher = ProcessAttacher()
    if not attacher.attach():
        print("Failed to attach to PVZ")
        return
    
    print(f"Attached to PVZ (PID: {attacher.pid})")
    
    reader = MemoryReader(attacher.kernel32, attacher.handle)
    injector = AsmInjector(attacher.kernel32, attacher.handle, reader)
    
    if not reader.is_in_game():
        print("Not in game, please start a level first")
        return
    
    board = reader.get_board()
    scene = reader.get_scene()
    sun = reader.get_sun()
    print(f"Board: 0x{board:08X}")
    print(f"Scene: {scene}")
    print(f"Sun: {sun}")
    
    # Read seed slots
    seed_array = reader.read_int(board + Offset.SEED_ARRAY)
    print(f"\n--- Seed Slots ---")
    for i in range(10):
        addr = seed_array + i * Offset.SEED_SIZE
        s_type = reader.read_int(addr + Offset.S_TYPE)
        s_usable = reader.read_byte(addr + Offset.S_USABLE)
        if s_type >= 0:
            print(f"Slot {i}: type={s_type:3d}, usable={s_usable}")
    
    # Test coordinate conversion
    print(f"\n--- Coordinate Test ---")
    for row in range(5):
        x, y = injector._grid_to_pixel(row, 4)
        print(f"Row {row}, Col 4 -> ({x}, {y})")
    
    # Test finding seed index
    print(f"\n--- Seed Index Test ---")
    test_types = [0, 1, 2, 3, 5, 7, 20]  # Peashooter, Sunflower, Cherry, Wallnut, Snow Pea, Repeater, Jalapeno
    for plant_type in test_types:
        idx = injector._find_seed_index_by_type(plant_type)
        print(f"Plant type {plant_type:2d} -> Slot index: {idx}")
    
    print("\n--- Ready to test planting ---")
    print("Enter 'p <row> <col> <type>' to plant, 'q' to quit")
    print("Example: p 2 5 0  (plant Peashooter at row 2, col 5)")
    
    while True:
        try:
            cmd = input("> ").strip().lower()
            if cmd == 'q':
                break
            if cmd.startswith('p '):
                parts = cmd.split()
                if len(parts) == 4:
                    row = int(parts[1])
                    col = int(parts[2])
                    plant_type = int(parts[3])
                    
                    sun_before = reader.get_sun()
                    print(f"Sun before: {sun_before}")
                    
                    result = injector.plant(row, col, plant_type)
                    
                    sun_after = reader.get_sun()
                    print(f"Plant result: {result}")
                    print(f"Sun after: {sun_after}")
                    print(f"Sun spent: {sun_before - sun_after}")
                else:
                    print("Usage: p <row> <col> <type>")
        except ValueError as e:
            print(f"Invalid input: {e}")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
