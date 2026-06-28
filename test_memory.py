#!/usr/bin/env python
"""Test script for new per-entry memory storage."""

import sys
from pathlib import Path

# Windows UTF-8 output fix
if sys.platform == "win32":
    from io import TextIOWrapper
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from memory import MemoryStore, MemoryEntry
import json

print("=" * 60)
print("Per-Entry Memory Storage Tests")
print("=" * 60)

# =============================================================================
# Test 1: Creating memory entries
# =============================================================================
print("\n[Test 1] Creating memory entries")
print("-" * 60)

store = MemoryStore('test_memory')

# Add memory entries
result1 = store.add('memory', 'Test: Project uses Python 3.11')
print(f"Add memory 1:")
print(f"  Success: {result1['success']}")
print(f"  Message: {result1.get('message', 'N/A')}")
print(f"  Entry count: {result1['entry_count']}")

result2 = store.add('memory', 'Test: API runs on port 8000')
print(f"\nAdd memory 2:")
print(f"  Success: {result2['success']}")
print(f"  Entry count: {result2['entry_count']}")

# Add user entry
result3 = store.add('user', 'Test: User prefers dark mode')
print(f"\nAdd user entry:")
print(f"  Success: {result3['success']}")
print(f"  Entry count: {result3['entry_count']}")

# =============================================================================
# Test 2: Verifying file structure
# =============================================================================
print("\n[Test 2] Verifying file structure")
print("-" * 60)

memory_dir = Path('memories/test_memory/memory')
user_dir = Path('memories/test_memory/user')

print(f"Memory directory exists: {memory_dir.exists()}")
print(f"User directory exists: {user_dir.exists()}")

memory_files = list(memory_dir.glob("*.json"))
user_files = list(user_dir.glob("*.json"))

print(f"\nMemory files: {len(memory_files)}")
for f in memory_files:
    print(f"  - {f.name}")

print(f"\nUser files: {len(user_files)}")
for f in user_files:
    print(f"  - {f.name}")

assert len(memory_files) == 2, f"Expected 2 memory files, got {len(memory_files)}"
assert len(user_files) == 1, f"Expected 1 user file, got {len(user_files)}"

# =============================================================================
# Test 3: Reading sample memory file
# =============================================================================
print("\n[Test 3] Reading sample memory file")
print("-" * 60)

if memory_files:
    sample_file = memory_files[0]
    print(f"\nReading {sample_file.name}:")
    content = sample_file.read_text(encoding='utf-8')
    data = json.loads(content)
    print(f"  ID: {data['id']}")
    print(f"  Content: {data['content']}")
    print(f"  Created: {data['created']}")
    print(f"  Updated: {data['updated']}")

    # Verify structure
    assert 'id' in data, "Missing 'id' field"
    assert 'content' in data, "Missing 'content' field"
    assert 'created' in data, "Missing 'created' field"
    assert 'updated' in data, "Missing 'updated' field"

# =============================================================================
# Test 4: Reloading from disk
# =============================================================================
print("\n[Test 4] Reloading from disk")
print("-" * 60)

store2 = MemoryStore('test_memory')
store2.load_from_disk()

print(f"Memory entries loaded: {len(store2.memory_entries)}")
for e in store2.memory_entries:
    print(f"  - [{e.id}] {e.content[:40]}...")

print(f"\nUser entries loaded: {len(store2.user_entries)}")
for e in store2.user_entries:
    print(f"  - [{e.id}] {e.content[:40]}...")

assert len(store2.memory_entries) == 2, f"Expected 2 memory entries, got {len(store2.memory_entries)}"
assert len(store2.user_entries) == 1, f"Expected 1 user entry, got {len(store2.user_entries)}"

# =============================================================================
# Test 5: Replacing entry
# =============================================================================
print("\n[Test 5] Replacing entry")
print("-" * 60)

result4 = store.replace('memory', 'port 8000', 'Test: API runs on port 8080')
print(f"Replace result:")
print(f"  Success: {result4['success']}")
print(f"  Message: {result4.get('message', 'N/A')}")
print(f"  Entry count: {result4['entry_count']}")

# Verify the content changed
store3 = MemoryStore('test_memory')
store3.load_from_disk()
port_8080_found = any('8080' in e.content for e in store3.memory_entries)
port_8000_found = any('8000' in e.content for e in store3.memory_entries)
assert port_8080_found, "Updated content (8080) not found"
assert not port_8000_found, "Old content (8000) still present"

# =============================================================================
# Test 6: Removing entry
# =============================================================================
print("\n[Test 6] Removing entry")
print("-" * 60)

result5 = store.remove('memory', 'Python 3.11')
print(f"Remove result:")
print(f"  Success: {result5['success']}")
print(f"  Message: {result5.get('message', 'N/A')}")
print(f"  Entry count: {result5['entry_count']}")

# Verify file was deleted
memory_files_after = list(memory_dir.glob("*.json"))
assert len(memory_files_after) == 1, f"Expected 1 memory file after removal, got {len(memory_files_after)}"

# =============================================================================
# Test 7: Format for system prompt
# =============================================================================
print("\n[Test 7] Format for system prompt")
print("-" * 60)

store4 = MemoryStore('test_memory')
store4.load_from_disk()

memory_block = store4.format_for_system_prompt('memory')
user_block = store4.format_for_system_prompt('user')

print(f"Memory block length: {len(memory_block) if memory_block else 0}")
print(f"User block length: {len(user_block) if user_block else 0}")

if memory_block:
    print(f"\nMemory block preview:")
    preview = memory_block[:300] + "..." if len(memory_block) > 300 else memory_block
    print(preview)

# =============================================================================
# Test 8: Duplicate prevention
# =============================================================================
print("\n[Test 8] Duplicate prevention")
print("-" * 60)

store5 = MemoryStore('test_dup')
result6 = store5.add('memory', 'Duplicate test')
print(f"First add: success={result6['success']}")

result7 = store5.add('memory', 'Duplicate test')
print(f"Duplicate add: success={result7['success']}")
print(f"Message: {result7.get('message', 'N/A')}")

assert result7['success'] == True, "Duplicate add should return success"
assert 'already exists' in result7.get('message', '').lower(), "Should indicate already exists"

# Verify only one entry
store5.load_from_disk()
assert len(store5.memory_entries) == 1, "Should have only one entry after duplicate add"

# =============================================================================
# Test 9: Character limit enforcement
# =============================================================================
print("\n[Test 9] Character limit enforcement")
print("-" * 60)

store6 = MemoryStore('test_limit', memory_char_limit=100, user_char_limit=50)

# Add entries up to limit
result8 = store6.add('memory', 'Small entry')
print(f"Add small entry: success={result8['success']}")

# Try to add oversized entry
large_content = "x" * 200  # Way over limit
result9 = store6.add('memory', large_content)
print(f"Add oversized entry: success={result9['success']}")
print(f"Error: {result9.get('error', 'N/A')[:80]}...")

assert result9['success'] == False, "Oversized entry should be rejected"
assert 'full' in result9.get('error', '').lower(), "Error should mention memory full"

# =============================================================================
# Test 10: Multi-user isolation
# =============================================================================
print("\n[Test 10] Multi-user isolation")
print("-" * 60)

store_a = MemoryStore('user_a')
store_a.add('memory', 'User A memory')

store_b = MemoryStore('user_b')
store_b.add('memory', 'User B memory')

# Verify isolation
store_a_reloaded = MemoryStore('user_a')
store_a_reloaded.load_from_disk()
assert len(store_a_reloaded.memory_entries) == 1, "User A should have 1 entry"
assert 'User A' in store_a_reloaded.memory_entries[0].content, "Should be User A's memory"

store_b_reloaded = MemoryStore('user_b')
store_b_reloaded.load_from_disk()
assert len(store_b_reloaded.memory_entries) == 1, "User B should have 1 entry"
assert 'User B' in store_b_reloaded.memory_entries[0].content, "Should be User B's memory"

print("User A entries:", len(store_a_reloaded.memory_entries))
print("User B entries:", len(store_b_reloaded.memory_entries))
print("Users are properly isolated!")

# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("[SUCCESS] All tests passed!")
print("=" * 60)
print("\nPer-entry memory storage is working correctly:")
print("  - Each entry stored as separate JSON file")
print("  - Proper directory structure per user")
print("  - Add, replace, remove operations work")
print("  - Character limits enforced")
print("  - Multi-user isolation verified")
print("  - Duplicate prevention working")
