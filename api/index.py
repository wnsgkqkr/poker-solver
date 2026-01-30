"""
Vercel Serverless Function
포커 솔버 API
"""

import random
import json
from http.server import BaseHTTPRequestHandler


# 간단한 핸드 평가 (treys 없이)
def get_hand_strength(hand_str):
    """핸드 강도 반환 (1=최강)"""
    rankings = {
        "AA": 1, "KK": 2, "QQ": 3, "JJ": 4, "AKs": 5, "TT": 6, "AKo": 7,
        "AQs": 8, "99": 9, "AJs": 10, "KQs": 11, "88": 12, "ATs": 13,
        "AQo": 14, "KJs": 15, "77": 16, "KTs": 17, "AJo": 18, "QJs": 19,
        "KQo": 20, "66": 21, "A9s": 22, "QTs": 23, "ATo": 24, "55": 25,
        "JTs": 26, "K9s": 27, "A8s": 28, "KJo": 29, "44": 30, "Q9s": 31,
        "A5s": 32, "A7s": 33, "33": 34, "J9s": 35, "QJo": 36, "A4s": 37,
        "A6s": 38, "T9s": 39, "22": 40, "K8s": 41, "A3s": 42, "K7s": 43,
        "A2s": 44, "Q8s": 45, "J8s": 46, "98s": 47, "KTo": 48, "T8s": 49,
        "K6s": 50, "87s": 51, "97s": 52, "QTo": 53, "A9o": 54, "76s": 55,
        "JTo": 56, "K5s": 57, "J7s": 58, "Q7s": 59, "65s": 60
    }
    return rankings.get(hand_str, 80)


def cards_to_hand(card1, card2):
    """두 카드를 핸드 문자열로 변환"""
    rank_order = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10,
                  '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
    
    r1, s1 = card1[0], card1[1]
    r2, s2 = card2[0], card2[1]
    
    if rank_order.get(r1, 0) < rank_order.get(r2, 0):
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    
    if r1 == r2:
        return f"{r1}{r2}"
    elif s1 == s2:
        return f"{r1}{r2}s"
    else:
        return f"{r1}{r2}o"


def estimate_equity(hand_str, board_len, num_opponents):
    """핸드 승률 추정 (간단 버전)"""
    strength = get_hand_strength(hand_str)
    
    # 기본 승률 (핸드 강도 기반)
    base_equity = max(20, 100 - strength * 1.5)
    
    # 상대 수에 따른 조정
    equity = base_equity / (1 + (num_opponents - 1) * 0.15)
    
    # 보드가 있으면 변동 추가
    if board_len > 0:
        equity += random.uniform(-10, 10)
    
    return max(5, min(95, equity))


def analyze_preflop(hole_cards, pot, to_call, my_pos, villain_pos, num_players, eff_stack):
    """프리플랍 분석 (스택 사이즈 고려)"""
    hand_str = cards_to_hand(hole_cards[0], hole_cards[1])
    equity = estimate_equity(hand_str, 0, num_players - 1)
    
    tier1 = ["AA", "KK"]
    tier2 = ["QQ", "JJ", "AKs", "AKo"]
    tier3 = ["TT", "99", "AQs", "AQo", "AJs", "KQs"]
    tier4 = ["88", "77", "ATs", "AJo", "KJs", "KQo", "QJs", "JTs"]
    tier5 = ["66", "55", "A9s", "KTs", "QTs", "T9s", "98s", "87s", "76s", "65s", "A8s", "A7s", "A6s", "A5s", "K9s"]
    
    # 스택 깊이 분류
    if eff_stack <= 25:
        stack_type = "short"
    elif eff_stack <= 50:
        stack_type = "mid"
    else:
        stack_type = "deep"
    
    detail = f"핸드: {hand_str}\n스택: {eff_stack}bb ({stack_type})\n내 포지션: {my_pos}\n상대 포지션: {villain_pos}\n승률: {equity:.0f}%\n"
    
    # 숏스택 전략 (25bb 이하) - Push/Fold
    if stack_type == "short":
        push_range = tier1 + tier2 + tier3 + ["A9s", "A8s", "A7s", "A5s", "KTs", "QTs", "JTs", "44", "33", "22"]
        if to_call == 0:
            if hand_str in push_range:
                return {'action': f'ALL-IN {eff_stack}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 푸시 {eff_stack}bb', 'equity': round(equity, 1)}
            else:
                return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
        else:
            call_range = tier1 + tier2 + ["TT", "99", "AQs", "AQo"]
            if to_call >= eff_stack * 0.5:  # 절반 이상이면 올인 콜
                if hand_str in call_range:
                    return {'action': f'ALL-IN {eff_stack}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인 콜', 'equity': round(equity, 1)}
            elif hand_str in tier1 + tier2:
                return {'action': f'ALL-IN {eff_stack}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인', 'equity': round(equity, 1)}
            return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
    
    open_range = tier1 + tier2 + tier3 + tier4 + tier5
    
    if to_call == 0:
        # 오픈 레이즈
        if hand_str in open_range:
            open_size = 2.5 if stack_type == "deep" else 2.2
            return {'action': f'RAISE {open_size}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 오픈 {open_size}bb', 'equity': round(equity, 1)}
        else:
            return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
    else:
        # vs 레이즈
        if hand_str in tier1:
            raise_size = min(to_call * 3, eff_stack)
            if raise_size >= eff_stack * 0.9:
                return {'action': f'ALL-IN {eff_stack}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인', 'equity': round(equity, 1)}
            return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 4bet {raise_size:.1f}bb', 'equity': round(equity, 1)}
        
        elif hand_str in tier2:
            if stack_type == "mid":  # 미들스택은 3bet/fold
                raise_size = min(to_call * 3, eff_stack)
                if raise_size >= eff_stack * 0.9:
                    return {'action': f'ALL-IN {eff_stack}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인', 'equity': round(equity, 1)}
                return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 3bet {raise_size:.1f}bb', 'equity': round(equity, 1)}
            else:  # 딥스택은 콜도 OK
                if random.random() < 0.7:
                    raise_size = to_call * 3
                    return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 3bet {raise_size:.1f}bb', 'equity': round(equity, 1)}
                return {'action': f'CALL {to_call}bb', 'color': '#3498db', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
        
        elif hand_str in tier3:
            if stack_type == "deep" and to_call <= 3:  # 딥스택 + 작은 레이즈
                if random.random() < 0.5:
                    return {'action': f'CALL {to_call}bb', 'color': '#3498db', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
                raise_size = to_call * 3
                return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 3bet {raise_size:.1f}bb', 'equity': round(equity, 1)}
            elif to_call <= pot * 0.3:
                return {'action': f'CALL {to_call}bb', 'color': '#3498db', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
            return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
        
        elif hand_str in tier4 + tier5:
            # 스펙 핸드 - 딥스택 + 좋은 오즈에서만 콜
            if stack_type == "deep" and to_call <= 3:
                return {'action': f'CALL {to_call}bb', 'color': '#3498db', 'detail': detail + f'\n→ 콜 {to_call}bb (셋마이닝/드로우)', 'equity': round(equity, 1)}
            return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
        
        return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}


def analyze_postflop(hole_cards, board, pot, to_call, num_players, eff_stack):
    """포스트플랍 분석 (SPR 고려)"""
    hand_str = cards_to_hand(hole_cards[0], hole_cards[1])
    equity = estimate_equity(hand_str, len(board), num_players - 1)
    
    # SPR (Stack to Pot Ratio) 계산
    remaining_stack = eff_stack - pot  # 대략적 남은 스택
    spr = remaining_stack / pot if pot > 0 else 10
    
    if spr <= 2:
        spr_type = "low"
    elif spr <= 6:
        spr_type = "mid"
    else:
        spr_type = "high"
    
    detail = f"승률: {equity:.0f}%\n스택: {eff_stack}bb\n팟: {pot}bb\nSPR: {spr:.1f} ({spr_type})\n"
    
    if to_call > 0:
        pot_odds = to_call / (pot + to_call) * 100
        ev = (equity/100 * (pot + to_call)) - ((1 - equity/100) * to_call)
        is_profitable = equity > pot_odds
        
        detail += f"콜: {to_call}bb\n팟오즈: {pot_odds:.0f}%\nEV: {'+' if ev >= 0 else ''}{ev:.1f}bb\n"
        
        # 낮은 SPR - 커밋 or 폴드
        if spr_type == "low":
            if equity > 45:
                return {'action': f'ALL-IN {remaining_stack:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인 (Low SPR)', 'equity': round(equity, 1)}
            elif is_profitable:
                return {'action': f'CALL {to_call}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
            return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
        
        if equity > 70:
            raise_size = min(pot + to_call, remaining_stack)
            if raise_size >= remaining_stack * 0.9:
                return {'action': f'ALL-IN {remaining_stack:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인', 'equity': round(equity, 1)}
            return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 레이즈 {raise_size:.1f}bb', 'equity': round(equity, 1)}
        elif equity > 55:
            if random.random() < 0.7:
                return {'action': f'CALL {to_call}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
            else:
                raise_size = pot + to_call
                return {'action': f'RAISE {raise_size:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 레이즈 {raise_size:.1f}bb', 'equity': round(equity, 1)}
        elif is_profitable:
            return {'action': f'CALL {to_call}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 콜 {to_call}bb', 'equity': round(equity, 1)}
        elif equity > 25 and spr_type == "high":  # 높은 SPR에서만 드로우 콜
            if random.random() < 0.35:
                return {'action': f'CALL {to_call}bb', 'color': '#f39c12', 'detail': detail + f'\n→ 드로우 콜 (Implied Odds)', 'equity': round(equity, 1)}
        return {'action': 'FOLD', 'color': '#e74c3c', 'detail': detail + '\n→ 폴드', 'equity': round(equity, 1)}
    else:
        # 낮은 SPR - 올인 or 체크
        if spr_type == "low" and equity > 50:
            return {'action': f'ALL-IN {remaining_stack:.1f}bb', 'color': '#9b59b6', 'detail': detail + f'\n→ 올인 (Low SPR)', 'equity': round(equity, 1)}
        
        if equity > 70:
            bet_size = pot * 0.67
            return {'action': f'BET {bet_size:.1f}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 베팅 {bet_size:.1f}bb', 'equity': round(equity, 1)}
        elif equity > 55:
            if random.random() < 0.6:
                bet_size = pot * 0.5
                return {'action': f'BET {bet_size:.1f}bb', 'color': '#27ae60', 'detail': detail + f'\n→ 베팅 {bet_size:.1f}bb', 'equity': round(equity, 1)}
            return {'action': 'CHECK', 'color': '#7f8c8d', 'detail': detail + '\n→ 체크', 'equity': round(equity, 1)}
        elif equity > 35:
            if random.random() < 0.25:
                bet_size = pot * 0.33
                return {'action': f'BET {bet_size:.1f}bb', 'color': '#3498db', 'detail': detail + f'\n→ 베팅 {bet_size:.1f}bb (블러프)', 'equity': round(equity, 1)}
            return {'action': 'CHECK', 'color': '#7f8c8d', 'detail': detail + '\n→ 체크', 'equity': round(equity, 1)}
        return {'action': 'CHECK', 'color': '#7f8c8d', 'detail': detail + '\n→ 체크', 'equity': round(equity, 1)}


# HTML 템플릿
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎰 포커 솔버</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 10px; }
        .container { max-width: 500px; margin: 0 auto; }
        .warning { background: #c0392b; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-size: 12px; }
        h1 { text-align: center; margin-bottom: 15px; font-size: 24px; }
        .section { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 15px; margin-bottom: 12px; }
        .section-title { font-size: 14px; color: #bbb; margin-bottom: 10px; }
        .row { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
        .col { flex: 1; min-width: 80px; }
        label { display: block; font-size: 12px; color: #aaa; margin-bottom: 4px; }
        select, input { width: 100%; padding: 10px; border: none; border-radius: 8px; background: rgba(255,255,255,0.15); color: #fff; font-size: 16px; }
        select option { background: #2c3e50; color: #fff; }
        .card-selector { display: flex; gap: 8px; }
        .card-selector select { flex: 1; }
        .street-btns { display: flex; gap: 5px; }
        .street-btn { flex: 1; padding: 10px 5px; border: none; border-radius: 8px; background: rgba(255,255,255,0.1); color: #fff; cursor: pointer; font-size: 13px; }
        .street-btn.active { background: #3498db; }
        .quick-bets { display: flex; gap: 5px; margin-top: 8px; }
        .quick-bet { flex: 1; padding: 8px; border: none; border-radius: 6px; background: rgba(255,255,255,0.1); color: #fff; cursor: pointer; font-size: 12px; }
        .analyze-btn { width: 100%; padding: 15px; border: none; border-radius: 10px; background: #27ae60; color: #fff; font-size: 18px; font-weight: bold; cursor: pointer; margin-bottom: 15px; }
        .result { text-align: center; }
        .equity { font-size: 20px; margin-bottom: 10px; }
        .action { font-size: 28px; font-weight: bold; padding: 20px; border-radius: 12px; margin-bottom: 10px; }
        .detail { background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-size: 13px; white-space: pre-line; text-align: left; }
        .board-cards { display: flex; gap: 5px; }
        .board-card { flex: 1; }
        .board-card select { padding: 8px 4px; font-size: 14px; }
        .reset-btn { width: 100%; padding: 12px; border: none; border-radius: 8px; background: #3498db; color: #fff; cursor: pointer; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="warning">⚠️ 학습용 - 리얼머니 게임 실시간 사용 금지</div>
        <h1>🎰 포커 솔버</h1>
        
        <div class="section">
            <div class="section-title">🃏 내 핸드</div>
            <div class="row">
                <div class="col">
                    <label>포지션</label>
                    <select id="myPosition">
                        <option value="BTN">BTN</option><option value="CO">CO</option><option value="HJ">HJ</option>
                        <option value="UTG">UTG</option><option value="SB">SB</option><option value="BB">BB</option>
                    </select>
                </div>
                <div class="col">
                    <label>카드 1</label>
                    <div class="card-selector">
                        <select id="card1Rank"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select>
                        <select id="card1Suit"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select>
                    </div>
                </div>
                <div class="col">
                    <label>카드 2</label>
                    <div class="card-selector">
                        <select id="card2Rank"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select>
                        <select id="card2Suit"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">👤 상대</div>
            <div class="row">
                <div class="col">
                    <label>상대 포지션</label>
                    <select id="villainPosition">
                        <option value="UTG">UTG</option><option value="HJ">HJ</option><option value="CO" selected>CO</option>
                        <option value="BTN">BTN</option><option value="SB">SB</option><option value="BB">BB</option>
                    </select>
                </div>
                <div class="col">
                    <label>플레이어 수</label>
                    <select id="numPlayers"><option value="2">2명</option><option value="3">3명</option><option value="4">4명</option><option value="5">5명</option><option value="6" selected>6명</option></select>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📍 스트릿</div>
            <div class="street-btns">
                <button class="street-btn active" onclick="setStreet('preflop')">프리플랍</button>
                <button class="street-btn" onclick="setStreet('flop')">플랍</button>
                <button class="street-btn" onclick="setStreet('turn')">턴</button>
                <button class="street-btn" onclick="setStreet('river')">리버</button>
            </div>
        </div>
        
        <div class="section" id="boardSection" style="display:none;">
            <div class="section-title">🎴 보드</div>
            <div class="board-cards">
                <div class="board-card"><select id="b1r"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select><select id="b1s"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select></div>
                <div class="board-card"><select id="b2r"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select><select id="b2s"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select></div>
                <div class="board-card"><select id="b3r"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select><select id="b3s"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select></div>
                <div class="board-card" id="turnCard" style="display:none;"><select id="b4r"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select><select id="b4s"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select></div>
                <div class="board-card" id="riverCard" style="display:none;"><select id="b5r"><option value="">-</option><option>A</option><option>K</option><option>Q</option><option>J</option><option>T</option><option>9</option><option>8</option><option>7</option><option>6</option><option>5</option><option>4</option><option>3</option><option>2</option></select><select id="b5s"><option value="">-</option><option value="s">♠</option><option value="h">♥</option><option value="d">♦</option><option value="c">♣</option></select></div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">💰 스택 & 팟</div>
            <div class="row">
                <div class="col"><label>Eff. Stack (BB)</label><input type="number" id="effStack" value="100" min="1"></div>
                <div class="col"><label>팟 (BB)</label><input type="number" id="pot" value="2.5" min="0" step="0.5"></div>
                <div class="col"><label>상대 베팅</label><input type="number" id="toCall" value="0" min="0" step="0.5"></div>
            </div>
            <div class="quick-bets">
                <button class="quick-bet" onclick="quickBet(0.33)">1/3</button>
                <button class="quick-bet" onclick="quickBet(0.5)">1/2</button>
                <button class="quick-bet" onclick="quickBet(0.67)">2/3</button>
                <button class="quick-bet" onclick="quickBet(1.0)">팟</button>
            </div>
            <div class="quick-bets" style="margin-top:5px;">
                <button class="quick-bet" onclick="setStack(20)">20bb</button>
                <button class="quick-bet" onclick="setStack(50)">50bb</button>
                <button class="quick-bet" onclick="setStack(100)">100bb</button>
                <button class="quick-bet" onclick="setStack(200)">200bb</button>
            </div>
        </div>
        
        <button class="analyze-btn" onclick="analyze()">🔍 분석</button>
        
        <div class="section result" id="resultSection" style="display:none;">
            <div class="equity" id="equity">승률: --%</div>
            <div class="action" id="action">--</div>
            <div class="detail" id="detail"></div>
        </div>
        
        <button class="reset-btn" onclick="resetAll()">🔄 새 핸드</button>
    </div>
    
    <script>
        let currentStreet = 'preflop';
        
        function setStreet(street) {
            currentStreet = street;
            document.querySelectorAll('.street-btn').forEach((btn,i) => {
                btn.classList.remove('active');
                if((street==='preflop'&&i===0)||(street==='flop'&&i===1)||(street==='turn'&&i===2)||(street==='river'&&i===3)) btn.classList.add('active');
            });
            document.getElementById('boardSection').style.display = street === 'preflop' ? 'none' : 'block';
            document.getElementById('turnCard').style.display = (street === 'turn' || street === 'river') ? 'block' : 'none';
            document.getElementById('riverCard').style.display = street === 'river' ? 'block' : 'none';
        }
        
        function quickBet(ratio) {
            document.getElementById('toCall').value = ((parseFloat(document.getElementById('pot').value)||0) * ratio).toFixed(1);
        }
        
        function setStack(bb) {
            document.getElementById('effStack').value = bb;
        }
        
        function getCard(rid, sid) {
            const r = document.getElementById(rid).value, s = document.getElementById(sid).value;
            return (r && s) ? r + s : null;
        }
        
        function analyze() {
            const c1 = getCard('card1Rank','card1Suit'), c2 = getCard('card2Rank','card2Suit');
            if (!c1 || !c2) { alert('홀 카드를 선택하세요'); return; }
            
            const board = [];
            if (currentStreet !== 'preflop') {
                for (let i = 1; i <= 5; i++) {
                    if (i <= 3 || (i === 4 && (currentStreet === 'turn' || currentStreet === 'river')) || (i === 5 && currentStreet === 'river')) {
                        const card = getCard('b'+i+'r', 'b'+i+'s');
                        if (card) board.push(card);
                    }
                }
            }
            
            fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    hole_cards: [c1, c2], board: board,
                    eff_stack: parseFloat(document.getElementById('effStack').value) || 100,
                    pot: parseFloat(document.getElementById('pot').value) || 2.5,
                    to_call: parseFloat(document.getElementById('toCall').value) || 0,
                    my_position: document.getElementById('myPosition').value,
                    villain_position: document.getElementById('villainPosition').value,
                    num_players: parseInt(document.getElementById('numPlayers').value),
                    street: currentStreet
                })
            })
            .then(res => res.json())
            .then(result => {
                if (result.error) { alert(result.error); return; }
                document.getElementById('resultSection').style.display = 'block';
                document.getElementById('equity').textContent = '승률: ' + result.equity + '%';
                document.getElementById('action').textContent = result.action;
                document.getElementById('action').style.background = result.color;
                document.getElementById('detail').textContent = result.detail;
            });
        }
        
        function resetAll() {
            ['card1Rank','card1Suit','card2Rank','card2Suit'].forEach(id => document.getElementById(id).selectedIndex = 0);
            for (let i = 1; i <= 5; i++) { document.getElementById('b'+i+'r').selectedIndex = 0; document.getElementById('b'+i+'s').selectedIndex = 0; }
            document.getElementById('effStack').value = 100;
            document.getElementById('pot').value = 2.5;
            document.getElementById('toCall').value = 0;
            setStreet('preflop');
            document.getElementById('resultSection').style.display = 'none';
        }
    </script>
</body>
</html>'''


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_TEMPLATE.encode())
    
    def do_POST(self):
        if self.path == '/api/analyze':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            try:
                hole_cards = data.get('hole_cards', [])
                board = data.get('board', [])
                eff_stack = float(data.get('eff_stack', 100))
                pot = float(data.get('pot', 2.5))
                to_call = float(data.get('to_call', 0))
                my_pos = data.get('my_position', 'BTN')
                villain_pos = data.get('villain_position', 'CO')
                num_players = int(data.get('num_players', 6))
                street = data.get('street', 'preflop')
                
                if len(hole_cards) != 2:
                    result = {'error': '홀 카드 2장을 선택하세요'}
                elif street == 'preflop':
                    result = analyze_preflop(hole_cards, pot, to_call, my_pos, villain_pos, num_players, eff_stack)
                else:
                    result = analyze_postflop(hole_cards, board, pot, to_call, num_players, eff_stack)
            except Exception as e:
                result = {'error': str(e)}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()
