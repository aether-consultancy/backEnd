# Pure crossword generation logic - no DB, no FastAPI.
# Given clue/answer word pairs, produces a grid layout via
# intersection-seeking placement, then derives blocked cells and
# numbered slots from wherever the words landed.

import random

MIN_WORD_LENGTH = 3
MAX_GRID_SIZE = 9


def _normalize(word: str) -> str:
    return word.strip().upper()


def place_words(words: list[dict]) -> dict:
    """
    words: [{"clue": str, "answer": str}, ...]
    Returns: {"placements": [{"answer", "clue", "row", "col", "direction"}]}
    direction: "across" | "down"
    Bounding box of all placed cells is capped at MAX_GRID_SIZE x MAX_GRID_SIZE -
    a placement that would push any cell outside that window (relative to
    the first word's origin) is rejected, same as a letter conflict.
    """
    ordered = sorted(words, key=lambda w: len(_normalize(w["answer"])), reverse=True)
    placements = []
    grid = {}  # (row, col) -> letter

    def fits(answer, row, col, direction):
        for i, ch in enumerate(answer):
            r = row + (i if direction == "down" else 0)
            c = col + (i if direction == "across" else 0)
            existing = grid.get((r, c))
            if existing is not None and existing != ch:
                return False

        all_r = [r for r, c in grid.keys()] + [row + (i if direction == "down" else 0) for i in range(len(answer))]
        all_c = [c for r, c in grid.keys()] + [col + (i if direction == "across" else 0) for i in range(len(answer))]
        if not grid:
            all_r = [row + (i if direction == "down" else 0) for i in range(len(answer))]
            all_c = [col + (i if direction == "across" else 0) for i in range(len(answer))]
        span_r = max(all_r) - min(all_r) + 1
        span_c = max(all_c) - min(all_c) + 1
        if span_r > MAX_GRID_SIZE or span_c > MAX_GRID_SIZE:
            return False

        return True

    def commit(answer, row, col, direction):
        for i, ch in enumerate(answer):
            r = row + (i if direction == "down" else 0)
            c = col + (i if direction == "across" else 0)
            grid[(r, c)] = ch

    ordered = [w for w in ordered if len(_normalize(w["answer"])) <= MAX_GRID_SIZE]
    if not ordered:
        return {"placements": [], "dropped": [w["answer"] for w in words]}

    first = ordered[0]
    first_answer = _normalize(first["answer"])
    commit(first_answer, 0, 0, "across")
    placements.append({"answer": first_answer, "clue": first["clue"], "row": 0, "col": 0, "direction": "across"})

    dropped = []
    for word in ordered[1:]:
        answer = _normalize(word["answer"])
        best = None
        for (r, c), letter in list(grid.items()):
            for i, ch in enumerate(answer):
                if ch != letter:
                    continue
                for direction in ("across", "down"):
                    row = r - (i if direction == "down" else 0)
                    col = c - (i if direction == "across" else 0)
                    if fits(answer, row, col, direction):
                        score = sum(
                            1 for j, ch2 in enumerate(answer)
                            if grid.get((row + (j if direction == "down" else 0),
                                         col + (j if direction == "across" else 0))) == ch2
                        )
                        if best is None or score > best[0]:
                            best = (score, row, col, direction)
        if best is None:
            dropped.append(word["answer"])
            continue
        _, row, col, direction = best
        commit(answer, row, col, direction)
        placements.append({"answer": answer, "clue": word["clue"], "row": row, "col": col, "direction": direction})

    return {"placements": placements, "dropped": dropped}


def build_grid(placements: list[dict]) -> dict:
    """Derives grid dims, blocked cells, slots, and solution from placements."""
    if not placements:
        return {"rows": 0, "cols": 0, "blocked_cells": [], "slots": [], "solution": {}}

    all_cells = {}
    for p in placements:
        for i, ch in enumerate(p["answer"]):
            r = p["row"] + (i if p["direction"] == "down" else 0)
            c = p["col"] + (i if p["direction"] == "across" else 0)
            all_cells[(r, c)] = ch

    min_r = min(r for r, c in all_cells)
    max_r = max(r for r, c in all_cells)
    min_c = min(c for r, c in all_cells)
    max_c = max(c for r, c in all_cells)

    rows = max_r - min_r + 1
    cols = max_c - min_c + 1

    norm_cells = {(r - min_r, c - min_c): ch for (r, c), ch in all_cells.items()}

    blocked_cells = [
        [r, c] for r in range(rows) for c in range(cols)
        if (r, c) not in norm_cells
    ]

    slots = []
    solution = {}
    number = 1
    starts = {}

    for r in range(rows):
        for c in range(cols):
            if (r, c) not in norm_cells:
                continue
            starts_across = (c == 0 or (r, c - 1) not in norm_cells) and (c + 1 < cols and (r, c + 1) in norm_cells)
            starts_down = (r == 0 or (r - 1, c) not in norm_cells) and (r + 1 < rows and (r + 1, c) in norm_cells)
            if starts_across or starts_down:
                starts[(r, c)] = number
                number += 1

    for p in placements:
        row = p["row"] - min_r
        col = p["col"] - min_c
        slot_number = starts.get((row, col))
        if slot_number is None:
            continue
        slots.append({
            "number": slot_number,
            "direction": p["direction"],
            "row": row,
            "col": col,
            "length": len(p["answer"]),
            "clue": p["clue"],
        })
        for i, ch in enumerate(p["answer"]):
            r = row + (i if p["direction"] == "down" else 0)
            c = col + (i if p["direction"] == "across" else 0)
            solution[f"{r},{c}"] = ch

    return {"rows": rows, "cols": cols, "blocked_cells": blocked_cells, "slots": slots, "solution": solution}


def assign_bonus_slots(slots: list[dict], bonus_coins: int, count: int = 1) -> list[dict]:
    """Randomly flags `count` slots with a hidden bonus_coins value."""
    if not slots:
        return slots
    chosen = random.sample(slots, k=min(count, len(slots)))
    chosen_numbers = {s["number"] for s in chosen}
    for s in slots:
        s["bonus_coins"] = bonus_coins if s["number"] in chosen_numbers else None
    return slots


def generate_crossword(words: list[dict], bonus_coins: int = 10, bonus_count: int = 1) -> dict:
    """Full pipeline: clue/answer pairs -> ready-to-save level data.
    Result includes a "dropped" list of answers that couldn't be placed
    (no valid intersection found) - caller must check and warn on this."""
    valid_words = [w for w in words if len(_normalize(w["answer"])) >= MIN_WORD_LENGTH]
    skipped_short = [w["answer"] for w in words if len(_normalize(w["answer"])) < MIN_WORD_LENGTH]
    placement_result = place_words(valid_words)
    grid = build_grid(placement_result["placements"])
    grid["slots"] = assign_bonus_slots(grid["slots"], bonus_coins, bonus_count)
    grid["dropped"] = placement_result["dropped"] + skipped_short
    return grid


def generate_crossword_at_least(words_pool: list[dict], min_words: int = 7, bonus_coins: int = 10, bonus_count: int = 1):
    """
    Grows the candidate set from words_pool (in order) until the placed
    word count reaches min_words, or the pool runs out. Returns
    (grid, consumed_count) - consumed_count is how many words from the
    front of words_pool were used in this attempt (placed or dropped),
    so the caller can advance its own queue past them.
    """
    candidates = []
    grid = None
    for word in words_pool:
        candidates.append(word)
        grid = generate_crossword(candidates, bonus_coins=bonus_coins, bonus_count=bonus_count)
        if len(grid["slots"]) >= min_words:
            return grid, len(candidates)
    return grid, len(candidates)
