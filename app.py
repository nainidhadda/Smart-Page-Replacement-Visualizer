"""app.py - the screen (PERSON B owns this file). Run with:  streamlit run app.py"""
import time
import pandas as pd
import streamlit as st
from engine import POLICIES, simulate, pages_to_accesses, faults_vs_frames

st.set_page_config(page_title="Virtual Memory Manager Simulator", layout="wide")
st.title("Virtual Memory Manager Simulator")
st.caption("Watch the OS handle page faults: address translation, page table, TLB, replacement, disk I/O.")

PRESETS = {
    "Textbook": ("7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1", 3),
    "Belady's anomaly (try 3 then 4 frames)": ("1 2 3 4 1 2 5 1 2 3 4 5", 3),
    "High locality": ("1 2 3 1 2 3 1 2 3 4 1 2 3 5 1 2 3", 3),
    "Sequential scan": ("1 2 3 4 5 6 7 8 1 2 3 4 5 6 7 8", 4),
}

with st.sidebar:
    st.header("Setup")
    preset = st.selectbox("Preset", list(PRESETS))
    text = st.text_input("Page reference string", PRESETS[preset][0], key=f"r{preset}")
    frames = st.number_input("RAM frames", 1, 8, PRESETS[preset][1], key=f"f{preset}")
    page_size = st.selectbox("Page size (bytes)", [512, 1024, 4096], index=1)
    tlb_size = st.number_input("TLB entries (0 = no TLB)", 0, 8, 2)
    writes_on = st.checkbox("Make every 4th access a write (dirty pages)")
    mem_ns = st.number_input("Memory access time (ns)", 1, 1000, 100)
    fault_ms = st.number_input("Page fault service time (ms)", 1, 50, 8)

pages = [int(x) for x in text.replace(",", " ").split() if x.isdigit()][:40]
if not pages:
    st.warning("Enter a reference string such as: 7 0 1 2 0 3")
    st.stop()
writes = [writes_on and i % 4 == 3 for i in range(len(pages))]
accesses = pages_to_accesses(pages, page_size, writes)

def run(alg):
    return simulate(accesses, int(frames), alg, page_size, int(tlb_size), mem_ns, fault_ms)

def show(ev, box):
    colour = "#fbe3e0" if ev["fault"] else "#d9f2e8"
    cells = "".join(
        f"<div style='width:56px;height:56px;border:2px solid #888;border-radius:6px;display:grid;"
        f"place-items:center;font:700 20px monospace;background:"
        f"{colour if i == ev['frame'] else 'transparent'};color:#222'>{'' if p is None else p}</div>"
        for i, p in enumerate(ev["frames"]))
    with box.container():
        st.markdown(f"**Step {ev['time'] + 1}** - virtual address `{ev['vaddr']}` "
                    f"({'write' if ev['write'] else 'read'}) -> page `{ev['page']}`, offset `{ev['offset']}`")
        st.markdown(("🔴 **PAGE FAULT**" if ev["fault"] else "🟢 **HIT**"))
        st.markdown(f"<div style='display:flex;gap:6px'>{cells}</div>", unsafe_allow_html=True)
        st.write("")
        left, right = st.columns(2)
        with left:
            st.markdown("**What the OS did**")
            for line in ev["log"]:
                st.write("- " + line)
        with right:
            st.markdown("**Page table (resident pages)**")
            st.dataframe(pd.DataFrame(ev["page_table"]), hide_index=True)
            if tlb_size:
                st.caption("TLB (oldest first): " + ", ".join(f"{p}->{f}" for p, f in ev["tlb"]))

tab1, tab2, tab3, tab4 = st.tabs(["Live simulation", "Compare algorithms", "Frames vs faults", "Belady's anomaly"])

with tab1:
    c1, c2 = st.columns(2)
    alg = c1.selectbox("Algorithm", list(POLICIES))
    speed = c2.slider("Speed (seconds per step)", 0.1, 2.0, 0.8)
    if st.button("Start simulation", type="primary"):
        events, stats = run(alg)
        box, bar = st.empty(), st.empty()
        for ev in events:
            show(ev, box)
            done = events[:ev["time"] + 1]
            bar.progress((ev["time"] + 1) / len(events),
                         text=f"Faults so far: {sum(e['fault'] for e in done)}")
            time.sleep(speed)
        st.success(f"{alg}: {stats['faults']} faults, hit ratio {stats['hit_ratio']:.0%}, "
                   f"EAT {stats['eat_ns']:,.0f} ns, disk reads {stats['disk_reads']}, disk writes {stats['disk_writes']}")

with tab2:
    rows = [run(a)[1] for a in POLICIES]
    df = pd.DataFrame(rows).set_index("algorithm")[["faults", "hit_ratio", "tlb_hits", "disk_reads", "disk_writes", "eat_ns"]]
    st.dataframe(df.style.format({"hit_ratio": "{:.0%}", "eat_ns": "{:,.0f}"}))
    st.bar_chart(df["faults"])
    prac = df.loc[["FIFO", "LRU", "Clock"], "faults"]
    best = list(prac[prac == prac.min()].index)
    st.success(f"Best practical choice here: {', '.join(best)} ({prac.min()} faults). "
               f"Optimal ({df.loc['Optimal', 'faults']}) is a benchmark: it needs future knowledge.")
    st.info("Why EAT matters: one fault costs about "
            f"{fault_ms * 1_000_000 // mem_ns:,}x a normal memory access.")

with tab3:
    top = 8
    data = pd.DataFrame({a: faults_vs_frames(pages, a, top) for a in POLICIES}, index=range(1, top + 1))
    data.index.name = "frames"
    st.line_chart(data)
    st.caption("More frames usually means fewer faults. Does it always? See the next tab.")

with tab4:
    belady = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    st.write("Reference string: `1 2 3 4 1 2 5 1 2 3 4 5`")
    res = pd.DataFrame({a: faults_vs_frames(belady, a, 6) for a in ["FIFO", "LRU"]}, index=range(1, 7))
    res.index.name = "frames"
    st.line_chart(res)
    st.write(f"FIFO: **{res.loc[3, 'FIFO']} faults with 3 frames, {res.loc[4, 'FIFO']} with 4.** "
             "More RAM, more faults. LRU never does this because it is a stack algorithm.")
