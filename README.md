# Virtual Memory Manager Simulator (OS project)

Run:  `pip install -r requirements.txt`  then  `streamlit run app.py`
Check the engine:  `python tests.py`

| File | Owner | Job |
|---|---|---|
| engine.py | Person A | The OS: page table, TLB, page fault handler, replacement policies, disk counters, EAT |
| app.py | Person B | Screens, animation, charts |
| tests.py | Both | Known answers (textbook 15/12/9, Belady 9 -> 10) |

## OS concepts this implements (use for the report and viva)
- Virtual address -> page number + offset; physical address = frame x page size + offset
- Page table entry: valid, referenced, dirty bits
- TLB (small LRU cache of translations), invalidated when a page is evicted
- Page fault handling: trap, free frame or victim, write-back if dirty, disk read, table update
- Replacement policies: FIFO, LRU, Optimal, Clock (second chance)
- Effective access time: EAT = (1 - p) x memory time + p x fault service time
- Belady's anomaly, and why LRU/Optimal (stack algorithms) are immune

## Ideas for your own additions (to make it yours)
1. Add LFU or MRU: write a new class in engine.py with choose_victim, then add it to POLICIES.
2. Two-level page table, or multiple processes with local vs global replacement.
3. Thrashing demo: shrink frames and plot EAT.
