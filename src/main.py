"""
Poker GTO Solver - 메인 진입점

Usage:
    python -m src.main           # 메인 GUI 실행
    python -m src.main --overlay # 오버레이만 실행
    python -m src.main --cli     # CLI 모드
"""

import sys
import argparse


def run_main_gui():
    """메인 GUI 실행"""
    from .ui.main_window import run_main_window
    run_main_window()


def run_overlay():
    """오버레이 실행"""
    from .ui.overlay import run_overlay
    run_overlay()


def run_cli():
    """CLI 모드"""
    from .core.equity_calculator import calculate_equity
    from .core.pot_odds import pot_odds, ev
    from .strategy.gto_advisor import GTOAdvisor
    
    print("=" * 50)
    print("🎰 Poker GTO Solver - CLI Mode")
    print("=" * 50)
    
    advisor = GTOAdvisor()
    
    while True:
        print("\n명령어:")
        print("  1. equity <카드1> <카드2> [보드] - 승률 계산")
        print("  2. odds <팟> <콜금액> - 팟 오즈 계산")
        print("  3. advice <카드1> <카드2> [보드] - GTO 추천")
        print("  4. quit - 종료")
        
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd == "quit" or cmd == "q":
                print("종료합니다.")
                break
            
            elif cmd == "equity":
                if len(parts) < 3:
                    print("사용법: equity As Kh [Qd Jc Ts]")
                    continue
                
                hole = [parts[1], parts[2]]
                board = parts[3:] if len(parts) > 3 else None
                
                result = calculate_equity(hole, board, num_opponents=1, iterations=10000)
                print(f"\n홀 카드: {hole[0]} {hole[1]}")
                if board:
                    print(f"보드: {' '.join(board)}")
                print(f"승률: {result['win']:.1f}%")
                print(f"무승부: {result['tie']:.1f}%")
                print(f"패배: {result['lose']:.1f}%")
            
            elif cmd == "odds":
                if len(parts) < 3:
                    print("사용법: odds <팟사이즈> <콜금액>")
                    continue
                
                pot = float(parts[1])
                call = float(parts[2])
                
                odds = pot_odds(pot, call)
                print(f"\n팟 오즈: {odds:.1f}%")
                print(f"필요 승률: {odds:.1f}%")
            
            elif cmd == "advice":
                if len(parts) < 3:
                    print("사용법: advice As Kh [Qd Jc Ts]")
                    continue
                
                hole = [parts[1], parts[2]]
                board = parts[3:] if len(parts) > 3 else None
                
                advice = advisor.get_quick_advice(
                    hole_cards=hole,
                    board=board,
                    position="BTN",
                    pot_size=100,
                    to_call=0,
                    num_opponents=1
                )
                print(advice)
            
            else:
                print(f"알 수 없는 명령어: {cmd}")
        
        except KeyboardInterrupt:
            print("\n종료합니다.")
            break
        except Exception as e:
            print(f"오류: {e}")


def run_live():
    """라이브 세션 CLI 실행"""
    from .live_session import run_live_session
    run_live_session()


def run_live_ui():
    """라이브 세션 UI 실행"""
    from .ui.live_ui import run_live_ui
    run_live_ui()


def run_web():
    """웹 서버 실행"""
    from .web.app import app
    print("\n" + "="*50)
    print("🎰 포커 솔버 웹 서버")
    print("="*50)
    print("\n📱 브라우저에서 접속: http://localhost:5000")
    print("📱 폰/다른 기기: http://[내 IP]:5000")
    print("\nCtrl+C로 종료\n")
    app.run(host='0.0.0.0', port=5000, debug=False)


def main():
    parser = argparse.ArgumentParser(
        description="Poker GTO Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python -m src.main --web        ⭐ 웹 버전 (폰에서 접속 가능!)
  python -m src.main --live       데스크톱 UI
  python -m src.main              메인 GUI 실행
  python -m src.main --overlay    오버레이 UI 실행
  python -m src.main --cli        CLI 모드 실행

⚠️ 학습/연습용 - 리얼머니 게임 실시간 사용 금지!
        """
    )
    
    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="⭐ 웹 서버 (폰/다른 기기에서 접속 가능)"
    )
    
    parser.add_argument(
        "--live", "-l",
        action="store_true",
        help="라이브 솔버 데스크톱 UI"
    )
    
    parser.add_argument(
        "--overlay", "-o",
        action="store_true",
        help="오버레이 UI만 실행"
    )
    
    parser.add_argument(
        "--cli", "-c",
        action="store_true",
        help="CLI 모드로 실행"
    )
    
    parser.add_argument(
        "--live-cli",
        action="store_true",
        help="라이브 CLI 모드"
    )
    
    args = parser.parse_args()
    
    if args.web:
        run_web()
    elif args.live:
        run_live_ui()
    elif args.overlay:
        run_overlay()
    elif args.cli:
        run_cli()
    elif args.live_cli:
        run_live()
    else:
        run_main_gui()


if __name__ == "__main__":
    main()
