# Poker Solver

실시간 포커 GTO 솔버 - 텍사스 홀덤 No Limit 전용

## 기능

- **승률 계산**: 몬테카를로 시뮬레이션 기반 핸드 승률 계산
- **팟 오즈/EV**: 실시간 팟 오즈 및 기대값 계산
- **레인지 분석**: 포지션별 프리플랍 레인지 및 상대 레인지 추정
- **GTO 추천**: 사전 계산된 GTO 솔루션 기반 액션 추천
- **오버레이 UI**: 게임 중 항상 최상단에 표시되는 정보 패널
- **화면 인식**: 자동 카드/팟 사이즈 인식 (PokerStars, DavaoPoker)
- **자동화**: 마우스/키보드 자동 입력 (선택적)

## 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 실행

```bash
python -m src.main
```

## 프로젝트 구조

```
poker-solver/
├── src/
│   ├── core/                   # 핵심 포커 로직
│   │   ├── hand_evaluator.py   # 핸드 평가
│   │   ├── equity_calculator.py # 승률 계산
│   │   └── pot_odds.py         # 팟 오즈/EV 계산
│   ├── strategy/               # 전략 모듈
│   │   ├── preflop_charts.py   # 프리플랍 차트
│   │   ├── range_analysis.py   # 레인지 분석
│   │   └── gto_advisor.py      # GTO 추천 엔진
│   ├── ui/                     # 사용자 인터페이스
│   │   ├── main_window.py      # 메인 윈도우
│   │   └── overlay.py          # 오버레이 UI
│   ├── automation/             # 자동화 모듈
│   │   ├── screen_capture.py   # 화면 캡처
│   │   ├── card_recognition.py # 카드 인식
│   │   └── auto_input.py       # 자동 입력
│   └── main.py
├── data/
│   ├── preflop_ranges/         # 프리플랍 레인지 데이터
│   └── gto_solutions/          # GTO 솔루션 데이터
└── requirements.txt
```

## 법적 고려사항

⚠️ **주의**: 대부분의 온라인 포커 사이트는 봇/자동화 도구 사용을 금지합니다.
- 자동화 기능은 플레이머니/연습 모드에서만 사용하세요
- 리얼머니 게임에서 사용 시 계정 제재 가능성이 있습니다
- 해당 사이트의 이용약관을 반드시 확인하세요

## 라이선스

MIT License
