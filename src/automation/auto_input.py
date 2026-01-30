"""
자동 입력 모듈
마우스/키보드 자동화로 포커 클라이언트 조작

⚠️ 주의: 대부분의 온라인 포커 사이트는 봇/자동화를 금지합니다.
         플레이머니/연습 모드에서만 사용하세요!
"""

import time
import random
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import pyautogui
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False


class PokerAction(Enum):
    """포커 액션 타입"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class ActionConfig:
    """액션 설정"""
    action: PokerAction
    amount: Optional[float] = None  # BET/RAISE 금액
    delay_before: float = 0.3       # 액션 전 대기 (초)
    delay_after: float = 0.2        # 액션 후 대기 (초)
    randomize_delay: bool = True    # 딜레이 랜덤화


class PokerAutomation:
    """포커 자동화 클래스"""
    
    def __init__(
        self,
        client: str = "pokerstars",
        human_like: bool = True,
        safe_mode: bool = True
    ):
        """
        Args:
            client: 포커 클라이언트 이름
            human_like: 인간적인 동작 시뮬레이션
            safe_mode: 안전 모드 (확인 프롬프트 등)
        """
        if not AUTOMATION_AVAILABLE:
            raise ImportError("pyautogui 필요: pip install pyautogui")
        
        self.client = client
        self.human_like = human_like
        self.safe_mode = safe_mode
        
        # 안전 설정
        pyautogui.FAILSAFE = True  # 왼쪽 상단으로 마우스 이동시 중단
        pyautogui.PAUSE = 0.1     # 모든 pyautogui 명령 후 대기
        
        # 버튼 좌표 (클라이언트별로 다름, 캘리브레이션 필요)
        self.button_coords = self._get_default_coords(client)
        
        # 콜백 함수들
        self.on_action_start: Optional[Callable] = None
        self.on_action_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    def _get_default_coords(self, client: str) -> dict:
        """클라이언트별 기본 버튼 좌표"""
        configs = {
            "pokerstars": {
                "fold": (350, 540),
                "check": (500, 540),
                "call": (500, 540),
                "bet": (650, 540),
                "raise": (650, 540),
                "bet_input": (650, 500),
                "all_in": (750, 540),
                "confirm": (500, 540)
            },
            "davaopoker": {
                "fold": (300, 670),
                "check": (500, 670),
                "call": (500, 670),
                "bet": (700, 670),
                "raise": (700, 670),
                "bet_input": (700, 620),
                "all_in": (800, 670),
                "confirm": (500, 670)
            }
        }
        return configs.get(client, configs["pokerstars"])
    
    def set_button_coords(self, coords: dict):
        """버튼 좌표 수동 설정"""
        self.button_coords.update(coords)
    
    def calibrate_button(self, button_name: str) -> Tuple[int, int]:
        """
        버튼 위치 캘리브레이션
        
        사용자가 버튼을 클릭하면 그 위치를 저장
        """
        print(f"'{button_name}' 버튼을 클릭하세요...")
        print("(현재 마우스 위치가 3초 후에 저장됩니다)")
        
        time.sleep(3)
        pos = pyautogui.position()
        
        self.button_coords[button_name] = (pos.x, pos.y)
        print(f"저장됨: {button_name} = {pos}")
        
        return pos
    
    def _humanize_delay(self, base_delay: float) -> float:
        """인간적인 딜레이 추가"""
        if self.human_like:
            # ±30% 랜덤 변동
            variation = base_delay * 0.3
            return base_delay + random.uniform(-variation, variation)
        return base_delay
    
    def _humanize_movement(
        self, 
        x: int, 
        y: int, 
        duration: float = 0.3
    ):
        """인간적인 마우스 이동"""
        if self.human_like:
            # 약간의 랜덤 오프셋
            x += random.randint(-3, 3)
            y += random.randint(-3, 3)
            
            # 이동 시간 변동
            duration = self._humanize_delay(duration)
        
        pyautogui.moveTo(x, y, duration=duration)
    
    def click_button(
        self, 
        button_name: str,
        delay_before: float = 0.3,
        delay_after: float = 0.2
    ) -> bool:
        """
        버튼 클릭
        
        Args:
            button_name: 버튼 이름 (fold, call, raise 등)
            delay_before: 클릭 전 대기
            delay_after: 클릭 후 대기
        
        Returns:
            성공 여부
        """
        coords = self.button_coords.get(button_name)
        if not coords:
            if self.on_error:
                self.on_error(f"Unknown button: {button_name}")
            return False
        
        try:
            # 콜백
            if self.on_action_start:
                self.on_action_start(button_name)
            
            # 대기
            time.sleep(self._humanize_delay(delay_before))
            
            # 마우스 이동
            self._humanize_movement(coords[0], coords[1])
            
            # 클릭
            pyautogui.click()
            
            # 대기
            time.sleep(self._humanize_delay(delay_after))
            
            # 콜백
            if self.on_action_complete:
                self.on_action_complete(button_name)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def enter_amount(
        self, 
        amount: float,
        clear_first: bool = True
    ) -> bool:
        """
        베팅 금액 입력
        
        Args:
            amount: 금액
            clear_first: 기존 입력 지우기
        """
        try:
            # 입력 필드 클릭
            self.click_button("bet_input")
            
            time.sleep(0.1)
            
            # 기존 내용 지우기
            if clear_first:
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.05)
            
            # 금액 입력
            amount_str = str(int(amount))
            
            if self.human_like:
                # 한 글자씩 입력 (인간처럼)
                for char in amount_str:
                    pyautogui.press(char)
                    time.sleep(random.uniform(0.05, 0.15))
            else:
                pyautogui.typewrite(amount_str)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def execute_action(self, config: ActionConfig) -> bool:
        """
        액션 실행
        
        Args:
            config: 액션 설정
        """
        if self.safe_mode:
            print(f"\n⚠️ 액션 실행: {config.action.value}")
            if config.amount:
                print(f"   금액: {config.amount}")
            confirm = input("실행하시겠습니까? (y/n): ")
            if confirm.lower() != 'y':
                print("취소됨")
                return False
        
        action = config.action
        delay_before = self._humanize_delay(config.delay_before) if config.randomize_delay else config.delay_before
        delay_after = self._humanize_delay(config.delay_after) if config.randomize_delay else config.delay_after
        
        if action == PokerAction.FOLD:
            return self.click_button("fold", delay_before, delay_after)
        
        elif action == PokerAction.CHECK:
            return self.click_button("check", delay_before, delay_after)
        
        elif action == PokerAction.CALL:
            return self.click_button("call", delay_before, delay_after)
        
        elif action == PokerAction.BET:
            if config.amount:
                if not self.enter_amount(config.amount):
                    return False
            return self.click_button("confirm", delay_before, delay_after)
        
        elif action == PokerAction.RAISE:
            if config.amount:
                if not self.enter_amount(config.amount):
                    return False
            return self.click_button("confirm", delay_before, delay_after)
        
        elif action == PokerAction.ALL_IN:
            return self.click_button("all_in", delay_before, delay_after)
        
        return False
    
    # 편의 메서드
    def fold(self) -> bool:
        """폴드"""
        return self.execute_action(ActionConfig(PokerAction.FOLD))
    
    def check(self) -> bool:
        """체크"""
        return self.execute_action(ActionConfig(PokerAction.CHECK))
    
    def call(self) -> bool:
        """콜"""
        return self.execute_action(ActionConfig(PokerAction.CALL))
    
    def bet(self, amount: float) -> bool:
        """베팅"""
        return self.execute_action(ActionConfig(PokerAction.BET, amount=amount))
    
    def raise_to(self, amount: float) -> bool:
        """레이즈"""
        return self.execute_action(ActionConfig(PokerAction.RAISE, amount=amount))
    
    def all_in(self) -> bool:
        """올인"""
        return self.execute_action(ActionConfig(PokerAction.ALL_IN))
    
    def take_screenshot(self, filename: str = "poker_screenshot.png"):
        """스크린샷 저장 (디버깅용)"""
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        print(f"스크린샷 저장됨: {filename}")
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """현재 마우스 위치 반환"""
        pos = pyautogui.position()
        return (pos.x, pos.y)
    
    def interactive_calibration(self):
        """대화형 캘리브레이션"""
        print("\n=== 포커 자동화 캘리브레이션 ===")
        print("각 버튼의 위치를 설정합니다.")
        print("마우스를 버튼 위에 올리고 Enter를 누르세요.\n")
        
        buttons = ["fold", "check", "call", "bet_input", "raise", "all_in", "confirm"]
        
        for button in buttons:
            input(f"'{button}' 버튼 위에 마우스를 올리고 Enter를 누르세요...")
            pos = self.get_mouse_position()
            self.button_coords[button] = pos
            print(f"  → {button}: {pos}")
        
        print("\n캘리브레이션 완료!")
        print("설정된 좌표:")
        for button, coords in self.button_coords.items():
            print(f"  {button}: {coords}")
        
        return self.button_coords


class PokerBot:
    """
    포커 봇 (자동 플레이)
    
    ⚠️ 경고: 실제 리얼머니 게임에서 사용하지 마세요!
             계정 정지 및 자금 몰수 위험이 있습니다.
    """
    
    def __init__(
        self,
        automation: PokerAutomation,
        advisor,  # GTOAdvisor
        screen_capture,  # ScreenCapture
        card_recognizer  # CardRecognizer
    ):
        self.automation = automation
        self.advisor = advisor
        self.capture = screen_capture
        self.recognizer = card_recognizer
        
        self.running = False
        self.action_count = 0
    
    def analyze_current_state(self) -> dict:
        """현재 게임 상태 분석"""
        # 화면 캡처
        hole_img = self.capture.capture_hole_cards()
        board_imgs = self.capture.capture_board()
        
        # 카드 인식
        hole_cards = []
        hole_detections = self.recognizer.recognize_cards([hole_img])
        for det in hole_detections:
            if det:
                hole_cards.append(det.card_string)
        
        board_cards = []
        board_detections = self.recognizer.recognize_cards(board_imgs)
        for det in board_detections:
            if det:
                board_cards.append(det.card_string)
        
        return {
            "hole_cards": hole_cards,
            "board": board_cards
        }
    
    def get_recommended_action(self, state: dict):
        """추천 액션 받기"""
        if len(state["hole_cards"]) != 2:
            return None
        
        return self.advisor.get_quick_advice(
            hole_cards=state["hole_cards"],
            board=state["board"] if state["board"] else None,
            position="BTN",  # 기본값
            pot_size=100,
            to_call=0,
            num_opponents=1
        )
    
    def execute_recommendation(self, recommendation) -> bool:
        """추천 액션 실행"""
        action_str = recommendation.primary_action.value
        
        if "fold" in action_str:
            return self.automation.fold()
        elif "check" in action_str:
            return self.automation.check()
        elif "call" in action_str:
            return self.automation.call()
        elif "bet" in action_str or "raise" in action_str:
            amount = recommendation.bet_sizing or 100
            return self.automation.bet(amount)
        elif "all_in" in action_str:
            return self.automation.all_in()
        
        return False
    
    def run_once(self) -> bool:
        """한 번 실행 (분석 → 추천 → 실행)"""
        print("\n--- 분석 중 ---")
        
        # 상태 분석
        state = self.analyze_current_state()
        print(f"홀 카드: {state['hole_cards']}")
        print(f"보드: {state['board']}")
        
        if len(state["hole_cards"]) != 2:
            print("홀 카드 인식 실패")
            return False
        
        # 추천 받기
        recommendation = self.get_recommended_action(state)
        if not recommendation:
            print("추천 생성 실패")
            return False
        
        print(f"\n추천 액션: {recommendation}")
        
        # 실행
        success = self.execute_recommendation(recommendation)
        self.action_count += 1
        
        return success
    
    def start(self, interval: float = 2.0):
        """자동 실행 시작"""
        print("\n⚠️ 경고: 자동 플레이 모드 시작")
        print("Ctrl+C로 중지하세요.\n")
        
        self.running = True
        
        try:
            while self.running:
                self.run_once()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n중지됨")
            self.running = False
    
    def stop(self):
        """자동 실행 중지"""
        self.running = False
