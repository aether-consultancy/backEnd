# Standalone seeding script - generates crossword levels from the word
# bank and saves them via gamemanager.crud. Run manually, not exposed
# as an API route.
#
# NOTE: insert-only, no upsert/dedupe. Re-running this appends a
# second full set of levels - if you need to reseed, wipe first:
#   DELETE FROM kid_level_bonus_claims WHERE level_id IN (SELECT id FROM game_levels WHERE game_type = 'crossword');
#   DELETE FROM kid_level_start_claims WHERE level_id IN (SELECT id FROM game_levels WHERE game_type = 'crossword');
#   DELETE FROM kid_slot_solve_claims WHERE level_id IN (SELECT id FROM game_levels WHERE game_type = 'crossword');
#   DELETE FROM game_levels WHERE game_type = 'crossword';

from itertools import cycle

from dbmanager.connection import SessionLocal
from gamemanager.logic import generate_crossword_at_least
from gamemanager.models import GameLevel
from gamemanager.wordbank import WORD_BANK

MIN_WORDS_PER_LEVEL = 7
POOL_TARGET = 15  # max candidates tried per level before giving up
TOTAL_LEVELS = 20
THEME_ORDER = ["english", "social studies", "chemistry", "astrology", "science", "animals", "plants"]


def seed_level(db, level_number: int, theme: str, grid: dict, completion_reward: int = 20):
    level = GameLevel(
        game_type="crossword",
        level_number=level_number,
        theme=theme,
        grid_rows=grid["rows"],
        grid_cols=grid["cols"],
        blocked_cells=grid["blocked_cells"],
        slots=grid["slots"],
        solution=grid["solution"],
        completion_reward=completion_reward,
    )
    db.add(level)
    db.commit()
    db.refresh(level)
    print(f"Seeded level {level_number} ({theme}) - id={level.id}, grid={grid['rows']}x{grid['cols']}, slots={len(grid['slots'])}")
    if grid["dropped"]:
        print(f"  !!! WARNING: {len(grid['dropped'])} word(s) DROPPED (no intersection / grid cap): {grid['dropped']}")


def seed_all():
    queues = {t: list(WORD_BANK[t]) for t in THEME_ORDER}
    db = SessionLocal()
    level_number = 1
    try:
        for theme in cycle(THEME_ORDER):
            if level_number > TOTAL_LEVELS:
                break
            if all(not q for q in queues.values()):
                print("All theme queues exhausted - stopping early.")
                break

            queue = queues[theme]
            if not queue:
                continue

            candidates = queue[:POOL_TARGET]
            grid, consumed = generate_crossword_at_least(candidates, min_words=MIN_WORDS_PER_LEVEL)
            queues[theme] = queue[consumed:]

            placed = len(grid["slots"])
            if placed < MIN_WORDS_PER_LEVEL:
                print(f"  !!! SKIPPED a {theme} level: only {placed} words placed (theme pool ran out), words returned to backlog not possible - pool consumed")
                continue

            seed_level(db, level_number, theme, grid)
            level_number += 1
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
