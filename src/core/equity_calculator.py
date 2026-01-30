"""
승률 계산 모듈
몬테카를로 시뮬레이션을 사용한 핸드 승률 계산
"""

import random
from typing import List, Optional, Tuple
from treys import Card, Evaluator, Deck


class EquityCalculator:
    """포커 승률 계산기 (몬테카를로 시뮬레이션)"""
    
    def __init__(self):
        self.evaluator = Evaluator()
    
    def calculate_equity(
        self, 
        hole_cards: List[int], 
        board: Optional[List[int]] = None,
        num_opponents: int = 1,
        iterations: int = 10000
    ) -> dict:
        """
        몬테카를로 시뮬레이션으로 승률 계산
        
        Args:
            hole_cards: 내 홀 카드 2장 (treys 정수)
            board: 현재 보드 카드 (없으면 프리플랍)
            num_opponents: 상대 수
            iterations: 시뮬레이션 반복 횟수
        
        Returns:
            dict: {
                "win": 승률,
                "tie": 무승부율,
                "lose": 패배율,
                "iterations": 실제 반복 횟수
            }
        """
        if board is None:
            board = []
        
        wins = 0
        ties = 0
        losses = 0
        
        # 사용된 카드 제외
        used_cards = set(hole_cards + board)
        
        # 사용 가능한 카드 덱 생성
        full_deck = Deck.GetFullDeck()
        available_cards = [c for c in full_deck if c not in used_cards]
        
        for _ in range(iterations):
            # 덱 섞기
            deck = available_cards.copy()
            random.shuffle(deck)
            
            deck_idx = 0
            
            # 보드 완성 (5장까지)
            sim_board = board.copy()
            cards_needed = 5 - len(sim_board)
            sim_board.extend(deck[deck_idx:deck_idx + cards_needed])
            deck_idx += cards_needed
            
            # 내 핸드 평가
            my_score = self.evaluator.evaluate(sim_board, hole_cards)
            
            # 상대 핸드 생성 및 평가
            best_opponent_score = float('inf')
            for _ in range(num_opponents):
                opp_hole = [deck[deck_idx], deck[deck_idx + 1]]
                deck_idx += 2
                opp_score = self.evaluator.evaluate(sim_board, opp_hole)
                best_opponent_score = min(best_opponent_score, opp_score)
            
            # 결과 비교 (낮은 점수가 강함)
            if my_score < best_opponent_score:
                wins += 1
            elif my_score > best_opponent_score:
                losses += 1
            else:
                ties += 1
        
        total = wins + ties + losses
        return {
            "win": wins / total * 100,
            "tie": ties / total * 100,
            "lose": losses / total * 100,
            "iterations": total
        }
    
    def calculate_equity_vs_range(
        self,
        hole_cards: List[int],
        opponent_range: List[List[int]],
        board: Optional[List[int]] = None,
        iterations: int = 10000
    ) -> dict:
        """
        특정 레인지에 대한 승률 계산
        
        Args:
            hole_cards: 내 홀 카드
            opponent_range: 상대 가능 핸드 리스트 [[c1, c2], [c1, c2], ...]
            board: 현재 보드
            iterations: 반복 횟수
        """
        if board is None:
            board = []
        
        if not opponent_range:
            return {"win": 50.0, "tie": 0.0, "lose": 50.0, "iterations": 0}
        
        wins = 0
        ties = 0
        losses = 0
        
        used_cards = set(hole_cards + board)
        
        # 유효한 상대 핸드만 필터링
        valid_range = [
            hand for hand in opponent_range 
            if hand[0] not in used_cards and hand[1] not in used_cards
        ]
        
        if not valid_range:
            return {"win": 50.0, "tie": 0.0, "lose": 50.0, "iterations": 0}
        
        full_deck = Deck.GetFullDeck()
        
        for _ in range(iterations):
            # 랜덤 상대 핸드 선택
            opp_hole = random.choice(valid_range)
            
            # 사용 가능한 카드
            current_used = used_cards | set(opp_hole)
            available = [c for c in full_deck if c not in current_used]
            random.shuffle(available)
            
            # 보드 완성
            sim_board = board.copy()
            cards_needed = 5 - len(sim_board)
            sim_board.extend(available[:cards_needed])
            
            # 평가
            my_score = self.evaluator.evaluate(sim_board, hole_cards)
            opp_score = self.evaluator.evaluate(sim_board, opp_hole)
            
            if my_score < opp_score:
                wins += 1
            elif my_score > opp_score:
                losses += 1
            else:
                ties += 1
        
        total = wins + ties + losses
        return {
            "win": wins / total * 100,
            "tie": ties / total * 100,
            "lose": losses / total * 100,
            "iterations": total
        }
    
    def calculate_preflop_equity(
        self,
        hole_cards: List[int],
        num_opponents: int = 1,
        iterations: int = 20000
    ) -> dict:
        """프리플랍 승률 계산 (보드 없음)"""
        return self.calculate_equity(
            hole_cards, 
            board=[], 
            num_opponents=num_opponents,
            iterations=iterations
        )
    
    def calculate_outs(
        self,
        hole_cards: List[int],
        board: List[int],
        target_hands: Optional[List[str]] = None
    ) -> dict:
        """
        아웃츠 계산 (특정 핸드를 완성시킬 카드 수)
        
        Args:
            hole_cards: 홀 카드
            board: 현재 보드 (플랍 또는 턴)
            target_hands: 목표 핸드 ["flush", "straight", ...]
                         None이면 모든 개선 카드 계산
        
        Returns:
            dict: 각 핸드별 아웃츠 정보
        """
        if len(board) >= 5:
            return {"outs": 0, "cards": [], "description": "이미 리버"}
        
        used_cards = set(hole_cards + board)
        full_deck = Deck.GetFullDeck()
        available = [c for c in full_deck if c not in used_cards]
        
        current_score = self.evaluator.evaluate(board, hole_cards)
        
        improving_cards = []
        for card in available:
            test_board = board + [card]
            if len(test_board) < 5:
                # 턴에서 테스트할 때는 리버 카드 하나 더 추가
                remaining = [c for c in available if c != card]
                test_board.append(remaining[0])
            
            new_score = self.evaluator.evaluate(test_board[:5], hole_cards)
            if new_score < current_score:
                improving_cards.append(card)
        
        return {
            "outs": len(improving_cards),
            "cards": [Card.int_to_str(c) for c in improving_cards],
            "current_hand": self.evaluator.class_to_string(
                self.evaluator.get_rank_class(current_score)
            )
        }


def calculate_equity(
    hole_cards: List[str], 
    board: Optional[List[str]] = None,
    num_opponents: int = 1,
    iterations: int = 10000
) -> dict:
    """
    간편한 승률 계산 함수
    
    Args:
        hole_cards: ["As", "Kh"]
        board: ["Qd", "Jc", "Ts"] or None
        num_opponents: 상대 수
        iterations: 시뮬레이션 횟수
    
    Returns:
        승률 정보 dict
    """
    calc = EquityCalculator()
    hole = [Card.new(c) for c in hole_cards]
    board_cards = [Card.new(c) for c in board] if board else None
    
    return calc.calculate_equity(
        hole, 
        board_cards, 
        num_opponents, 
        iterations
    )
