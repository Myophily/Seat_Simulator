"""Student model and generation helpers for the seat simulation."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import random
from typing import Dict, List, Mapping, Optional

from classroom_model import COLS, ROWS, SeatCoord


STUDENTS_PER_RUN = 60

STUDENT_TYPE_RATIOS: Dict[str, Fraction] = {
    "focused": Fraction(30, 100),
    "avoidant": Fraction(20, 100),
    "comfort": Fraction(20, 100),
    "social": Fraction(20, 100),
    "random": Fraction(10, 100),
}

STUDENT_TYPE_LABELS = {
    "focused": "집중형",
    "avoidant": "회피형",
    "comfort": "쾌적형",
    "social": "사회형",
    "random": "무작위형",
}

STUDENT_TYPE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "focused": {
        "focus": 3.2,
        "aircon": 0.35,
        "aisle": 0.30,
        "friend": 0.30,
        "crowding": 0.45,
        "noise": 0.25,
    },
    "avoidant": {
        "focus": 2.0,
        "aircon": 0.35,
        "aisle": 0.75,
        "friend": 0.35,
        "crowding": 0.55,
        "noise": 0.35,
    },
    "comfort": {
        "focus": 1.45,
        "aircon": 2.4,
        "aisle": 1.8,
        "friend": 0.30,
        "crowding": 0.65,
        "noise": 0.35,
    },
    "social": {
        "focus": 1.35,
        "aircon": 0.35,
        "aisle": 0.55,
        "friend": 1.6,
        "crowding": 0.75,
        "noise": 0.40,
    },
    "random": {
        "focus": 0.70,
        "aircon": 0.30,
        "aisle": 0.30,
        "friend": 0.25,
        "crowding": 0.50,
        "noise": 1.35,
    },
}

STUDENT_TYPE_IDEAL_PROFESSOR_DISTANCE: Dict[str, float] = {
    "focused": 2.6,
    "avoidant": 4.8,
    "comfort": 3.5,
    "social": 3.8,
    "random": 3.6,
}


@dataclass
class Student:
    student_type: str
    weights: Dict[str, float]
    friend_group: Optional[int] = None
    selected_seat: Optional[SeatCoord] = None
    ideal_professor_distance: float = 3.6

    @classmethod
    def for_type(
        cls,
        student_type: str,
        friend_group: Optional[int] = None,
    ) -> "Student":
        normalized_type = student_type if student_type in STUDENT_TYPE_WEIGHTS else "focused"
        return cls(
            student_type=normalized_type,
            weights=dict(STUDENT_TYPE_WEIGHTS[normalized_type]),
            friend_group=friend_group,
            ideal_professor_distance=STUDENT_TYPE_IDEAL_PROFESSOR_DISTANCE[
                normalized_type
            ],
        )


def generate_students(
    count: int,
    rng: Optional[random.Random] = None,
) -> List[Student]:
    rng = rng or random.Random()
    safe_count = max(0, min(int(count), ROWS * COLS))
    type_counts = _counts_from_ratios(safe_count, STUDENT_TYPE_RATIOS)
    students: List[Student] = []
    group_ids = _group_ids(safe_count, rng)
    group_index = 0

    for student_type, type_count in type_counts.items():
        for _ in range(type_count):
            students.append(
                Student.for_type(
                    student_type,
                    friend_group=group_ids[group_index],
                )
            )
            group_index += 1

    rng.shuffle(students)
    return students


def _counts_from_ratios(
    count: int,
    ratios: Mapping[str, Fraction],
) -> Dict[str, int]:
    raw_counts = {name: count * ratio for name, ratio in ratios.items()}
    counts = {name: int(math.floor(value)) for name, value in raw_counts.items()}
    remaining = count - sum(counts.values())
    ordered_remainders = sorted(
        raw_counts,
        key=lambda name: (raw_counts[name] - counts[name], ratios[name]),
        reverse=True,
    )
    for name in ordered_remainders[:remaining]:
        counts[name] += 1
    return counts


def _group_ids(student_count: int, rng: random.Random) -> List[int]:
    if student_count <= 0:
        return []
    sizes = _group_sizes(student_count, rng)
    group_ids: List[int] = []
    for group_id, size in enumerate(sizes):
        group_ids.extend([group_id] * size)
    rng.shuffle(group_ids)
    return group_ids


def _group_sizes(student_count: int, rng: random.Random) -> List[int]:
    sizes: List[int] = []
    remaining = student_count
    while remaining > 0:
        size = rng.randint(1, min(4, remaining))
        sizes.append(size)
        remaining -= size
    return sizes
