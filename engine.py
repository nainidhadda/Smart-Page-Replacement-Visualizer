"""
engine.py - a small virtual memory manager (the OS part of the project).

It models what a real OS + MMU do on every memory access:

  virtual address -> (page number, offset) -> TLB -> page table
      -> hit:  physical address = frame * page_size + offset
      -> miss: PAGE FAULT -> find a free frame (or pick a victim with the
               replacement policy) -> write the victim to disk if dirty
               -> read the page from disk -> update page table -> retry

PERSON A owns this file. Nothing here knows about Streamlit or the screen.
"""
from collections import OrderedDict


# ---------------------------------------------------------------- data ----
class PageTableEntry:
    """One row of the page table (what the MMU looks at)."""
    def __init__(self):
        self.valid = False        # is the page in RAM?
        self.frame = None         # which frame holds it
        self.referenced = False   # set on every access (used by Clock)
        self.dirty = False        # set on a write (must be saved to disk on eviction)
        self.loaded_at = -1       # time it was loaded (used by FIFO)
        self.last_used = -1       # time of last access (used by LRU)


# ------------------------------------------------------------ policies ----
class Policy:
    """A replacement policy answers one question: which page do we evict?"""
    name = "base"

    def reset(self, mm):
        pass

    def choose_victim(self, mm, now):
        """Return (victim_page, human_readable_reason)."""
        raise NotImplementedError


class FIFO(Policy):
    name = "FIFO"

    def choose_victim(self, mm, now):
        victim = min(mm.resident_pages(), key=lambda p: mm.page_table[p].loaded_at)
        return victim, f"page {victim} has been in RAM longest (loaded at step {mm.page_table[victim].loaded_at})"


class LRU(Policy):
    name = "LRU"

    def choose_victim(self, mm, now):
        victim = min(mm.resident_pages(), key=lambda p: mm.page_table[p].last_used)
        idle = now - mm.page_table[victim].last_used
        return victim, f"page {victim} was last used {idle} step(s) ago, the longest idle"


class Optimal(Policy):
    name = "Optimal"

    def choose_victim(self, mm, now):
        future = mm.future_pages[now + 1:]
        best, best_dist = None, -1
        for p in mm.resident_pages():
            dist = future.index(p) if p in future else float("inf")
            if dist > best_dist:
                best, best_dist = p, dist
        if best_dist == float("inf"):
            return best, f"page {best} is never used again"
        return best, f"page {best} is not needed for {best_dist} more step(s)"


class Clock(Policy):
    name = "Clock"

    def reset(self, mm):
        self.hand = 0

    def choose_victim(self, mm, now):
        n = mm.num_frames
        skipped = 0
        while True:
            page = mm.frames[self.hand]
            pte = mm.page_table[page]
            if pte.referenced:                 # second chance
                pte.referenced = False
                skipped += 1
                self.hand = (self.hand + 1) % n
            else:
                self.hand = (self.hand + 1) % n
                return page, f"clock hand cleared {skipped} reference bit(s), then found page {page} with bit 0"


POLICIES = {"FIFO": FIFO, "LRU": LRU, "Optimal": Optimal, "Clock": Clock}


# ------------------------------------------------------ memory manager ----
class MemoryManager:
    def __init__(self, num_frames, policy, page_size=1024, num_pages=64, tlb_size=0):
        self.num_frames = num_frames
        self.page_size = page_size
        self.num_pages = num_pages
        self.tlb_size = tlb_size
        self.policy = policy
        self.frames = [None] * num_frames                       # frame -> page
        self.page_table = {p: PageTableEntry() for p in range(num_pages)}
        self.tlb = OrderedDict()                                # page -> frame (LRU order)
        self.time = 0
        self.future_pages = []                                  # only Optimal reads this
        self.disk_reads = self.disk_writes = self.tlb_hits = 0
        policy.reset(self)

    def resident_pages(self):
        return [p for p in self.frames if p is not None]

    def access(self, vaddr, write=False):
        """Perform one memory access and return an event describing everything."""
        page, offset = divmod(vaddr, self.page_size)
        if page >= self.num_pages:
            raise ValueError(f"segmentation fault: address {vaddr} is outside the address space")
        now = self.time
        self.time += 1
        pte = self.page_table[page]
        log, victim, victim_reason, wrote_back = [], None, "", False

        # 1. TLB lookup (a small cache of page -> frame translations)
        tlb_hit = self.tlb_size > 0 and page in self.tlb
        if self.tlb_size:
            if tlb_hit:
                self.tlb.move_to_end(page)
                self.tlb_hits += 1
                log.append(f"TLB hit: page {page} -> frame {pte.frame}")
            else:
                log.append("TLB miss: walk the page table")

        # 2. Page table lookup
        fault = not pte.valid
        if fault:
            log.append(f"Page table: valid bit of page {page} is 0 -> PAGE FAULT (trap to OS)")
            if None in self.frames:
                frame = self.frames.index(None)
                log.append(f"OS finds free frame {frame}")
            else:
                victim, victim_reason = self.policy.choose_victim(self, now)
                vpte = self.page_table[victim]
                frame = vpte.frame
                log.append(f"No free frame. {self.policy.name} evicts: {victim_reason}")
                if vpte.dirty:
                    self.disk_writes += 1
                    wrote_back = True
                    log.append(f"Page {victim} is dirty -> written back to disk")
                vpte.valid, vpte.frame, vpte.dirty, vpte.referenced = False, None, False, False
                self.tlb.pop(victim, None)                       # stale translation
                self.frames[frame] = None
            self.disk_reads += 1
            log.append(f"Disk read: page {page} loaded into frame {frame}; page table updated")
            pte.valid, pte.frame, pte.loaded_at = True, frame, now
            self.frames[frame] = page
        else:
            log.append(f"Page table: valid bit is 1 -> frame {pte.frame}" if not tlb_hit else "Translation served from TLB")

        # 3. The access itself (hardware sets these bits)
        pte.referenced, pte.last_used = True, now
        if write:
            pte.dirty = True
        if self.tlb_size and page not in self.tlb:
            if len(self.tlb) >= self.tlb_size:
                self.tlb.popitem(last=False)
            self.tlb[page] = pte.frame

        paddr = pte.frame * self.page_size + offset
        log.append(f"Physical address = frame {pte.frame} x {self.page_size} + {offset} = {paddr}")
        return {
            "time": now, "vaddr": vaddr, "page": page, "offset": offset, "write": write,
            "tlb_hit": tlb_hit, "fault": fault, "frame": pte.frame, "paddr": paddr,
            "victim": victim, "victim_reason": victim_reason, "wrote_back": wrote_back,
            "log": log, "frames": list(self.frames),
            "ref_bits": [self.page_table[p].referenced if p is not None else None for p in self.frames],
            "page_table": [
                {"page": p, "frame": e.frame, "valid": int(e.valid),
                 "referenced": int(e.referenced), "dirty": int(e.dirty)}
                for p, e in self.page_table.items() if e.valid
            ],
            "tlb": list(self.tlb.items()),
        }


# ------------------------------------------------------------- runners ----
def effective_access_time(fault_rate, mem_ns=100, fault_ms=8):
    """EAT = (1 - p) * memory access time + p * page fault service time (in ns)."""
    return (1 - fault_rate) * mem_ns + fault_rate * fault_ms * 1_000_000


def simulate(accesses, num_frames, policy_name, page_size=1024, tlb_size=0, mem_ns=100, fault_ms=8):
    """accesses = list of (virtual_address, is_write). Returns (events, stats)."""
    pages_needed = max(a // page_size for a, _ in accesses) + 1
    mm = MemoryManager(num_frames, POLICIES[policy_name](), page_size, max(64, pages_needed), tlb_size)
    mm.future_pages = [a // page_size for a, _ in accesses]
    events = [mm.access(a, w) for a, w in accesses]
    faults = sum(e["fault"] for e in events)
    total = len(events)
    rate = faults / total if total else 0
    stats = {
        "algorithm": policy_name, "accesses": total, "faults": faults, "hits": total - faults,
        "hit_ratio": 1 - rate, "fault_rate": rate, "tlb_hits": mm.tlb_hits,
        "disk_reads": mm.disk_reads, "disk_writes": mm.disk_writes,
        "eat_ns": effective_access_time(rate, mem_ns, fault_ms),
    }
    return events, stats


def pages_to_accesses(pages, page_size=1024, writes=None):
    """Turn a page reference string into virtual addresses (offset 100 inside each page)."""
    writes = writes or [False] * len(pages)
    return [(p * page_size + 100, w) for p, w in zip(pages, writes)]


def faults_vs_frames(pages, policy_name, max_frames=8):
    return [simulate(pages_to_accesses(pages), f, policy_name)[1]["faults"] for f in range(1, max_frames + 1)]
