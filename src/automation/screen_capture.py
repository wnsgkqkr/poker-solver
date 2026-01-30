"""
화면 캡처 모듈
포커 클라이언트의 화면을 캡처하고 분석
"""

import time
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import numpy as np

try:
    import pyautogui
    import cv2
    from PIL import Image
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False


@dataclass
class Region:
    """화면 영역"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class TableLayout:
    """포커 테이블 레이아웃 정보"""
    # 전체 테이블 영역
    table_region: Region
    
    # 내 홀 카드 영역
    hole_cards_region: Region
    
    # 보드 카드 영역들
    board_regions: List[Region]
    
    # 팟 사이즈 표시 영역
    pot_region: Region
    
    # 버튼 영역들
    fold_button: Region
    call_button: Region
    raise_button: Region
    bet_input: Region
    
    # 플레이어 영역들 (0 = 내 자리, 시계방향)
    player_regions: List[Region]
    
    # 칩/스택 표시 영역들
    stack_regions: List[Region]


class ScreenCapture:
    """화면 캡처 클래스"""
    
    # 포커 클라이언트별 기본 레이아웃
    LAYOUTS = {
        "pokerstars": {
            "table_size": (800, 600),
            "hole_cards": Region(350, 450, 100, 60),
            "board": [
                Region(250, 250, 50, 70),
                Region(310, 250, 50, 70),
                Region(370, 250, 50, 70),
                Region(430, 250, 50, 70),
                Region(490, 250, 50, 70)
            ],
            "pot": Region(350, 200, 100, 30),
            "buttons": {
                "fold": Region(200, 520, 80, 40),
                "call": Region(350, 520, 80, 40),
                "raise": Region(500, 520, 80, 40),
                "bet_input": Region(500, 480, 80, 30)
            }
        },
        "davaopoker": {
            "table_size": (1024, 768),
            "hole_cards": Region(450, 580, 120, 80),
            "board": [
                Region(300, 320, 60, 85),
                Region(370, 320, 60, 85),
                Region(440, 320, 60, 85),
                Region(510, 320, 60, 85),
                Region(580, 320, 60, 85)
            ],
            "pot": Region(450, 260, 120, 35),
            "buttons": {
                "fold": Region(250, 650, 100, 50),
                "call": Region(450, 650, 100, 50),
                "raise": Region(650, 650, 100, 50),
                "bet_input": Region(650, 600, 100, 35)
            }
        }
    }
    
    def __init__(self, client: str = "pokerstars"):
        """
        Args:
            client: 포커 클라이언트 이름 ("pokerstars", "davaopoker")
        """
        if not CAPTURE_AVAILABLE:
            raise ImportError("pyautogui, opencv-python, Pillow 필요")
        
        self.client = client
        self.layout_config = self.LAYOUTS.get(client, self.LAYOUTS["pokerstars"])
        self.window_offset = (0, 0)  # 윈도우 위치 오프셋
        
        # 캡처 설정
        pyautogui.FAILSAFE = True  # 마우스를 왼쪽 상단으로 이동시 중단
    
    def find_poker_window(self) -> Optional[Region]:
        """
        포커 클라이언트 윈도우 찾기
        
        Returns:
            윈도우 영역 또는 None
        """
        try:
            import pygetwindow as gw
            
            # 클라이언트별 윈도우 제목
            titles = {
                "pokerstars": "PokerStars",
                "davaopoker": "Davao"
            }
            
            title_pattern = titles.get(self.client, self.client)
            windows = gw.getWindowsWithTitle(title_pattern)
            
            if windows:
                win = windows[0]
                self.window_offset = (win.left, win.top)
                return Region(win.left, win.top, win.width, win.height)
            
            return None
            
        except ImportError:
            # pygetwindow 없으면 수동 설정 필요
            return None
    
    def set_window_offset(self, x: int, y: int):
        """윈도우 오프셋 수동 설정"""
        self.window_offset = (x, y)
    
    def capture_screen(self, region: Optional[Region] = None) -> np.ndarray:
        """
        화면 캡처
        
        Args:
            region: 캡처할 영역 (None이면 전체 화면)
        
        Returns:
            OpenCV 이미지 (BGR)
        """
        if region:
            # 윈도우 오프셋 적용
            adjusted_region = (
                region.x + self.window_offset[0],
                region.y + self.window_offset[1],
                region.width,
                region.height
            )
            screenshot = pyautogui.screenshot(region=adjusted_region)
        else:
            screenshot = pyautogui.screenshot()
        
        # PIL -> OpenCV 변환
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    
    def capture_hole_cards(self) -> np.ndarray:
        """홀 카드 영역 캡처"""
        region = Region(**{
            'x': self.layout_config['hole_cards'].x,
            'y': self.layout_config['hole_cards'].y,
            'width': self.layout_config['hole_cards'].width,
            'height': self.layout_config['hole_cards'].height
        }) if isinstance(self.layout_config['hole_cards'], Region) else Region(
            *self.layout_config['hole_cards'].tuple
        )
        return self.capture_screen(self.layout_config['hole_cards'])
    
    def capture_board(self) -> List[np.ndarray]:
        """보드 카드들 캡처"""
        images = []
        for region in self.layout_config['board']:
            img = self.capture_screen(region)
            images.append(img)
        return images
    
    def capture_pot(self) -> np.ndarray:
        """팟 사이즈 영역 캡처"""
        return self.capture_screen(self.layout_config['pot'])
    
    def capture_table(self) -> np.ndarray:
        """전체 테이블 캡처"""
        window = self.find_poker_window()
        if window:
            return self.capture_screen(window)
        return self.capture_screen()
    
    def get_button_position(self, button: str) -> Tuple[int, int]:
        """
        버튼 중앙 좌표 반환
        
        Args:
            button: "fold", "call", "raise", "bet_input"
        """
        region = self.layout_config['buttons'].get(button)
        if region:
            x = region.x + self.window_offset[0] + region.width // 2
            y = region.y + self.window_offset[1] + region.height // 2
            return (x, y)
        return (0, 0)
    
    def save_screenshot(self, filename: str, region: Optional[Region] = None):
        """스크린샷 저장 (디버깅용)"""
        img = self.capture_screen(region)
        cv2.imwrite(filename, img)
    
    def calibrate(self) -> Dict:
        """
        레이아웃 캘리브레이션 도구
        사용자가 영역을 클릭해서 설정
        
        Returns:
            캘리브레이션된 레이아웃 설정
        """
        print("캘리브레이션 모드")
        print("각 영역의 왼쪽 상단을 클릭한 후, 오른쪽 하단을 클릭하세요.")
        print("ESC를 누르면 취소됩니다.\n")
        
        calibrated = {}
        
        regions_to_calibrate = [
            ("hole_cards", "홀 카드 영역"),
            ("pot", "팟 사이즈 영역"),
            ("fold_button", "폴드 버튼"),
            ("call_button", "콜 버튼"),
            ("raise_button", "레이즈 버튼")
        ]
        
        for key, description in regions_to_calibrate:
            print(f"\n{description}의 왼쪽 상단을 클릭하세요...")
            time.sleep(0.5)
            
            # 첫 번째 클릭 대기
            start_pos = None
            while start_pos is None:
                try:
                    import keyboard
                    if keyboard.is_pressed('esc'):
                        print("캘리브레이션 취소됨")
                        return calibrated
                except:
                    pass
                
                # 마우스 클릭 감지 (간단한 방법)
                time.sleep(0.1)
                start_pos = pyautogui.position()
                print(f"  시작점: {start_pos}")
            
            print(f"{description}의 오른쪽 하단을 클릭하세요...")
            time.sleep(1)
            
            end_pos = pyautogui.position()
            print(f"  끝점: {end_pos}")
            
            calibrated[key] = Region(
                x=min(start_pos[0], end_pos[0]),
                y=min(start_pos[1], end_pos[1]),
                width=abs(end_pos[0] - start_pos[0]),
                height=abs(end_pos[1] - start_pos[1])
            )
        
        print("\n캘리브레이션 완료!")
        return calibrated
    
    def monitor_loop(
        self, 
        callback, 
        interval: float = 0.5,
        stop_event=None
    ):
        """
        지속적 모니터링 루프
        
        Args:
            callback: 캡처된 이미지를 처리할 콜백 함수
            interval: 캡처 간격 (초)
            stop_event: 중지 이벤트 (threading.Event)
        """
        print(f"모니터링 시작 (간격: {interval}초)")
        
        while True:
            if stop_event and stop_event.is_set():
                break
            
            try:
                # 테이블 캡처
                table_img = self.capture_table()
                hole_img = self.capture_hole_cards()
                board_imgs = self.capture_board()
                pot_img = self.capture_pot()
                
                # 콜백 호출
                callback({
                    'table': table_img,
                    'hole_cards': hole_img,
                    'board': board_imgs,
                    'pot': pot_img,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                print(f"캡처 오류: {e}")
            
            time.sleep(interval)
