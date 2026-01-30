"""
라이브 세션 모듈
실시간 포커 핸드 추적 및 결정 지원
"""

import os
import sys
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum

from .core.equity_calculator import calculate_equity, EquityCalculator
from .core.pot_odds import PotOddsCalculator, pot_odds, ev
from .strategy.gto_advisor import GTOAdvisor, GameState, RecommendedAction
from .strategy.preflop_charts import PreflopCharts, Position
from .strategy.range_analysis import Street, RangeAnalyzer, PlayerProfile


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "allin"


@dataclass
class PlayerState:
    """플레이어 상태"""
    position: str
    stack: float
    is_active: bool = True
    current_bet: float = 0
    is_hero: bool = False


@dataclass
class LiveHand:
    """라이브 핸드 세션"""
    # 기본 설정
    hero_position: str = "BTN"
    hero_cards: List[str] = field(default_factory=list)
    
    # 게임 상태
    street: Street = Street.PREFLOP
    board: List[str] = field(default_factory=list)
    pot: float = 0
    current_bet: float = 0  # 현재 스트릿의 최대 베팅
    hero_invested: float = 0  # 히어로가 이번 스트릿에 투자한 금액
    
    # 플레이어
    num_players: int = 2  # 핸드에 남은 플레이어 수
    villain_positions: List[str] = field(default_factory=list)
    
    # 블라인드
    bb: float = 1
    
    # 액션 히스토리
    actions: List[Dict] = field(default_factory=list)
    
    @property
    def to_call(self) -> float:
        """콜해야 하는 금액"""
        return max(0, self.current_bet - self.hero_invested)
    
    @property
    def street_name(self) -> str:
        return self.street.value.upper()


class LiveSession:
    """라이브 포커 세션"""
    
    POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    STREETS = [Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER]
    
    def __init__(self):
        self.advisor = GTOAdvisor()
        self.pot_calc = PotOddsCalculator()
        self.equity_calc = EquityCalculator()
        self.charts = PreflopCharts()
        
        self.hand: Optional[LiveHand] = None
        self.history: List[LiveHand] = []
    
    def new_hand(self):
        """새 핸드 시작"""
        self.hand = LiveHand()
        print("\n" + "="*60)
        print("🎴 새 핸드 시작")
        print("="*60)
    
    def set_hero(self, position: str, cards: List[str], stack: float = 100):
        """히어로 설정"""
        if not self.hand:
            self.new_hand()
        
        self.hand.hero_position = position.upper()
        
        # 카드 파싱 및 검증
        valid_ranks = "AKQJT98765432"
        valid_suits = "shdc"
        
        parsed_cards = []
        for card in cards:
            card = card.strip()
            if len(card) >= 2:
                rank = card[0].upper()
                suit = card[1].lower()
                
                if rank in valid_ranks and suit in valid_suits:
                    parsed_cards.append(f"{rank}{suit}")
                else:
                    print(f"⚠️ 잘못된 카드: {card} (예: As, Kh, Qd, Jc)")
                    return
            else:
                print(f"⚠️ 잘못된 카드 형식: {card}")
                return
        
        self.hand.hero_cards = parsed_cards
        print(f"\n✅ 히어로: {position} - {' '.join(self.hand.hero_cards)}")
    
    def set_blinds(self, bb: float = 1, sb: float = 0.5):
        """블라인드 설정"""
        if self.hand:
            self.hand.bb = bb
            self.hand.pot = bb + sb
            print(f"블라인드: {sb}/{bb}")
    
    def set_players(self, num_players: int, villain_positions: List[str] = None):
        """플레이어 수 설정"""
        if self.hand:
            self.hand.num_players = num_players
            if villain_positions:
                self.hand.villain_positions = [p.upper() for p in villain_positions]
            print(f"플레이어 수: {num_players}")
    
    def set_pot(self, pot: float):
        """팟 사이즈 설정"""
        if self.hand:
            self.hand.pot = pot
            print(f"팟: ${pot}")
    
    def facing_bet(self, bet_amount: float, raiser_position: str = None):
        """베팅에 직면"""
        if not self.hand:
            return
        
        self.hand.current_bet = bet_amount
        self.hand.pot += bet_amount  # 상대 베팅을 팟에 추가
        
        if raiser_position:
            self.hand.villain_positions = [raiser_position.upper()]
        
        print(f"\n⚠️ {raiser_position or '상대'}가 ${bet_amount} 베팅")
        self._show_decision()
    
    def facing_raise(self, raise_to: float, raiser_position: str = None):
        """레이즈에 직면"""
        if not self.hand:
            return
        
        self.hand.current_bet = raise_to
        print(f"\n⚠️ {raiser_position or '상대'}가 ${raise_to}로 레이즈")
        self._show_decision()
    
    def _show_decision(self):
        """결정 도움 표시"""
        if not self.hand or not self.hand.hero_cards:
            print("❌ 먼저 히어로 카드를 설정하세요")
            return
        
        to_call = self.hand.to_call
        pot = self.hand.pot
        
        print(f"\n{'─'*50}")
        print(f"📍 {self.hand.street_name} | 팟: ${pot} | 콜: ${to_call}")
        print(f"🃏 핸드: {' '.join(self.hand.hero_cards)}", end="")
        if self.hand.board:
            print(f" | 보드: {' '.join(self.hand.board)}")
        else:
            print()
        print(f"{'─'*50}")
        
        # 승률 계산
        board = self.hand.board if self.hand.board else None
        equity_result = calculate_equity(
            self.hand.hero_cards,
            board,
            num_opponents=self.hand.num_players - 1,
            iterations=10000
        )
        equity = equity_result["win"]
        
        # 프리플랍은 별도 로직
        if self.hand.street == Street.PREFLOP:
            self._show_preflop_decision(equity, to_call, pot)
            return
        
        # 포스트플랍 팟 오즈 분석
        if to_call > 0:
            pot_analysis = self.pot_calc.analyze(pot, to_call, equity)
            
            print(f"\n📊 분석:")
            print(f"   승률: {equity:.1f}%")
            print(f"   팟 오즈: {pot_analysis.pot_odds:.1f}%")
            print(f"   필요 승률: {pot_analysis.required_equity:.1f}%")
            print(f"   EV: {'+' if pot_analysis.ev >= 0 else ''}{pot_analysis.ev:.2f}")
            
            # 결정
            print(f"\n🎯 추천:")
            if pot_analysis.is_profitable_call:
                if equity > 60:
                    print(f"   ✅ RAISE (강한 핸드 - 밸류)")
                    raise_size = pot + to_call  # 팟 사이즈 레이즈
                    print(f"      레이즈 사이즈: ${raise_size:.0f} (팟)")
                else:
                    print(f"   ✅ CALL (EV+)")
            else:
                # 블러프 가치 체크
                if equity > 25 and equity < 40:
                    print(f"   ⚠️ CALL/FOLD (경계선)")
                    print(f"      드로우 있으면 콜, 없으면 폴드")
                else:
                    print(f"   ❌ FOLD (EV-)")
        else:
            # 체크 또는 베팅
            print(f"\n📊 분석:")
            print(f"   승률: {equity:.1f}%")
            
            print(f"\n🎯 추천:")
            if equity > 65:
                bet_size = pot * 0.67
                print(f"   ✅ BET ${bet_size:.0f} (2/3 팟) - 밸류")
            elif equity > 50:
                bet_size = pot * 0.33
                print(f"   ⚠️ BET ${bet_size:.0f} (1/3 팟) 또는 CHECK")
            else:
                print(f"   ✅ CHECK")
        
        print()
    
    def _show_preflop_decision(self, equity: float, to_call: float, pot: float):
        """프리플랍 결정 표시"""
        # 핸드 문자열로 변환
        hand_str = self.charts.cards_to_hand(
            self.hand.hero_cards[0], 
            self.hand.hero_cards[1]
        )
        
        try:
            position = Position[self.hand.hero_position]
        except:
            position = Position.BTN
        
        print(f"\n📊 분석:")
        print(f"   핸드: {hand_str}")
        print(f"   프리플랍 승률: {equity:.1f}%")
        
        # 오픈 레인지 확인
        open_range = self.charts.get_open_range(position)
        in_open_range = hand_str in open_range
        
        print(f"\n🎯 추천:")
        
        if to_call == 0:
            # 오픈 상황
            if in_open_range:
                print(f"   ✅ RAISE 2.5-3BB (오픈 레인지에 포함)")
            else:
                print(f"   ❌ FOLD (오픈 레인지 밖)")
        else:
            # 레이즈에 직면
            # 프리미엄 핸드 체크
            premium = ["AA", "KK", "QQ", "JJ", "AKs", "AKo"]
            strong = ["TT", "99", "AQs", "AQo", "AJs", "KQs"]
            playable = ["88", "77", "66", "55", "ATs", "AJo", "KJs", "KQo", "QJs", "JTs"]
            
            if hand_str in premium:
                raise_size = to_call * 3
                print(f"   ✅ RAISE ${raise_size:.0f} (프리미엄 핸드)")
                print(f"      4bet 또는 올인 가능")
            elif hand_str in strong:
                print(f"   ✅ CALL 또는 RAISE (강한 핸드)")
                print(f"      포지션이 좋으면 콜, IP면 레이즈 고려")
            elif hand_str in playable:
                # 팟 오즈 확인
                if to_call <= pot * 0.5:
                    print(f"   ✅ CALL (플레이어블 핸드, 좋은 오즈)")
                else:
                    print(f"   ⚠️ CALL/FOLD (경계선)")
                    print(f"      3bet 사이즈가 크면 폴드 고려")
            elif in_open_range:
                if to_call <= pot * 0.3:
                    print(f"   ⚠️ CALL (오픈 레인지, 저렴한 콜)")
                else:
                    print(f"   ❌ FOLD (오픈 레인지지만 비싼 콜)")
            else:
                print(f"   ❌ FOLD (레인지 밖)")
        
        print()
    
    def flop(self, cards: List[str]):
        """플랍 설정"""
        if not self.hand:
            return
        
        self.hand.street = Street.FLOP
        self.hand.board = [c.capitalize() for c in cards[:3]]
        self.hand.current_bet = 0
        self.hand.hero_invested = 0
        
        print(f"\n🃏 FLOP: {' '.join(self.hand.board)}")
        self._show_decision()
    
    def turn(self, card: str):
        """턴 설정"""
        if not self.hand:
            return
        
        self.hand.street = Street.TURN
        self.hand.board.append(card.capitalize())
        self.hand.current_bet = 0
        self.hand.hero_invested = 0
        
        print(f"\n🃏 TURN: {' '.join(self.hand.board)}")
        self._show_decision()
    
    def river(self, card: str):
        """리버 설정"""
        if not self.hand:
            return
        
        self.hand.street = Street.RIVER
        self.hand.board.append(card.capitalize())
        self.hand.current_bet = 0
        self.hand.hero_invested = 0
        
        print(f"\n🃏 RIVER: {' '.join(self.hand.board)}")
        self._show_decision()
    
    def action(self, action_type: str, amount: float = 0):
        """히어로 액션 기록"""
        if not self.hand:
            return
        
        action_type = action_type.lower()
        call_amount = self.hand.to_call
        
        if action_type == "fold":
            print("접었습니다.")
            self.end_hand()
        elif action_type == "check":
            print("체크")
        elif action_type == "call":
            self.hand.pot += call_amount
            self.hand.hero_invested = self.hand.current_bet
            print(f"콜 ${call_amount}")
        elif action_type in ["bet", "raise"]:
            self.hand.pot += amount
            self.hand.current_bet = amount
            self.hand.hero_invested = amount
            print(f"{'베팅' if action_type == 'bet' else '레이즈'} ${amount}")
    
    def villain_action(self, action_type: str, amount: float = 0, position: str = None):
        """상대 액션"""
        if not self.hand:
            return
        
        action_type = action_type.lower()
        pos = position or "상대"
        
        if action_type == "fold":
            self.hand.num_players -= 1
            print(f"{pos} 폴드")
            if self.hand.num_players <= 1:
                print("\n🎉 승리!")
                self.end_hand()
        elif action_type == "check":
            print(f"{pos} 체크")
        elif action_type == "call":
            call_amount = self.hand.current_bet
            self.hand.pot += call_amount
            print(f"{pos} 콜 ${call_amount}")
        elif action_type in ["bet", "raise"]:
            self.hand.current_bet = amount
            self.hand.pot += amount
            print(f"{pos} {'베팅' if action_type == 'bet' else '레이즈'} ${amount}")
            self._show_decision()
    
    def end_hand(self):
        """핸드 종료"""
        if self.hand:
            self.history.append(self.hand)
            self.hand = None
        print("\n핸드 종료")
        print("="*60)
    
    def status(self):
        """현재 상태 표시"""
        if not self.hand:
            print("진행 중인 핸드 없음")
            return
        
        print(f"\n{'='*50}")
        print(f"📍 {self.hand.street_name}")
        print(f"🃏 핸드: {' '.join(self.hand.hero_cards)} ({self.hand.hero_position})")
        if self.hand.board:
            print(f"🎴 보드: {' '.join(self.hand.board)}")
        print(f"💰 팟: ${self.hand.pot}")
        if self.hand.to_call > 0:
            print(f"📞 콜: ${self.hand.to_call}")
        print(f"👥 플레이어: {self.hand.num_players}명")
        print(f"{'='*50}")
    
    def help(self):
        """도움말"""
        print("""
╔════════════════════════════════════════════════════════════╗
║                    🎰 라이브 세션 명령어                      ║
╠════════════════════════════════════════════════════════════╣
║ 핸드 시작                                                   ║
║   new                    새 핸드 시작                        ║
║   hero BTN As Kh         히어로 설정 (포지션 + 카드)           ║
║   pot 100                팟 사이즈 설정                       ║
║   players 3              플레이어 수 설정                     ║
║                                                            ║
║ 스트릿 진행                                                  ║
║   flop Qd Jc Ts          플랍 카드 설정                       ║
║   turn 9h                턴 카드 추가                        ║
║   river 2s               리버 카드 추가                       ║
║                                                            ║
║ 액션                                                        ║
║   bet 50                 상대가 50 베팅                      ║
║   raise 150              상대가 150으로 레이즈                ║
║   vbet 75                상대 베팅 (villain bet)             ║
║   vraise 200             상대 레이즈                         ║
║   vcall                  상대 콜                             ║
║   vfold                  상대 폴드                           ║
║                                                            ║
║ 내 액션                                                      ║
║   call                   콜                                 ║
║   fold                   폴드                               ║
║   check                  체크                               ║
║   mybat 100              내가 베팅                           ║
║                                                            ║
║ 기타                                                        ║
║   status / s             현재 상태                           ║
║   help / h               도움말                             ║
║   quit / q               종료                               ║
╚════════════════════════════════════════════════════════════╝
        """)


def run_live_session():
    """라이브 세션 실행"""
    session = LiveSession()
    
    print("\n" + "="*60)
    print("🎰 포커 라이브 세션")
    print("="*60)
    print("'help' 또는 'h'로 명령어 확인")
    print("'new'로 새 핸드 시작\n")
    
    while True:
        try:
            user_input = input("▶ ").strip()
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            # 종료
            if cmd in ["quit", "q", "exit"]:
                print("세션 종료")
                break
            
            # 도움말
            elif cmd in ["help", "h"]:
                session.help()
            
            # 새 핸드
            elif cmd == "new":
                session.new_hand()
            
            # 히어로 설정
            elif cmd == "hero":
                if len(args) >= 3:
                    position = args[0]
                    cards = args[1:3]
                    session.set_hero(position, cards)
                else:
                    print("사용법: hero BTN As Kh")
            
            # 팟 설정
            elif cmd == "pot":
                if args:
                    session.set_pot(float(args[0]))
                else:
                    print("사용법: pot 100")
            
            # 플레이어 수
            elif cmd == "players":
                if args:
                    session.set_players(int(args[0]))
                else:
                    print("사용법: players 3")
            
            # 플랍
            elif cmd == "flop":
                if len(args) >= 3:
                    session.flop(args[:3])
                else:
                    print("사용법: flop Qd Jc Ts")
            
            # 턴
            elif cmd == "turn":
                if args:
                    session.turn(args[0])
                else:
                    print("사용법: turn 9h")
            
            # 리버
            elif cmd == "river":
                if args:
                    session.river(args[0])
                else:
                    print("사용법: river 2s")
            
            # 상대 베팅
            elif cmd in ["bet", "vbet"]:
                if args:
                    position = args[1] if len(args) > 1 else None
                    session.facing_bet(float(args[0]), position)
                else:
                    print("사용법: bet 50 [position]")
            
            # 상대 레이즈
            elif cmd in ["raise", "vraise"]:
                if args:
                    position = args[1] if len(args) > 1 else None
                    session.facing_raise(float(args[0]), position)
                else:
                    print("사용법: raise 150 [position]")
            
            # 상대 콜
            elif cmd == "vcall":
                position = args[0] if args else None
                session.villain_action("call", position=position)
            
            # 상대 폴드
            elif cmd == "vfold":
                position = args[0] if args else None
                session.villain_action("fold", position=position)
            
            # 상대 체크
            elif cmd == "vcheck":
                position = args[0] if args else None
                session.villain_action("check", position=position)
            
            # 내 콜
            elif cmd == "call":
                session.action("call")
            
            # 내 폴드
            elif cmd == "fold":
                session.action("fold")
            
            # 내 체크
            elif cmd == "check":
                session.action("check")
            
            # 내 베팅
            elif cmd == "mybet":
                if args:
                    session.action("bet", float(args[0]))
                else:
                    print("사용법: mybet 100")
            
            # 내 레이즈
            elif cmd == "myraise":
                if args:
                    session.action("raise", float(args[0]))
                else:
                    print("사용법: myraise 200")
            
            # 상태
            elif cmd in ["status", "s"]:
                session.status()
            
            # 분석 (현재 상태 다시 분석)
            elif cmd in ["analyze", "a"]:
                session._show_decision()
            
            # 핸드 종료
            elif cmd == "end":
                session.end_hand()
            
            else:
                print(f"알 수 없는 명령어: {cmd}")
                print("'help'로 명령어 확인")
        
        except KeyboardInterrupt:
            print("\n세션 종료")
            break
        except ValueError as e:
            print(f"입력 오류: {e}")
        except Exception as e:
            print(f"오류: {e}")


if __name__ == "__main__":
    run_live_session()
