"""Run with:  python tests.py   - checks the engine against known textbook answers."""
from engine import simulate, pages_to_accesses, faults_vs_frames

TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]

def faults(pages, frames, alg):
    return simulate(pages_to_accesses(pages), frames, alg)[1]["faults"]

assert faults(TEXTBOOK, 3, "FIFO") == 15
assert faults(TEXTBOOK, 3, "LRU") == 12
assert faults(TEXTBOOK, 3, "Optimal") == 9
assert faults(BELADY, 3, "FIFO") == 9
assert faults(BELADY, 4, "FIFO") == 10          # Belady's anomaly
assert faults(BELADY, 4, "LRU") <= faults(BELADY, 3, "LRU")   # LRU never suffers it

# address translation: 5230 with 1024-byte pages -> page 5, offset 110
ev, _ = simulate([(5230, False)], 2, "FIFO")
assert (ev[0]["page"], ev[0]["offset"]) == (5, 110)

# dirty page must be written back when evicted
_, st = simulate([(0, True), (1024, False), (2048, False)], 2, "FIFO")
assert st["disk_writes"] == 1

print("Clock on textbook string:", faults(TEXTBOOK, 3, "Clock"), "faults")
print("All tests passed")
