"""
팟 오즈 및 기대값(EV) 계산 모듈
"""

from typing import Optional
from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """포커 액션"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class PotOddsResult:
    """팟 오즈 계산 결과"""
    pot_odds: float              # 팟 오즈 (퍼센트)
    required_equity: float       # 콜하기 위한 최소 승률
    current_equity: Optional[float] = None  # 현재 승률 (있으면)
    ev: Optional[float] = None   # 기대값 (있으면)
    is_profitable_call: Optional[bool] = None  # 콜이 이익인지
    
    def __str__(self) -> str:
        result = f"팟 오즈: {self.pot_odds:.1f}%\n"
        result += f"필요 승률: {self.required_equity:.1f}%\n"
        if self.current_equity is not None:
            result += f"현재 승률: {self.current_equity:.1f}%\n"
            result += f"콜 EV: {'+' if self.ev >= 0 else ''}{self.ev:.2f}\n"
            result += f"판정: {'✓ 콜 가능' if self.is_profitable_call else '✗ 폴드 권장'}"
        return result


class PotOddsCalculator:
    """팟 오즈 및 EV 계산기"""
    
    @staticmethod
    def calculate_pot_odds(pot_size: float, call_amount: float) -> float:
        """
        팟 오즈 계산
        
        Args:
            pot_size: 현재 팟 사이즈 (콜 금액 포함하지 않음)
            call_amount: 콜해야 하는 금액
        
        Returns:
            팟 오즈 (퍼센트) - 투자해야 할 금액 / (팟 + 투자 금액)
        """
        if call_amount <= 0:
            return 0.0
        total_pot = pot_size + call_amount
        return (call_amount / total_pot) * 100
    
    @staticmethod
    def calculate_required_equity(pot_size: float, call_amount: float) -> float:
        """
        콜하기 위해 필요한 최소 승률 계산
        
        팟 오즈와 같은 값 (브레이크이븐 포인트)
        """
        return PotOddsCalculator.calculate_pot_odds(pot_size, call_amount)
    
    @staticmethod
    def calculate_ev(
        equity: float, 
        pot_size: float, 
        call_amount: float,
        include_call_in_pot: bool = False
    ) -> float:
        """
        콜의 기대값(EV) 계산
        
        Args:
            equity: 현재 승률 (0-100)
            pot_size: 팟 사이즈
            call_amount: 콜 금액
            include_call_in_pot: pot_size에 콜 금액이 포함되어 있는지
        
        Returns:
            기대값 (양수 = +EV, 음수 = -EV)
        
        EV 공식:
        EV = (승률 × 이길 때 얻는 금액) - ((1 - 승률) × 질 때 잃는 금액)
        """
        equity_decimal = equity / 100
        
        if include_call_in_pot:
            win_amount = pot_size  # 이미 콜이 포함됨
        else:
            win_amount = pot_size + call_amount  # 팟 + 상대 콜
        
        # 이기면: 팟 전체를 가져옴 (내 콜 금액 제외한 순이익)
        # 지면: 콜 금액을 잃음
        ev = (equity_decimal * win_amount) - ((1 - equity_decimal) * call_amount)
        return ev
    
    @staticmethod
    def calculate_fold_equity(
        bluff_success_rate: float,
        pot_size: float,
        bet_amount: float
    ) -> float:
        """
        폴드 에쿼티 계산 (블러프 EV)
        
        Args:
            bluff_success_rate: 상대가 폴드할 확률 (0-100)
            pot_size: 현재 팟
            bet_amount: 베팅 금액
        
        Returns:
            블러프의 기대값
        """
        fold_rate = bluff_success_rate / 100
        
        # 상대 폴드시: 팟 획득
        # 상대 콜시: 베팅 금액 손실 (단순화 - 쇼다운 무시)
        ev = (fold_rate * pot_size) - ((1 - fold_rate) * bet_amount)
        return ev
    
    @staticmethod
    def calculate_implied_odds(
        pot_size: float,
        call_amount: float,
        expected_future_winnings: float
    ) -> float:
        """
        임플라이드 오즈 계산
        
        Args:
            pot_size: 현재 팟
            call_amount: 콜 금액
            expected_future_winnings: 이후 스트릿에서 예상되는 추가 획득 금액
        
        Returns:
            임플라이드 오즈 (퍼센트)
        """
        total_potential = pot_size + call_amount + expected_future_winnings
        return (call_amount / total_potential) * 100
    
    @staticmethod
    def calculate_reverse_implied_odds(
        pot_size: float,
        call_amount: float,
        potential_loss: float
    ) -> float:
        """
        리버스 임플라이드 오즈 계산
        
        강한 핸드를 만들어도 질 수 있는 상황 고려
        """
        total_risk = call_amount + potential_loss
        return (total_risk / (pot_size + total_risk)) * 100
    
    def analyze(
        self,
        pot_size: float,
        call_amount: float,
        current_equity: Optional[float] = None
    ) -> PotOddsResult:
        """
        종합 분석
        
        Args:
            pot_size: 팟 사이즈
            call_amount: 콜 금액
            current_equity: 현재 승률 (알고 있으면)
        
        Returns:
            PotOddsResult: 분석 결과
        """
        pot_odds = self.calculate_pot_odds(pot_size, call_amount)
        required_equity = self.calculate_required_equity(pot_size, call_amount)
        
        ev = None
        is_profitable = None
        
        if current_equity is not None:
            ev = self.calculate_ev(current_equity, pot_size, call_amount)
            is_profitable = current_equity >= required_equity
        
        return PotOddsResult(
            pot_odds=pot_odds,
            required_equity=required_equity,
            current_equity=current_equity,
            ev=ev,
            is_profitable_call=is_profitable
        )
    
    @staticmethod
    def calculate_bet_sizing(
        pot_size: float,
        target_fold_equity: float
    ) -> dict:
        """
        목표 폴드 에쿼티를 달성하기 위한 베팅 사이즈 계산
        
        Args:
            pot_size: 현재 팟
            target_fold_equity: 원하는 상대 폴드 확률
        
        Returns:
            다양한 베팅 사이즈 옵션
        """
        return {
            "1/3_pot": pot_size * 0.33,
            "1/2_pot": pot_size * 0.5,
            "2/3_pot": pot_size * 0.67,
            "3/4_pot": pot_size * 0.75,
            "pot": pot_size,
            "1.5x_pot": pot_size * 1.5,
            "2x_pot": pot_size * 2.0
        }
    
    @staticmethod
    def outs_to_equity(outs: int, street: str = "flop") -> dict:
        """
        아웃츠를 승률로 변환
        
        Args:
            outs: 아웃츠 수
            street: "flop" (2장 남음) 또는 "turn" (1장 남음)
        
        Returns:
            대략적인 승률
        """
        if street == "flop":
            # 플랍: 2장 더 볼 수 있음
            # Rule of 4: outs × 4
            approx = outs * 4
            # 정확한 계산: 1 - (47-outs)/47 × (46-outs)/46
            exact = (1 - ((47 - outs) / 47) * ((46 - outs) / 46)) * 100
        else:
            # 턴: 1장 남음
            # Rule of 2: outs × 2
            approx = outs * 2
            # 정확한 계산: outs / 46
            exact = (outs / 46) * 100
        
        return {
            "rule_of_4_or_2": min(approx, 100),
            "exact": exact,
            "outs": outs
        }


# 편의 함수
def pot_odds(pot_size: float, call_amount: float) -> float:
    """팟 오즈 계산 (퍼센트)"""
    return PotOddsCalculator.calculate_pot_odds(pot_size, call_amount)


def ev(equity: float, pot_size: float, call_amount: float) -> float:
    """콜의 기대값 계산"""
    return PotOddsCalculator.calculate_ev(equity, pot_size, call_amount)


def should_call(equity: float, pot_size: float, call_amount: float) -> bool:
    """콜해야 하는지 판단"""
    required = PotOddsCalculator.calculate_required_equity(pot_size, call_amount)
    return equity >= required
