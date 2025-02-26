import sqlite3
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM stocks WHERE name = '쁘허'")  # 테이블 이름 및 주식 이름 변경
conn.commit()

# 데이터베이스 연결 종료
conn.close()