"""
핸드 평가 모듈
treys 라이브러리를 활용한 포커 핸드 평가
"""

from typing import List, Tuple, Optional
from treys import Card, Evaluator


class HandEvaluator:
    """포커 핸드 평가기"""
    
    # 핸드 랭크 이름
    HAND_RANKS = {
        1: "Royal Flush",
        2: "Straight Flush", 
        3: "Four of a Kind",
        4: "Full House",
        5: "Flush",
        6: "Straight",
        7: "Three of a Kind",
        8: "Two Pair",
        9: "One Pair",
        10: "High Card"
    }
    
    def __init__(self):
        self.evaluator = Evaluator()
    
    @staticmethod
    def parse_card(card_str: str) -> int:
        """
        카드 문자열을 treys 카드 정수로 변환
        
        Args:
            card_str: 카드 문자열 (예: "As", "Kh", "2d", "Tc")
                      랭크: A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
                      슈트: s(스페이드), h(하트), d(다이아몬드), c(클럽)
        
        Returns:
            treys 카드 정수
        """
        return Card.new(card_str)
    
    @staticmethod
    def parse_cards(card_strs: List[str]) -> List[int]:
        """여러 카드 문자열을 treys 카드 리스트로 변환"""
        return [Card.new(card) for card in card_strs]
    
    @staticmethod
    def card_to_string(card: int) -> str:
        """treys 카드 정수를 문자열로 변환"""
        return Card.int_to_str(card)
    
    @staticmethod
    def print_pretty_cards(cards: List[int]) -> str:
        """카드를 예쁘게 출력"""
        return Card.print_pretty_cards(cards)
    
    def evaluate(self, hole_cards: List[int], board: List[int]) -> int:
        """
        핸드 강도 평가 (낮을수록 강함)
        
        Args:
            hole_cards: 홀 카드 2장 (treys 정수)
            board: 보드 카드 3-5장 (treys 정수)
        
        Returns:
            핸드 강도 점수 (1 = Royal Flush, 7462 = 최약 하이카드)
        """
        return self.evaluator.evaluate(board, hole_cards)
    
    def evaluate_from_strings(self, hole_cards: List[str], board: List[str]) -> int:
        """문자열로 핸드 평가"""
        hole = self.parse_cards(hole_cards)
        board_cards = self.parse_cards(board)
        return self.evaluate(hole, board_cards)
    
    def get_rank_class(self, score: int) -> int:
        """
        핸드 랭크 클래스 반환 (1-10)
        1: Royal/Straight Flush, 2: Four of a Kind, ...
        """
        return self.evaluator.get_rank_class(score)
    
    def get_rank_name(self, score: int) -> str:
        """핸드 랭크 이름 반환"""
        rank_class = self.get_rank_class(score)
        return self.evaluator.class_to_string(rank_class)
    
    def get_rank_percentage(self, score: int) -> float:
        """
        핸드 강도를 백분율로 반환 (높을수록 강함)
        100% = 최강, 0% = 최약
        """
        # treys 점수: 1 (최강) ~ 7462 (최약)
        max_score = 7462
        return (max_score - score + 1) / max_score * 100
    
    def compare_hands(
        self, 
        hand1: Tuple[List[int], List[int]], 
        hand2: Tuple[List[int], List[int]], 
        board: List[int]
    ) -> int:
        """
        두 핸드 비교
        
        Returns:
            1: hand1 승리, -1: hand2 승리, 0: 무승부
        """
        score1 = self.evaluate(hand1, board)
        score2 = self.evaluate(hand2, board)
        
        if score1 < score2:
            return 1
        elif score1 > score2:
            return -1
        else:
            return 0


# 편의를 위한 전역 인스턴스
_evaluator = HandEvaluator()

def evaluate_hand(hole_cards: List[str], board: List[str]) -> dict:
    """
    간편한 핸드 평가 함수
    
    Args:
        hole_cards: 홀 카드 ["As", "Kh"]
        board: 보드 카드 ["Qd", "Jc", "Ts"]
    
    Returns:
        dict: 평가 결과
    """
    score = _evaluator.evaluate_from_strings(hole_cards, board)
    return {
        "score": score,
        "rank_name": _evaluator.get_rank_name(score),
        "percentile": _evaluator.get_rank_percentage(score)
    }
