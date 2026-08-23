from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dbmanager.connection import get_db
from gamemanager import crud
from gamemanager.schemas import (
    NextLevelsOut, GameLevelOut, SlotSolveIn, SlotSolveOut,
    LevelCompleteIn, LevelCompleteOut, WalletOut, LeaderboardEntryOut,
)
from sessionmanager.deps import get_current_kid

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/crossword/next", response_model=NextLevelsOut)
def get_next_crossword_levels(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    current_level, levels = crud.get_next_levels(db, kid.id, "crossword")
    return NextLevelsOut(current_level=current_level, levels=[GameLevelOut.model_validate(l) for l in levels])


@router.get("/crossword/{level_id}", response_model=GameLevelOut)
def get_crossword_level(level_id: int, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    level = crud.get_level_by_id(db, level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")

    if crud.mark_level_started(db, kid.id, level.id):
        crud.add_xp(db, kid.id, crud.XP_START_LEVEL)

    return level


@router.post("/crossword/slot-solved", response_model=SlotSolveOut)
def report_slot_solved(payload: SlotSolveIn, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    level = crud.get_level_by_id(db, payload.level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")

    xp_awarded = 0
    if crud.mark_slot_solved(db, kid.id, level.id, payload.slot_number):
        crud.add_xp(db, kid.id, crud.XP_SLOT_SOLVED)
        xp_awarded = crud.XP_SLOT_SOLVED

    slot = next((s for s in level.slots if s["number"] == payload.slot_number), None)
    if not slot or not slot.get("bonus_coins"):
        wallet = crud.get_or_create_wallet(db, kid.id)
        return SlotSolveOut(bonus_awarded=False, wallet_coins=wallet.coins, wallet_keys=wallet.keys, xp_awarded=xp_awarded)

    if crud.has_claimed_bonus(db, kid.id, level.id, payload.slot_number):
        wallet = crud.get_or_create_wallet(db, kid.id)
        return SlotSolveOut(bonus_awarded=False, wallet_coins=wallet.coins, wallet_keys=wallet.keys, xp_awarded=xp_awarded)

    wallet = crud.claim_bonus(db, kid.id, level.id, payload.slot_number, slot["bonus_coins"])
    return SlotSolveOut(
        bonus_awarded=True, bonus_coins=slot["bonus_coins"],
        wallet_coins=wallet.coins, wallet_keys=wallet.keys,
        xp_awarded=xp_awarded,
    )


@router.post("/crossword/complete", response_model=LevelCompleteOut)
def report_level_complete(payload: LevelCompleteIn, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    level = crud.get_level_by_id(db, payload.level_id)
    if not level:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Level not found")

    wallet, progress, xp_awarded = crud.complete_level(db, kid.id, level)
    return LevelCompleteOut(
        coins_awarded=level.completion_reward,
        wallet_coins=wallet.coins, wallet_keys=wallet.keys,
        current_level=progress.current_level,
        xp_awarded=xp_awarded,
    )


@router.get("/wallet", response_model=WalletOut)
def get_wallet(db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.get_or_create_wallet(db, kid.id)


@router.get("/leaderboard", response_model=list[LeaderboardEntryOut])
def get_leaderboard(limit: int = 50, db: Session = Depends(get_db), kid=Depends(get_current_kid)):
    return crud.get_leaderboard(db, limit=limit)
