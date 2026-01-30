"""
라이브 세션 UI
실시간 포커 핸드 추적용 GUI
"""

import sys
from typing import List, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QFrame, QTextEdit, QSizePolicy,
    QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..core.equity_calculator import calculate_equity
from ..core.pot_odds import PotOddsCalculator
from ..strategy.preflop_charts import PreflopCharts, Position
from ..strategy.range_analysis import Street


class CardSelector(QWidget):
    """카드 선택 위젯"""
    
    RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    SUITS = [('♠', 's', '#000000'), ('♥', 'h', '#e74c3c'), 
             ('♦', 'd', '#3498db'), ('♣', 'c', '#27ae60')]
    
    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self.selected_card = None
        self.setup_ui(label)
    
    def setup_ui(self, label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        if label:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
        
        # 카드 표시
        self.card_label = QLabel("--")
        self.card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.card_label.setFixedSize(50, 40)
        self.card_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #333;
                border-radius: 5px;
                color: #333;
            }
        """)
        layout.addWidget(self.card_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 랭크 선택
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(['--'] + self.RANKS)
        self.rank_combo.currentTextChanged.connect(self.update_card)
        layout.addWidget(self.rank_combo)
        
        # 슈트 선택
        self.suit_combo = QComboBox()
        self.suit_combo.addItem('--', '')
        for symbol, code, color in self.SUITS:
            self.suit_combo.addItem(symbol, code)
        self.suit_combo.currentTextChanged.connect(self.update_card)
        layout.addWidget(self.suit_combo)
    
    def update_card(self):
        rank = self.rank_combo.currentText()
        suit_code = self.suit_combo.currentData()
        suit_symbol = self.suit_combo.currentText()
        
        if rank != '--' and suit_code:
            self.selected_card = f"{rank}{suit_code}"
            
            # 색상 설정
            color = '#000000'
            for s, c, clr in self.SUITS:
                if c == suit_code:
                    color = clr
                    break
            
            self.card_label.setText(f"{rank}{suit_symbol}")
            self.card_label.setStyleSheet(f"""
                QLabel {{
                    background-color: white;
                    border: 2px solid #333;
                    border-radius: 5px;
                    color: {color};
                }}
            """)
        else:
            self.selected_card = None
            self.card_label.setText("--")
            self.card_label.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 2px solid #333;
                    border-radius: 5px;
                    color: #333;
                }
            """)
    
    def get_card(self) -> Optional[str]:
        return self.selected_card
    
    def clear(self):
        self.rank_combo.setCurrentIndex(0)
        self.suit_combo.setCurrentIndex(0)
        self.selected_card = None


class LiveSessionUI(QMainWindow):
    """라이브 세션 UI"""
    
    def __init__(self):
        super().__init__()
        self.pot_calc = PotOddsCalculator()
        self.charts = PreflopCharts()
        
        # 상태
        self.street = Street.PREFLOP
        self.pot = 0
        self.to_call = 0
        self.num_players = 2
        
        self.setup_ui()
        self.setup_style()
    
    def setup_ui(self):
        self.setWindowTitle("🎰 포커 솔버 (학습/연습용)")
        self.setMinimumSize(700, 850)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        
        # === 경고 배너 ===
        warning_label = QLabel("⚠️ 학습/연습용 - 리얼머니 게임에서 실시간 사용 시 계정 정지 위험")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet("""
            QLabel {
                background-color: #c0392b;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(warning_label)
        
        # === 히어로 섹션 ===
        hero_group = QGroupBox("🃏 내 핸드")
        hero_layout = QHBoxLayout(hero_group)
        
        # 포지션
        pos_layout = QVBoxLayout()
        pos_layout.addWidget(QLabel("포지션"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["BTN", "CO", "HJ", "UTG", "SB", "BB"])
        pos_layout.addWidget(self.position_combo)
        hero_layout.addLayout(pos_layout)
        
        # 홀 카드
        self.hole_card1 = CardSelector("카드 1")
        self.hole_card2 = CardSelector("카드 2")
        hero_layout.addWidget(self.hole_card1)
        hero_layout.addWidget(self.hole_card2)
        
        hero_layout.addStretch()
        main_layout.addWidget(hero_group)
        
        # === 보드 섹션 ===
        board_group = QGroupBox("🎴 보드")
        board_layout = QHBoxLayout(board_group)
        
        self.board_cards = []
        for i, name in enumerate(["플랍1", "플랍2", "플랍3", "턴", "리버"]):
            card = CardSelector(name)
            self.board_cards.append(card)
            board_layout.addWidget(card)
        
        main_layout.addWidget(board_group)
        
        # === 스트릿 선택 ===
        street_group = QGroupBox("📍 스트릿")
        street_layout = QHBoxLayout(street_group)
        
        self.street_buttons = QButtonGroup()
        streets = [("프리플랍", Street.PREFLOP), ("플랍", Street.FLOP), 
                   ("턴", Street.TURN), ("리버", Street.RIVER)]
        
        for i, (name, street) in enumerate(streets):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, s=street: self.set_street(s))
            self.street_buttons.addButton(btn, i)
            street_layout.addWidget(btn)
        
        self.street_buttons.button(0).setChecked(True)
        main_layout.addWidget(street_group)
        
        # === 상대 정보 섹션 ===
        villain_group = QGroupBox("👤 상대 정보")
        villain_layout = QHBoxLayout(villain_group)
        
        villain_layout.addWidget(QLabel("상대 포지션:"))
        self.villain_position = QComboBox()
        self.villain_position.addItems(["UTG", "HJ", "CO", "BTN", "SB", "BB"])
        villain_layout.addWidget(self.villain_position)
        
        villain_layout.addWidget(QLabel("플레이어 수:"))
        self.players_input = QSpinBox()
        self.players_input.setRange(2, 9)
        self.players_input.setValue(2)
        villain_layout.addWidget(self.players_input)
        
        villain_layout.addStretch()
        main_layout.addWidget(villain_group)
        
        # === 팟/베팅 섹션 ===
        pot_group = QGroupBox("💰 팟 & 베팅")
        pot_layout = QGridLayout(pot_group)
        
        pot_layout.addWidget(QLabel("팟 사이즈:"), 0, 0)
        self.pot_input = QDoubleSpinBox()
        self.pot_input.setRange(0, 100000)
        self.pot_input.setValue(100)
        self.pot_input.setPrefix("$")
        self.pot_input.valueChanged.connect(self.on_pot_changed)
        pot_layout.addWidget(self.pot_input, 0, 1)
        
        pot_layout.addWidget(QLabel("상대 베팅:"), 0, 2)
        self.bet_input = QDoubleSpinBox()
        self.bet_input.setRange(0, 100000)
        self.bet_input.setValue(0)
        self.bet_input.setPrefix("$")
        self.bet_input.valueChanged.connect(self.on_bet_changed)
        pot_layout.addWidget(self.bet_input, 0, 3)
        
        # 빠른 베팅 버튼
        pot_layout.addWidget(QLabel("빠른 베팅:"), 1, 2)
        quick_bet_layout = QHBoxLayout()
        for ratio, name in [(0.33, "1/3"), (0.5, "1/2"), (0.67, "2/3"), (1.0, "팟")]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, r=ratio: self.quick_bet(r))
            quick_bet_layout.addWidget(btn)
        pot_layout.addLayout(quick_bet_layout, 1, 3)
        
        main_layout.addWidget(pot_group)
        
        # === 분석 버튼 ===
        analyze_btn = QPushButton("🔍 분석하기")
        analyze_btn.setFixedHeight(50)
        analyze_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        analyze_btn.clicked.connect(self.analyze)
        analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        main_layout.addWidget(analyze_btn)
        
        # === 결과 섹션 ===
        result_group = QGroupBox("📊 분석 결과")
        result_layout = QVBoxLayout(result_group)
        
        # 승률 표시
        self.equity_label = QLabel("승률: --%")
        self.equity_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.equity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.equity_label)
        
        # 추천 액션
        self.action_label = QLabel("추천: --")
        self.action_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.action_label.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                color: #f1c40f;
                padding: 20px;
                border-radius: 10px;
            }
        """)
        result_layout.addWidget(self.action_label)
        
        # 상세 분석
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        self.detail_text.setFont(QFont("Consolas", 11))
        result_layout.addWidget(self.detail_text)
        
        main_layout.addWidget(result_group)
        
        # === 새 핸드 버튼 ===
        new_hand_btn = QPushButton("🔄 새 핸드")
        new_hand_btn.clicked.connect(self.new_hand)
        new_hand_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(new_hand_btn)
    
    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a252f;
            }
            QGroupBox {
                font-weight: bold;
                color: #ecf0f1;
                border: 2px solid #34495e;
                border-radius: 8px;
                margin-top: 12px;
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
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                padding: 5px;
                border-radius: 4px;
                min-height: 25px;
            }
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a6785;
            }
            QPushButton:checked {
                background-color: #2980b9;
            }
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
            }
        """)
    
    def set_street(self, street: Street):
        self.street = street
    
    def on_pot_changed(self, value):
        self.pot = value
    
    def on_bet_changed(self, value):
        self.to_call = value
    
    def quick_bet(self, ratio: float):
        bet = self.pot_input.value() * ratio
        self.bet_input.setValue(bet)
    
    def get_hole_cards(self) -> List[str]:
        cards = []
        c1 = self.hole_card1.get_card()
        c2 = self.hole_card2.get_card()
        if c1:
            cards.append(c1)
        if c2:
            cards.append(c2)
        return cards
    
    def get_board(self) -> List[str]:
        board = []
        
        # 스트릿에 따라 카드 수 결정
        if self.street == Street.PREFLOP:
            return []
        elif self.street == Street.FLOP:
            max_cards = 3
        elif self.street == Street.TURN:
            max_cards = 4
        else:
            max_cards = 5
        
        for i, card_widget in enumerate(self.board_cards[:max_cards]):
            card = card_widget.get_card()
            if card:
                board.append(card)
        
        return board
    
    def analyze(self):
        hole_cards = self.get_hole_cards()
        
        if len(hole_cards) != 2:
            self.action_label.setText("❌ 홀 카드 2장을 선택하세요")
            self.action_label.setStyleSheet("""
                QLabel {
                    background-color: #c0392b;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                }
            """)
            return
        
        board = self.get_board()
        pot = self.pot_input.value()
        to_call = self.bet_input.value()
        num_opponents = self.players_input.value() - 1
        
        # 승률 계산
        try:
            equity_result = calculate_equity(
                hole_cards,
                board if board else None,
                num_opponents=num_opponents,
                iterations=10000
            )
            equity = equity_result["win"]
        except Exception as e:
            self.action_label.setText(f"❌ 오류: {str(e)}")
            return
        
        self.equity_label.setText(f"승률: {equity:.1f}%")
        
        # 프리플랍 분석
        if self.street == Street.PREFLOP:
            self._analyze_preflop(hole_cards, equity, pot, to_call)
        else:
            self._analyze_postflop(hole_cards, board, equity, pot, to_call)
    
    def _analyze_preflop(self, hole_cards, equity, pot, to_call):
        """프리플랍 분석 - 단일 액션 추천"""
        import random
        
        hand_str = self.charts.cards_to_hand(hole_cards[0], hole_cards[1])
        
        try:
            position = Position[self.position_combo.currentText()]
        except:
            position = Position.BTN
        
        open_range = self.charts.get_open_range(position)
        in_range = hand_str in open_range
        
        # 핸드 티어 분류
        tier1 = ["AA", "KK"]
        tier2 = ["QQ", "JJ", "AKs", "AKo"]
        tier3 = ["TT", "99", "AQs", "AQo", "AJs", "KQs"]
        tier4 = ["88", "77", "ATs", "AJo", "KJs", "KQo", "QJs", "JTs"]
        
        detail = f"핸드: {hand_str}\n"
        detail += f"포지션: {position.value}\n"
        detail += f"승률: {equity:.1f}%\n"
        
        if to_call == 0:
            # 오픈 상황
            if in_range:
                raise_size = 2.5 if position in [Position.UTG, Position.HJ] else 2.5
                self._set_action(f"RAISE {raise_size}BB", "#27ae60")
                detail += f"\n→ 레이즈 {raise_size}BB"
            else:
                self._set_action("FOLD", "#e74c3c")
                detail += "\n→ 폴드"
        else:
            # 레이즈 facing - 빈도 기반 단일 액션
            if hand_str in tier1:
                # AA, KK: 항상 4bet
                raise_size = to_call * 2.5
                self._set_action(f"RAISE ${raise_size:.0f}", "#9b59b6")
                detail += f"\n→ 4bet ${raise_size:.0f}"
            
            elif hand_str in tier2:
                # QQ, JJ, AK: 80% 4bet, 20% call
                if random.random() < 0.8:
                    raise_size = to_call * 2.5
                    self._set_action(f"RAISE ${raise_size:.0f}", "#9b59b6")
                    detail += f"\n→ 4bet ${raise_size:.0f}"
                else:
                    self._set_action("CALL", "#3498db")
                    detail += f"\n→ 콜 ${to_call:.0f}"
            
            elif hand_str in tier3:
                # TT-99, AQ, AJ, KQ: 60% call, 30% 3bet, 10% fold
                r = random.random()
                if r < 0.6:
                    self._set_action("CALL", "#3498db")
                    detail += f"\n→ 콜 ${to_call:.0f}"
                elif r < 0.9:
                    raise_size = to_call * 2.5
                    self._set_action(f"RAISE ${raise_size:.0f}", "#9b59b6")
                    detail += f"\n→ 3bet ${raise_size:.0f}"
                else:
                    self._set_action("FOLD", "#e74c3c")
                    detail += "\n→ 폴드"
            
            elif hand_str in tier4 or in_range:
                # 플레이어블 핸드: 콜 또는 폴드
                if to_call <= pot * 0.4:
                    self._set_action("CALL", "#3498db")
                    detail += f"\n→ 콜 ${to_call:.0f}"
                else:
                    self._set_action("FOLD", "#e74c3c")
                    detail += "\n→ 폴드 (비싼 콜)"
            else:
                self._set_action("FOLD", "#e74c3c")
                detail += "\n→ 폴드"
        
        self.detail_text.setText(detail)
    
    def _analyze_postflop(self, hole_cards, board, equity, pot, to_call):
        """포스트플랍 분석 - 단일 액션 추천"""
        import random
        
        detail = f"승률: {equity:.1f}%\n"
        detail += f"팟: ${pot:.0f}\n"
        
        if to_call > 0:
            # 베팅에 직면
            pot_analysis = self.pot_calc.analyze(pot, to_call, equity)
            
            detail += f"콜: ${to_call:.0f}\n"
            detail += f"팟 오즈: {pot_analysis.pot_odds:.1f}%\n"
            detail += f"필요 승률: {pot_analysis.required_equity:.1f}%\n"
            detail += f"EV: {'+' if pot_analysis.ev >= 0 else ''}{pot_analysis.ev:.2f}\n"
            
            if equity > 70:
                # 매우 강한 핸드 - 레이즈
                raise_size = pot + to_call
                self._set_action(f"RAISE ${raise_size:.0f}", "#9b59b6")
                detail += f"\n→ 레이즈 ${raise_size:.0f}"
            
            elif equity > 55:
                # 강한 핸드 - 빈도: 70% 콜, 30% 레이즈
                if random.random() < 0.7:
                    self._set_action(f"CALL ${to_call:.0f}", "#27ae60")
                    detail += f"\n→ 콜 ${to_call:.0f}"
                else:
                    raise_size = pot + to_call
                    self._set_action(f"RAISE ${raise_size:.0f}", "#9b59b6")
                    detail += f"\n→ 레이즈 ${raise_size:.0f}"
            
            elif pot_analysis.is_profitable_call:
                # EV+ 콜
                self._set_action(f"CALL ${to_call:.0f}", "#27ae60")
                detail += f"\n→ 콜 ${to_call:.0f}"
            
            elif equity > 25:
                # 드로우 가능성 - 임플라이드 오즈 고려
                # 빈도: 40% 콜, 60% 폴드
                if random.random() < 0.4:
                    self._set_action(f"CALL ${to_call:.0f}", "#f39c12")
                    detail += f"\n→ 콜 ${to_call:.0f} (드로우)"
                else:
                    self._set_action("FOLD", "#e74c3c")
                    detail += "\n→ 폴드"
            else:
                self._set_action("FOLD", "#e74c3c")
                detail += "\n→ 폴드"
        
        else:
            # 체크 또는 베팅
            if equity > 70:
                # 강한 핸드 - 밸류 베팅
                bet_size = pot * 0.67
                self._set_action(f"BET ${bet_size:.0f}", "#27ae60")
                detail += f"\n→ 베팅 ${bet_size:.0f}"
            
            elif equity > 55:
                # 중강 핸드 - 빈도: 60% 베팅, 40% 체크
                if random.random() < 0.6:
                    bet_size = pot * 0.5
                    self._set_action(f"BET ${bet_size:.0f}", "#27ae60")
                    detail += f"\n→ 베팅 ${bet_size:.0f}"
                else:
                    self._set_action("CHECK", "#7f8c8d")
                    detail += "\n→ 체크"
            
            elif equity > 35:
                # 중간 핸드 - 빈도: 30% 베팅 (블러프), 70% 체크
                if random.random() < 0.3:
                    bet_size = pot * 0.33
                    self._set_action(f"BET ${bet_size:.0f}", "#3498db")
                    detail += f"\n→ 베팅 ${bet_size:.0f}"
                else:
                    self._set_action("CHECK", "#7f8c8d")
                    detail += "\n→ 체크"
            
            else:
                # 약한 핸드 - 대부분 체크, 가끔 블러프
                if random.random() < 0.15:
                    bet_size = pot * 0.33
                    self._set_action(f"BET ${bet_size:.0f}", "#f39c12")
                    detail += f"\n→ 블러프 베팅 ${bet_size:.0f}"
                else:
                    self._set_action("CHECK", "#7f8c8d")
                    detail += "\n→ 체크"
        
        self.detail_text.setText(detail)
    
    def _set_action(self, text: str, color: str):
        self.action_label.setText(text)
        self.action_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 20px;
                border-radius: 10px;
                font-size: 20px;
            }}
        """)
    
    def new_hand(self):
        # 카드 초기화
        self.hole_card1.clear()
        self.hole_card2.clear()
        for card in self.board_cards:
            card.clear()
        
        # 값 초기화
        self.pot_input.setValue(100)
        self.bet_input.setValue(0)
        self.players_input.setValue(2)
        
        # 스트릿 초기화
        self.street_buttons.button(0).setChecked(True)
        self.street = Street.PREFLOP
        
        # 결과 초기화
        self.equity_label.setText("승률: --%")
        self.action_label.setText("새 핸드를 시작하세요")
        self.action_label.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                color: #95a5a6;
                padding: 20px;
                border-radius: 10px;
            }
        """)
        self.detail_text.clear()


def run_live_ui():
    """라이브 UI 실행"""
    app = QApplication(sys.argv)
    window = LiveSessionUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_live_ui()
