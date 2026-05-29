"""Classroom layout, seats, and professor-position model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


ROWS = 9
BLOCK_SIZES = (4, 3, 4)
COLS = sum(BLOCK_SIZES)
DEFAULT_PROFESSOR_SCENARIO = "front_center"

SeatCoord = Tuple[int, int]
Point = Tuple[float, float]

SCREEN_POSITION: Point = (6.0, -1.2)
DEFAULT_AIRCON_POSITIONS: Tuple[Point, Point] = ((2.0, 4.0), (10.0, 4.0))
AISLE_X_POSITIONS = (4.0, 8.0)

PROFESSOR_SCENARIOS: Dict[str, Dict[str, object]] = {
    "front_center": {
        "label": "앞쪽 중앙 고정",
        "path": ((6.0, -0.8),),
    },
    "front_left": {
        "label": "앞쪽 왼쪽 고정",
        "path": ((1.0, -0.8),),
    },
    "front_right": {
        "label": "앞쪽 오른쪽 고정",
        "path": ((11.0, -0.8),),
    },
    "custom": {
        "label": "사용자 지정 위치",
        "path": ((6.0, -0.8),),
    },
    "side_to_side": {
        "label": "좌우 이동",
        "path": (
            (1.0, -0.8),
            (3.5, -0.8),
            (6.0, -0.8),
            (8.5, -0.8),
            (11.0, -0.8),
        ),
    },
    "front_to_back_left_aisle": {
        "label": "왼쪽 통로 앞뒤 이동",
        "path": (
            (4.0, -0.8),
            (4.0, 1.0),
            (4.0, 3.0),
            (4.0, 5.0),
            (4.0, 7.0),
            (4.0, 8.0),
        ),
    },
    "front_to_back_right_aisle": {
        "label": "오른쪽 통로 앞뒤 이동",
        "path": (
            (8.0, -0.8),
            (8.0, 1.0),
            (8.0, 3.0),
            (8.0, 5.0),
            (8.0, 7.0),
            (8.0, 8.0),
        ),
    },
}


@dataclass(frozen=True)
class Seat:
    row: int
    col: int
    block: str
    x: float
    y: float

    @property
    def coord(self) -> SeatCoord:
        return (self.row, self.col)


@dataclass
class Classroom:
    seats: List[Seat] = field(default_factory=lambda: generate_seats())
    screen_position: Point = SCREEN_POSITION
    aircon_positions: Tuple[Point, ...] = DEFAULT_AIRCON_POSITIONS
    professor_scenario: str = DEFAULT_PROFESSOR_SCENARIO
    professor_position: Optional[Point] = None
    _seat_lookup: Dict[SeatCoord, Seat] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.professor_scenario = _normalize_professor_scenario(self.professor_scenario)
        if self.professor_position is None:
            default_path = PROFESSOR_SCENARIOS[self.professor_scenario]["path"]
            self.professor_position = tuple(default_path[0])  # type: ignore[index]
        self.aircon_positions = tuple(self.aircon_positions)
        self._seat_lookup = {seat.coord: seat for seat in self.seats}

    @property
    def professor_path(self) -> Tuple[Point, ...]:
        return professor_path_for(self.professor_scenario, self.professor_position)

    def seat_at(self, row: int, col: int) -> Seat:
        return self._seat_lookup[(row, col)]


def format_seat_number(row: int, col: int) -> int:
    return row * COLS + col + 1


def generate_seats() -> List[Seat]:
    seats: List[Seat] = []
    for row in range(ROWS):
        for col in range(COLS):
            seats.append(
                Seat(
                    row=row,
                    col=col,
                    block=_block_for_col(col),
                    x=_x_for_col(col),
                    y=float(row),
                )
            )
    return seats


def professor_path_for(
    scenario: str,
    custom_position: Optional[Point] = None,
) -> Tuple[Point, ...]:
    normalized = _normalize_professor_scenario(scenario)
    if normalized == "custom" and custom_position is not None:
        return (custom_position,)
    path = PROFESSOR_SCENARIOS[normalized]["path"]
    return tuple(path)  # type: ignore[arg-type]


def _block_for_col(col: int) -> str:
    if col < BLOCK_SIZES[0]:
        return "left"
    if col < BLOCK_SIZES[0] + BLOCK_SIZES[1]:
        return "center"
    return "right"


def _x_for_col(col: int) -> float:
    if col < BLOCK_SIZES[0]:
        return float(col)
    if col < BLOCK_SIZES[0] + BLOCK_SIZES[1]:
        return float(col + 1)
    return float(col + 2)


def _normalize_professor_scenario(scenario: str) -> str:
    if scenario in PROFESSOR_SCENARIOS:
        return scenario
    return DEFAULT_PROFESSOR_SCENARIO
