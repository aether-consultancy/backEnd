from sqlalchemy import Column, Integer, String, JSON, DateTime, Date, ForeignKey, UniqueConstraint, func
from dbmanager.connection import Base


class GameLevel(Base):
    __tablename__ = "game_levels"

    id = Column(Integer, primary_key=True, index=True)
    game_type = Column(String, nullable=False, index=True)
    level_number = Column(Integer, nullable=False)
    theme = Column(String, nullable=True)
    grid_rows = Column(Integer, nullable=False)
    grid_cols = Column(Integer, nullable=False)
    blocked_cells = Column(JSON, nullable=False)
    slots = Column(JSON, nullable=False)
    solution = Column(JSON, nullable=False)
    completion_reward = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KidGameProgress(Base):
    __tablename__ = "kid_game_progress"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    game_type = Column(String, nullable=False, index=True)
    current_level = Column(Integer, nullable=False, default=1)
    completed_levels = Column(JSON, nullable=False, default=list)
    current_streak = Column(Integer, nullable=False, default=0, server_default="0")
    longest_streak = Column(Integer, nullable=False, default=0, server_default="0")
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("kid_id", "game_type", name="uq_kid_game_progress"),)


class KidWallet(Base):
    __tablename__ = "kid_wallets"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, unique=True, index=True)
    coins = Column(Integer, nullable=False, default=0)
    keys = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KidLevelBonusClaim(Base):
    __tablename__ = "kid_level_bonus_claims"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("game_levels.id"), nullable=False, index=True)
    slot_number = Column(Integer, nullable=False)
    claimed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("kid_id", "level_id", "slot_number", name="uq_kid_level_slot_claim"),)


class KidLevelStartClaim(Base):
    # first time a kid opens a given level - grants start XP once
    __tablename__ = "kid_level_start_claims"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("game_levels.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("kid_id", "level_id", name="uq_kid_level_start_claim"),)


class KidSlotSolveClaim(Base):
    # first time a kid solves a given slot (bonus or not) - grants slot XP once
    __tablename__ = "kid_slot_solve_claims"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("game_levels.id"), nullable=False, index=True)
    slot_number = Column(Integer, nullable=False)
    solved_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("kid_id", "level_id", "slot_number", name="uq_kid_slot_solve_claim"),)


class KidLeaderboardScore(Base):
    __tablename__ = "kid_leaderboard_scores"

    id = Column(Integer, primary_key=True, index=True)
    kid_id = Column(Integer, ForeignKey("kids.id"), nullable=False, unique=True, index=True)
    score = Column(Integer, nullable=False, default=0)
    xp = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
