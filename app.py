
The tool will search for a **7-number combination (1–37)** that:

- Produces the **lowest total payout**
- Has **exactly ONE 4-match**
- Has **ZERO 5/6/7 matches**
""")

uploaded_file = st.file_uploader("📂 Upload Excel File", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Parse tickets into list-of-lists
    tickets = [list(map(int, str(row).split(','))) for row in df.iloc[:, 0]]
    n_tickets = len(tickets)

    # Build presence matrix for fast match calculation
    presence = np.zeros((n_tickets, 37), dtype=np.uint8)
    for i, t in enumerate(tickets):
        for num in t:
            presence[i, num - 1] = 1

    payout_map = np.zeros(8, dtype=np.int64)
    payout_map[3] = 15
    payout_map[4] = 1000
    payout_map[5] = 4000
    payout_map[6] = 10000
    payout_map[7] = 100000

    def score_and_check(combo):
        """Returns payout if valid, else None."""
        cols = [c - 1 for c in combo]
        matches = presence[:, cols].sum(axis=1)

        # reject 5+ matches
        if np.any(matches >= 5):
            return None

        # must have exactly ONE 4-match
        if np.sum(matches == 4) != 1:
            return None

        total = int(payout_map[matches].sum())
        return total

    st.subheader("⚙ Settings")
    TIME_LIMIT = st.slider("Random Search Time (seconds)", 10, 300, 120)
    MAX_RANDOM = st.number_input("Max Random Tries", 50000, 1000000, 300000)
    LOCAL_IMPROVE = st.number_input("Local Improvement Steps", 5000, 100000, 20000)

    if st.button("🚀 Start Deep Search"):
        nums = list(range(1, 38))
        best_combo = None
        best_score = 10**18
        valid_found = 0

        st.write("⏳ Running deep search…")
        progress = st.progress(0)
        status = st.empty()

        start = time.time()
        iters = 0

        # -------------------------
        # RANDOM SEARCH
        # -------------------------
        while time.time() - start < TIME_LIMIT and iters < MAX_RANDOM:
            iters += 1
            combo = random.sample(nums, 7)
            s = score_and_check(combo)
            if s is None:
                continue

            valid_found += 1
            if s < best_score:
                best_score = s
                best_combo = sorted(combo)

            if iters % 1000 == 0:
                progress.progress(min(1.0, iters / MAX_RANDOM))
                status.write(f"Checked {iters:,} combos…")

        st.success("Random search finished.")

        # -------------------------
        # TARGETED SEARCH
        # -------------------------
        if best_combo is None:
            st.warning("No valid combo in random search. Starting targeted search…")
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

        st.write("Best after targeted search:", best_combo, best_score)

        # -------------------------
        # LOCAL IMPROVEMENT
        # -------------------------
        if best_combo:
            st.write("🔧 Running local improvement…")
            current = best_combo.copy()
            current_score = best_score
            top_candidates = {tuple(current): current_score}

            for _ in range(LOCAL_IMPROVE):
                num_out = random.choice(current)
                pool = [x for x in range(1, 38) if x not in current]
                num_in = random.choice(pool)

                cand = current.copy()
                cand[cand.index(num_out)] = num_in
                cand = sorted(cand)

                s = score_and_check(cand)
                if s is None:
                    continue

                if s < current_score:
                    current = cand
                    current_score = s
                    top_candidates[tuple(cand)] = s

            # Sort top results
            top_sorted = sorted([(s, list(c)) for c, s in top_candidates.items()])
            top10 = top_sorted[:10]

            st.subheader("🏆 Top 10 Results")
            for s, c in top10:
                st.write(f"**₹{s}** — {c}")

            # Export CSV
            out_df = pd.DataFrame([{"score": s, "combo": ",".join(map(str, c))} for s, c in top10])
            csv_data = out_df.to_csv(index=False).encode()
            st.download_button(
                "📥 Download Result CSV",
                csv_data,
                "top_exact_one_4match.csv",
                "text/csv"
            )

        else:
            st.error("❌ No valid combinations found!")
