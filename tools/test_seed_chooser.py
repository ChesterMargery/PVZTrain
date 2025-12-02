#!/usr/bin/env python3
"""
Comprehensive test script for seed chooser functions.
Tests the fixes for choose_seed(), click_seed_chooser_button(), and pick_random_seeds_and_start().

This script performs step-by-step validation to ensure the fixes prevent game crashes.
"""

import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.process import ProcessAttacher
from memory.reader import MemoryReader
from memory.injector import AsmInjector
from data.offsets import Offset

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "seed_chooser_test.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SeedChooserTester:
    """Test harness for seed chooser functionality"""
    
    def __init__(self):
        self.attacher = None
        self.reader = None
        self.injector = None
        self.attached = False
    
    def connect(self) -> bool:
        """Connect to PVZ process"""
        logger.info("=" * 60)
        logger.info("Connecting to PVZ...")
        
        self.attacher = ProcessAttacher()
        if not self.attacher.attach():
            logger.error("Failed to attach to PVZ process")
            logger.error("Please ensure PVZ is running!")
            return False
        
        logger.info(f"✓ Attached to PVZ (PID: {self.attacher.pid})")
        
        self.reader = MemoryReader(self.attacher.kernel32, self.attacher.handle)
        self.injector = AsmInjector(self.attacher.kernel32, self.attacher.handle, self.reader)
        self.attached = True
        
        return True
    
    def check_game_state(self) -> bool:
        """Check if game is in seed chooser state"""
        if not self.attached:
            logger.error("Not attached to PVZ")
            return False
        
        base = self.reader.read_int(Offset.BASE)
        if not base:
            logger.error("Failed to read base address")
            return False
        
        game_ui = self.reader.read_int(base + Offset.GAME_UI)
        logger.info(f"Game UI State: {game_ui} (2=seed chooser, 3=in game)")
        
        if game_ui != 2:
            logger.warning("Not in seed chooser! Please enter seed selection screen.")
            logger.warning("Hint: Start any level and wait at the seed selection screen")
            return False
        
        return True
    
    def print_avz_comparison(self):
        """Print AVZ address comparison table"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("AVZ Address Reference (from avz_asm.cpp)")
        logger.info("=" * 60)
        logger.info("Function                Address    Offset Constant")
        logger.info("-" * 60)
        logger.info(f"FUNC_CHOOSE_CARD        0x{Offset.FUNC_CHOOSE_CARD:06X}    Offset.FUNC_CHOOSE_CARD")
        logger.info(f"FUNC_ROCK               0x{Offset.FUNC_ROCK:06X}    Offset.FUNC_ROCK")
        logger.info(f"FUNC_PICK_RANDOM        0x{Offset.FUNC_PICK_RANDOM:06X}    Offset.FUNC_PICK_RANDOM")
        logger.info(f"BASE                    0x{Offset.BASE:06X}    Offset.BASE")
        logger.info(f"SEED_CHOOSER            0x{Offset.SEED_CHOOSER:03X}       Offset.SEED_CHOOSER")
        logger.info("=" * 60)
        logger.info("")
    
    def test_1_memory_read(self) -> bool:
        """Test 1: Read memory to verify offsets are correct"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 1: Memory Read (Verify Offsets)")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            base = self.reader.read_int(Offset.BASE)
            logger.info(f"✓ PVZ Base: 0x{base:08X}")
            
            seed_chooser = self.reader.read_int(base + Offset.SEED_CHOOSER)
            logger.info(f"✓ Seed Chooser: 0x{seed_chooser:08X}")
            
            if seed_chooser == 0:
                logger.error("✗ Seed chooser pointer is NULL!")
                return False
            
            logger.info("✓ TEST 1 PASSED: Memory offsets are correct")
            return True
            
        except Exception as e:
            logger.error(f"✗ TEST 1 FAILED: {e}")
            return False
    
    def test_2_simple_shellcode(self) -> bool:
        """Test 2: Execute simple ret shellcode to verify injection mechanism"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 2: Simple Shellcode (Verify Injection Mechanism)")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            # Simple shellcode that just returns
            shellcode = bytes([0xC3])  # ret
            
            logger.info("Executing simple 'ret' shellcode...")
            success = self.injector.execute_shellcode(shellcode, timeout=500, debug_name="test_ret")
            
            if success:
                logger.info("✓ TEST 2 PASSED: Shellcode injection works")
                return True
            else:
                logger.error("✗ TEST 2 FAILED: Shellcode injection failed")
                return False
                
        except Exception as e:
            logger.error(f"✗ TEST 2 FAILED: {e}")
            return False
    
    def test_3_choose_seed(self, plant_type: int = 0) -> bool:
        """Test 3: Choose a single seed"""
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"TEST 3: Choose Seed (Plant Type {plant_type})")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            logger.info(f"Attempting to choose plant type {plant_type}...")
            success = self.injector.choose_seed(plant_type)
            
            if success:
                logger.info(f"✓ TEST 3 PASSED: Successfully chose seed {plant_type}")
                logger.info("Check the game - the seed should be selected")
                return True
            else:
                logger.error("✗ TEST 3 FAILED: choose_seed returned False")
                return False
                
        except Exception as e:
            logger.error(f"✗ TEST 3 FAILED: {e}")
            return False
    
    def test_4_click_button(self) -> bool:
        """Test 4: Click the Let's Rock button"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 4: Click Let's Rock Button")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            logger.info("Attempting to click Let's Rock button...")
            logger.info("WARNING: This will start the game if successful!")
            
            # Give user a chance to cancel
            logger.info("Press Ctrl+C within 3 seconds to cancel...")
            time.sleep(3)
            
            success = self.injector.click_seed_chooser_button()
            
            if success:
                logger.info("✓ TEST 4 PASSED: Successfully clicked Let's Rock")
                logger.info("Game should have started")
                return True
            else:
                logger.error("✗ TEST 4 FAILED: click_seed_chooser_button returned False")
                return False
                
        except KeyboardInterrupt:
            logger.info("Cancelled by user")
            return False
        except Exception as e:
            logger.error(f"✗ TEST 4 FAILED: {e}")
            return False
    
    def test_5_full_flow(self) -> bool:
        """Test 5: Full flow - choose some seeds and start"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 5: Full Flow (Choose Seeds + Start)")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            # Choose a few seeds
            seeds_to_choose = [0, 1, 2]  # Peashooter, Sunflower, Cherry Bomb
            
            for plant_type in seeds_to_choose:
                logger.info(f"Choosing plant type {plant_type}...")
                success = self.injector.choose_seed(plant_type)
                if not success:
                    logger.error(f"Failed to choose seed {plant_type}")
                    return False
                time.sleep(0.5)  # Small delay between selections
            
            logger.info("All seeds chosen successfully")
            logger.info("Now clicking Let's Rock...")
            logger.info("Press Ctrl+C within 3 seconds to cancel...")
            time.sleep(3)
            
            success = self.injector.click_seed_chooser_button()
            
            if success:
                logger.info("✓ TEST 5 PASSED: Full flow completed successfully")
                return True
            else:
                logger.error("✗ TEST 5 FAILED: Failed to click Let's Rock")
                return False
                
        except KeyboardInterrupt:
            logger.info("Cancelled by user")
            return False
        except Exception as e:
            logger.error(f"✗ TEST 5 FAILED: {e}")
            return False
    
    def test_6_pick_random(self) -> bool:
        """Test 6: Pick random seeds and start"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("TEST 6: Pick Random Seeds and Start")
        logger.info("=" * 60)
        
        if not self.check_game_state():
            return False
        
        try:
            logger.info("Attempting to fill with random seeds and start...")
            logger.info("WARNING: This will start the game if successful!")
            logger.info("Press Ctrl+C within 3 seconds to cancel...")
            time.sleep(3)
            
            success = self.injector.pick_random_seeds_and_start()
            
            if success:
                logger.info("✓ TEST 6 PASSED: Successfully picked random seeds and started")
                return True
            else:
                logger.error("✗ TEST 6 FAILED: pick_random_seeds_and_start returned False")
                return False
                
        except KeyboardInterrupt:
            logger.info("Cancelled by user")
            return False
        except Exception as e:
            logger.error(f"✗ TEST 6 FAILED: {e}")
            return False
    
    def detect_crash(self) -> bool:
        """Detect if game has crashed"""
        try:
            base = self.reader.read_int(Offset.BASE)
            return base == 0
        except:
            return True
    
    def run_interactive(self):
        """Run interactive test menu"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Seed Chooser Function Test Suite")
        logger.info("=" * 60)
        logger.info("")
        logger.info(f"Log file: {log_file}")
        logger.info("")
        
        if not self.connect():
            return
        
        self.print_avz_comparison()
        
        while True:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Test Menu:")
            logger.info("  1. Test Memory Read (verify offsets)")
            logger.info("  2. Test Simple Shellcode (verify injection)")
            logger.info("  3. Test Choose Seed (select one card)")
            logger.info("  4. Test Click Let's Rock (start game)")
            logger.info("  5. Test Full Flow (choose seeds + start)")
            logger.info("  6. Test Pick Random Seeds (random + start)")
            logger.info("  7. Print AVZ Address Reference")
            logger.info("  8. Reconnect to PVZ")
            logger.info("  0. Exit")
            logger.info("=" * 60)
            
            try:
                choice = input("Enter choice: ").strip()
            except (KeyboardInterrupt, EOFError):
                logger.info("\nExiting...")
                break
            
            if choice == "0":
                logger.info("Exiting...")
                break
            elif choice == "1":
                self.test_1_memory_read()
            elif choice == "2":
                self.test_2_simple_shellcode()
            elif choice == "3":
                try:
                    plant_type = int(input("Enter plant type (0-47, default 0): ") or "0")
                    self.test_3_choose_seed(plant_type)
                except ValueError:
                    self.test_3_choose_seed(0)
            elif choice == "4":
                self.test_4_click_button()
            elif choice == "5":
                self.test_5_full_flow()
            elif choice == "6":
                self.test_6_pick_random()
            elif choice == "7":
                self.print_avz_comparison()
            elif choice == "8":
                logger.info("Reconnecting...")
                if self.connect():
                    logger.info("✓ Reconnected successfully")
                else:
                    logger.error("✗ Failed to reconnect")
            else:
                logger.warning("Invalid choice")
            
            # Check for crash after each test
            if choice in ["2", "3", "4", "5", "6"]:
                time.sleep(0.5)
                if self.detect_crash():
                    logger.error("")
                    logger.error("!" * 60)
                    logger.error("GAME CRASH DETECTED!")
                    logger.error("!" * 60)
                    logger.error("")
                    reconnect = input("Attempt to reconnect? (y/n): ").strip().lower()
                    if reconnect == 'y':
                        if self.connect():
                            logger.info("✓ Reconnected successfully")
                        else:
                            logger.error("✗ Failed to reconnect")
                            break


def main():
    """Main entry point"""
    tester = SeedChooserTester()
    tester.run_interactive()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Fatal error:")
        sys.exit(1)
