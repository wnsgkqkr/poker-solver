"""
레인지 분석 모듈
상대 레인지 추정 및 분석
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from treys import Card
import random

from .preflop_charts import PreflopCharts, Position, Action, Hand


class Street(Enum):
    """스트릿"""
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(Enum):
    """액션 타입"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class PlayerAction:
    """플레이어 액션 기록"""
    street: Street
    action_type: ActionType
    amount: Optional[float] = None  # 베팅/레이즈 금액
    pot_size: Optional[float] = None  # 액션 시점 팟 사이즈
    
    @property
    def is_aggressive(self) -> bool:
        """공격적인 액션인지"""
        return self.action_type in [ActionType.BET, ActionType.RAISE, ActionType.ALL_IN]
    
    @property
    def bet_size_ratio(self) -> Optional[float]:
        """팟 대비 베팅 비율"""
        if self.amount and self.pot_size and self.pot_size > 0:
            return self.amount / self.pot_size
        return None


@dataclass
class PlayerProfile:
    """플레이어 프로파일 (스탯 기반)"""
    vpip: float = 25.0        # Voluntarily Put $ In Pot (%)
    pfr: float = 18.0         # Pre-Flop Raise (%)
    aggression: float = 2.0   # Aggression Factor
    three_bet: float = 7.0    # 3-bet (%)
    fold_to_3bet: float = 55.0  # Fold to 3-bet (%)
    cbet: float = 65.0        # C-bet (%)
    fold_to_cbet: float = 45.0  # Fold to C-bet (%)
    
    @classmethod
    def tight_aggressive(cls) -> "PlayerProfile":
        """타이트-어그레시브 (TAG)"""
        return cls(vpip=22, pfr=18, aggression=2.5, three_bet=8, fold_to_3bet=50, cbet=70, fold_to_cbet=40)
    
    @classmethod
    def loose_aggressive(cls) -> "PlayerProfile":
        """루즈-어그레시브 (LAG)"""
        return cls(vpip=32, pfr=24, aggression=3.0, three_bet=10, fold_to_3bet=45, cbet=75, fold_to_cbet=35)
    
    @classmethod
    def tight_passive(cls) -> "PlayerProfile":
        """타이트-패시브"""
        return cls(vpip=18, pfr=10, aggression=1.2, three_bet=4, fold_to_3bet=65, cbet=50, fold_to_cbet=55)
    
    @classmethod
    def loose_passive(cls) -> "PlayerProfile":
        """루즈-패시브 (피쉬)"""
        return cls(vpip=40, pfr=8, aggression=0.8, three_bet=3, fold_to_3bet=70, cbet=40, fold_to_cbet=30)
    
    @classmethod
    def unknown(cls) -> "PlayerProfile":
        """알 수 없는 플레이어 (기본값)"""
        return cls()


@dataclass
class RangeEstimate:
    """레인지 추정 결과"""
    hands: Set[str]                    # 가능한 핸드들
    combos: int = 0                    # 총 콤보 수
    equity_vs_range: Optional[float] = None  # 이 레인지에 대한 승률
    
    def __post_init__(self):
        self.combos = self._count_combos()
    
    def _count_combos(self) -> int:
        """콤보 수 계산"""
        total = 0
        for hand in self.hands:
            h = Hand.from_string(hand)
            if h.card1 == h.card2:
                total += 6  # 포켓 페어
            elif h.suited:
                total += 4  # 수티드
            else:
                total += 12  # 오프수티드
        return total
    
    @property
    def range_percentage(self) -> float:
        """전체 핸드 대비 비율"""
        return (self.combos / 1326) * 100


class RangeAnalyzer:
    """레인지 분석기"""
    
    def __init__(self, preflop_charts: Optional[PreflopCharts] = None):
        self.charts = preflop_charts or PreflopCharts()
        
        # 핸드 강도 순위 (프리플랍)
        self.hand_rankings = self._generate_hand_rankings()
    
    def _generate_hand_rankings(self) -> Dict[str, int]:
        """프리플랍 핸드 강도 순위 생성"""
        # 대략적인 프리플랍 핸드 강도 (1 = 최강)
        rankings = {}
        rank = 1
        
        # 프리미엄 핸드
        premium = ["AA", "KK", "QQ", "AKs", "JJ", "AKo", "AQs", "TT", "AQo", "AJs"]
        for h in premium:
            rankings[h] = rank
            rank += 1
        
        # 강한 핸드
        strong = ["99", "ATs", "AJo", "KQs", "88", "KJs", "ATo", "A9s", "KQo", "77",
                  "KTs", "A8s", "QJs", "A5s", "66", "A7s", "KJo", "A4s", "A9o", "QTs"]
        for h in strong:
            rankings[h] = rank
            rank += 1
        
        # 중간 핸드
        medium = ["A6s", "55", "A3s", "KTo", "JTs", "QJo", "A8o", "A2s", "K9s", "44",
                  "A7o", "K8s", "A5o", "Q9s", "J9s", "QTo", "33", "A6o", "K7s", "A4o",
                  "JTo", "T9s", "K9o", "A3o", "K6s", "22", "Q8s", "K5s", "A2o", "J8s"]
        for h in medium:
            rankings[h] = rank
            rank += 1
        
        # 나머지는 낮은 순위
        return rankings
    
    def get_hand_strength_rank(self, hand: str) -> int:
        """핸드 강도 순위 반환 (없으면 100 반환)"""
        return self.hand_rankings.get(hand, 100)
    
    def estimate_opening_range(
        self, 
        position: Position, 
        profile: Optional[PlayerProfile] = None
    ) -> RangeEstimate:
        """
        포지션에서 오픈 레인지 추정
        
        Args:
            position: 플레이어 포지션
            profile: 플레이어 프로파일
        """
        if profile is None:
            profile = PlayerProfile.unknown()
        
        # 기본 GTO 레인지
        base_range = self.charts.get_open_range(position)
        
        # 프로파일에 따라 조정
        # VPIP가 높으면 레인지 확장, 낮으면 축소
        if profile.vpip > 30:
            # 루즈한 플레이어 - 더 많은 핸드 추가
            expanded = self._expand_range(base_range, profile.vpip / 100)
            return RangeEstimate(expanded)
        elif profile.vpip < 20:
            # 타이트한 플레이어 - 레인지 축소
            contracted = self._contract_range(base_range, profile.vpip / 100)
            return RangeEstimate(contracted)
        
        return RangeEstimate(base_range)
    
    def estimate_range_after_action(
        self,
        current_range: Set[str],
        action: PlayerAction,
        position: Position,
        board: Optional[List[str]] = None,
        profile: Optional[PlayerProfile] = None
    ) -> RangeEstimate:
        """
        액션 후 레인지 업데이트
        
        Args:
            current_range: 현재 추정 레인지
            action: 플레이어의 액션
            position: 플레이어 포지션
            board: 현재 보드 (포스트플랍)
            profile: 플레이어 프로파일
        """
        if not current_range:
            return RangeEstimate(set())
        
        # 프리플랍
        if action.street == Street.PREFLOP:
            return self._update_preflop_range(current_range, action, position, profile)
        
        # 포스트플랍
        return self._update_postflop_range(current_range, action, board, profile)
    
    def _update_preflop_range(
        self,
        current_range: Set[str],
        action: PlayerAction,
        position: Position,
        profile: Optional[PlayerProfile]
    ) -> RangeEstimate:
        """프리플랍 레인지 업데이트"""
        
        if action.action_type == ActionType.FOLD:
            return RangeEstimate(set())
        
        if action.action_type == ActionType.CALL:
            # 콜은 중간 강도 핸드
            # 너무 강하면 레이즈, 너무 약하면 폴드
            medium_hands = {h for h in current_range 
                          if 10 < self.get_hand_strength_rank(h) < 50}
            return RangeEstimate(medium_hands if medium_hands else current_range)
        
        if action.action_type in [ActionType.RAISE, ActionType.BET]:
            # 레이즈는 강한 핸드 + 일부 블러프
            strong_hands = {h for h in current_range 
                          if self.get_hand_strength_rank(h) <= 30}
            
            # 블러프 핸드 추가 (수티드 에이스 로우, 수티드 커넥터)
            bluff_hands = {h for h in current_range 
                         if h.endswith('s') and h[0] == 'A' and h[1] in '5432'}
            
            combined = strong_hands | bluff_hands
            return RangeEstimate(combined if combined else current_range)
        
        if action.action_type == ActionType.ALL_IN:
            # 올인은 매우 강한 핸드 또는 블러프
            premium = {h for h in current_range 
                      if self.get_hand_strength_rank(h) <= 15}
            return RangeEstimate(premium if premium else current_range)
        
        return RangeEstimate(current_range)
    
    def _update_postflop_range(
        self,
        current_range: Set[str],
        action: PlayerAction,
        board: Optional[List[str]],
        profile: Optional[PlayerProfile]
    ) -> RangeEstimate:
        """포스트플랍 레인지 업데이트"""
        
        if action.action_type == ActionType.FOLD:
            return RangeEstimate(set())
        
        if action.action_type == ActionType.CHECK:
            # 체크는 약한~중간 핸드, 또는 슬로우플레이
            # 레인지 유지 또는 약간 약한 쪽으로
            return RangeEstimate(current_range)
        
        if action.action_type == ActionType.CALL:
            # 콜은 드로우 또는 중간 강도
            return RangeEstimate(current_range)
        
        if action.action_type in [ActionType.BET, ActionType.RAISE]:
            bet_ratio = action.bet_size_ratio or 0.5
            
            if bet_ratio >= 1.0:
                # 큰 베팅 = 밸류 또는 블러프 양극화
                # 레인지를 강한 쪽으로 좁힘
                strong_percentage = min(0.5, 1.0 / (bet_ratio + 1))
                return RangeEstimate(
                    self._filter_top_percentage(current_range, strong_percentage)
                )
            else:
                # 작은 베팅 = 넓은 레인지
                return RangeEstimate(current_range)
        
        return RangeEstimate(current_range)
    
    def _expand_range(self, base_range: Set[str], factor: float) -> Set[str]:
        """레인지 확장"""
        all_hands = self._get_all_hands()
        sorted_hands = sorted(all_hands, key=lambda h: self.get_hand_strength_rank(h))
        
        target_size = int(len(sorted_hands) * factor)
        return set(sorted_hands[:target_size])
    
    def _contract_range(self, base_range: Set[str], factor: float) -> Set[str]:
        """레인지 축소"""
        sorted_hands = sorted(base_range, key=lambda h: self.get_hand_strength_rank(h))
        target_size = max(1, int(len(sorted_hands) * factor * 2))
        return set(sorted_hands[:target_size])
    
    def _filter_top_percentage(self, range_hands: Set[str], percentage: float) -> Set[str]:
        """상위 N% 핸드만 필터"""
        sorted_hands = sorted(range_hands, key=lambda h: self.get_hand_strength_rank(h))
        target_size = max(1, int(len(sorted_hands) * percentage))
        return set(sorted_hands[:target_size])
    
    def _get_all_hands(self) -> List[str]:
        """모든 169개 핸드 반환"""
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        hands = []
        
        for i, r1 in enumerate(ranks):
            for j, r2 in enumerate(ranks):
                if i == j:
                    hands.append(f"{r1}{r2}")
                elif i < j:
                    hands.append(f"{r1}{r2}s")
                    hands.append(f"{r1}{r2}o")
        
        return hands
    
    def range_to_combos(
        self, 
        range_hands: Set[str],
        dead_cards: Optional[List[str]] = None
    ) -> List[Tuple[str, str]]:
        """
        레인지를 실제 카드 콤보로 변환
        
        Args:
            range_hands: 핸드 집합
            dead_cards: 제외할 카드 (보드, 내 핸드 등)
        """
        dead = set(dead_cards) if dead_cards else set()
        combos = []
        
        for hand in range_hands:
            hand_combos = self.charts.hand_to_combos(hand)
            for c1, c2 in hand_combos:
                if c1 not in dead and c2 not in dead:
                    combos.append((c1, c2))
        
        return combos
    
    def calculate_range_equity(
        self,
        my_hand: List[str],
        opponent_range: Set[str],
        board: Optional[List[str]] = None,
        iterations: int = 5000
    ) -> float:
        """
        특정 레인지에 대한 승률 계산
        
        Args:
            my_hand: 내 홀 카드 ["As", "Kh"]
            opponent_range: 상대 레인지
            board: 보드 카드
            iterations: 시뮬레이션 횟수
        """
        from ..core.equity_calculator import EquityCalculator
        
        calculator = EquityCalculator()
        my_cards = [Card.new(c) for c in my_hand]
        board_cards = [Card.new(c) for c in board] if board else []
        
        # 레인지를 콤보로 변환
        dead_cards = my_hand + (board or [])
        combos = self.range_to_combos(opponent_range, dead_cards)
        
        if not combos:
            return 50.0
        
        # 각 콤보를 treys 형식으로 변환
        opp_range_cards = [
            [Card.new(c1), Card.new(c2)] for c1, c2 in combos
        ]
        
        result = calculator.calculate_equity_vs_range(
            my_cards, opp_range_cards, board_cards, iterations
        )
        
        return result["win"]
    
    def suggest_exploit(
        self,
        opponent_range: RangeEstimate,
        my_hand: str,
        street: Street,
        profile: PlayerProfile
    ) -> Dict:
        """
        상대 레인지에 대한 익스플로잇 전략 제안
        
        Returns:
            dict: 추천 전략
        """
        suggestions = {
            "action": None,
            "sizing": None,
            "reasoning": []
        }
        
        my_rank = self.get_hand_strength_rank(my_hand)
        range_top = min(self.get_hand_strength_rank(h) for h in opponent_range.hands) if opponent_range.hands else 100
        
        # 상대 레인지가 타이트하면
        if opponent_range.range_percentage < 15:
            if my_rank <= range_top:
                suggestions["action"] = "value_bet"
                suggestions["sizing"] = "large"
                suggestions["reasoning"].append("상대 레인지가 타이트함 - 밸류 추출 가능")
            else:
                suggestions["action"] = "fold_or_bluff"
                suggestions["reasoning"].append("상대 레인지가 강함 - 신중하게 플레이")
        
        # 상대 레인지가 와이드하면
        elif opponent_range.range_percentage > 30:
            suggestions["action"] = "value_bet"
            suggestions["sizing"] = "medium"
            suggestions["reasoning"].append("상대 레인지가 와이드함 - 중간 사이즈 밸류 베팅")
        
        # 상대가 폴드를 많이 하면
        if profile.fold_to_cbet > 55:
            suggestions["action"] = "bluff_cbet"
            suggestions["sizing"] = "small"
            suggestions["reasoning"].append(f"상대 폴드 투 시벳 {profile.fold_to_cbet}% - 블러프 수익적")
        
        return suggestions
