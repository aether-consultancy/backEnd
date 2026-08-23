from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta, timezone

from gamemanager.models import (
    GameLevel, KidGameProgress, KidWallet, KidLevelBonusClaim,
    KidLevelStartClaim, KidSlotSolveClaim, KidLeaderboardScore,
)
from kidsmanager.models import Kid, KidInfo

# ---------- XP config ----------
XP_START_LEVEL = 2
XP_SLOT_SOLVED = 5
XP_LEVEL_COMPLETE = 15

# leaderboard rank weighting - XP counts for more than raw coins
XP_WEIGHT = 3
COIN_WEIGHT = 1


def get_or_create_progress(db: Session, kid_id: int, game_type: str) -> KidGameProgress:
    progress = db.query(KidGameProgress).filter(
        KidGameProgress.kid_id == kid_id, KidGameProgress.game_type == game_type
    ).first()
    if progress:
        return progress
    progress = KidGameProgress(kid_id=kid_id, game_type=game_type, current_level=1, completed_levels=[])
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def get_next_levels(db: Session, kid_id: int, game_type: str, batch_size: int = 5) -> tuple[int, list[GameLevel]]:
    progress = get_or_create_progress(db, kid_id, game_type)
    levels = db.query(GameLevel).filter(
        GameLevel.game_type == game_type,
        GameLevel.level_number >= progress.current_level,
    ).order_by(GameLevel.level_number.asc()).limit(batch_size).all()
    return progress.current_level, levels


def get_level_by_id(db: Session, level_id: int) -> GameLevel | None:
    return db.query(GameLevel).filter(GameLevel.id == level_id).first()


def get_or_create_wallet(db: Session, kid_id: int) -> KidWallet:
    wallet = db.query(KidWallet).filter(KidWallet.kid_id == kid_id).first()
    if wallet:
        return wallet
    wallet = KidWallet(kid_id=kid_id, coins=0, keys=0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def has_claimed_bonus(db: Session, kid_id: int, level_id: int, slot_number: int) -> bool:
    return db.query(KidLevelBonusClaim).filter(
        and_(
            KidLevelBonusClaim.kid_id == kid_id,
            KidLevelBonusClaim.level_id == level_id,
            KidLevelBonusClaim.slot_number == slot_number,
        )
    ).first() is not None


def claim_bonus(db: Session, kid_id: int, level_id: int, slot_number: int, coins: int) -> KidWallet:
    claim = KidLevelBonusClaim(kid_id=kid_id, level_id=level_id, slot_number=slot_number)
    db.add(claim)
    wallet = get_or_create_wallet(db, kid_id)
    wallet.coins += coins
    db.commit()
    db.refresh(wallet)
    add_score(db, kid_id, coins)
    return wallet


def mark_level_started(db: Session, kid_id: int, level_id: int) -> bool:
    # returns True only the first time this kid opens this level
    exists = db.query(KidLevelStartClaim).filter(
        and_(KidLevelStartClaim.kid_id == kid_id, KidLevelStartClaim.level_id == level_id)
    ).first()
    if exists:
        return False
    db.add(KidLevelStartClaim(kid_id=kid_id, level_id=level_id))
    db.commit()
    return True


def mark_slot_solved(db: Session, kid_id: int, level_id: int, slot_number: int) -> bool:
    # returns True only the first time this kid solves this slot
    exists = db.query(KidSlotSolveClaim).filter(
        and_(
            KidSlotSolveClaim.kid_id == kid_id,
            KidSlotSolveClaim.level_id == level_id,
            KidSlotSolveClaim.slot_number == slot_number,
        )
    ).first()
    if exists:
        return False
    db.add(KidSlotSolveClaim(kid_id=kid_id, level_id=level_id, slot_number=slot_number))
    db.commit()
    return True


def _apply_streak(progress: KidGameProgress) -> None:
    # streak expires 24h after the last completion, not calendar-day based.
    # completing again within 24h of the last one does not double-count;
    # completing again between 24h-48h continues the streak; anything
    # beyond 48h (or no prior completion) resets it to 1.
    now = datetime.now(timezone.utc)
    last = progress.last_completed_at

    if last is None:
        progress.current_streak = 1
        progress.last_completed_at = now
    else:
        gap = now - last
        if gap <= timedelta(hours=24):
            pass  # already within the current streak window
        elif gap <= timedelta(hours=48):
            progress.current_streak += 1
            progress.last_completed_at = now
        else:
            progress.current_streak = 1
            progress.last_completed_at = now

    progress.longest_streak = max(progress.longest_streak, progress.current_streak)


def is_streak_active(progress: KidGameProgress) -> bool:
    if progress.current_streak <= 0 or progress.last_completed_at is None:
        return False
    return datetime.now(timezone.utc) - progress.last_completed_at <= timedelta(hours=24)


def complete_level(db: Session, kid_id: int, level: GameLevel) -> tuple[KidWallet, KidGameProgress, int]:
    wallet = get_or_create_wallet(db, kid_id)
    wallet.coins += level.completion_reward

    progress = get_or_create_progress(db, kid_id, level.game_type)
    if level.level_number not in progress.completed_levels:
        progress.completed_levels = progress.completed_levels + [level.level_number]
    if level.level_number >= progress.current_level:
        progress.current_level = level.level_number + 1

    _apply_streak(progress)

    db.commit()
    db.refresh(wallet)
    db.refresh(progress)
    add_score(db, kid_id, level.completion_reward)
    add_xp(db, kid_id, XP_LEVEL_COMPLETE)
    return wallet, progress, XP_LEVEL_COMPLETE


# ---------- leaderboard / XP ----------

def get_or_create_leaderboard_entry(db: Session, kid_id: int) -> KidLeaderboardScore:
    entry = db.query(KidLeaderboardScore).filter(KidLeaderboardScore.kid_id == kid_id).first()
    if entry:
        return entry
    entry = KidLeaderboardScore(kid_id=kid_id, score=0, xp=0)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def add_score(db: Session, kid_id: int, amount: int) -> None:
    if amount <= 0:
        return
    entry = get_or_create_leaderboard_entry(db, kid_id)
    entry.score += amount
    db.commit()


def add_xp(db: Session, kid_id: int, amount: int) -> None:
    if amount <= 0:
        return
    entry = get_or_create_leaderboard_entry(db, kid_id)
    entry.xp += amount
    db.commit()


def get_leaderboard(db: Session, limit: int = 50) -> list[dict]:
    # start from Kid so every kid shows up even before they've earned
    # any XP/coins - score/wallet/info rows are all lazily created, so
    # a kid with none yet still ranks at 0 rather than being omitted.
    # nickname/avatar live on KidInfo (favorite_animal doubles as the
    # avatar, matching how the FE already renders it via getAnimalEmoji).
    rows = (
        db.query(Kid, KidInfo, KidLeaderboardScore, KidWallet)
        .outerjoin(KidInfo, KidInfo.kid_id == Kid.id)
        .outerjoin(KidLeaderboardScore, KidLeaderboardScore.kid_id == Kid.id)
        .outerjoin(KidWallet, KidWallet.kid_id == Kid.id)
        .all()
    )
    ranked = []
    for kid, info, score_row, wallet in rows:
        xp = score_row.xp if score_row else 0
        score = score_row.score if score_row else 0
        rank_score = xp * XP_WEIGHT + score * COIN_WEIGHT
        ranked.append({
            "kid_id": kid.id,
            "nickname": (info.nickname if info and info.nickname else kid.full_name),
            "avatar": info.favorite_animal if info else None,
            "xp": xp,
            "coins": wallet.coins if wallet else 0,
            "keys": wallet.keys if wallet else 0,
            "rank_score": rank_score,
        })
    ranked.sort(key=lambda r: r["rank_score"], reverse=True)
    for i, r in enumerate(ranked[:limit], start=1):
        r["rank"] = i
    return ranked[:limit]
