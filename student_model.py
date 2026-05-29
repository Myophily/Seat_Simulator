# 이 모듈은 시뮬레이션에 참여하는 학생들의 성향, 선호도, 친구 그룹을 생성합니다.
"""Student model and generation helpers for the seat simulation."""

# 타입 힌트를 문자열처럼 늦게 평가해, 타입 선언 때문에 런타임 의존성이 꼬이는 일을 줄입니다.

# dataclass는 Student처럼 속성 중심의 클래스를 간결하게 정의하게 해 줍니다.
# Fraction은 30%, 20% 같은 비율을 부동소수점 오차 없이 정확하게 표현하기 위해 사용합니다.
from fractions import Fraction
# math.floor는 비율로 계산한 학생 수에서 정수 부분만 먼저 가져올 때 사용합니다.
import math
# random.Random은 재현 가능한 난수 생성기를 외부에서 주입할 수 있게 해 줍니다.
import random
# Dict/List/Mapping/Optional은 학생 설정 자료구조와 선택적 값을 타입으로 설명합니다.

# 좌석 수 제한을 계산하기 위해 강의실의 행/열 수와 좌석 좌표 타입을 가져옵니다.
from classroom_model import COLS, ROWS


# 한 번의 시뮬레이션에서 기본적으로 생성할 학생 수입니다.
STUDENTS_PER_RUN = 60

# 학생 유형별 비율입니다. 전체 학생 수를 이 비율대로 나누어 유형별 인원을 만듭니다.
STUDENT_TYPE_RATIOS = {
    # 집중형은 교수자와 화면을 잘 볼 수 있는 자리를 중요하게 생각한다고 가정합니다.
    "focused": Fraction(30, 100),
    # 회피형은 교수자와 너무 가까운 자리를 피하려는 경향이 있다고 가정합니다.
    "avoidant": Fraction(20, 100),
    # 쾌적형은 냉난방기와 통로처럼 편의 요소를 중요하게 봅니다.
    "comfort": Fraction(20, 100),
    # 사회형은 친구와 가까이 앉는 것을 상대적으로 중요하게 봅니다.
    "social": Fraction(20, 100),
    # 무작위형은 뚜렷한 선호가 약하고 난수 영향이 크게 작동합니다.
    "random": Fraction(10, 100),
}

# 학생 유형별 좌석 선택 가중치입니다. 값이 클수록 해당 요소가 최종 점수에 더 크게 반영됩니다.
STUDENT_TYPE_WEIGHTS = {
    # 집중형 학생은 교수자/스크린 관련 focus 점수를 가장 강하게 반영합니다.
    "focused": {
        # 교수자와 시야 조건을 중요하게 보는 정도입니다.
        "focus": 3.2,
        # 냉난방기와 가까운 정도를 조금만 반영합니다.
        "aircon": 0.35,
        # 통로 접근성도 약하게 반영합니다.
        "aisle": 0.30,
        # 친구 근접성은 보조 요소로만 반영합니다.
        "friend": 0.30,
        # 이미 사람이 가까이 앉아 있을 때 피하는 정도입니다.
        "crowding": 0.45,
        # 점수에 무작위 흔들림을 조금 넣어 매번 완전히 같은 선택을 줄입니다.
        "noise": 0.25,
    },
    # 회피형 학생은 교수자에게 너무 가까운 자리를 피하고 통로 쪽을 선호하는 경향을 줍니다.
    "avoidant": {
        # focus 점수는 보지만 집중형보다 낮게 둡니다.
        "focus": 2.0,
        # 냉난방기 영향은 약하게 둡니다.
        "aircon": 0.35,
        # 통로 근처 선호를 집중형보다 크게 둡니다.
        "aisle": 0.75,
        # 친구 근접성은 약간만 반영합니다.
        "friend": 0.35,
        # 밀집된 자리를 피하는 정도입니다.
        "crowding": 0.55,
        # 선택의 우연성을 약간 부여합니다.
        "noise": 0.35,
    },
    # 쾌적형 학생은 냉난방기와 통로 접근성에 큰 가중치를 둡니다.
    "comfort": {
        # 교수자/시야 조건은 보조적으로만 반영합니다.
        "focus": 1.45,
        # 냉난방기 가까움이 매우 중요합니다.
        "aircon": 2.4,
        # 통로 접근성도 높게 반영합니다.
        "aisle": 1.8,
        # 친구 근접성은 낮게 반영합니다.
        "friend": 0.30,
        # 주변이 붐비면 쾌적성이 떨어지므로 회피 가중치를 둡니다.
        "crowding": 0.65,
        # 약간의 난수 흔들림을 줍니다.
        "noise": 0.35,
    },
    # 사회형 학생은 친구 그룹과 가까이 앉는 것을 크게 반영합니다.
    "social": {
        # 교수자/시야 조건은 기본적으로 어느 정도만 봅니다.
        "focus": 1.35,
        # 냉난방기 영향은 낮게 둡니다.
        "aircon": 0.35,
        # 통로 접근성은 중간 정도로 반영합니다.
        "aisle": 0.55,
        # 친구가 이미 앉은 자리와 가까울수록 높은 점수를 주기 위한 핵심 가중치입니다.
        "friend": 1.6,
        # 사람 많은 곳을 완전히 좋아한다고 보지는 않으므로 밀집 패널티도 큽니다.
        "crowding": 0.75,
        # 친구 배치 상황에 따라 선택이 달라질 수 있게 난수도 조금 둡니다.
        "noise": 0.40,
    },
    # 무작위형 학생은 모든 선호가 약하고 noise가 커서 예측하기 어려운 선택을 하게 됩니다.
    "random": {
        # 교수자/시야 조건을 아주 약하게 반영합니다.
        "focus": 0.70,
        # 냉난방기 영향도 약합니다.
        "aircon": 0.30,
        # 통로 영향도 약합니다.
        "aisle": 0.30,
        # 친구 영향도 약합니다.
        "friend": 0.25,
        # 너무 붐비는 자리는 어느 정도 피합니다.
        "crowding": 0.50,
        # 무작위성이 크게 작동하도록 높은 noise 값을 둡니다.
        "noise": 1.35,
    },
}

# 학생 유형별로 교수자와 가장 편안하다고 느끼는 이상적인 거리입니다.
STUDENT_TYPE_IDEAL_PROFESSOR_DISTANCE = {
    # 집중형은 교수자와 비교적 가까운 거리를 선호합니다.
    "focused": 2.6,
    # 회피형은 교수자와 어느 정도 떨어진 거리를 선호합니다.
    "avoidant": 4.8,
    # 쾌적형은 너무 앞도 너무 뒤도 아닌 중간 거리를 선호한다고 둡니다.
    "comfort": 3.5,
    # 사회형도 친구와 함께 앉기 좋은 중간 근처 거리를 선호한다고 둡니다.
    "social": 3.8,
    # 무작위형은 특별한 성향이 약하므로 평균적인 값을 둡니다.
    "random": 3.6,
}


# Student는 한 명의 학생이 좌석을 고를 때 필요한 상태와 선호 정보를 담습니다.

class Student:

    def __init__(
        self,
        student_type,
        weights,
        friend_group=None,
        selected_seat=None,
        ideal_professor_distance=3.6
    ):
        self.student_type = student_type
        self.weights = weights
        self.friend_group = friend_group
        self.selected_seat = selected_seat
        self.ideal_professor_distance = ideal_professor_distance


def create_student(student_type, friend_group=None):

    if student_type not in STUDENT_TYPE_WEIGHTS:
        student_type = "focused"

    return Student(
        student_type,
        dict(STUDENT_TYPE_WEIGHTS[student_type]),
        friend_group,
        None,
        STUDENT_TYPE_IDEAL_PROFESSOR_DISTANCE[student_type]
    )


# 지정한 인원수만큼 학생 객체를 생성합니다.
def generate_students(
    # 만들고 싶은 학생 수입니다.
    count,
    # 테스트나 반복 시뮬레이션에서 난수를 통제하고 싶을 때 외부 난수 생성기를 받을 수 있습니다.
    rng,
):
    # rng가 없으면 새 난수 생성기를 만들어 사용합니다.
    rng = rng or random.Random()
    # 학생 수는 음수가 되지 않게 하고, 좌석 수보다 많아지지 않게 제한합니다.
    safe_count = max(0, min(int(count), ROWS * COLS))
    # 전체 학생 수를 유형별 비율에 맞춰 정수 인원으로 나눕니다.
    type_counts = _counts_from_ratios(safe_count, STUDENT_TYPE_RATIOS)
    # 최종적으로 반환할 Student 객체 목록입니다.
    students = []
    # 친구 그룹 번호를 학생 수만큼 만들어 둡니다.
    group_ids = _group_ids(safe_count, rng)
    # group_ids에서 현재 몇 번째 그룹 번호를 꺼낼지 가리키는 인덱스입니다.
    group_index = 0

    # 유형별 인원수 딕셔너리를 순회하며 해당 유형의 학생을 만듭니다.
    for student_type, type_count in type_counts.items():
        # 해당 유형에 배정된 수만큼 Student를 생성합니다.
        for _ in range(type_count):
            # 한 명의 학생을 만들어 students 리스트에 넣습니다.
            students.append(
                create_student(
                    # 현재 반복 중인 유형을 학생에게 부여합니다.
                    student_type,
                    # group_ids에서 하나씩 친구 그룹 번호를 꺼내 부여합니다.
                    friend_group=group_ids[group_index],
                )
            )
            # 다음 학생은 다음 친구 그룹 번호를 사용해야 하므로 인덱스를 1 증가시킵니다.
            group_index += 1

    # 유형 순서대로 생성하면 앞쪽 학생들이 같은 유형에 몰리므로, 실제 선택 순서를 섞습니다.
    rng.shuffle(students)
    # 완성된 학생 목록을 반환합니다.
    return students


# 전체 인원과 유형별 비율을 받아, 유형별 정수 인원수를 계산합니다.
def _counts_from_ratios(
    # 나눌 전체 학생 수입니다.
    count,
    # 유형 이름 -> 비율 형태의 매핑입니다.
    ratios,
):
    # 먼저 각 유형의 이론상 학생 수를 분수로 계산합니다.
    raw_counts = {name: count * ratio for name, ratio in ratios.items()}
    # 각 이론값에서 소수 부분을 버린 정수 부분만 가져옵니다.
    counts = {name: int(math.floor(value)) for name, value in raw_counts.items()}
    # 버려진 소수 부분 때문에 아직 배정되지 않은 학생 수를 계산합니다.
    remaining = count - sum(counts.values())
    # 남은 인원은 소수 부분이 큰 유형부터 1명씩 추가해야 비율에 가장 가깝습니다.
    ordered_remainders = sorted(
        # 정렬할 대상은 유형 이름들입니다.
        raw_counts,
        # 첫 기준은 소수 부분, 두 번째 기준은 원래 비율입니다.
        key=lambda name: (raw_counts[name] - counts[name], ratios[name]),
        # 소수 부분이 큰 순서대로 앞에 오게 합니다.
        reverse=True,
    )
    # 남은 인원 수만큼 앞에서부터 유형을 골라 1명씩 더합니다.
    for name in ordered_remainders[:remaining]:
        # 해당 유형의 최종 인원수를 1 증가시킵니다.
        counts[name] += 1
    # 모든 유형의 인원수를 더하면 정확히 count가 되는 딕셔너리를 반환합니다.
    return counts


# 학생 수만큼 친구 그룹 번호 목록을 만듭니다.
def _group_ids(student_count, rng):
    # 학생이 0명 이하라면 그룹도 만들 필요가 없습니다.
    if student_count <= 0:
        # 빈 리스트를 반환해 이후 로직이 안전하게 끝나게 합니다.
        return []
    # 1~4명 크기의 그룹들을 만들어 전체 학생 수를 채웁니다.
    sizes = _group_sizes(student_count, rng)
    # 각 학생에게 붙일 그룹 번호를 담는 리스트입니다.
    group_ids = []
    # enumerate는 그룹 번호와 그룹 크기를 동시에 만들어 줍니다.
    for group_id, size in enumerate(sizes):
        # 같은 그룹에 속한 학생 수만큼 같은 group_id를 반복해서 넣습니다.
        group_ids.extend([group_id] * size)
    # 그룹 번호가 생성 순서대로 있으면 앞 학생들이 같은 그룹에 몰리므로 섞습니다.
    rng.shuffle(group_ids)
    # 학생 수와 길이가 같은 그룹 번호 목록을 반환합니다.
    return group_ids


# 전체 학생 수를 1~4명짜리 친구 그룹 크기들의 합으로 나눕니다.
def _group_sizes(student_count, rng):
    # 각 친구 그룹의 크기를 순서대로 담을 리스트입니다.
    sizes = []
    # 아직 그룹에 배정되지 않은 학생 수입니다.
    remaining = student_count
    # 모든 학생이 어떤 그룹에 들어갈 때까지 반복합니다.
    while remaining > 0:
        # 남은 학생 수를 넘지 않는 범위에서 1~4명 사이의 그룹 크기를 무작위로 고릅니다.
        size = rng.randint(1, min(4, remaining))
        # 방금 고른 그룹 크기를 목록에 기록합니다.
        sizes.append(size)
        # 그만큼 학생이 배정되었으므로 남은 수를 줄입니다.
        remaining -= size
    # 전체 합이 student_count와 같은 그룹 크기 목록을 반환합니다.
    return sizes
