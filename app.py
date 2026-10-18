"""app.py - the screen for the Virtual Memory Manager Simulator."""
import time

import pandas as pd
import streamlit as st
from engine import POLICIES, faults_vs_frames, pages_to_accesses, simulate

st.set_page_config(page_title="Virtual Memory Manager Simulator", layout="wide")

st.markdown(
    """
    <style>
    .stDeployButton { display: none; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stAppViewContainer"] {
        background: #101820;
        color: #e5edf1;
        font-family: "Aptos", "Segoe UI", sans-serif;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: #151f28;
        border-right: 1px solid #2b3944;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.55rem; }
    .main .block-container {
        max-width: 1480px;
        padding: 2rem clamp(1rem, 3vw, 3rem) 3rem;
    }
    h1, h2, h3 { color: #f1f5f7; letter-spacing: 0; }
    h1 { font-size: 2rem; font-weight: 650; }
    [data-testid="stCaptionContainer"] { color: #9aabb6; }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.35rem;
        border-bottom: 1px solid #2b3944;
    }
    [data-testid="stTabs"] button[role="tab"] {
        color: #aab8c1;
        border-radius: 5px 5px 0 0;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #73c7bd;
        border-bottom-color: #73c7bd;
    }
    [data-testid="stWidgetLabel"] p { color: #c3cfd5; font-size: 0.88rem; }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #1b2731;
        border-color: #354550;
        color: #e5edf1;
        border-radius: 5px;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #2b3944;
        border-radius: 5px;
        overflow: hidden;
    }
    [data-testid="stMetric"] {
        background: #17232c;
        border: 1px solid #2b3944;
        border-radius: 5px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stMetricLabel"] { color: #aab8c1; }
    [data-testid="stMetricValue"] { color: #edf4f5; }
    button[kind="primary"] {
        background: #287f79;
        border: 1px solid #3b9990;
        border-radius: 5px;
    }
    [data-testid="stProgressBar"] > div > div { background: #55aaa1; }
    .memory-grid { display: flex; flex-wrap: wrap; gap: 0.55rem; }
    .memory-slot { flex: 1 1 76px; max-width: 104px; min-width: 68px; }
    .memory-label {
        display: block;
        margin: 0 0 0.3rem 0.15rem;
        color: #8fa1ac;
        font: 600 0.66rem "Consolas", monospace;
        letter-spacing: 0.04em;
    }
    .memory-cell {
        display: grid;
        place-items: center;
        height: 54px;
        border: 1px solid #42515b;
        border-radius: 4px;
        color: #e5edf1;
        font: 650 1.2rem "Consolas", monospace;
    }
    .memory-cell.resident { background: #202e38; }
    .memory-cell.empty { background: #141e26; border-style: dashed; color: #657681; }
    .memory-cell.hit { background: #1b3938; border-color: #4b918a; color: #9de0d6; }
    .memory-cell.fault { background: #3b292a; border-color: #a56868; color: #efb2aa; }
    .event-status {
        display: inline-block;
        margin: 0.15rem 0 0.8rem;
        padding: 0.25rem 0.55rem;
        border: 1px solid;
        border-radius: 3px;
        font: 650 0.72rem "Consolas", monospace;
        letter-spacing: 0.04em;
    }
    .event-status.hit { color: #9de0d6; border-color: #4b918a; background: #1b3938; }
    .event-status.fault { color: #efb2aa; border-color: #a56868; background: #3b292a; }
    @media (max-width: 640px) {
        .main .block-container { padding: 1.2rem 0.8rem 2rem; }
        h1 { font-size: 1.65rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.html(
    """
    <script>
    (() => {
        const observedRoots = new WeakSet();
        const installStyle = (root) => {
            if (observedRoots.has(root)) return;
            observedRoots.add(root);
            const styleRoot = root instanceof Document ? root.head : root;
            if (!styleRoot.querySelector("#vm-hide-deploy")) {
                const style = document.createElement("style");
                style.id = "vm-hide-deploy";
                style.textContent = ".stDeployButton, .stAppDeployButton, [data-testid='stAppDeployButton'] { display: none !important; }";
                styleRoot.appendChild(style);
            }
            const scan = () => root.querySelectorAll("*").forEach((element) => {
                if (element.shadowRoot) installStyle(element.shadowRoot);
            });
            new MutationObserver(scan).observe(root, { childList: true, subtree: true });
            scan();
        };
        installStyle(document);
    })();
    </script>
    """,
    unsafe_allow_javascript=True,
)

st.title("Virtual Memory Manager Simulator")
st.caption("Operating systems lab · Address translation, page replacement, TLB, and disk I/O")

PRESETS = {
    "Textbook": ("7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1", 3),
    "Belady's anomaly (try 3 then 4 frames)": ("1 2 3 4 1 2 5 1 2 3 4 5", 3),
    "High locality": ("1 2 3 1 2 3 1 2 3 4 1 2 3 5 1 2 3", 3),
    "Sequential scan": ("1 2 3 4 5 6 7 8 1 2 3 4 5 6 7 8", 4),
}
BELADY_PRESET = "Belady's anomaly (try 3 then 4 frames)"

if st.session_state.get("example") not in PRESETS:
    st.session_state.example = "Textbook"
    st.session_state.reference_string = PRESETS["Textbook"][0]
    st.session_state.frame_count = PRESETS["Textbook"][1]
if "reference_string" not in st.session_state:
    st.session_state.reference_string = PRESETS[st.session_state.example][0]
if "frame_count" not in st.session_state:
    st.session_state.frame_count = PRESETS[st.session_state.example][1]
if "algorithm" not in st.session_state:
    st.session_state.algorithm = "FIFO"


def apply_preset():
    reference, frame_count = PRESETS[st.session_state.example]
    st.session_state.reference_string = reference
    st.session_state.frame_count = frame_count
    if st.session_state.example == BELADY_PRESET:
        st.session_state.algorithm = "FIFO"


def select_belady_frames(frame_count):
    st.session_state.frame_count = frame_count
    st.session_state.algorithm = "FIFO"


with st.sidebar:
    st.header("Basic setup")
    preset = st.selectbox("Preset", list(PRESETS), key="example", on_change=apply_preset)
    text = st.text_input("Page reference string", key="reference_string")
    frames = st.number_input("Number of RAM frames", 1, 8, key="frame_count")
    alg = st.selectbox("Page replacement algorithm", list(POLICIES), key="algorithm")
    run_three_clicked = run_four_clicked = False
    if preset == BELADY_PRESET:
        run_3_col, run_4_col = st.columns(2)
        run_three_clicked = run_3_col.button(
            "Run with 3 frames", type="primary", on_click=select_belady_frames, args=(3,))
        run_four_clicked = run_4_col.button(
            "Run with 4 frames", type="primary", on_click=select_belady_frames, args=(4,))
        run_clicked = run_three_clicked or run_four_clicked
        run_frames = 3 if run_three_clicked else 4 if run_four_clicked else int(frames)
        simulation_algorithm = "FIFO"
    else:
        run_clicked = st.button("Run simulation", type="primary")
        run_frames = int(frames)
        simulation_algorithm = alg

    with st.expander("Advanced settings", expanded=False):
        page_size = st.selectbox("Page size (bytes)", [512, 1024, 4096], index=1)
        tlb_size = st.number_input("TLB entries (0 = no TLB)", 0, 8, 2)
        writes_on = st.checkbox("Make every 4th access a write (dirty pages)")
        mem_ns = st.number_input("Memory access time (ns)", 1, 1000, 100)
        fault_ms = st.number_input("Page fault service time (ms)", 1, 50, 8)

pages = [int(value) for value in text.replace(",", " ").split() if value.isdigit()][:40]
if not pages:
    st.warning("Enter a reference string such as: 7 0 1 2 0 3")
    st.stop()
writes = [writes_on and index % 4 == 3 for index in range(len(pages))]
accesses = pages_to_accesses(pages, page_size, writes)


def run(algorithm, frame_count=None):
    selected_frames = int(frames if frame_count is None else frame_count)
    return simulate(accesses, selected_frames, algorithm, page_size, int(tlb_size), mem_ns, fault_ms)


def show(event, box, algorithm):
    box.empty()
    cells = "".join(
        f"<div class='memory-slot'><span class='memory-label'>FRAME {index}</span>"
        f"<div class='memory-cell {'empty' if page is None else 'resident' if index != event['frame'] else 'fault' if event['fault'] else 'hit'}'>"
        f"{'' if page is None else page}</div></div>"
        for index, page in enumerate(event["frames"])
    )
    with box.container():
        st.markdown(
            f"**Step {event['time'] + 1}** - virtual address `{event['vaddr']}` "
            f"({'write' if event['write'] else 'read'}) -> page `{event['page']}`, offset `{event['offset']}`"
        )
        event_class = "fault" if event["fault"] else "hit"
        event_label = "PAGE FAULT" if event["fault"] else "PAGE HIT"
        st.markdown(f"<div class='event-status {event_class}'>{event_label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='memory-grid'>{cells}</div>", unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            st.markdown("#### OS activity")
            activity = []
            if event["fault"]:
                activity.append(f"Page {event['page']} was not in RAM.")
                if event["victim"] is not None:
                    activity.append(f"RAM was full, so {algorithm} removed page {event['victim']}.")
                activity.append(f"Page {event['page']} was loaded into frame {event['frame']}.")
            else:
                activity.append(f"Page {event['page']} was found in RAM.")
            activity.append(f"Memory access completed. Physical address: {event['paddr']}.")
            st.markdown("\n".join(f"- {line}" for line in activity))
        with right:
            st.markdown("#### Resident page table")
            st.dataframe(pd.DataFrame(event["page_table"]), hide_index=True, width="stretch")
            if tlb_size:
                st.caption("TLB · oldest first: " + ", ".join(f"{page} → frame {frame}" for page, frame in event["tlb"]))


tab1, tab2, tab3, tab4 = st.tabs(
    ["Live simulation", "Compare algorithms", "Frames vs faults", "Belady's anomaly"]
)

with tab1:
    if preset == BELADY_PRESET:
        fifo_3_faults = run("FIFO", 3)[1]["faults"]
        fifo_4_faults = run("FIFO", 4)[1]["faults"]
        st.caption(f"FIFO page faults · 3 frames: {fifo_3_faults} · 4 frames: {fifo_4_faults}")
    speed = st.slider("Speed (seconds per step)", 0.1, 2.0, 0.8)
    if run_clicked:
        events, stats = run(simulation_algorithm, run_frames)
        box, bar = st.empty(), st.empty()
        for event in events:
            show(event, box, simulation_algorithm)
            completed = events[:event["time"] + 1]
            bar.progress(
                (event["time"] + 1) / len(events),
                text=f"Faults so far: {sum(item['fault'] for item in completed)}",
            )
            time.sleep(speed)
        st.subheader("Run summary")
        metric_columns = st.columns(4)
        metric_columns[0].metric("Page faults", stats["faults"])
        metric_columns[1].metric("Hit ratio", f"{stats['hit_ratio']:.0%}")
        metric_columns[2].metric("Effective access time", f"{stats['eat_ns']:,.0f} ns")
        metric_columns[3].metric("Disk I/O", f"{stats['disk_reads']} reads · {stats['disk_writes']} writes")

with tab2:
    st.subheader("Algorithm comparison")
    rows = [run(algorithm)[1] for algorithm in POLICIES]
    comparison = pd.DataFrame(rows).set_index("algorithm")
    table = comparison[["faults", "hit_ratio", "eat_ns"]].rename(
        columns={
            "faults": "Page Faults",
            "hit_ratio": "Hit Ratio",
            "eat_ns": "Effective Access Time (ns)",
        }
    )
    table.index.name = "Algorithm"
    table = table.reset_index()
    st.dataframe(
        table.style.format(
            {"Hit Ratio": "{:.1%}", "Effective Access Time (ns)": "{:,.0f}"}
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Page Faults by Replacement Algorithm")
    chart_data = table[["Algorithm", "Page Faults"]]
    st.bar_chart(

        chart_data,
        x="Algorithm",
        y="Page Faults",
        height=300,
)

    st.subheader("Understanding the Results")
    fewest_faults = comparison["faults"].min()
    most_faults = comparison["faults"].max()
    fewest_algorithms = list(comparison.index[comparison["faults"] == fewest_faults])
    most_algorithms = list(comparison.index[comparison["faults"] == most_faults])
    st.write(
        f"Fewest page faults: **{', '.join(fewest_algorithms)}** ({fewest_faults}). "
        f"Most page faults: **{', '.join(most_algorithms)}** ({most_faults})."
    )
    st.caption(
        "Results depend on the current reference string and frame count. "
        "Optimal uses future knowledge, so it is a theoretical benchmark."
    )

BELADY_REFERENCE_STRING = "1 2 3 4 1 2 5 1 2 3 4 5"

if "frames_faults_reference" not in st.session_state:
    st.session_state.frames_faults_reference = text

def load_belady_reference():
    st.session_state.frames_faults_reference = BELADY_REFERENCE_STRING

with tab3:
    st.subheader("Page faults by available RAM frames")
    reference_text = st.text_input(
        "Page reference string for this experiment",
        key="frames_faults_reference",
    )
    max_frames = st.slider("Maximum number of frames to test", 1, 10, 8)
    st.button(
        "Load classic Belady's anomaly string",
        on_click=load_belady_reference,
    )

    reference_tokens = reference_text.replace(",", " ").split()
    if not reference_tokens:
        st.error("Enter a page reference string, for example: 1 2 3 1 2 4.")
    elif any(not token.isdecimal() for token in reference_tokens):
        st.error("Use non-negative whole page numbers separated by spaces or commas.")
    elif len(reference_tokens) > 40:
        st.error("Enter no more than 40 page references for this experiment.")
    else:
        experiment_pages = [int(token) for token in reference_tokens]
        frame_counts = range(1, max_frames + 1)
        fault_counts = {
            algorithm: faults_vs_frames(experiment_pages, algorithm, max_frames)
            for algorithm in POLICIES
        }
        results = pd.DataFrame(fault_counts, index=frame_counts)
        chart_data = results.rename_axis("Number of frames").reset_index()
        st.line_chart(
            chart_data,
            x="Number of frames",
            y=["FIFO", "LRU", "Optimal", "Clock"],
            x_label="Number of RAM frames",
            y_label="Page faults",
            height=400,
        )

        table = results.rename(
            columns={algorithm: f"{algorithm} faults" for algorithm in POLICIES}
        )
        table.insert(0, "Number of frames", table.index)
        st.dataframe(table, hide_index=True, width="stretch")

        faults_at_max = results.loc[max_frames]
        fewest_faults = faults_at_max.min()
        fewest_algorithms = list(faults_at_max[faults_at_max == fewest_faults].index)
        st.markdown(
            f"**At {max_frames} frames:** {', '.join(fewest_algorithms)} had the fewest faults "
            f"({fewest_faults}). Results depend on this reference string and frame count."
        )

        first_counts = results.iloc[0]
        last_counts = results.iloc[-1]
        frame_changes = "; ".join(
            f"{algorithm}: {int(first_counts[algorithm])} to {int(last_counts[algorithm])}"
            for algorithm in POLICIES
        )
        st.write(f"**From 1 to {max_frames} frames:** {frame_changes} page faults.")

        reductions = []
        for algorithm in POLICIES:
            first_faults = int(first_counts[algorithm])
            last_faults = int(last_counts[algorithm])
            if first_faults == 0:
                change = "not meaningful because there were no faults at 1 frame"
            else:
                percent_change = (first_faults - last_faults) / first_faults * 100
                if percent_change > 0:
                    change = f"{percent_change:.1f}% fewer"
                elif percent_change < 0:
                    change = f"{abs(percent_change):.1f}% more"
                else:
                    change = "no change"
            reductions.append(f"{algorithm}: {change}")
        st.write(f"**Change from 1 to {max_frames} frames:** " + "; ".join(reductions) + ".")

        fifo_faults = results["FIFO"]
        anomaly_pairs = [
            (smaller, larger)
            for smaller in range(1, max_frames + 1)
            for larger in range(smaller + 1, max_frames + 1)
            if fifo_faults.loc[larger] > fifo_faults.loc[smaller]
        ]
        if anomaly_pairs:
            examples = ", ".join(
                f"{smaller} to {larger} frames ({fifo_faults.loc[smaller]} to {fifo_faults.loc[larger]} faults)"
                for smaller, larger in anomaly_pairs
            )
            st.markdown(
                f"**FIFO anomaly observed:** page faults increased for {examples}. "
                "This is possible with FIFO, but does not happen for every workload. "
                "Visit the Belady's anomaly tab for the detailed demonstration."
            )
        else:
            st.caption(
                "No FIFO anomaly appeared for this workload and frame range. "
                "Belady's anomaly is possible with FIFO, but does not happen for every workload. "
                "Visit the Belady's anomaly tab for the detailed demonstration."
            )

with tab4:
    st.subheader("FIFO and LRU frame behavior")
    belady = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    st.write("Reference string: `1 2 3 4 1 2 5 1 2 3 4 5`")
    res = pd.DataFrame(
        {algorithm: faults_vs_frames(belady, algorithm, 6) for algorithm in ["FIFO", "LRU"]},
        index=range(1, 7),
    )
    chart_data = res.rename_axis("frames").reset_index()
    st.line_chart(
        chart_data,
        x="frames",
        y=["FIFO", "LRU"],
        x_label="Number of RAM frames",
        y_label="Page faults",
    )
    st.write(f"FIFO: **{res.loc[3, 'FIFO']} faults with 3 frames, {res.loc[4, 'FIFO']} with 4.** "
             "More RAM, more faults. LRU never does this because it is a stack algorithm.")
