"""
GTO 어드바이저 모듈
상황별 최적 액션 추천
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import os

from .preflop_charts import PreflopCharts, Position, Hand
from .range_analysis import RangeAnalyzer, Street, ActionType, PlayerAction, PlayerProfile, RangeEstimate
from ..core.pot_odds import PotOddsCalculator, PotOddsResult
from ..core.equity_calculator import EquityCalculator


class RecommendedAction(Enum):
    """추천 액션"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET_SMALL = "bet_small"      # 25-40% pot
    BET_MEDIUM = "bet_medium"    # 50-75% pot
    BET_LARGE = "bet_large"      # 75-100% pot
    BET_OVERBET = "bet_overbet"  # 100%+ pot
    RAISE_SMALL = "raise_small"  # Min-2.5x
    RAISE_MEDIUM = "raise_medium"  # 2.5-3.5x
    RAISE_LARGE = "raise_large"  # 3.5x+
    ALL_IN = "all_in"


@dataclass
class ActionRecommendation:
    """액션 추천 결과"""
    primary_action: RecommendedAction
    confidence: float  # 0-1
    ev: Optional[float] = None
    bet_sizing: Optional[float] = None  # 실제 금액
    sizing_ratio: Optional[float] = None  # 팟 대비 비율
    reasoning: List[str] = field(default_factory=list)
    alternatives: List[Tuple[RecommendedAction, float]] = field(default_factory=list)  # (액션, 빈도)
    
    def __str__(self) -> str:
        action_str = self.primary_action.value.upper()
        if self.bet_sizing:
            action_str += f" ${self.bet_sizing:.0f}"
        if self.sizing_ratio:
            action_str += f" ({self.sizing_ratio*100:.0f}% pot)"
        
        result = f"추천: {action_str} (확신도: {self.confidence*100:.0f}%)\n"
        if self.ev is not None:
            result += f"기대값: {'+' if self.ev >= 0 else ''}{self.ev:.2f}\n"
        if self.reasoning:
            result += "이유:\n"
            for r in self.reasoning:
                result += f"  - {r}\n"
        if self.alternatives:
            result += "대안:\n"
            for alt, freq in self.alternatives:
                result += f"  - {alt.value}: {freq*100:.0f}%\n"
        
        return result


@dataclass 
class GameState:
    """현재 게임 상태"""
    # 내 정보
    my_hand: List[str]  # ["As", "Kh"]
    my_position: Position
    my_stack: float
    
    # 보드 정보
    board: List[str] = field(default_factory=list)
    
    # 팟 정보
    pot_size: float = 0
    to_call: float = 0
    
    # 상대 정보
    num_opponents: int = 1
    opponent_positions: List[Position] = field(default_factory=list)
    opponent_stacks: List[float] = field(default_factory=list)
    
    # 액션 히스토리
    action_history: List[PlayerAction] = field(default_factory=list)
    
    # 스트릿
    street: Street = Street.PREFLOP
    
    @property
    def is_preflop(self) -> bool:
        return self.street == Street.PREFLOP
    
    @property
    def effective_stack(self) -> float:
        """유효 스택 (가장 작은 스택)"""
        all_stacks = [self.my_stack] + self.opponent_stacks
        return min(all_stacks) if all_stacks else self.my_stack
    
    @property
    def spr(self) -> float:
        """Stack to Pot Ratio"""
        if self.pot_size == 0:
            return float('inf')
        return self.effective_stack / self.pot_size
    
    @property
    def my_hand_str(self) -> str:
        """내 핸드를 문자열로"""
        return PreflopCharts.cards_to_hand(self.my_hand[0], self.my_hand[1])


class GTOAdvisor:
    """GTO 기반 액션 어드바이저"""
    
    def __init__(self):
        self.charts = PreflopCharts()
        self.range_analyzer = RangeAnalyzer(self.charts)
        self.pot_calculator = PotOddsCalculator()
        self.equity_calculator = EquityCalculator()
        
        # 사전 계산된 솔루션 로드
        self.precomputed_solutions = self._load_solutions()
    
    def _load_solutions(self) -> Dict:
        """사전 계산된 GTO 솔루션 로드"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        solution_path = os.path.join(base_dir, "data", "gto_solutions", "basic_solutions.json")
        
        if os.path.exists(solution_path):
            with open(solution_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 기본 솔루션 반환
        return self._get_default_solutions()
    
    def _get_default_solutions(self) -> Dict:
        """기본 GTO 솔루션"""
        return {
            "preflop": {
                "open_sizing": {
                    "UTG": 2.5,
                    "HJ": 2.5,
                    "CO": 2.5,
                    "BTN": 2.5,
                    "SB": 3.0
                },
                "3bet_sizing": {
                    "in_position": 3.0,  # x 오픈 사이즈
                    "out_of_position": 3.5
                },
                "4bet_sizing": 2.5  # x 3bet 사이즈
            },
            "postflop": {
                "cbet_sizing": {
                    "dry_board": 0.33,   # 드라이 보드
                    "wet_board": 0.67,   # 웻 보드
                    "coordinated": 0.75  # 코디네이티드 보드
                },
                "value_sizing": {
                    "thin_value": 0.5,
                    "strong_value": 0.75,
                    "nuts": 1.0
                }
            }
        }
    
    def get_recommendation(
        self,
        game_state: GameState,
        opponent_profile: Optional[PlayerProfile] = None
    ) -> ActionRecommendation:
        """
        현재 상황에 대한 액션 추천
        
        Args:
            game_state: 현재 게임 상태
            opponent_profile: 상대 프로파일 (없으면 기본값)
        """
        if game_state.is_preflop:
            return self._get_preflop_recommendation(game_state, opponent_profile)
        else:
            return self._get_postflop_recommendation(game_state, opponent_profile)
    
    def _get_preflop_recommendation(
        self,
        state: GameState,
        profile: Optional[PlayerProfile]
    ) -> ActionRecommendation:
        """프리플랍 추천"""
        hand = state.my_hand_str
        position = state.my_position
        
        # 콜해야 하는 상황인지 확인
        facing_raise = state.to_call > 0
        
        if not facing_raise:
            # 오픈 상황
            return self._get_open_recommendation(hand, position, state)
        else:
            # 레이즈를 facing
            return self._get_vs_raise_recommendation(hand, position, state, profile)
    
    def _get_open_recommendation(
        self,
        hand: str,
        position: Position,
        state: GameState
    ) -> ActionRecommendation:
        """오픈 레이즈 추천"""
        open_range = self.charts.get_open_range(position)
        
        if hand in open_range:
            # 오픈 가능
            sizing_bb = self.precomputed_solutions["preflop"]["open_sizing"].get(
                position.value, 2.5
            )
            
            return ActionRecommendation(
                primary_action=RecommendedAction.RAISE_MEDIUM,
                confidence=1.0,
                sizing_ratio=sizing_bb,
                reasoning=[
                    f"{position.value} 오픈 레인지에 포함",
                    f"표준 오픈 사이즈: {sizing_bb}BB"
                ]
            )
        else:
            # 폴드
            return ActionRecommendation(
                primary_action=RecommendedAction.FOLD,
                confidence=1.0,
                reasoning=[f"{position.value} 오픈 레인지에 미포함"]
            )
    
    def _get_vs_raise_recommendation(
        self,
        hand: str,
        position: Position,
        state: GameState,
        profile: Optional[PlayerProfile]
    ) -> ActionRecommendation:
        """레이즈에 대한 대응 추천"""
        
        # 레이저의 포지션 추정 (첫 번째 상대)
        raiser_position = state.opponent_positions[0] if state.opponent_positions else Position.UTG
        
        # 3bet 레인지 확인
        threbet_range = self.charts.get_3bet_range(position, raiser_position)
        call_range = self.charts.get_call_range(position, raiser_position)
        
        if hand in threbet_range:
            # 3bet
            in_position = self._is_in_position(position, raiser_position)
            sizing_mult = self.precomputed_solutions["preflop"]["3bet_sizing"][
                "in_position" if in_position else "out_of_position"
            ]
            
            return ActionRecommendation(
                primary_action=RecommendedAction.RAISE_LARGE,
                confidence=0.9,
                bet_sizing=state.to_call * sizing_mult,
                reasoning=[
                    f"{raiser_position.value} 오픈에 대한 3bet 레인지",
                    f"{'인 포지션' if in_position else '아웃 오브 포지션'}: {sizing_mult}x 사이징"
                ],
                alternatives=[(RecommendedAction.CALL, 0.1)]  # 가끔 콜
            )
        
        elif hand in call_range:
            # 콜
            # 팟 오즈 체크
            pot_analysis = self.pot_calculator.analyze(
                state.pot_size, state.to_call
            )
            
            return ActionRecommendation(
                primary_action=RecommendedAction.CALL,
                confidence=0.85,
                reasoning=[
                    f"{raiser_position.value} 오픈에 대한 콜 레인지",
                    f"팟 오즈: {pot_analysis.pot_odds:.1f}%"
                ],
                alternatives=[(RecommendedAction.RAISE_LARGE, 0.15)]  # 가끔 3bet
            )
        
        else:
            # 폴드
            return ActionRecommendation(
                primary_action=RecommendedAction.FOLD,
                confidence=1.0,
                reasoning=[f"{raiser_position.value} 오픈에 대해 플레이 불가 핸드"]
            )
    
    def _get_postflop_recommendation(
        self,
        state: GameState,
        profile: Optional[PlayerProfile]
    ) -> ActionRecommendation:
        """포스트플랍 추천"""
        from treys import Card
        
        # 승률 계산
        my_cards = [Card.new(c) for c in state.my_hand]
        board_cards = [Card.new(c) for c in state.board]
        
        equity_result = self.equity_calculator.calculate_equity(
            my_cards, board_cards, state.num_opponents, iterations=5000
        )
        equity = equity_result["win"]
        
        # 보드 텍스처 분석
        board_texture = self._analyze_board_texture(state.board)
        
        # 콜해야 하는 상황
        if state.to_call > 0:
            return self._get_facing_bet_recommendation(state, equity, board_texture, profile)
        else:
            return self._get_betting_recommendation(state, equity, board_texture, profile)
    
    def _get_facing_bet_recommendation(
        self,
        state: GameState,
        equity: float,
        board_texture: str,
        profile: Optional[PlayerProfile]
    ) -> ActionRecommendation:
        """베팅을 facing할 때 추천"""
        
        # 팟 오즈 분석
        pot_analysis = self.pot_calculator.analyze(
            state.pot_size, state.to_call, equity
        )
        
        if pot_analysis.is_profitable_call:
            # EV+ 콜
            if equity > 65:
                # 강한 핸드 - 레이즈 고려
                return ActionRecommendation(
                    primary_action=RecommendedAction.RAISE_MEDIUM,
                    confidence=0.7,
                    ev=pot_analysis.ev,
                    reasoning=[
                        f"승률 {equity:.1f}% - 밸류 레이즈 가능",
                        f"팟 오즈 {pot_analysis.pot_odds:.1f}% < 승률"
                    ],
                    alternatives=[
                        (RecommendedAction.CALL, 0.3)
                    ]
                )
            else:
                # 중간 핸드 - 콜
                return ActionRecommendation(
                    primary_action=RecommendedAction.CALL,
                    confidence=0.8,
                    ev=pot_analysis.ev,
                    reasoning=[
                        f"승률 {equity:.1f}% >= 필요 승률 {pot_analysis.required_equity:.1f}%",
                        f"EV: {pot_analysis.ev:+.2f}"
                    ]
                )
        else:
            # EV- 상황
            # 블러프 레이즈 고려 (프로파일 기반)
            if profile and profile.fold_to_cbet > 60 and equity > 20:
                return ActionRecommendation(
                    primary_action=RecommendedAction.RAISE_MEDIUM,
                    confidence=0.5,
                    reasoning=[
                        f"상대 폴드 투 레이즈 높음 ({profile.fold_to_cbet}%)",
                        "블러프 레이즈 가능"
                    ],
                    alternatives=[
                        (RecommendedAction.FOLD, 0.4),
                        (RecommendedAction.CALL, 0.1)
                    ]
                )
            
            return ActionRecommendation(
                primary_action=RecommendedAction.FOLD,
                confidence=0.85,
                ev=pot_analysis.ev,
                reasoning=[
                    f"승률 {equity:.1f}% < 필요 승률 {pot_analysis.required_equity:.1f}%",
                    f"EV: {pot_analysis.ev:+.2f}"
                ]
            )
    
    def _get_betting_recommendation(
        self,
        state: GameState,
        equity: float,
        board_texture: str,
        profile: Optional[PlayerProfile]
    ) -> ActionRecommendation:
        """베팅 추천 (체크 또는 베팅)"""
        
        # SPR에 따른 전략
        spr = state.spr
        
        # 승률에 따른 베팅
        if equity > 70:
            # 매우 강한 핸드 - 밸류 베팅
            sizing = self.precomputed_solutions["postflop"]["value_sizing"]["strong_value"]
            return ActionRecommendation(
                primary_action=RecommendedAction.BET_LARGE,
                confidence=0.85,
                sizing_ratio=sizing,
                bet_sizing=state.pot_size * sizing,
                reasoning=[
                    f"승률 {equity:.1f}% - 강한 밸류 베팅",
                    f"보드: {board_texture}"
                ]
            )
        
        elif equity > 55:
            # 중간 강도 - 씬 밸류 또는 체크
            sizing = self.precomputed_solutions["postflop"]["value_sizing"]["thin_value"]
            return ActionRecommendation(
                primary_action=RecommendedAction.BET_MEDIUM,
                confidence=0.6,
                sizing_ratio=sizing,
                bet_sizing=state.pot_size * sizing,
                reasoning=[
                    f"승률 {equity:.1f}% - 씬 밸류",
                    f"SPR: {spr:.1f}"
                ],
                alternatives=[
                    (RecommendedAction.CHECK, 0.4)
                ]
            )
        
        elif equity > 35:
            # 약한 핸드 - 주로 체크, 가끔 블러프
            return ActionRecommendation(
                primary_action=RecommendedAction.CHECK,
                confidence=0.7,
                reasoning=[
                    f"승률 {equity:.1f}% - 쇼다운 밸류 보호",
                ],
                alternatives=[
                    (RecommendedAction.BET_SMALL, 0.2),  # 블러프
                    (RecommendedAction.BET_MEDIUM, 0.1)
                ]
            )
        
        else:
            # 매우 약한 핸드 - 체크 또는 블러프
            # 상대 폴드율 고려
            bluff_freq = 0.2
            if profile and profile.fold_to_cbet > 55:
                bluff_freq = 0.35
            
            sizing = self.precomputed_solutions["postflop"]["cbet_sizing"][board_texture]
            
            return ActionRecommendation(
                primary_action=RecommendedAction.CHECK,
                confidence=1 - bluff_freq,
                reasoning=[
                    f"승률 {equity:.1f}% - 쇼다운 밸류 없음"
                ],
                alternatives=[
                    (RecommendedAction.BET_SMALL, bluff_freq)  # 블러프
                ]
            )
    
    def _analyze_board_texture(self, board: List[str]) -> str:
        """보드 텍스처 분석"""
        if not board:
            return "dry_board"
        
        ranks = [c[0] for c in board]
        suits = [c[1] for c in board]
        
        # 플러시 드로우 체크
        suit_counts = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        
        flush_draw = max(suit_counts.values()) >= 3
        
        # 스트레이트 드로우 체크 (간단 버전)
        rank_values = []
        rank_map = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
                    '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
        for r in ranks:
            rank_values.append(rank_map.get(r, 0))
        
        rank_values.sort()
        straight_draw = len(rank_values) >= 3 and (rank_values[-1] - rank_values[0]) <= 4
        
        # 페어 보드 체크
        paired = len(set(ranks)) < len(ranks)
        
        if flush_draw and straight_draw:
            return "coordinated"
        elif flush_draw or straight_draw:
            return "wet_board"
        elif paired:
            return "dry_board"
        else:
            return "dry_board"
    
    def _is_in_position(self, my_pos: Position, opp_pos: Position) -> bool:
        """내가 인 포지션인지"""
        order = [Position.SB, Position.BB, Position.UTG, Position.HJ, Position.CO, Position.BTN]
        return order.index(my_pos) > order.index(opp_pos)
    
    def get_quick_advice(
        self,
        hole_cards: List[str],
        board: Optional[List[str]] = None,
        position: str = "BTN",
        pot_size: float = 100,
        to_call: float = 0,
        num_opponents: int = 1
    ) -> str:
        """
        빠른 어드바이스 (문자열 반환)
        
        Args:
            hole_cards: ["As", "Kh"]
            board: ["Qd", "Jc", "Ts"] or None
            position: "BTN", "CO", etc.
            pot_size: 팟 사이즈
            to_call: 콜 금액
            num_opponents: 상대 수
        """
        try:
            pos = Position[position.upper()]
        except KeyError:
            pos = Position.BTN
        
        state = GameState(
            my_hand=hole_cards,
            my_position=pos,
            my_stack=1000,  # 기본값
            board=board or [],
            pot_size=pot_size,
            to_call=to_call,
            num_opponents=num_opponents,
            street=Street.PREFLOP if not board else Street.FLOP
        )
        
        recommendation = self.get_recommendation(state)
        return str(recommendation)
