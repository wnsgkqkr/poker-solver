"""
프리플랍 차트 모듈
포지션별 GTO 기반 프리플랍 레인지 관리
"""

import json
import os
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class Position(Enum):
    """포커 포지션 (6-max)"""
    UTG = "UTG"     # Under The Gun
    HJ = "HJ"       # Hijack
    CO = "CO"       # Cutoff
    BTN = "BTN"     # Button
    SB = "SB"       # Small Blind
    BB = "BB"       # Big Blind


class Action(Enum):
    """프리플랍 액션"""
    FOLD = "fold"
    OPEN = "open"
    CALL = "call"
    RAISE_3BET = "3bet"
    RAISE_4BET = "4bet"
    ALL_IN = "all_in"


@dataclass
class Hand:
    """포커 핸드 (프리플랍)"""
    card1: str  # 예: "A", "K", "Q", ...
    card2: str
    suited: bool
    
    @classmethod
    def from_string(cls, hand_str: str) -> "Hand":
        """
        문자열에서 핸드 생성
        예: "AKs" -> Hand("A", "K", True)
            "QJo" -> Hand("Q", "J", False)
            "TT"  -> Hand("T", "T", False)
        """
        if len(hand_str) == 2:
            # 포켓 페어 (예: "AA", "KK")
            return cls(hand_str[0], hand_str[1], False)
        elif len(hand_str) == 3:
            suited = hand_str[2].lower() == 's'
            return cls(hand_str[0], hand_str[1], suited)
        else:
            raise ValueError(f"Invalid hand format: {hand_str}")
    
    def __str__(self) -> str:
        if self.card1 == self.card2:
            return f"{self.card1}{self.card2}"
        suffix = "s" if self.suited else "o"
        return f"{self.card1}{self.card2}{suffix}"
    
    def __hash__(self) -> int:
        return hash(str(self))
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Hand):
            return str(self) == str(other)
        return False


class PreflopCharts:
    """프리플랍 레인지 차트 관리자"""
    
    # 모든 가능한 핸드 (169개)
    RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Args:
            data_path: 레인지 데이터 JSON 파일 경로
        """
        self.ranges: Dict = {}
        
        if data_path is None:
            # 기본 경로
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(base_dir, "data", "preflop_ranges", "6max_ranges.json")
        
        if os.path.exists(data_path):
            self.load_ranges(data_path)
        else:
            # 기본 레인지 사용
            self._init_default_ranges()
    
    def load_ranges(self, filepath: str) -> None:
        """JSON 파일에서 레인지 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.ranges = data.get("ranges", {})
    
    def _init_default_ranges(self) -> None:
        """기본 레인지 초기화"""
        # 간단한 기본 레인지
        self.ranges = {
            "UTG": {
                "open": {
                    "hands": ["AA", "KK", "QQ", "JJ", "TT", "99", "88",
                             "AKs", "AQs", "AJs", "ATs", "AKo", "AQo",
                             "KQs", "KJs", "QJs", "JTs"]
                }
            },
            "BTN": {
                "open": {
                    "hands": ["AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                             "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                             "AKo", "AQo", "AJo", "ATo", "A9o",
                             "KQs", "KJs", "KTs", "K9s", "KQo", "KJo",
                             "QJs", "QTs", "Q9s", "QJo",
                             "JTs", "J9s", "JTo",
                             "T9s", "T8s", "98s", "87s", "76s", "65s", "54s"]
                }
            }
        }
    
    def get_open_range(self, position: Position) -> Set[str]:
        """포지션의 오픈 레인지 반환"""
        pos_data = self.ranges.get(position.value, {})
        open_data = pos_data.get("open", {})
        return set(open_data.get("hands", []))
    
    def get_3bet_range(self, position: Position, vs_position: Position) -> Set[str]:
        """특정 포지션 오픈에 대한 3bet 레인지"""
        pos_data = self.ranges.get(position.value, {})
        vs_key = f"vs_{vs_position.value.lower()}_open"
        vs_data = pos_data.get(vs_key, {})
        return set(vs_data.get("3bet", []))
    
    def get_call_range(self, position: Position, vs_position: Position) -> Set[str]:
        """특정 포지션 오픈에 대한 콜 레인지"""
        pos_data = self.ranges.get(position.value, {})
        vs_key = f"vs_{vs_position.value.lower()}_open"
        vs_data = pos_data.get(vs_key, {})
        return set(vs_data.get("call", []))
    
    def is_in_range(self, hand: str, range_hands: Set[str]) -> bool:
        """핸드가 레인지에 포함되는지 확인"""
        # 정확한 매칭
        if hand in range_hands:
            return True
        
        # suited/offsuit 변환 시도
        if len(hand) == 3:
            # AKs -> AKo 또는 그 반대
            alt_hand = hand[:2] + ('o' if hand[2] == 's' else 's')
            if alt_hand in range_hands:
                return False  # 다른 타입만 있음
        
        return False
    
    def get_action(
        self, 
        hand: str, 
        position: Position,
        vs_position: Optional[Position] = None,
        facing_raise: bool = False
    ) -> Tuple[Action, float]:
        """
        핸드와 상황에 따른 추천 액션
        
        Args:
            hand: 핸드 문자열 (예: "AKs")
            position: 내 포지션
            vs_position: 상대 포지션 (레이즈가 있을 때)
            facing_raise: 레이즈를 facing 하고 있는지
        
        Returns:
            (추천 액션, 확신도 0-1)
        """
        if not facing_raise:
            # 오픈 상황
            open_range = self.get_open_range(position)
            if self.is_in_range(hand, open_range):
                return (Action.OPEN, 1.0)
            else:
                return (Action.FOLD, 1.0)
        else:
            # 레이즈를 facing
            if vs_position is None:
                return (Action.FOLD, 0.5)
            
            threbet_range = self.get_3bet_range(position, vs_position)
            call_range = self.get_call_range(position, vs_position)
            
            if self.is_in_range(hand, threbet_range):
                return (Action.RAISE_3BET, 1.0)
            elif self.is_in_range(hand, call_range):
                return (Action.CALL, 1.0)
            else:
                return (Action.FOLD, 1.0)
    
    def get_range_percentage(self, range_hands: Set[str]) -> float:
        """레인지의 총 핸드 비율 계산 (169개 중)"""
        # 실제로는 1326 콤보 중 계산해야 하지만, 단순화
        total_combos = 0
        for hand in range_hands:
            h = Hand.from_string(hand)
            if h.card1 == h.card2:
                # 포켓 페어: 6 콤보
                total_combos += 6
            elif h.suited:
                # 수티드: 4 콤보
                total_combos += 4
            else:
                # 오프수티드: 12 콤보
                total_combos += 12
        
        return (total_combos / 1326) * 100
    
    def hand_to_combos(self, hand_str: str) -> List[Tuple[str, str]]:
        """
        핸드 문자열을 실제 카드 콤보로 변환
        예: "AKs" -> [("As", "Ks"), ("Ah", "Kh"), ("Ad", "Kd"), ("Ac", "Kc")]
        """
        hand = Hand.from_string(hand_str)
        suits = ['s', 'h', 'd', 'c']
        combos = []
        
        if hand.card1 == hand.card2:
            # 포켓 페어
            for i, s1 in enumerate(suits):
                for s2 in suits[i+1:]:
                    combos.append((f"{hand.card1}{s1}", f"{hand.card2}{s2}"))
        elif hand.suited:
            # 수티드
            for s in suits:
                combos.append((f"{hand.card1}{s}", f"{hand.card2}{s}"))
        else:
            # 오프수티드
            for s1 in suits:
                for s2 in suits:
                    if s1 != s2:
                        combos.append((f"{hand.card1}{s1}", f"{hand.card2}{s2}"))
        
        return combos
    
    @staticmethod
    def cards_to_hand(card1: str, card2: str) -> str:
        """
        두 카드를 핸드 문자열로 변환
        예: ("As", "Kh") -> "AKo"
            ("Qd", "Qh") -> "QQ"
        """
        rank_order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
                      '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
        
        r1, s1 = card1[0], card1[1]
        r2, s2 = card2[0], card2[1]
        
        # 높은 랭크를 먼저
        if rank_order[r1] < rank_order[r2]:
            r1, r2 = r2, r1
            s1, s2 = s2, s1
        
        if r1 == r2:
            return f"{r1}{r2}"
        elif s1 == s2:
            return f"{r1}{r2}s"
        else:
            return f"{r1}{r2}o"
    
    def print_range_grid(self, range_hands: Set[str]) -> str:
        """레인지를 그리드 형식으로 출력"""
        output = "    " + "  ".join(self.RANKS) + "\n"
        
        for i, r1 in enumerate(self.RANKS):
            row = f"{r1}  "
            for j, r2 in enumerate(self.RANKS):
                if i == j:
                    # 포켓 페어
                    hand = f"{r1}{r2}"
                elif i < j:
                    # 수티드 (대각선 위)
                    hand = f"{r1}{r2}s"
                else:
                    # 오프수티드 (대각선 아래)
                    hand = f"{r2}{r1}o"
                
                if hand in range_hands:
                    row += " ■ "
                else:
                    row += " · "
            output += row + "\n"
        
        return output
