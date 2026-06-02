"""Tkinter GUI for the classroom seat choice simulation."""

import tkinter as tk
from tkinter import messagebox, ttk

import classroom_model as cm
from simulation_engine import run_simulation
from student_model import STUDENTS_PER_RUN


SCENARIO_LABELS = {key: str(value["label"]) for key, value in cm.PROFESSOR_SCENARIOS.items()}
SCENARIO_BY_LABEL = {label: key for key, label in SCENARIO_LABELS.items()}
PROFESSOR_SCENARIO_LABELS = SCENARIO_LABELS
PROFESSOR_SCENARIO_KEYS_BY_LABEL = SCENARIO_BY_LABEL

CANVAS_WIDTH, CANVAS_HEIGHT = 780, 650
ORIGIN_X, ORIGIN_Y = 92, 120
X_SCALE, Y_SCALE = 46, 50
SEAT_WIDTH, SEAT_HEIGHT = 34, 32
MARKER_RADIUS = 15
AIRCON_RADIUS = MARKER_RADIUS * 2

APP_BG = "#f8fafc"
TEXT_COLOR = "#0f172a"
COLOR_STOPS = (
    (248, 250, 252),
    (191, 219, 254),
    (93, 165, 250),
    (251, 146, 60),
    (220, 38, 38),
)
LEGEND_VALUES = (0.05, 0.30, 0.55, 0.80, 1.0)


def _clamp(value, low, high):
    return max(low, min(high, value))


def _positive_int(value, message, maximum=None):
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(message) from exc
    if number < 1 or (maximum is not None and number > maximum):
        raise ValueError(message)
    return number


def _font(size, bold=False):
    return ("Helvetica", size, "bold") if bold else ("Helvetica", size)


def probability_to_color(probability):
    probability = _clamp(probability, 0.0, 1.0)
    scaled = probability * (len(COLOR_STOPS) - 1)
    index = min(int(scaled), len(COLOR_STOPS) - 2)
    fraction = scaled - index
    return "#%02x%02x%02x" % tuple(
        round(start + (end - start) * fraction)
        for start, end in zip(COLOR_STOPS[index], COLOR_STOPS[index + 1])
    )


def probability_text_color(probability):
    return "white" if probability >= 0.58 else TEXT_COLOR


def parse_student_count(value, max_students=cm.ROWS * cm.COLS):
    return _positive_int(value, f"Student count must be between 1 and {max_students}.", max_students)


class SeatSimulationApp:
    def __init__(self, root):
        self.root = root
        self.seats = cm.generate_seats()
        self.current_probabilities = self._empty_probabilities()
        self.professor_position = cm.professor_path_for(cm.DEFAULT_PROFESSOR_SCENARIO)[0]
        self.dragging_professor = False

        self.runs_var = tk.StringVar(value="100")
        self.students_var = tk.StringVar(value=str(STUDENTS_PER_RUN))
        self.professor_scenario_var = tk.StringVar(value=SCENARIO_LABELS[cm.DEFAULT_PROFESSOR_SCENARIO])
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._draw_classroom()

    def _build_ui(self):
        self.root.title("강의실 좌석 선택 시뮬레이터")
        self.root.geometry("1160x760")
        self.root.minsize(1040, 680)
        self.root.configure(background=APP_BG)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        for name in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel"):
            style.configure(name, background=APP_BG, foreground=TEXT_COLOR)
        style.configure("TButton", padding=(10, 6))

        settings = ttk.LabelFrame(self.root, text="설정", padding=14)
        settings.grid(row=0, column=0, sticky="ns", padx=(14, 8), pady=14)
        settings.columnconfigure(0, weight=1)

        self._add_entry(settings, 0, "반복 횟수", self.runs_var)
        self._add_entry(settings, 2, f"학생 수 (1~{len(self.seats)}명)", self.students_var)

        ttk.Label(settings, text="교수자 위치 / 이동").grid(row=4, column=0, sticky="w")
        professor_select = ttk.Combobox(
            settings,
            textvariable=self.professor_scenario_var,
            values=list(SCENARIO_LABELS.values()),
            state="readonly",
            width=22,
        )
        professor_select.grid(row=5, column=0, sticky="ew", pady=(4, 14))
        professor_select.bind("<<ComboboxSelected>>", self._on_professor_scenario_change)

        for row, text, command, pady in (
            (6, "시뮬레이션 실행", self._run_simulation, (0, 8)),
            (7, "결과 초기화", self._reset_results, (0, 16)),
        ):
            ttk.Button(settings, text=text, command=command).grid(row=row, column=0, sticky="ew", pady=pady)
        ttk.Label(settings, textvariable=self.status_var).grid(row=8, column=0, sticky="w")

        classroom = ttk.LabelFrame(self.root, text="강의실 배치", padding=14)
        classroom.grid(row=0, column=1, sticky="nsew", padx=(8, 14), pady=14)
        classroom.columnconfigure(0, weight=1)
        classroom.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(classroom, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="#ffffff", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        for event, handler in (
            ("<ButtonPress-1>", self._on_canvas_press),
            ("<B1-Motion>", self._on_canvas_drag),
            ("<ButtonRelease-1>", self._on_canvas_release),
        ):
            self.canvas.bind(event, handler)

    def _add_entry(self, parent, row, label, variable):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=variable, width=12).grid(row=row + 1, column=0, sticky="ew", pady=(4, 14))

    def _run_simulation(self):
        try:
            runs = self._parse_runs()
            students = parse_student_count(self.students_var.get(), len(self.seats))
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.status_var.set("Running...")
        self.root.update_idletasks()

        scenario = self._read_professor_scenario()
        self.current_probabilities = run_simulation(
            runs=runs,
            students=students,
            professor_scenario=scenario,
            professor_position=self.professor_position if scenario == "custom" else None,
        )
        self._draw_classroom()
        self.status_var.set(f"Complete: {runs} runs, {students} students")

    def _parse_runs(self):
        return _positive_int(self.runs_var.get(), "Simulation runs must be a positive integer.")

    def _read_professor_scenario(self):
        return SCENARIO_BY_LABEL.get(self.professor_scenario_var.get(), cm.DEFAULT_PROFESSOR_SCENARIO)

    def _professor_path(self):
        scenario = self._read_professor_scenario()
        return cm.professor_path_for(scenario, self.professor_position if scenario == "custom" else None)

    def _empty_probabilities(self):
        return {seat.coord: 0.0 for seat in self.seats}

    def _on_professor_scenario_change(self, _event):
        self.professor_position = cm.professor_path_for(self._read_professor_scenario())[0]
        self._draw_classroom()

    def _reset_results(self):
        self.current_probabilities = self._empty_probabilities()
        self.professor_scenario_var.set(SCENARIO_LABELS[cm.DEFAULT_PROFESSOR_SCENARIO])
        self.professor_position = cm.professor_path_for(cm.DEFAULT_PROFESSOR_SCENARIO)[0]
        self.runs_var.set("100")
        self.students_var.set(str(STUDENTS_PER_RUN))
        self.status_var.set("Reset")
        self._draw_classroom()

    def _draw_classroom(self):
        c = self.canvas
        c.delete("all")

        screen_x, screen_y = self._to_canvas(cm.SCREEN_POSITION)
        c.create_rectangle(screen_x - 170, screen_y - 20, screen_x + 170, screen_y + 18, fill="#334155", outline="#1e293b")
        c.create_text(screen_x, screen_y, text="스크린 / 칠판", fill="white")

        top = self._to_canvas((0.0, -0.2))[1]
        bottom = self._to_canvas((0.0, cm.ROWS - 0.3))[1]
        for aisle_x in cm.AISLE_X_POSITIONS:
            x = self._to_canvas((aisle_x, 0.0))[0]
            c.create_rectangle(x - 17, top, x + 17, bottom, fill="#ecfeff", outline="#bae6fd", dash=(5, 4))
            c.create_text(x, top + 16, text="통로", fill="#0369a1", font=_font(8, True))

        for position in cm.DEFAULT_AIRCON_POSITIONS:
            x, y = self._circle(position, AIRCON_RADIUS, fill="#bae6fd", outline="#0284c7", width=2, dash=(6, 4), stipple="gray25")
            c.create_text(x, y - AIRCON_RADIUS + 9, text="AC", fill="#0369a1", font=_font(8, True))

        for seat in self.seats:
            probability = self.current_probabilities.get(seat.coord, 0.0)
            x, y = self._to_canvas((seat.x, seat.y))
            text_color = probability_text_color(probability)
            c.create_rectangle(
                x - SEAT_WIDTH / 2, y - SEAT_HEIGHT / 2,
                x + SEAT_WIDTH / 2, y + SEAT_HEIGHT / 2,
                fill=probability_to_color(probability),
                outline="#cbd5e1" if probability == 0 else "#64748b",
                width=1,
            )
            c.create_text(x, y - 6, text=cm.format_seat_number(seat.row, seat.col), fill=text_color, font=_font(9, True))
            c.create_text(x, y + 8, text=f"{probability * 100:.1f}%", fill=text_color, font=_font(8))

        path = self._professor_path()
        if len(path) >= 2:
            points = [coord for point in path for coord in self._to_canvas(point)]
            c.create_line(*points, fill="#7c3aed", width=3, arrow=tk.LAST, dash=(8, 5))

        professor_position = self.professor_position if self._read_professor_scenario() == "custom" else path[0]
        x, y = self._circle(professor_position, MARKER_RADIUS, fill="#8b5cf6", outline="#5b21b6", width=2, tags=("draggable", "professor"))
        c.create_text(x, y, text="P", fill="white", font=_font(10, True), tags=("draggable", "professor"))

        x, y = 92, CANVAS_HEIGHT - 42
        c.create_text(x, y, text="Low", fill="#475569", anchor="w")
        for index, value in enumerate(LEGEND_VALUES):
            c.create_rectangle(x + 40 + index * 34, y - 10, x + 68 + index * 34, y + 10, fill=probability_to_color(value), outline="#cbd5e1")
        c.create_text(x + 220, y, text="High", fill="#475569", anchor="w")
        c.create_text(CANVAS_WIDTH - 34, y, text="P: 교수자   AC: 냉난방기", fill="#475569", anchor="e")

    def _circle(self, point, radius, **options):
        x, y = self._to_canvas(point)
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, **options)
        return x, y

    def _on_canvas_press(self, _event):
        item = self.canvas.find_withtag("current")
        self.dragging_professor = bool(item and "professor" in self.canvas.gettags(item[0]))

    def _on_canvas_drag(self, event):
        if not self.dragging_professor:
            return
        self.professor_position = self._from_canvas(event.x, event.y)
        self.professor_scenario_var.set(SCENARIO_LABELS["custom"])
        self._draw_classroom()

    def _on_canvas_release(self, _event):
        self.dragging_professor = False

    def _to_canvas(self, point):
        x, y = point
        return ORIGIN_X + x * X_SCALE, ORIGIN_Y + (y + 1.0) * Y_SCALE

    def _from_canvas(self, x, y):
        return (
            _clamp((x - ORIGIN_X) / X_SCALE, -0.5, 12.5),
            _clamp((y - ORIGIN_Y) / Y_SCALE - 1.0, -1.0, float(cm.ROWS - 1)),
        )


def main():
    root = tk.Tk()
    SeatSimulationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
