import math
import random

from classroom_model import (
    AISLE_X_POSITIONS,
    DEFAULT_PROFESSOR_SCENARIO,
    ROWS,
    Classroom,
    generate_seats,
)
from student_model import STUDENTS_PER_RUN, generate_students


class Simulator:
    def __init__(self, classroom, students, rng=None):
        if rng is None:
            rng = random.Random()
        self.classroom = classroom
        self.students = students
        self.rng = rng

        self._professor_path = self.classroom.professor_path
        self._max_professor_distance = self._max_distance_to_points(self._professor_path)
        self._max_aircon_distance = self._max_distance_to_points(self.classroom.aircon_positions)

        self._view_scores = {}
        self._aircon_scores = {}
        self._aisle_scores = {}
        for seat in self.classroom.seats:
            self._view_scores[seat.coord] = self._calculate_view_score(seat)
            self._aircon_scores[seat.coord] = self._calculate_aircon_score(seat)
            self._aisle_scores[seat.coord] = self._calculate_aisle_score(seat)

    def run(self):
        occupied_groups = {}
        selected = []

        for student in self.students[:len(self.classroom.seats)]:
            seat = self.choose_seat(student, occupied_groups)
            if seat is None:
                break
            student.selected_seat = seat.coord
            selected.append(seat.coord)
            occupied_groups[seat.coord] = student.friend_group

        return selected

    def choose_seat(self, student, occupied_groups):
        available = []
        for seat in self.classroom.seats:
            if seat.coord not in occupied_groups:
                available.append(seat)

        if not available:
            return None

        best_seat = available[0]
        best_score = self.calculate_score(student, available[0], occupied_groups)
        for seat in available[1:]:
            score = self.calculate_score(student, seat, occupied_groups)
            if score > best_score:
                best_score = score
                best_seat = seat

        return best_seat

    def calculate_score(self, student, seat, occupied_groups, include_noise=True):
        weights = student.weights
        score = (
            weights["focus"] * self._focus_score(student, seat)
            + weights["aircon"] * self._aircon_scores[seat.coord]
            + weights["aisle"] * self._aisle_scores[seat.coord]
            + weights["friend"] * self._friend_score(student, seat, occupied_groups)
            - weights.get("crowding", 0.0) * self._crowding_penalty(seat, occupied_groups)
        )
        if include_noise:
            score += self.rng.uniform(-1.0, 1.0) * weights["noise"]
        return score

    def _calculate_view_score(self, seat):
        screen_x = self.classroom.screen_position[0]
        center_score = 1.0 - min(abs(seat.x - screen_x) / screen_x, 1.0)
        row_score = 1.0 - (seat.row / max(ROWS - 1, 1))
        return (0.60 * center_score) + (0.40 * row_score)

    def _focus_score(self, student, seat):
        distance = self._distance_to_professor_path(seat)
        distance_score = _ideal_distance_score(
            distance,
            student.ideal_professor_distance,
            self._max_professor_distance,
        )
        return (0.55 * distance_score) + (0.45 * self._view_scores[seat.coord])

    def _calculate_aircon_score(self, seat):
        distance = _nearest_distance((seat.x, seat.y), self.classroom.aircon_positions)
        return 1.0 - min(distance / max(self._max_aircon_distance, 1.0), 1.0)

    def _calculate_aisle_score(self, seat):
        min_dist = abs(seat.x - AISLE_X_POSITIONS[0])
        for aisle_x in AISLE_X_POSITIONS:
            dist = abs(seat.x - aisle_x)
            if dist < min_dist:
                min_dist = dist
        return 1.0 - min(min_dist / 4.0, 1.0)

    def _friend_score(self, student, seat, occupied_groups):
        if student.friend_group is None:
            return 0.0

        friend_seats = []
        for coord, group in occupied_groups.items():
            if group == student.friend_group:
                friend_seats.append(self.classroom.seat_at(*coord))

        if not friend_seats:
            return 0.0

        best = 0.0
        for friend in friend_seats:
            score = self._friend_proximity_score(seat, friend)
            if score > best:
                best = score
        return best

    def _crowding_penalty(self, seat, occupied_groups):
        penalty = 0.0

        for coord in occupied_groups:
            occupied = self.classroom.seat_at(*coord)
            distance = math.dist((seat.x, seat.y), (occupied.x, occupied.y))
            if distance <= 1.1:
                penalty += 0.32
            elif distance <= 1.6:
                penalty += 0.22
            elif distance <= 2.5:
                penalty += 0.10

        if penalty > 1.0:
            penalty = 1.0
        return penalty

    def _distance_to_professor_path(self, seat):
        total = 0.0
        for professor in self._professor_path:
            total += math.dist((seat.x, seat.y), professor)
        return total / len(self._professor_path)

    def _friend_proximity_score(self, seat, friend):
        if seat.row == friend.row and abs(seat.x - friend.x) <= 1.1:
            return 1.0
        if seat.col == friend.col and abs(seat.row - friend.row) == 1:
            return 0.75
        distance = math.dist((seat.x, seat.y), (friend.x, friend.y))
        return max(0.0, 0.45 * (1.0 - min(distance / 8.0, 1.0)))

    def _max_distance_to_points(self, points):
        max_dist = 0.0
        for seat in self.classroom.seats:
            dist = self._average_distance_to_points((seat.x, seat.y), points)
            if dist > max_dist:
                max_dist = dist
        return max_dist

    def _average_distance_to_points(self, point, targets):
        total = 0.0
        for target in targets:
            total += math.dist(point, target)
        return total / len(targets)


def run_single_simulation(rng=None, students=STUDENTS_PER_RUN, professor_scenario=DEFAULT_PROFESSOR_SCENARIO, professor_position=None):
    if rng is None:
        rng = random.Random()
    classroom = Classroom(
        professor_scenario=professor_scenario,
        professor_position=professor_position,
    )
    generated_students = generate_students(students, rng)
    return Simulator(classroom, generated_students, rng=rng).run()


def run_simulation(runs=100, rng_seed=None, students=STUDENTS_PER_RUN, professor_scenario=DEFAULT_PROFESSOR_SCENARIO, professor_position=None):
    if runs < 1:
        raise ValueError("runs must be a positive integer")

    rng = random.Random(rng_seed)
    seats = [seat.coord for seat in generate_seats()]
    counts = {}
    for seat in seats:
        counts[seat] = 0

    for _ in range(runs):
        occupied = run_single_simulation(
            rng=rng,
            students=students,
            professor_scenario=professor_scenario,
            professor_position=professor_position,
        )
        for seat in occupied:
            counts[seat] += 1

    result = {}
    for seat, count in counts.items():
        result[seat] = count / runs
    return result


def _nearest_distance(point, targets):
    min_dist = math.dist(point, targets[0])
    for target in targets[1:]:
        dist = math.dist(point, target)
        if dist < min_dist:
            min_dist = dist
    return min_dist


def _ideal_distance_score(distance, ideal, max_distance):
    denominator = max(ideal, max_distance - ideal, 1.0)
    return 1.0 - min(abs(distance - ideal) / denominator, 1.0)