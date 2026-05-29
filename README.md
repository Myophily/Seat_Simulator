# Classroom Seat Selection Simulator

강의실 좌석 선택 경향을 시뮬레이션하는 Python Tkinter 프로그램입니다.
학생 수, 반복 횟수, 교수자 위치 또는 이동 시나리오를 설정하면 좌석별 선택 확률을
히트맵 형태로 확인할 수 있습니다.

## 실행 방법

```bash
python3 app.py
```

## 포함 파일

- `app.py`: Tkinter GUI와 프로그램 실행 진입점
- `classroom_model.py`: 강의실 좌석, 통로, 스크린, 냉난방기, 교수자 위치 모델
- `simulation_engine.py`: 좌석 선택 점수 계산과 반복 시뮬레이션 로직
- `student_model.py`: 학생 유형, 선호도 가중치, 친구 그룹 생성 로직

## 주요 기능

- 9행, 99석 강의실 배치 표시
- 학생 수와 시뮬레이션 반복 횟수 설정
- 교수자 고정 위치, 좌우 이동, 통로 이동 시나리오 선택
- 교수자 위치 직접 드래그 지정
- 좌석별 선택 확률을 색상과 퍼센트로 표시
