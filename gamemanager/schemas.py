from pydantic import BaseModel


class SlotOut(BaseModel):
    number: int
    direction: str
    row: int
    col: int
    length: int
    clue: str


class GameLevelOut(BaseModel):
    id: int
    game_type: str
    level_number: int
    theme: str | None = None
    grid_rows: int
    grid_cols: int
    blocked_cells: list[list[int]]
    slots: list[SlotOut]
    solution: dict[str, str]
    completion_reward: int

    class Config:
        from_attributes = True


class NextLevelsOut(BaseModel):
    current_level: int
    levels: list[GameLevelOut]


class SlotSolveIn(BaseModel):
    level_id: int
    slot_number: int


class SlotSolveOut(BaseModel):
    bonus_awarded: bool
    bonus_coins: int = 0
    wallet_coins: int
    wallet_keys: int
    xp_awarded: int = 0


class LevelCompleteIn(BaseModel):
    level_id: int


class LevelCompleteOut(BaseModel):
    coins_awarded: int
    wallet_coins: int
    wallet_keys: int
    current_level: int
    xp_awarded: int = 0


class WalletOut(BaseModel):
    coins: int
    keys: int

    class Config:
        from_attributes = True


class LeaderboardEntryOut(BaseModel):
    rank: int
    kid_id: int
    nickname: str
    avatar: str | None = None
    xp: int
    coins: int
    keys: int
