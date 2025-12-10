# ==========================================
#  STREAMLIT LOTTERY OPTIMIZER
#  EXACTLY ONE 4-MATCH — NO 5+ MATCHES
# ==========================================

import streamlit as st
import pandas as pd
import numpy as np
import random
import time
from itertools import combinations

st.set_page_config(page_title="Lottery Optimizer", layout="wide")

st.title("🎯 Lottery Optimizer — EXACTLY One 4-Match")

st.write(
    """
Upload an Excel file where **Column A contains tickets** in this format:

`1,2,3,4,5,6,7`

The tool will search for a 7-number combination (1 to 37) that:

- Produces the **lowest possible payout**
- Has **exactly one 4-match**
- Has **zero 5, 6, or 7 matches**
"""
)

uploaded_file = st.file_uploader("📂 Upload Excel File", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Parse tickets to list of lists
    tickets = [list(map(int, str(row).split(','))) for row in df.iloc[:, 0]]
    n_tickets = len(tickets)

    # Create binary presence matrix for fast match calculation
    presence = np.zeros((n_tickets, 37), dtype=np.uint8)
    for i, t in enumerate(tickets):
        for num in t:
            presence[i, num - 1] = 1

    # Payouts
    payout_map = np.zeros(8, dtype=np.int64)
    payout_map[3] = 15
    payout_map[4] = 1000
    payout_map[5] = 4000
    payout_map[6] = 10000
    payout_map[7] = 100000

    def score_and_check(combo):
        """Calculate payout if valid, else return None."""
        cols = [c - 1 for c in combo]
        matches = presence[:, cols].sum(axis=1)

        # Reject 5+ matches
        if np.any(matches >= 5):
            return None

        # Require exactly one 4-match
        if np.sum(matches == 4) != 1:
            return None

        return int(payout_map[matches].sum())

    st.subheader("⚙ Settings")
    TIME_LIMIT = st.slider("Random Search Time (seconds)", 10, 300, 120)
    MAX_RANDOM = st.number_input("Max Random Attempts", 50000, 1000000, 300000)
    LOCAL_IMPROVE = st.number_input("Local Improvement Steps", 5000, 100000, 20000)

    if st.button("🚀 Start Search"):

        nums = list(range(1, 38))
        best_combo = None
        best_score = 10**18
        valid_found = 0

        st.write("⏳ Running deep random search...")
        progress = st.progress(0)
        status = st.empty()

        start = time.time()
        iters = 0

        # RANDOM SEARCH
        while time.time() - start < TIME_LIMIT and iters < MAX_RANDOM:
            iters += 1
            combo = random.sample(nums, 7)
            s = score_and_check(combo)

            if s is not None:
                valid_found += 1
                if s < best_score:
                    best_score = s
                    best_combo = sorted(combo)

            if iters % 2000 == 0:
                progress.progress(min(1.0, iters / MAX_RANDOM))
                status.write(f"Checked {iters:,} combinations...")

        st.success("Random search completed.")

        # TARGETED SEARCH (if random failed)
        if best_combo is None:
            st.warning("No valid result found in random search. Trying targeted method...")

            for t in tickets:
                for four in combinations(t, 4):
                    pool = [x for x in range(1, 38) if x not in four and x not in t]

                    for _ in range(200):
                        add = random.sample(pool, 3)
                        combo = sorted(list(four) + add)
                        s = score_and_check(combo)

                        if s is not None and s < best_score:
                            best_score = s
                            best_combo = combo

        # LOCAL IMPROVEMENT
        if best_combo:
            st.write("🔧 Running local improvement...")

            current = best_combo.copy()
            current_score = best_score
            top_candidates = {tuple(current): current_score}

            for _ in range(int(LOCAL_IMPROVE)):
                num_out = random.choice(current)
                pool = [x for x in range(1, 38) if x not in current]
                num_in = random.choice(pool)

                new_combo = current.copy()
                new_combo[new_combo.index(num_out)] = num_in
                new_combo = sorted(new_combo)

                s = score_and_check(new_combo)

                if s is not None and s < current_score:
                    current = new_combo
                    current_score = s
                    top_candidates[tuple(new_combo)] = s

            # Sort top results
            top_list = sorted([(s, list(c)) for c, s in top_candidates.items()])[:10]

            st.subheader("🏆 Top 10 Best Combinations")
            for s, c in top_list:
                st.write(f"₹{s} — {c}")

            # CSV Export
            out_df = pd.DataFrame(
                [{"score": s, "combo": ",".join(map(str, c))} for s, c in top_list]
            )
            csv_data = out_df.to_csv(index=False).encode()

            st.download_button(
                "📥 Download CSV Results",
                csv_data,
                "top_exact_one_4match.csv",
                "text/csv",
            )

        else:
            st.error("❌ No valid combination found!")
