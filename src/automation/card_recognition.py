"""
카드 인식 모듈
OpenCV와 EasyOCR을 사용한 포커 카드 인식
"""

import os
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


@dataclass
class CardDetection:
    """인식된 카드 정보"""
    rank: str          # A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
    suit: str          # s, h, d, c
    confidence: float  # 인식 신뢰도 (0-1)
    bbox: Tuple[int, int, int, int] = None  # x, y, w, h
    
    @property
    def card_string(self) -> str:
        """카드 문자열 (예: "As", "Kh")"""
        return f"{self.rank}{self.suit}"
    
    def __str__(self) -> str:
        suit_symbols = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
        return f"{self.rank}{suit_symbols.get(self.suit, self.suit)}"


class CardRecognizer:
    """카드 인식기"""
    
    # 랭크 문자 매핑
    RANK_MAP = {
        'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J', 'T': 'T', '10': 'T',
        '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', 
        '4': '4', '3': '3', '2': '2'
    }
    
    # 슈트 색상 범위 (HSV)
    SUIT_COLORS = {
        'hearts': {  # 빨강
            'lower': np.array([0, 100, 100]),
            'upper': np.array([10, 255, 255])
        },
        'diamonds': {  # 빨강 (하트와 비슷)
            'lower': np.array([0, 100, 100]),
            'upper': np.array([10, 255, 255])
        },
        'clubs': {  # 검정/회색
            'lower': np.array([0, 0, 0]),
            'upper': np.array([180, 50, 80])
        },
        'spades': {  # 검정/회색
            'lower': np.array([0, 0, 0]),
            'upper': np.array([180, 50, 80])
        }
    }
    
    def __init__(self, use_ocr: bool = True, use_template: bool = True):
        """
        Args:
            use_ocr: OCR 사용 여부
            use_template: 템플릿 매칭 사용 여부
        """
        if not CV2_AVAILABLE:
            raise ImportError("opencv-python 필요: pip install opencv-python")
        
        self.use_ocr = use_ocr and OCR_AVAILABLE
        self.use_template = use_template
        
        self.reader = None
        if self.use_ocr:
            try:
                self.reader = easyocr.Reader(['en'], gpu=False)
            except Exception as e:
                print(f"EasyOCR 초기화 실패: {e}")
                self.use_ocr = False
        
        # 템플릿 로드
        self.templates = {}
        if self.use_template:
            self._load_templates()
    
    def _load_templates(self):
        """카드 템플릿 이미지 로드"""
        # 템플릿 디렉토리
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        template_dir = os.path.join(base_dir, "data", "card_templates")
        
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            print(f"템플릿 디렉토리 생성됨: {template_dir}")
            print("카드 템플릿 이미지를 추가하세요 (예: As.png, Kh.png)")
            return
        
        # 템플릿 파일 로드
        for filename in os.listdir(template_dir):
            if filename.endswith(('.png', '.jpg')):
                card_name = filename.split('.')[0]  # "As" from "As.png"
                filepath = os.path.join(template_dir, filename)
                template = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self.templates[card_name] = template
    
    def recognize_card(self, image: np.ndarray) -> Optional[CardDetection]:
        """
        단일 카드 인식
        
        Args:
            image: 카드 이미지 (OpenCV BGR)
        
        Returns:
            CardDetection 또는 None
        """
        if image is None or image.size == 0:
            return None
        
        # 빈 카드 체크 (대부분 흰색이면 빈 슬롯)
        if self._is_empty_card(image):
            return None
        
        # 방법 1: 템플릿 매칭
        if self.use_template and self.templates:
            result = self._recognize_by_template(image)
            if result and result.confidence > 0.7:
                return result
        
        # 방법 2: OCR
        if self.use_ocr:
            result = self._recognize_by_ocr(image)
            if result and result.confidence > 0.5:
                return result
        
        # 방법 3: 색상/모양 기반
        result = self._recognize_by_features(image)
        return result
    
    def recognize_cards(self, images: List[np.ndarray]) -> List[CardDetection]:
        """여러 카드 인식"""
        results = []
        for img in images:
            card = self.recognize_card(img)
            if card:
                results.append(card)
        return results
    
    def _is_empty_card(self, image: np.ndarray) -> bool:
        """빈 카드 슬롯인지 확인"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 평균 밝기가 매우 높거나 (흰색) 매우 낮으면 (검정) 빈 슬롯
        mean_val = np.mean(gray)
        if mean_val > 240 or mean_val < 15:
            return True
        
        # 표준편차가 매우 낮으면 단색 = 빈 슬롯
        std_val = np.std(gray)
        if std_val < 10:
            return True
        
        return False
    
    def _recognize_by_template(self, image: np.ndarray) -> Optional[CardDetection]:
        """템플릿 매칭으로 인식"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        best_match = None
        best_score = 0
        
        for card_name, template in self.templates.items():
            # 크기 조정
            scales = [0.5, 0.75, 1.0, 1.25, 1.5]
            
            for scale in scales:
                resized = cv2.resize(
                    template, 
                    None, 
                    fx=scale, 
                    fy=scale,
                    interpolation=cv2.INTER_AREA
                )
                
                if resized.shape[0] > gray.shape[0] or resized.shape[1] > gray.shape[1]:
                    continue
                
                result = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = card_name
        
        if best_match and best_score > 0.6:
            rank = best_match[0]
            suit = best_match[1] if len(best_match) > 1 else 's'
            return CardDetection(
                rank=rank,
                suit=suit,
                confidence=best_score
            )
        
        return None
    
    def _recognize_by_ocr(self, image: np.ndarray) -> Optional[CardDetection]:
        """OCR로 인식"""
        if not self.reader:
            return None
        
        # 전처리
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # OCR 실행
        try:
            results = self.reader.readtext(enhanced)
        except Exception as e:
            print(f"OCR 오류: {e}")
            return None
        
        if not results:
            return None
        
        # 결과 파싱
        rank = None
        confidence = 0
        
        for (bbox, text, conf) in results:
            text = text.upper().strip()
            
            # 랭크 찾기
            if text in self.RANK_MAP:
                rank = self.RANK_MAP[text]
                confidence = conf
                break
            
            # 부분 매칭
            for key, val in self.RANK_MAP.items():
                if key in text:
                    rank = val
                    confidence = conf * 0.8
                    break
        
        if rank:
            # 슈트 감지 (색상 기반)
            suit = self._detect_suit_by_color(image)
            return CardDetection(rank=rank, suit=suit, confidence=confidence)
        
        return None
    
    def _recognize_by_features(self, image: np.ndarray) -> Optional[CardDetection]:
        """색상/모양 특징으로 인식 (기본 방법)"""
        # 슈트 감지
        suit = self._detect_suit_by_color(image)
        
        # 랭크는 기본값으로 (추가 분석 필요)
        # 실제 구현에서는 윤곽선 분석 등 추가
        
        return CardDetection(
            rank='?',
            suit=suit,
            confidence=0.3
        )
    
    def _detect_suit_by_color(self, image: np.ndarray) -> str:
        """색상으로 슈트 감지"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 빨간색 (하트/다이아) 검출
        red_mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        red_mask = red_mask1 | red_mask2
        
        red_pixels = cv2.countNonZero(red_mask)
        
        # 검은색 (스페이드/클럽) 검출
        black_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 50, 80]))
        black_pixels = cv2.countNonZero(black_mask)
        
        total_pixels = image.shape[0] * image.shape[1]
        red_ratio = red_pixels / total_pixels
        black_ratio = black_pixels / total_pixels
        
        # 빨간색이 더 많으면 하트 (대략적)
        if red_ratio > black_ratio and red_ratio > 0.05:
            return 'h'  # 하트 (또는 다이아)
        else:
            return 's'  # 스페이드 (또는 클럽)
    
    def preprocess_card_image(self, image: np.ndarray) -> np.ndarray:
        """카드 이미지 전처리"""
        # BGR -> 그레이스케일
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 노이즈 제거
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # 이진화
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_card_region(
        self, 
        table_image: np.ndarray,
        region: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """테이블 이미지에서 카드 영역 추출"""
        x, y, w, h = region
        return table_image[y:y+h, x:x+w].copy()
    
    def create_template(self, image: np.ndarray, card_name: str):
        """
        새 템플릿 생성 및 저장
        
        Args:
            image: 카드 이미지
            card_name: 카드 이름 (예: "As", "Kh")
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        template_dir = os.path.join(base_dir, "data", "card_templates")
        
        os.makedirs(template_dir, exist_ok=True)
        
        # 전처리
        processed = self.preprocess_card_image(image)
        
        # 저장
        filepath = os.path.join(template_dir, f"{card_name}.png")
        cv2.imwrite(filepath, processed)
        
        # 메모리에도 로드
        self.templates[card_name] = processed
        
        print(f"템플릿 저장됨: {filepath}")
