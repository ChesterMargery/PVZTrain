# Testing Guide for Hook Bug Fixes

This document provides a comprehensive guide for testing the bug fixes made to the Hook DLL implementation.

## Prerequisites

### Required Software
1. **Operating System**: Windows 10/11
2. **Plants vs. Zombies**: Version 1.0.0.1051 (Chinese Annual Edition / 中文年度版)
3. **Visual Studio 2022**: With "Desktop development with C++" workload
4. **Python**: 3.7+ with required packages (see requirements.txt)

### Optional Tools
- DLL injector (e.g., Extreme Injector) if not using the built-in injector
- Process Explorer (to verify DLL injection)

## Build Instructions

### Step 1: Build the Hook DLL

```batch
cd hook
build.bat
```

Expected output:
```
Building PVZ Hook DLL...
Configuring CMake...
-- Build files have been written to: .../build
Building Release...
Build succeeded.
Copying DLL...
Build successful! pvz_hook.dll is ready.
```

The DLL will be located at: `hook/pvz_hook.dll`

### Step 2: Verify Build

Check that the DLL was created:
```batch
dir hook\pvz_hook.dll
```

## Testing Strategy

The testing is divided into critical, medium, and functional tests.

## Phase 1: Critical Bug Tests

These tests verify that the game doesn't crash or freeze with the hook active.

### Test 1.1: Hook Installation (Bug #1)

**What it tests**: Vtable hook method and original game loop execution

**Steps**:
1. Start Plants vs. Zombies
2. Run the injector:
   ```python
   python -c "from hook_client import inject_dll; inject_dll()"
   ```
3. Wait 2 seconds

**Expected Result**:
- ✅ DLL injected successfully
- ✅ Game continues running normally (not frozen)
- ✅ Can navigate menus
- ✅ Can start a level

**What would fail if bug still exists**: Game would freeze immediately after injection because g_originalGameLoop was nullptr.

### Test 1.2: Game Loop Stability

**What it tests**: Hook doesn't interfere with normal game operations

**Steps**:
1. With DLL injected, start Adventure mode
2. Play for at least 5 minutes
3. Plant various plants
4. Let zombies appear
5. Complete or lose the level

**Expected Result**:
- ✅ Game runs smoothly
- ✅ No freezes or stutters
- ✅ All game mechanics work normally

### Test 1.3: BackToMain Function (Bug #2)

**What it tests**: Correct __thiscall convention with ecx register

**Steps**:
1. Start a level (Adventure or Mini-game)
2. Run the test:
   ```python
   from hook_client import HookClient
   client = HookClient()
   client.connect()
   client.back()  # Call BackToMain
   ```

**Expected Result**:
- ✅ Game returns to main menu
- ✅ No crash
- ✅ Can start another level

**What would fail if bug still exists**: Crash or game not responding because ecx contained the function pointer instead of the this pointer.

### Test 1.4: EnterGame Function (Bug #3)

**What it tests**: Correct calling convention with esi and stack cleanup

**Steps**:
```python
from hook_client import HookClient
client = HookClient()
client.connect()
client.enter(0)  # Enter Adventure mode
# Wait a few seconds for transition
```

**Expected Result**:
- ✅ Game transitions to card selection screen
- ✅ No crash
- ✅ Stack properly cleaned up (no corruption)

**What would fail if bug still exists**: Stack corruption, crash, or random behavior due to missing "add esp, 8".

### Test 1.5: Rock Function (Bug #4)

**What it tests**: Safe ebp register usage with push/pop

**Steps**:
1. Use EnterGame to get to card selection
2. Select some cards
3. Run:
   ```python
   client.rock()  # Start the game (Let's Rock)
   ```

**Expected Result**:
- ✅ Game starts normally
- ✅ No crash
- ✅ Level loads properly

**What would fail if bug still exists**: Crash on return from function due to corrupted stack frame (ebp modified without saving).

## Phase 2: Medium Bug Tests

### Test 2.1: IsInGame Logic (Bug #5)

**What it tests**: Correct UI state reading

**Steps**:
```python
from hook_client import HookClient
client = HookClient()
client.connect()

# Test 1: At main menu
state = client.get_state()
print(f"At menu - In game: {state.get('in_game')}")  # Should be False

# Test 2: Enter a level
client.enter(0)
# Wait for card selection and start game
# ...
state = client.get_state()
print(f"In level - In game: {state.get('in_game')}")  # Should be True
```

**Expected Result**:
- ✅ Returns False at main menu
- ✅ Returns True during gameplay
- ✅ Correctly distinguishes UI states

**What would fail if bug still exists**: Would always return False because comparing pointer address (e.g., 0x12345678) with 3.

### Test 2.2: Zombie Count Reading (Bug #6)

**What it tests**: Zombie death status check

**Steps**:
1. Start a level
2. Wait for zombies to appear
3. Query state:
   ```python
   state = client.get_state()
   print(f"Zombies: {state.get('zombie_count')}")
   ```
4. Kill some zombies
5. Query again

**Expected Result**:
- ✅ Count increases as zombies spawn
- ✅ Count decreases as zombies die
- ✅ Count matches visual zombie count (±1)

**Note**: This test verifies the current implementation works. If zombies with certain states are incorrectly counted, this is a known limitation documented in the code.

## Phase 3: Functional Tests

### Test 3.1: Plant Operations

```python
from hook_client import HookClient
client = HookClient()
client.connect()

# Plant a sunflower
success = client.plant(0, 0, 0)
print(f"Plant success: {success}")  # Should be True

# Shovel it
success = client.shovel(0, 0)
print(f"Shovel success: {success}")  # Should be True
```

**Expected Result**:
- ✅ Plant appears on the lawn
- ✅ Plant is removed when shoveled
- ✅ Both operations return success

### Test 3.2: Card Selection Flow

```python
from hook_client import HookClient
client = HookClient()
client.connect()

# Full card selection flow
client.enter(0)        # Enter adventure
time.sleep(2)

for i in range(5):     # Choose 5 cards
    client.choose(i)
    time.sleep(0.5)

client.rock()          # Start game
```

**Expected Result**:
- ✅ Cards are selected
- ✅ Game starts with chosen cards
- ✅ No crashes during transitions

### Test 3.3: Level Reset

```python
from hook_client import HookClient
client = HookClient()
client.connect()

# During gameplay
client.reset()  # Reset the level
```

**Expected Result**:
- ✅ Level restarts
- ✅ All plants/zombies cleared
- ✅ Returns to card selection (or starts fresh level)

### Test 3.4: State Reading Accuracy

```python
from hook_client import HookClient
client = HookClient()
client.connect()

# During gameplay
state = client.get_state()
print(f"Sun: {state['sun']}")
print(f"Wave: {state['wave']}")
print(f"Total waves: {state['total_waves']}")
print(f"Game clock: {state['game_clock']}")
print(f"Plant count: {state['plant_count']}")
print(f"Zombie count: {state['zombie_count']}")
```

**Expected Result**:
- ✅ All values are reasonable and match game state
- ✅ Values update as game progresses

## Phase 4: Stress Tests

### Test 4.1: Extended Gameplay

**Duration**: 30+ minutes

**Steps**:
1. Inject DLL
2. Run training loop continuously
3. Monitor for crashes, freezes, or memory leaks

**Expected Result**:
- ✅ No crashes
- ✅ No memory leaks (check Task Manager)
- ✅ Performance remains stable

### Test 4.2: Rapid Operations

```python
from hook_client import HookClient
import time

client = HookClient()
client.connect()

# Rapid plant/shovel
for i in range(100):
    client.plant(0, 0, 0)
    time.sleep(0.1)
    client.shovel(0, 0)
    time.sleep(0.1)
```

**Expected Result**:
- ✅ All operations complete successfully
- ✅ No crashes
- ✅ No corruption

### Test 4.3: UI State Transitions

```python
from hook_client import HookClient
import time

client = HookClient()
client.connect()

# Rapid state transitions
for i in range(10):
    client.enter(0)
    time.sleep(2)
    # Choose cards and start...
    client.rock()
    time.sleep(5)
    client.back()
    time.sleep(2)
```

**Expected Result**:
- ✅ All transitions work
- ✅ No crashes during rapid UI changes
- ✅ No stuck states

## Phase 5: Regression Tests

Ensure that the fixes didn't break anything that was working.

### Test 5.1: TCP Communication

**Steps**:
1. Inject DLL
2. Verify connection:
   ```python
   from hook_client import HookClient
   client = HookClient()
   assert client.connect(), "Failed to connect"
   ```

**Expected Result**: ✅ Connection successful

### Test 5.2: All Commands

Test every command:
- PLANT
- SHOVEL
- FIRE (should return error/false - not implemented)
- RESET
- ENTER
- CHOOSE
- ROCK
- BACK
- STATE

**Expected Result**: ✅ All commands work as documented

## Common Issues and Solutions

### Issue: DLL Injection Fails

**Symptoms**: "Failed to inject DLL" error

**Solutions**:
1. Run Python as Administrator
2. Verify game is running
3. Check DLL exists at `hook/pvz_hook.dll`
4. Try using a third-party injector

### Issue: Connection Refused

**Symptoms**: "Failed to connect to Hook DLL"

**Solutions**:
1. Verify DLL was injected (check with Process Explorer)
2. Check port 12345 is not in use
3. Wait longer after injection (try 5 seconds)
4. Restart game and try again

### Issue: Game Crashes on Injection

**Symptoms**: Game closes immediately after DLL injection

**Solutions**:
1. Verify game version is 1.0.0.1051
2. Rebuild DLL with latest code
3. Check Windows Event Viewer for error details
4. Report the crash with details

### Issue: Commands Don't Work

**Symptoms**: Commands return success but nothing happens

**Solutions**:
1. Verify you're in the correct game state (e.g., can't plant without being in game)
2. Check state before issuing command
3. Ensure sufficient sun for planting
4. Check position is valid (row 0-4, col 0-8)

## Success Criteria

All tests should pass with these results:

✅ **Critical Tests**: No crashes, no freezes, game runs normally
✅ **Medium Tests**: Correct state reading, accurate zombie counts
✅ **Functional Tests**: All operations work as expected
✅ **Stress Tests**: Stable over extended periods
✅ **Regression Tests**: Existing functionality preserved

## Reporting Issues

If any test fails, please report with:

1. Test name and phase
2. Expected vs. actual result
3. Game version
4. Python version
5. Full error message or crash dump
6. Steps to reproduce

## Performance Benchmarks

Expected performance (for reference):

- Hook overhead: < 1ms per frame
- Command latency: < 5ms
- State query: < 2ms
- Memory usage: +5MB for DLL
- No measurable FPS impact

## Conclusion

If all tests pass, the bug fixes are successful and the Hook DLL is ready for production use. The implementation now matches the AVZ reference and should be stable for automated gameplay.
