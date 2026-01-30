"""
포커 솔버 웹 버전
Flask 기반 - 브라우저에서 접속 가능
"""

import random
from flask import Flask, render_template, request, jsonify

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.equity_calculator import calculate_equity
from src.core.pot_odds import PotOddsCalculator
from src.strategy.preflop_charts import PreflopCharts, Position

app = Flask(__name__)
pot_calc = PotOddsCalculator()
charts = PreflopCharts()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        
        hole_cards = data.get('hole_cards', [])
        board = data.get('board', [])
        pot = float(data.get('pot', 100))
        to_call = float(data.get('to_call', 0))
        my_position = data.get('my_position', 'BTN')
        villain_position = data.get('villain_position', 'CO')
        num_players = int(data.get('num_players', 2))
        street = data.get('street', 'preflop')
        
        if len(hole_cards) != 2:
            return jsonify({'error': '홀 카드 2장을 선택하세요'})
        
        # 승률 계산
        equity_result = calculate_equity(
            hole_cards,
            board if board else None,
            num_opponents=num_players - 1,
            iterations=10000
        )
        equity = equity_result['win']
        
        # 분석
        if street == 'preflop':
            result = analyze_preflop(hole_cards, equity, pot, to_call, my_position, villain_position)
        else:
            result = analyze_postflop(hole_cards, board, equity, pot, to_call)
        
        result['equity'] = round(equity, 1)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})


def analyze_preflop(hole_cards, equity, pot, to_call, my_position, villain_position):
    """프리플랍 분석"""
    hand_str = charts.cards_to_hand(hole_cards[0], hole_cards[1])
    
    try:
        position = Position[my_position]
        v_position = Position[villain_position]
    except:
        position = Position.BTN
        v_position = Position.CO
    
    open_range = charts.get_open_range(position)
    in_range = hand_str in open_range
    
    # 3bet 레인지 확인
    threbet_range = charts.get_3bet_range(position, v_position)
    call_range = charts.get_call_range(position, v_position)
    
    tier1 = ["AA", "KK"]
    tier2 = ["QQ", "JJ", "AKs", "AKo"]
    tier3 = ["TT", "99", "AQs", "AQo", "AJs", "KQs"]
    
    detail = f"핸드: {hand_str}\n"
    detail += f"내 포지션: {my_position}\n"
    detail += f"상대 포지션: {villain_position}\n"
    
    if to_call == 0:
        # 오픈 상황
        if in_range:
            return {
                'action': 'RAISE 2.5BB',
                'color': '#27ae60',
                'detail': detail + '\n→ 오픈 레인지 - 레이즈!'
            }
        else:
            return {
                'action': 'FOLD',
                'color': '#e74c3c',
                'detail': detail + '\n→ 오픈 레인지 밖 - 폴드'
            }
    else:
        # 상대 오픈에 대한 대응
        if hand_str in tier1:
            raise_size = to_call * 3
            return {
                'action': f'RAISE ${raise_size:.0f}',
                'color': '#9b59b6',
                'detail': detail + f'\n→ 프리미엄! 3bet/4bet ${raise_size:.0f}'
            }
        
        elif hand_str in tier2:
            if random.random() < 0.75:
                raise_size = to_call * 3
                return {
                    'action': f'RAISE ${raise_size:.0f}',
                    'color': '#9b59b6',
                    'detail': detail + f'\n→ 강한 핸드 - 3bet ${raise_size:.0f}'
                }
            else:
                return {
                    'action': f'CALL ${to_call:.0f}',
                    'color': '#3498db',
                    'detail': detail + f'\n→ 콜 ${to_call:.0f} (트랩)'
                }
        
        elif hand_str in threbet_range:
            raise_size = to_call * 3
            return {
                'action': f'RAISE ${raise_size:.0f}',
                'color': '#9b59b6',
                'detail': detail + f'\n→ 3bet 레인지 - 레이즈 ${raise_size:.0f}'
            }
        
        elif hand_str in call_range:
            return {
                'action': f'CALL ${to_call:.0f}',
                'color': '#3498db',
                'detail': detail + f'\n→ 콜 레인지 - 콜 ${to_call:.0f}'
            }
        
        elif hand_str in tier3 and to_call <= pot * 0.4:
            return {
                'action': f'CALL ${to_call:.0f}',
                'color': '#3498db',
                'detail': detail + f'\n→ 저렴한 콜 - 콜 ${to_call:.0f}'
            }
        
        else:
            return {
                'action': 'FOLD',
                'color': '#e74c3c',
                'detail': detail + '\n→ 레인지 밖 - 폴드'
            }


def analyze_postflop(hole_cards, board, equity, pot, to_call):
    """포스트플랍 분석"""
    detail = f"승률: {equity:.1f}%\n"
    detail += f"팟: ${pot:.0f}\n"
    
    if to_call > 0:
        pot_analysis = pot_calc.analyze(pot, to_call, equity)
        detail += f"콜: ${to_call:.0f}\n"
        detail += f"팟오즈: {pot_analysis.pot_odds:.1f}%\n"
        detail += f"EV: {'+' if pot_analysis.ev >= 0 else ''}{pot_analysis.ev:.2f}\n"
        
        if equity > 70:
            raise_size = pot + to_call
            return {
                'action': f'RAISE ${raise_size:.0f}',
                'color': '#9b59b6',
                'detail': detail + f'\n→ 레이즈 ${raise_size:.0f}'
            }
        
        elif equity > 55:
            if random.random() < 0.7:
                return {
                    'action': f'CALL ${to_call:.0f}',
                    'color': '#27ae60',
                    'detail': detail + f'\n→ 콜 ${to_call:.0f}'
                }
            else:
                raise_size = pot + to_call
                return {
                    'action': f'RAISE ${raise_size:.0f}',
                    'color': '#9b59b6',
                    'detail': detail + f'\n→ 레이즈 ${raise_size:.0f}'
                }
        
        elif pot_analysis.is_profitable_call:
            return {
                'action': f'CALL ${to_call:.0f}',
                'color': '#27ae60',
                'detail': detail + f'\n→ EV+ 콜 ${to_call:.0f}'
            }
        
        elif equity > 25:
            if random.random() < 0.35:
                return {
                    'action': f'CALL ${to_call:.0f}',
                    'color': '#f39c12',
                    'detail': detail + f'\n→ 드로우 콜 ${to_call:.0f}'
                }
            else:
                return {
                    'action': 'FOLD',
                    'color': '#e74c3c',
                    'detail': detail + '\n→ 폴드'
                }
        else:
            return {
                'action': 'FOLD',
                'color': '#e74c3c',
                'detail': detail + '\n→ 폴드'
            }
    
    else:
        # 체크 또는 베팅
        if equity > 70:
            bet_size = pot * 0.67
            return {
                'action': f'BET ${bet_size:.0f}',
                'color': '#27ae60',
                'detail': detail + f'\n→ 베팅 ${bet_size:.0f}'
            }
        
        elif equity > 55:
            if random.random() < 0.6:
                bet_size = pot * 0.5
                return {
                    'action': f'BET ${bet_size:.0f}',
                    'color': '#27ae60',
                    'detail': detail + f'\n→ 베팅 ${bet_size:.0f}'
                }
            else:
                return {
                    'action': 'CHECK',
                    'color': '#7f8c8d',
                    'detail': detail + '\n→ 체크'
                }
        
        elif equity > 35:
            if random.random() < 0.25:
                bet_size = pot * 0.33
                return {
                    'action': f'BET ${bet_size:.0f}',
                    'color': '#3498db',
                    'detail': detail + f'\n→ 베팅 ${bet_size:.0f}'
                }
            else:
                return {
                    'action': 'CHECK',
                    'color': '#7f8c8d',
                    'detail': detail + '\n→ 체크'
                }
        
        else:
            return {
                'action': 'CHECK',
                'color': '#7f8c8d',
                'detail': detail + '\n→ 체크'
            }


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎰 포커 솔버 웹 서버")
    print("="*50)
    print("\n브라우저에서 접속: http://localhost:5000")
    print("다른 기기에서 접속: http://[내IP]:5000")
    print("\nCtrl+C로 종료\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
