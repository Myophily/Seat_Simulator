"""Tkinter GUI for the classroom seat choice simulation."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Optional, Tuple

from classroom_model import (
    AISLE_X_POSITIONS,
    COLS,
    DEFAULT_AIRCON_POSITIONS,
    DEFAULT_PROFESSOR_SCENARIO,
    PROFESSOR_SCENARIOS,
    ROWS,
    SCREEN_POSITION,
    SeatCoord,
    format_seat_number,
    generate_seats,
    professor_path_for,
)
from simulation_engine import run_simulation
from student_model import STUDENTS_PER_RUN


PROFESSOR_SCENARIO_LABELS = {
    key: str(value["label"])
    for key, value in PROFESSOR_SCENARIOS.items()
}
PROFESSOR_SCENARIO_KEYS_BY_LABEL = {
    label: key for key, label in PROFESSOR_SCENARIO_LABELS.items()
}

Point = Tuple[float, float]

CANVAS_WIDTH = 780
CANVAS_HEIGHT = 650
ORIGIN_X = 92
ORIGIN_Y = 120
X_SCALE = 46
Y_SCALE = 50
SEAT_WIDTH = 34
SEAT_HEIGHT = 32
MARKER_RADIUS = 15
AIRCON_RADIUS = MARKER_RADIUS * 2


def probability_to_color(probability: float) -> str:
    probability = max(0.0, min(1.0, probability))
    stops = (
        (248, 250, 252),
        (191, 219, 254),
        (93, 165, 250),
        (251, 146, 60),
        (220, 38, 38),
    )
    scaled = probability * (len(stops) - 1)
    index = min(int(scaled), len(stops) - 2)
    fraction = scaled - index
    start = stops[index]
    end = stops[index + 1]
    red = round(start[0] + (end[0] - start[0]) * fraction)
    green = round(start[1] + (end[1] - start[1]) * fraction)
    blue = round(start[2] + (end[2] - start[2]) * fraction)
    return f"#{red:02x}{green:02x}{blue:02x}"


def probability_text_color(probability: float) -> str:
    return "white" if probability >= 0.58 else "#0f172a"


def parse_student_count(value: str, max_students: int = ROWS * COLS) -> int:
    try:
        student_count = int(value)
    except ValueError as exc:
        raise ValueError(
            f"Student count must be between 1 and {max_students}."
        ) from exc
    if student_count < 1 or student_count > max_students:
        raise ValueError(f"Student count must be between 1 and {max_students}.")
    return student_count


class SeatSimulationApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("강의실 좌석 선택 시뮬레이터")
        self.root.geometry("1160x760")
        self.root.minsize(1040, 680)

        self.seats = generate_seats()
        self.current_probabilities: Dict[SeatCoord, float] = {
            seat.coord: 0.0 for seat in self.seats
        }
        self.professor_position = professor_path_for(DEFAULT_PROFESSOR_SCENARIO)[0]
        self.drag_target: Optional[Tuple[str, Optional[int]]] = None

        self.runs_var = tk.StringVar(value="100")
        self.students_var = tk.StringVar(value=str(STUDENTS_PER_RUN))
        self.professor_scenario_var = tk.StringVar(
            value=PROFESSOR_SCENARIO_LABELS[DEFAULT_PROFESSOR_SCENARIO]
        )
        self.status_var = tk.StringVar(value="Ready")

        self._configure_style()
        self._build_layout()
        self._draw_classroom()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f8fafc")
        style.configure("TLabelframe", background="#f8fafc")
        style.configure("TLabelframe.Label", background="#f8fafc", foreground="#0f172a")
        style.configure("TLabel", background="#f8fafc", foreground="#0f172a")
        style.configure("TButton", padding=(10, 6))

    def _build_layout(self) -> None:
        self.root.configure(background="#f8fafc")
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_control_panel()
        self._build_classroom_panel()

    def _build_control_panel(self) -> None:
        panel = ttk.LabelFrame(self.root, text="설정", padding=14)
        panel.grid(row=0, column=0, sticky="ns", padx=(14, 8), pady=14)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="반복 횟수").grid(row=0, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.runs_var, width=12).grid(
            row=1, column=0, sticky="ew", pady=(4, 14)
        )

        ttk.Label(panel, text=f"학생 수 (1~{len(self.seats)}명)").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(panel, textvariable=self.students_var, width=12).grid(
            row=3, column=0, sticky="ew", pady=(4, 14)
        )

        ttk.Label(panel, text="교수자 위치 / 이동").grid(row=4, column=0, sticky="w")
        professor_select = ttk.Combobox(
            panel,
            textvariable=self.professor_scenario_var,
            values=list(PROFESSOR_SCENARIO_LABELS.values()),
            state="readonly",
            width=22,
        )
        professor_select.grid(row=5, column=0, sticky="ew", pady=(4, 14))
        professor_select.bind("<<ComboboxSelected>>", self._on_professor_scenario_change)

        ttk.Button(panel, text="시뮬레이션 실행", command=self._run_simulation).grid(
            row=6, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(panel, text="결과 초기화", command=self._reset_results).grid(
            row=7, column=0, sticky="ew", pady=(0, 16)
        )

        ttk.Label(panel, textvariable=self.status_var).grid(row=8, column=0, sticky="w")

    def _build_classroom_panel(self) -> None:
        panel = ttk.LabelFrame(self.root, text="강의실 배치", padding=14)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 14), pady=14)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            panel,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg="#ffffff",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _run_simulation(self) -> None:
        try:
            runs = self._parse_runs()
            student_count = parse_student_count(
                self.students_var.get(),
                max_students=len(self.seats),
            )
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.status_var.set("Running...")
        self.root.update_idletasks()

        scenario = self._read_professor_scenario()
        custom_position = self.professor_position if scenario == "custom" else None
        probabilities = run_simulation(
            runs=runs,
            students=student_count,
            professor_scenario=scenario,
            professor_position=custom_position,
        )
        self.current_probabilities = probabilities
        self._draw_classroom()
        self.status_var.set(f"Complete: {runs} runs, {student_count} students")

    def _parse_runs(self) -> int:
        try:
            runs = int(self.runs_var.get())
        except ValueError as exc:
            raise ValueError("Simulation runs must be a positive integer.") from exc
        if runs < 1:
            raise ValueError("Simulation runs must be a positive integer.")
        return runs

    def _read_professor_scenario(self) -> str:
        label = self.professor_scenario_var.get()
        return PROFESSOR_SCENARIO_KEYS_BY_LABEL.get(label, DEFAULT_PROFESSOR_SCENARIO)

    def _on_professor_scenario_change(self, _event: object) -> None:
        scenario = self._read_professor_scenario()
        self.professor_position = professor_path_for(scenario)[0]
        self._draw_classroom()

    def _reset_results(self) -> None:
        self.current_probabilities = {seat.coord: 0.0 for seat in self.seats}
        self.professor_scenario_var.set(PROFESSOR_SCENARIO_LABELS[DEFAULT_PROFESSOR_SCENARIO])
        self.professor_position = professor_path_for(DEFAULT_PROFESSOR_SCENARIO)[0]
        self.runs_var.set("100")
        self.students_var.set(str(STUDENTS_PER_RUN))
        self._draw_classroom()
        self.status_var.set("Reset")

    def _draw_classroom(self) -> None:
        self.canvas.delete("all")
        self._draw_front_area()
        self._draw_aisles()
        self._draw_aircons()
        self._draw_seats()
        self._draw_professor_path()
        self._draw_professor()
        self._draw_legend()

    def _draw_front_area(self) -> None:
        screen_x, screen_y = self._to_canvas(SCREEN_POSITION)
        self.canvas.create_rectangle(
            screen_x - 170,
            screen_y - 20,
            screen_x + 170,
            screen_y + 18,
            fill="#334155",
            outline="#1e293b",
        )
        self.canvas.create_text(screen_x, screen_y, text="스크린 / 칠판", fill="white")

    def _draw_aisles(self) -> None:
        top = self._to_canvas((0.0, -0.2))[1]
        bottom = self._to_canvas((0.0, ROWS - 0.3))[1]
        for aisle_x in AISLE_X_POSITIONS:
            x, _y = self._to_canvas((aisle_x, 0.0))
            self.canvas.create_rectangle(
                x - 17,
                top,
                x + 17,
                bottom,
                fill="#ecfeff",
                outline="#bae6fd",
                dash=(5, 4),
            )
            self.canvas.create_text(
                x,
                top + 16,
                text="통로",
                fill="#0369a1",
                font=("Helvetica", 8, "bold"),
            )

    def _draw_professor_path(self) -> None:
        scenario = self._read_professor_scenario()
        path = professor_path_for(
            scenario,
            self.professor_position if scenario == "custom" else None,
        )
        if len(path) < 2:
            return
        points = []
        for point in path:
            points.extend(self._to_canvas(point))
        self.canvas.create_line(
            *points,
            fill="#7c3aed",
            width=3,
            arrow=tk.LAST,
            dash=(8, 5),
        )

    def _draw_seats(self) -> None:
        for seat in self.seats:
            probability = self.current_probabilities.get(seat.coord, 0.0)
            x, y = self._to_canvas((seat.x, seat.y))
            fill = probability_to_color(probability)
            outline = "#cbd5e1" if probability == 0 else "#64748b"
            self.canvas.create_rectangle(
                x - SEAT_WIDTH / 2,
                y - SEAT_HEIGHT / 2,
                x + SEAT_WIDTH / 2,
                y + SEAT_HEIGHT / 2,
                fill=fill,
                outline=outline,
                width=1,
            )
            self.canvas.create_text(
                x,
                y - 6,
                text=f"{format_seat_number(seat.row, seat.col)}",
                fill=probability_text_color(probability),
                font=("Helvetica", 9, "bold"),
            )
            self.canvas.create_text(
                x,
                y + 8,
                text=f"{probability * 100:.1f}%",
                fill=probability_text_color(probability),
                font=("Helvetica", 8),
            )

    def _draw_aircons(self) -> None:
        for position in DEFAULT_AIRCON_POSITIONS:
            x, y = self._to_canvas(position)
            self.canvas.create_oval(
                x - AIRCON_RADIUS,
                y - AIRCON_RADIUS,
                x + AIRCON_RADIUS,
                y + AIRCON_RADIUS,
                fill="#bae6fd",
                outline="#0284c7",
                width=2,
                dash=(6, 4),
                stipple="gray25",
            )
            self.canvas.create_text(
                x,
                y - AIRCON_RADIUS + 9,
                text="AC",
                fill="#0369a1",
                font=("Helvetica", 8, "bold"),
            )

    def _draw_professor(self) -> None:
        scenario = self._read_professor_scenario()
        path = professor_path_for(
            scenario,
            self.professor_position if scenario == "custom" else None,
        )
        position = path[0] if scenario != "custom" else self.professor_position
        x, y = self._to_canvas(position)
        self.canvas.create_oval(
            x - MARKER_RADIUS,
            y - MARKER_RADIUS,
            x + MARKER_RADIUS,
            y + MARKER_RADIUS,
            fill="#8b5cf6",
            outline="#5b21b6",
            width=2,
            tags=("draggable", "professor"),
        )
        self.canvas.create_text(
            x,
            y,
            text="P",
            fill="white",
            font=("Helvetica", 10, "bold"),
            tags=("draggable", "professor"),
        )

    def _draw_legend(self) -> None:
        x = 92
        y = CANVAS_HEIGHT - 42
        self.canvas.create_text(x, y, text="Low", fill="#475569", anchor="w")
        for index, value in enumerate((0.05, 0.30, 0.55, 0.80, 1.0)):
            self.canvas.create_rectangle(
                x + 40 + (index * 34),
                y - 10,
                x + 68 + (index * 34),
                y + 10,
                fill=probability_to_color(value),
                outline="#cbd5e1",
            )
        self.canvas.create_text(x + 220, y, text="High", fill="#475569", anchor="w")
        self.canvas.create_text(
            CANVAS_WIDTH - 34,
            y,
            text="P: 교수자   AC: 냉난방기",
            fill="#475569",
            anchor="e",
        )

    def _on_canvas_press(self, event: tk.Event) -> None:
        item = self.canvas.find_withtag("current")
        if not item:
            self.drag_target = None
            return
        tags = self.canvas.gettags(item[0])
        if "professor" in tags:
            self.drag_target = ("professor", None)
            return
        self.drag_target = None

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if self.drag_target is None:
            return
        point = self._from_canvas(event.x, event.y)
        kind, _index = self.drag_target
        if kind == "professor":
            self.professor_position = point
            self.professor_scenario_var.set(PROFESSOR_SCENARIO_LABELS["custom"])
        self._draw_classroom()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        self.drag_target = None

    def _to_canvas(self, point: Point) -> Tuple[float, float]:
        x, y = point
        return ORIGIN_X + (x * X_SCALE), ORIGIN_Y + ((y + 1.0) * Y_SCALE)

    def _from_canvas(self, x: float, y: float) -> Point:
        sim_x = (x - ORIGIN_X) / X_SCALE
        sim_y = ((y - ORIGIN_Y) / Y_SCALE) - 1.0
        return (
            max(-0.5, min(12.5, sim_x)),
            max(-1.0, min(float(ROWS - 1), sim_y)),
        )


def main() -> None:
    root = tk.Tk()
    SeatSimulationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
