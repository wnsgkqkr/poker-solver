"""
포커 오버레이 UI
게임 중 항상 최상단에 표시되는 미니 정보 패널
"""

import sys
from typing import Optional, List
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QMouseEvent

from ..core.equity_calculator import calculate_equity
from ..core.pot_odds import PotOddsCalculator
from ..strategy.gto_advisor import GTOAdvisor, GameState, RecommendedAction
from ..strategy.preflop_charts import Position
from ..strategy.range_analysis import Street


class QuickCardInput(QLineEdit):
    """빠른 카드 입력 필드"""
    
    def __init__(self, placeholder: str = "As Kh", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMaxLength(10)
        self.setFixedWidth(80)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
                border-radius: 3px;
                padding: 3px;
                font-family: Consolas;
                font-size: 12px;
            }
        """)
    
    def get_cards(self) -> List[str]:
        """입력된 카드들 파싱"""
        text = self.text().strip()
        if not text:
            return []
        return text.split()


class PokerOverlay(QMainWindow):
    """포커 오버레이 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.advisor = GTOAdvisor()
        self.pot_calculator = PotOddsCalculator()
        
        self.dragging = False
        self.drag_position = QPoint()
        
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        """UI 설정"""
        # 윈도우 플래그 설정 - 항상 최상단, 프레임 없음
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setWindowTitle("Poker HUD")
        self.setFixedSize(320, 400)
        
        # 중앙 위젯
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 타이틀 바 (드래그용)
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(5, 5, 5, 5)
        
        title_label = QLabel("🎰 Poker Solver")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 최소화/닫기 버튼
        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(20, 20)
        minimize_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #34495e;")
        layout.addWidget(line)
        
        # 입력 영역
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = QGridLayout(input_frame)
        input_layout.setSpacing(5)
        
        # 홀 카드
        input_layout.addWidget(QLabel("핸드:"), 0, 0)
        self.hole_input = QuickCardInput("As Kh")
        input_layout.addWidget(self.hole_input, 0, 1)
        
        # 보드
        input_layout.addWidget(QLabel("보드:"), 1, 0)
        self.board_input = QuickCardInput("Qd Jc Ts")
        self.board_input.setFixedWidth(120)
        input_layout.addWidget(self.board_input, 1, 1)
        
        # 포지션
        input_layout.addWidget(QLabel("포지션:"), 2, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["BTN", "CO", "HJ", "UTG", "SB", "BB"])
        self.position_combo.setFixedWidth(80)
        input_layout.addWidget(self.position_combo, 2, 1)
        
        # 팟/콜
        input_layout.addWidget(QLabel("팟:"), 3, 0)
        self.pot_input = QLineEdit("100")
        self.pot_input.setFixedWidth(60)
        input_layout.addWidget(self.pot_input, 3, 1)
        
        input_layout.addWidget(QLabel("콜:"), 4, 0)
        self.call_input = QLineEdit("0")
        self.call_input.setFixedWidth(60)
        input_layout.addWidget(self.call_input, 4, 1)
        
        layout.addWidget(input_frame)
        
        # 분석 버튼
        analyze_btn = QPushButton("⚡ 분석")
        analyze_btn.setObjectName("analyzeBtn")
        analyze_btn.clicked.connect(self.quick_analyze)
        layout.addWidget(analyze_btn)
        
        # 결과 표시 영역
        self.result_frame = QFrame()
        self.result_frame.setObjectName("resultFrame")
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setSpacing(5)
        
        # 승률
        self.equity_label = QLabel("승률: ---%")
        self.equity_label.setObjectName("equityLabel")
        self.equity_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        result_layout.addWidget(self.equity_label)
        
        # 팟 오즈
        self.pot_odds_label = QLabel("팟 오즈: ---%")
        result_layout.addWidget(self.pot_odds_label)
        
        # 추천 액션
        self.action_label = QLabel("추천: ---")
        self.action_label.setObjectName("actionLabel")
        self.action_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.action_label)
        
        # EV
        self.ev_label = QLabel("EV: ---")
        result_layout.addWidget(self.ev_label)
        
        # 이유
        self.reason_label = QLabel("")
        self.reason_label.setWordWrap(True)
        self.reason_label.setStyleSheet("color: #95a5a6; font-size: 10px;")
        result_layout.addWidget(self.reason_label)
        
        layout.addWidget(self.result_frame)
        layout.addStretch()
        
        # 상태 바
        self.status_label = QLabel("준비됨")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 9px;")
        layout.addWidget(self.status_label)
    
    def setup_style(self):
        """스타일 설정"""
        self.setStyleSheet("""
            #centralWidget {
                background-color: rgba(26, 37, 47, 240);
                border: 1px solid #34495e;
                border-radius: 10px;
            }
            #titleBar {
                background-color: transparent;
            }
            #titleBar QLabel {
                color: #ecf0f1;
            }
            #titleBar QPushButton {
                background-color: transparent;
                color: #95a5a6;
                border: none;
                font-size: 14px;
            }
            #titleBar QPushButton:hover {
                color: #ecf0f1;
            }
            #inputFrame {
                background-color: rgba(44, 62, 80, 150);
                border-radius: 5px;
                padding: 5px;
            }
            #inputFrame QLabel {
                color: #bdc3c7;
                font-size: 11px;
            }
            QComboBox {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
                border-radius: 3px;
                padding: 3px;
            }
            QLineEdit {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
                border-radius: 3px;
                padding: 3px;
            }
            #analyzeBtn {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            #analyzeBtn:hover {
                background-color: #2ecc71;
            }
            #resultFrame {
                background-color: rgba(44, 62, 80, 200);
                border-radius: 8px;
                padding: 10px;
            }
            #equityLabel {
                color: #3498db;
            }
            #actionLabel {
                color: #f1c40f;
                padding: 10px;
                background-color: rgba(0, 0, 0, 50);
                border-radius: 5px;
            }
            QLabel {
                color: #ecf0f1;
            }
        """)
    
    def quick_analyze(self):
        """빠른 분석"""
        try:
            # 입력 파싱
            hole_cards = self.hole_input.get_cards()
            if len(hole_cards) != 2:
                self.status_label.setText("❌ 홀 카드 2장 필요")
                return
            
            board = self.board_input.get_cards()
            
            try:
                position = Position[self.position_combo.currentText()]
            except:
                position = Position.BTN
            
            pot_size = float(self.pot_input.text() or 100)
            to_call = float(self.call_input.text() or 0)
            
            # 승률 계산
            equity_result = calculate_equity(
                hole_cards,
                board if board else None,
                num_opponents=1,
                iterations=5000
            )
            equity = equity_result["win"]
            
            # 팟 오즈
            if to_call > 0:
                pot_analysis = self.pot_calculator.analyze(pot_size, to_call, equity)
                pot_odds_text = f"팟 오즈: {pot_analysis.pot_odds:.1f}% (필요: {pot_analysis.required_equity:.1f}%)"
                ev_text = f"EV: {'+' if pot_analysis.ev >= 0 else ''}{pot_analysis.ev:.2f}"
            else:
                pot_odds_text = "팟 오즈: N/A"
                ev_text = "EV: N/A"
            
            # GTO 추천
            state = GameState(
                my_hand=hole_cards,
                my_position=position,
                my_stack=1000,
                board=board,
                pot_size=pot_size,
                to_call=to_call,
                num_opponents=1,
                street=Street.PREFLOP if not board else Street.FLOP
            )
            
            recommendation = self.advisor.get_recommendation(state)
            
            # 결과 표시
            self.equity_label.setText(f"승률: {equity:.1f}%")
            self.pot_odds_label.setText(pot_odds_text)
            self.ev_label.setText(ev_text)
            
            # 액션 색상
            action_text = recommendation.primary_action.value.upper()
            if recommendation.bet_sizing:
                action_text += f" ${recommendation.bet_sizing:.0f}"
            
            action_colors = {
                RecommendedAction.FOLD: "#e74c3c",
                RecommendedAction.CHECK: "#95a5a6",
                RecommendedAction.CALL: "#3498db",
                RecommendedAction.BET_SMALL: "#2ecc71",
                RecommendedAction.BET_MEDIUM: "#27ae60",
                RecommendedAction.BET_LARGE: "#16a085",
                RecommendedAction.RAISE_SMALL: "#9b59b6",
                RecommendedAction.RAISE_MEDIUM: "#8e44ad",
                RecommendedAction.RAISE_LARGE: "#6c3483",
                RecommendedAction.ALL_IN: "#c0392b"
            }
            
            color = action_colors.get(recommendation.primary_action, "#f1c40f")
            self.action_label.setText(action_text)
            self.action_label.setStyleSheet(f"""
                color: {color};
                padding: 10px;
                background-color: rgba(0, 0, 0, 50);
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            """)
            
            # 이유
            if recommendation.reasoning:
                self.reason_label.setText(" | ".join(recommendation.reasoning[:2]))
            
            self.status_label.setText("✅ 분석 완료")
            
        except Exception as e:
            self.status_label.setText(f"❌ 오류: {str(e)}")
    
    # 드래그 이동 구현
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False


def run_overlay():
    """오버레이 실행"""
    app = QApplication(sys.argv)
    overlay = PokerOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_overlay()
