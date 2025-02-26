# jungbo.py

import random
import sqlite3
import asyncio
from datetime import datetime, timedelta

# 데이터베이스 연결
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

# 주식 테이블 생성 (이미 존재하면 무시)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        code TEXT PRIMARY KEY,
        name TEXT,
        price INTEGER,
        volatility INTEGER,
        previous_price INTEGER
    )
''')
conn.commit()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stocks (
        user_id INTEGER,
        stock_code TEXT,
        quantity INTEGER,
        average_price INTEGER,
        PRIMARY KEY (user_id, stock_code)
    )
''')
conn.commit()

# 초기 주식 데이터 (종목 코드, 종목명, 현재가, 변동폭)
initial_stocks = {
    'SAMSUNG': {'name': '삼성', 'price': 60000, 'volatility': 500, 'previous_price': 60000},
    'NOKIA': {'name': '노키아', 'price': 5000, 'volatility': 200, 'previous_price': 5000},
    'RIOT': {'name': '라이엇게임즈', 'price': 80000, 'volatility': 10000, 'previous_price': 80000},
    'HANJIN': {'name': '한진유통', 'price': 10000, 'volatility': 100, 'previous_price': 10000},
    'BBEOHEO': {'name': '쁘허', 'price': 30000, 'volatility': 2000, 'previous_price': 30000},
    'VALVE': {'name': 'Valve', 'price': 20000, 'volatility': 300, 'previous_price': 20000},
}

# 초기 주식 데이터 삽입
for code, data in initial_stocks.items():
    cursor.execute('''
        INSERT OR REPLACE INTO stocks (code, name, price, volatility, previous_price)
        VALUES (?, ?, ?, ?, ?)
    ''', (code, data['name'], data['price'], data['volatility'], data['previous_price']))
conn.commit()

# 데이터베이스에서 주식 데이터 로드
def load_stocks_from_db():
    cursor.execute('SELECT * FROM stocks')
    rows = cursor.fetchall()
    stocks = {}
    for row in rows:
        stocks[row[0]] = {
            'name': row[1],
            'price': row[2],
            'volatility': row[3],
            'previous_price': row[4]
        }
    return stocks

stocks = load_stocks_from_db()

async def update_stock_prices():
    """주식 가격을 랜덤하게 업데이트하고 30초 전 가격을 저장합니다."""
    global stocks
    while True:
        for stock_code, stock_data in stocks.items():
            stock_data['previous_price'] = stock_data['price']  # 현재가를 30초 전 가격으로 저장
            # Valve 주식은 60% 확률로 상승
            if stock_code == 'VALVE' and random.random() < 0.7:
                change = random.randint(0, stock_data['volatility']) # 상승만
            else:
                change = random.randint(-stock_data['volatility'], stock_data['volatility'])
            stock_data['price'] += change
            if stock_data['price'] < 0:
                stock_data['price'] = 0
            # 데이터베이스 업데이트
            cursor.execute('''
                UPDATE stocks SET price = ?, previous_price = ? WHERE code = ?
            ''', (stock_data['price'], stock_data['previous_price'], stock_code))
        conn.commit()
        # stocks 딕셔너리 업데이트
        stocks = load_stocks_from_db()
        await asyncio.sleep(10)  # 10초마다 업데이트

def get_stocks():
    return stocks

def close_db():
    conn.close()