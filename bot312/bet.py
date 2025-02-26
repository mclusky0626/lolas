# bet.py

import random

def gamble(user_id, bet_amount, balance, success_rate):
    """도박 기능을 수행합니다."""
    if balance < bet_amount:
        return "잔액이 부족합니다.", balance, success_rate

    if random.random()*100 < success_rate:
        # 도박 성공
        win_amount = bet_amount * 2
        new_balance = balance + win_amount
        new_success_rate = max(0.1, success_rate - 2) # 성공할수록 확률 감소 (최소 10%)
        return f"{win_amount}원을 획득했습니다! 다음 성공 확률```{new_success_rate}%```", new_balance, new_success_rate
    else:
        # 도박 실패
        new_balance = balance - bet_amount
        new_success_rate = 50 # 실패시 확률 초기화
        return f"{bet_amount}원을 잃었습니다.", new_balance, new_success_rate