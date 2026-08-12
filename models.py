from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Position:
    x: int
    y: int


@dataclass
class Pie:
    position: Position
    reward: int
    is_power: bool = False


@dataclass
class Obstacle:
    position: Position
    damage: int


@dataclass
class Snake:
    player_id: str
    username: str
    body: List[Position]
    direction: str
    next_direction: str
    health: int
    color: str = "pink"
    took_damage: bool = False
    alive: bool = True


@dataclass
class MatchState:
    width: int
    height: int
    player1: Snake
    player2: Snake
    pies: List[Pie] = field(default_factory=list)
    obstacles: List[Obstacle] = field(default_factory=list)
    status: str = "WAITING"
    winner: Optional[str] = None
    remaining_time: int = 0
    tick_count: int = 0

    normal_pies_since_power: int = 0
    crown_owner: Optional[str] = None
    pies_eaten_after_power: int = 0