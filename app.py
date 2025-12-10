"""
==========================================
 LOTTERY OPTIMIZER – EXACTLY ONE 4-MATCH
==========================================

This script:
- Loads an Excel file containing lottery tickets (Column A: "1,2,3,4,5,6,7")
- Finds a 7-number combination (1–37) that:
    • Matches EXACTLY ONE ticket with 4 numbers
    • Matches ZERO tickets with 5, 6, or 7 numbers
    • Minimizes total payout
- Performs:
    • Random deep search
    • Targeted fallback search
    • Local improvement search
- Saves top 10 combinations to CSV

Author: Your Name
GitHub: your_link_here
"""

import pandas as pd
import numpy as np
import random
import time
from itertools import combinations


def load_tickets(filename):
    df = pd.read_excel(filename)
    tickets = [list(map(int, str(row).split(','))) for row in df.iloc[:, 0]]
    return tickets


def build_presence_matrix(tickets):
    n = len(tickets)
    presence = np.zeros((n, 37), dtype=np.uint8)
    for i, t in enumerate(tickets):
        for num in t:
            presence[i, num - 1] = 1
    return presence


def score_and_check(combo, presence, payout_map):
    cols = [c - 1 for c in combo]
    matches = presence[:, cols].sum(axis=1)

    if np.any(matches >= 5):      # reject 5+, 6, 7 matches
        return None
    if np.sum(matches == 4) != 1: # require EXACTLY one 4-match
        return None

    return int(payout_map[matches].sum())


def random_search(nums, presence, payout_map, time_limit, max_random):
    best_combo = None
    best_score = 10**18
    found = 0

    start = time.time()
    iters = 0

    while time.time() - start < time_limit and iters < max_random:
        iters += 1
        combo = random.sample(nums, 7)
        score = score_and_check(combo, presence, payout_map)

        if score is None:
            continue

        found += 1
        if score < best_score:
            best_combo = sorted(combo)
            best_score = score

    return best_combo, best_score, found


def targeted_search(tickets, nums, presence, payout_map, best_combo, best_score):
    if best_combo is not None:
        return best_combo, best_score

    for t in tickets:
        for four in combinations(t, 4):
            pool = [x for x in nums if x not in four and x not in t]
            for _ in range(300):
                add = random.sample(pool, 3)
                combo = sorted(list(four) + add)
                score = score_and_check(combo, presence, payout_map)

                if score is not None and score < best_score:
                    best_combo = combo
                    best_score = score

    return best_combo, best_score


def local_improvement(best_combo, best_score, nums, presence, payout_map, iterations=20000):
    current = best_combo.copy()
    current_score = best_score
    saved = {tuple(current): current_score}

    for _ in range(iterations):
        num_out = random.choice(current)
        pool = [x for x in nums if x not in current]
        num_in = random.choice(pool)

        cand = current.copy()
        cand[cand.index(num_out)] = num_in
        cand = sorted(cand)

        score = score_and_check(cand, presence, payout_map)
        if score is None:
            continue

        if score < current_score:
            current = cand
            current_score = score
            saved[tuple(cand)] = score
        else:
            saved.setdefault(tuple(cand), score)

    top_sorted = sorted([(s, list(c)) for c, s in saved.items()])
    return top_sorted


def main(filename):
    tickets = load_tickets(filename)
    nums = list(range(1, 38))

    presence = build_presence_matrix(tickets)

    payout_map = np.zeros(8, dtype=np.int64)
    payout_map[3], payout_map[4], payout_map[5] = 15, 1000, 4000
    payout_map[6], payout_map[7] = 10000, 100000

    best_combo, best_score, found = random_search(
        nums, presence, payout_map,
        time_limit=120,
        max_random=300000
    )

    best_combo, best_score = targeted_search(
        tickets, nums, presence, payout_map,
        best_combo, best_score
    )

    if best_combo is None:
        print("❌ No valid combinations found.")
        return

    top_results = local_improvement(best_combo, best_score, nums, presence, payout_map)

    out_df = pd.DataFrame([{"score": s, "combo": ",".join(map(str, c))} for s, c in top_results[:10]])
    out_df.to_csv("top_exact_one_4match.csv", index=False)

    print("\n🏆 Best combinations:")
    for s, c in top_results[:10]:
        print(s, c)


if __name__ == "__main__":
    # Change filename manually or pass via command line
    main("tickets.xlsx")
