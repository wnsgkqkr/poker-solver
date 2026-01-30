"""
메인 윈도우 UI
포커 솔버의 기본 인터페이스
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QGroupBox, QGridLayout,
    QSpinBox, QDoubleSpinBox, QTextEdit, QFrame, QTabWidget,
    QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from ..core.equity_calculator import calculate_equity
from ..core.pot_odds import PotOddsCalculator, pot_odds, ev
from ..strategy.preflop_charts import PreflopCharts, Position
from ..strategy.gto_advisor import GTOAdvisor, GameState


class CardInput(QWidget):
    """카드 입력 위젯"""
    
    RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    SUITS = ['s', 'h', 'd', 'c']
    SUIT_SYMBOLS = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
    
    def __init__(self, label: str = "Card", parent=None):
        super().__init__(parent)
        self.setup_ui(label)
    
    def setup_ui(self, label: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(self.RANKS)
        
        self.suit_combo = QComboBox()
        for suit in self.SUITS:
            self.suit_combo.addItem(self.SUIT_SYMBOLS[suit], suit)
        
        layout.addWidget(self.label)
        layout.addWidget(self.rank_combo)
        layout.addWidget(self.suit_combo)
    
    def get_card(self) -> str:
        """선택된 카드 반환 (예: "As")"""
        rank = self.rank_combo.currentText()
        suit = self.suit_combo.currentData()
        return f"{rank}{suit}"
    
    def set_card(self, card: str):
        """카드 설정"""
        if len(card) >= 2:
            rank = card[0]
            suit = card[1]
            
            rank_idx = self.RANKS.index(rank) if rank in self.RANKS else 0
            suit_idx = self.SUITS.index(suit) if suit in self.SUITS else 0
            
            self.rank_combo.setCurrentIndex(rank_idx)
            self.suit_combo.setCurrentIndex(suit_idx)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.advisor = GTOAdvisor()
        self.pot_calculator = PotOddsCalculator()
        self.charts = PreflopCharts()
        
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        self.setWindowTitle("Poker GTO Solver")
        self.setMinimumSize(800, 600)
        
        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # 탭 위젯
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 탭 1: 핸드 분석
        tabs.addTab(self.create_hand_analysis_tab(), "핸드 분석")
        
        # 탭 2: 승률 계산
        tabs.addTab(self.create_equity_tab(), "승률 계산")
        
        # 탭 3: 레인지 차트
        tabs.addTab(self.create_range_tab(), "레인지 차트")
    
    def create_hand_analysis_tab(self) -> QWidget:
        """핸드 분석 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 상단: 입력 영역
        input_group = QGroupBox("게임 상황 입력")
        input_layout = QGridLayout(input_group)
        
        # 홀 카드
        row = 0
        input_layout.addWidget(QLabel("내 홀 카드:"), row, 0)
        self.hole_card1 = CardInput("", self)
        self.hole_card2 = CardInput("", self)
        hole_layout = QHBoxLayout()
        hole_layout.addWidget(self.hole_card1)
        hole_layout.addWidget(self.hole_card2)
        hole_widget = QWidget()
        hole_widget.setLayout(hole_layout)
        input_layout.addWidget(hole_widget, row, 1)
        
        # 보드
        row += 1
        input_layout.addWidget(QLabel("보드:"), row, 0)
        self.board_cards = []
        board_layout = QHBoxLayout()
        for i in range(5):
            card = CardInput("", self)
            self.board_cards.append(card)
            board_layout.addWidget(card)
        board_widget = QWidget()
        board_widget.setLayout(board_layout)
        input_layout.addWidget(board_widget, row, 1)
        
        # 포지션
        row += 1
        input_layout.addWidget(QLabel("내 포지션:"), row, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(["UTG", "HJ", "CO", "BTN", "SB", "BB"])
        self.position_combo.setCurrentText("BTN")
        input_layout.addWidget(self.position_combo, row, 1)
        
        # 팟 사이즈
        row += 1
        input_layout.addWidget(QLabel("팟 사이즈:"), row, 0)
        self.pot_size_input = QDoubleSpinBox()
        self.pot_size_input.setRange(0, 100000)
        self.pot_size_input.setValue(100)
        self.pot_size_input.setPrefix("$")
        input_layout.addWidget(self.pot_size_input, row, 1)
        
        # 콜 금액
        row += 1
        input_layout.addWidget(QLabel("콜 금액:"), row, 0)
        self.call_amount_input = QDoubleSpinBox()
        self.call_amount_input.setRange(0, 100000)
        self.call_amount_input.setValue(0)
        self.call_amount_input.setPrefix("$")
        input_layout.addWidget(self.call_amount_input, row, 1)
        
        # 상대 수
        row += 1
        input_layout.addWidget(QLabel("상대 수:"), row, 0)
        self.opponents_input = QSpinBox()
        self.opponents_input.setRange(1, 8)
        self.opponents_input.setValue(1)
        input_layout.addWidget(self.opponents_input, row, 1)
        
        layout.addWidget(input_group)
        
        # 분석 버튼
        self.analyze_btn = QPushButton("분석하기")
        self.analyze_btn.clicked.connect(self.analyze_hand)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.analyze_btn)
        
        # 결과 표시
        result_group = QGroupBox("분석 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 11))
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        return widget
    
    def create_equity_tab(self) -> QWidget:
        """승률 계산 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 입력
        input_group = QGroupBox("승률 계산")
        input_layout = QGridLayout(input_group)
        
        # 홀 카드
        input_layout.addWidget(QLabel("홀 카드:"), 0, 0)
        self.eq_hole1 = CardInput("", self)
        self.eq_hole2 = CardInput("", self)
        hole_layout = QHBoxLayout()
        hole_layout.addWidget(self.eq_hole1)
        hole_layout.addWidget(self.eq_hole2)
        hole_widget = QWidget()
        hole_widget.setLayout(hole_layout)
        input_layout.addWidget(hole_widget, 0, 1)
        
        # 보드
        input_layout.addWidget(QLabel("보드:"), 1, 0)
        self.eq_board = QLineEdit()
        self.eq_board.setPlaceholderText("예: Qd Jc Ts (공백으로 구분)")
        input_layout.addWidget(self.eq_board, 1, 1)
        
        # 상대 수
        input_layout.addWidget(QLabel("상대 수:"), 2, 0)
        self.eq_opponents = QSpinBox()
        self.eq_opponents.setRange(1, 8)
        self.eq_opponents.setValue(1)
        input_layout.addWidget(self.eq_opponents, 2, 1)
        
        layout.addWidget(input_group)
        
        # 계산 버튼
        calc_btn = QPushButton("승률 계산")
        calc_btn.clicked.connect(self.calculate_equity)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
            }
        """)
        layout.addWidget(calc_btn)
        
        # 결과
        self.equity_result = QLabel("결과가 여기에 표시됩니다")
        self.equity_result.setFont(QFont("Arial", 14))
        self.equity_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.equity_result.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 20px;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.equity_result)
        
        layout.addStretch()
        
        return widget
    
    def create_range_tab(self) -> QWidget:
        """레인지 차트 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 포지션 선택
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("포지션:"))
        self.range_pos_combo = QComboBox()
        self.range_pos_combo.addItems(["UTG", "HJ", "CO", "BTN", "SB", "BB"])
        self.range_pos_combo.currentTextChanged.connect(self.update_range_display)
        pos_layout.addWidget(self.range_pos_combo)
        pos_layout.addStretch()
        layout.addLayout(pos_layout)
        
        # 레인지 그리드
        self.range_display = QTextEdit()
        self.range_display.setReadOnly(True)
        self.range_display.setFont(QFont("Courier New", 10))
        layout.addWidget(self.range_display)
        
        # 초기 표시
        self.update_range_display()
        
        return widget
    
    def setup_style(self):
        """스타일 설정"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #ecf0f1;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                padding: 5px;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #1a252f;
                color: #ecf0f1;
                border: 1px solid #34495e;
            }
            QTabWidget::pane {
                border: 1px solid #34495e;
            }
            QTabBar::tab {
                background-color: #34495e;
                color: white;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2980b9;
            }
        """)
    
    def analyze_hand(self):
        """핸드 분석 실행"""
        try:
            # 입력 수집
            hole_cards = [
                self.hole_card1.get_card(),
                self.hole_card2.get_card()
            ]
            
            # 보드 카드 수집 (비어있지 않은 것만)
            board = []
            for card_input in self.board_cards:
                card = card_input.get_card()
                # 기본값이 아닌 경우만 추가 (첫 번째 카드가 아닌 경우)
                if len(board) < 5:  # 최대 5장
                    board.append(card)
            
            position = Position[self.position_combo.currentText()]
            pot_size = self.pot_size_input.value()
            to_call = self.call_amount_input.value()
            num_opponents = self.opponents_input.value()
            
            # 게임 상태 생성
            from ..strategy.range_analysis import Street
            state = GameState(
                my_hand=hole_cards,
                my_position=position,
                my_stack=1000,
                board=board[:3] if len(board) >= 3 else [],  # 플랍만 사용
                pot_size=pot_size,
                to_call=to_call,
                num_opponents=num_opponents,
                street=Street.PREFLOP if len(board) < 3 else Street.FLOP
            )
            
            # 추천 받기
            recommendation = self.advisor.get_recommendation(state)
            
            # 승률 계산
            if board and len(board) >= 3:
                equity_result = calculate_equity(
                    hole_cards, board[:min(len(board), 5)], 
                    num_opponents, iterations=10000
                )
            else:
                equity_result = calculate_equity(
                    hole_cards, None, num_opponents, iterations=10000
                )
            
            # 팟 오즈 계산
            if to_call > 0:
                pot_analysis = self.pot_calculator.analyze(
                    pot_size, to_call, equity_result["win"]
                )
            else:
                pot_analysis = None
            
            # 결과 표시
            result = f"{'='*50}\n"
            result += f"핸드: {hole_cards[0]} {hole_cards[1]}\n"
            if board:
                result += f"보드: {' '.join(board[:min(len(board), 5)])}\n"
            result += f"포지션: {position.value}\n"
            result += f"{'='*50}\n\n"
            
            result += f"📊 승률 분석\n"
            result += f"  승률: {equity_result['win']:.1f}%\n"
            result += f"  무승부: {equity_result['tie']:.1f}%\n"
            result += f"  패배: {equity_result['lose']:.1f}%\n\n"
            
            if pot_analysis:
                result += f"💰 팟 오즈 분석\n"
                result += f"  팟 오즈: {pot_analysis.pot_odds:.1f}%\n"
                result += f"  필요 승률: {pot_analysis.required_equity:.1f}%\n"
                if pot_analysis.ev is not None:
                    result += f"  콜 EV: {'+' if pot_analysis.ev >= 0 else ''}{pot_analysis.ev:.2f}\n"
                result += f"  판정: {'✅ 콜 가능' if pot_analysis.is_profitable_call else '❌ 폴드 권장'}\n\n"
            
            result += f"🎯 추천 액션\n"
            result += str(recommendation)
            
            self.result_text.setText(result)
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"분석 중 오류 발생: {str(e)}")
    
    def calculate_equity(self):
        """승률 계산"""
        try:
            hole_cards = [
                self.eq_hole1.get_card(),
                self.eq_hole2.get_card()
            ]
            
            board_text = self.eq_board.text().strip()
            board = board_text.split() if board_text else None
            
            num_opponents = self.eq_opponents.value()
            
            result = calculate_equity(
                hole_cards, board, num_opponents, iterations=20000
            )
            
            text = f"<h2>승률: {result['win']:.1f}%</h2>"
            text += f"<p>무승부: {result['tie']:.1f}% | 패배: {result['lose']:.1f}%</p>"
            text += f"<p><small>시뮬레이션 {result['iterations']:,}회 기준</small></p>"
            
            self.equity_result.setText(text)
            
        except Exception as e:
            self.equity_result.setText(f"오류: {str(e)}")
    
    def update_range_display(self):
        """레인지 차트 업데이트"""
        try:
            position = Position[self.range_pos_combo.currentText()]
            open_range = self.charts.get_open_range(position)
            
            grid = self.charts.print_range_grid(open_range)
            percentage = self.charts.get_range_percentage(open_range)
            
            text = f"{position.value} 오픈 레인지 ({percentage:.1f}%)\n\n"
            text += grid
            text += f"\n총 {len(open_range)}개 핸드"
            
            self.range_display.setText(text)
            
        except Exception as e:
            self.range_display.setText(f"오류: {str(e)}")


def run_main_window():
    """메인 윈도우 실행"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_main_window()
