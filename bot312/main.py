import discord
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
import jungbo  # jungbo.py 파일 임포트하는 코드
import bet

# 봇 토큰 설정
TOKEN = '니 토큰 입력하셀'

# 객체 만들기이이ㅣ
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 데이터베이스 연결
conn = sqlite3.connect('user_balances.db')
cursor = conn.cursor()

# 사용자 돈 테이블 생성 (이미 존재하면 무시)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS balances (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER
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

user_success_rates = {}
user_last_work_times = {}
@client.event
async def on_ready():
    print(f'{client.user}에 로그인했습니다!')
    client.loop.create_task(jungbo.update_stock_prices()) # jungbo.py의 stock_update 함수를 비동기적으로 실행 async

def is_admin(user):
    """사용자가 관리자 권한을 가지고 있는지 확인합니다."""
    return user.guild_permissions.administrator

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == '팔일':
        user_id = message.author.id
        now = datetime.now()

        # 마지막 팔일 명령어 사용 시간 확인
        last_work_time = user_last_work_times.get(user_id)
        if last_work_time and (now - last_work_time).total_seconds() < 2:
            remaining_time = 2 - (now - last_work_time).total_seconds()
            await message.channel.send(f"{remaining_time:.1f}초 후에 다시 일할 수 있습니다.")
            return

        user_last_work_times[user_id] = now  # 마지막 팔일 명령어 사용 시간 업데이트

        money = random.randint(3000, 4000)

        # 데이터베이스에서 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result:
            balance = result[0] + money
            # 데이터베이스 업데이트
            cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (balance, user_id))
        else:
            balance = money
            # 데이터베이스에 사용자 돈 추가
            cursor.execute('INSERT INTO balances (user_id, balance) VALUES (?, ?)', (user_id, balance))

        conn.commit()

        await message.channel.send(f'{message.author.mention}님이 팔일을 하여 {money}원을 벌었습니다! 현재 잔액: {balance}원')


    if message.content == '팔주식':
        embed = discord.Embed(title=" 주식 현재가", timestamp=datetime.now())
        stocks = jungbo.get_stocks()  # jungbo.py에서 주식 데이터 가져오기
        for stock_code, stock_data in stocks.items():
            price = stock_data['price']
            previous_price = stock_data['previous_price']
            change = price - previous_price
            if change > 0:
                color = discord.Color.red()
                change_str = f"```▲ {change}원```"
            elif change < 0:
                color = discord.Color.blue()
                change_str = f"```▼ {abs(change)}원```"
            else:
                color = discord.Color.light_grey()
                change_str = "변동 없음"
            embed.add_field(name=f"[{stock_code}] {stock_data['name']}", value=f"현재가: {price}원 {change_str}",
                            inline=False)
        await message.channel.send(embed=embed)

    if message.content == '팔통장':
        user_id = message.author.id
        user = message.author

        # 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0

        # 사용자 주식 보유 정보 조회ㅇㅇ
        cursor.execute('''
                SELECT stock_code, quantity, average_price FROM user_stocks WHERE user_id = ?
            ''', (user_id,))
        user_stocks = cursor.fetchall()

        embed = discord.Embed(title=f"{user.display_name}님의 팔통장", color=discord.Color.green())
        embed.set_thumbnail(url=user.avatar.url)  # 사용자 아이콘 사진 설정
        embed.add_field(name="현재 잔액", value=f"{balance}원", inline=False)

        if user_stocks:
            stock_info = ""
            total_profit_loss = 0
            for stock_code, quantity, average_price in user_stocks:
                stock_data = jungbo.get_stocks().get(stock_code)
                if stock_data:
                    current_price = stock_data['price']
                    profit_loss = round((current_price - average_price) * quantity)  # 반올림
                    total_profit_loss += profit_loss
                    profit_rate = round(((current_price - average_price) / average_price) * 100, 2)  # 수익률 계산 및 반올림
                    profit_loss_str = f"▲ {profit_loss}원 ({profit_rate:.2f}%)" if profit_loss > 0 else f"▼ {abs(profit_loss)}원 ({abs(profit_rate):.2f}%)" if profit_loss < 0 else f"변동 없음 (0.00%)"
                    stock_info += f"[{stock_code}] {stock_data['name']} {quantity}주 ({profit_loss_str})\n"
            embed.add_field(name="보유 주식", value=stock_info, inline=False)
            embed.add_field(name="총 수익", value=f"{total_profit_loss}원", inline=False)
        else:
            embed.add_field(name="보유 주식", value="보유한 주식이 없습니다.", inline=False)

        await message.channel.send(embed=embed)


    if message.content.startswith('팔매수'):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("사용법: 팔매수 (주식 이름) (갯수 또는 전부)")
            return

        stock_name = parts[1].upper()
        user_id = message.author.id

        stock_data = jungbo.get_stocks().get(stock_name)
        if not stock_data:
            await message.channel.send("존재하지 않는 주식입니다.")
            return

        current_price = stock_data['price']

        # 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0

        if len(parts) == 3 and parts[2].lower() == '전부':
            quantity = balance // current_price  # 최대 구매 가능 수량 계산
        else:
            try:
                quantity = int(parts[2])
            except ValueError:
                await message.channel.send("갯수는 숫자로 입력해야 합니다.")
                return

        total_price = current_price * quantity
        if balance < total_price:
            await message.channel.send("잔액이 부족합니다.")
            return

        # 사용자 돈 차감
        new_balance = balance - total_price
        cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (new_balance, user_id))

        # 사용자 주식 보유 정보 조회
        cursor.execute('''
            SELECT quantity, average_price FROM user_stocks WHERE user_id = ? AND stock_code = ?
        ''', (user_id, stock_name))
        result = cursor.fetchone()

        if result:
            existing_quantity, existing_average_price = result
            new_quantity = existing_quantity + quantity
            new_average_price = ((existing_average_price * existing_quantity) + total_price) / new_quantity
            # 사용자 주식 보유 정보 업데이트
            cursor.execute('''
                UPDATE user_stocks SET quantity = ?, average_price = ? WHERE user_id = ? AND stock_code = ?
            ''', (new_quantity, new_average_price, user_id, stock_name))
        else:
            # 사용자 주식 보유 정보 추가
            cursor.execute('''
                INSERT INTO user_stocks (user_id, stock_code, quantity, average_price) VALUES (?, ?, ?, ?)
            ''', (user_id, stock_name, quantity, current_price))

        conn.commit()
        await message.channel.send(f"{stock_data['name']} {quantity}주를 {total_price}원에 매수했습니다. 현재 잔액: {new_balance}원")


    if message.content.startswith('팔매도'):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("사용법: !팔매도 (주식 이름) (갯수 또는 전부)")
            return

        stock_name = parts[1].upper()
        user_id = message.author.id

        stock_data = jungbo.get_stocks().get(stock_name)
        if not stock_data:
            await message.channel.send("존재하지 않는 주식입니다.")
            return

        current_price = stock_data['price']

        # 사용자 주식 보유 정보 조회
        cursor.execute('''
                SELECT quantity, average_price FROM user_stocks WHERE user_id = ? AND stock_code = ?
            ''', (user_id, stock_name))
        result = cursor.fetchone() #fetch쓸때 조심해라 파람 불가함함

        if not result:
            await message.channel.send("보유한 주식이 없습니다.")
            return

        existing_quantity, existing_average_price = result

        if len(parts) == 3 and parts[2].lower() == '전부':
            quantity = existing_quantity
        else:
            try:
                quantity = int(parts[2])
            except ValueError:
                await message.channel.send("갯수는 숫자로 입력해야 합니다.")
                return

            if existing_quantity < quantity:
                await message.channel.send("보유한 주식 수가 부족합니다.")
                return

        # 사용자 돈 추가
        total_price = current_price * quantity
        cursor.execute('UPDATE balances SET balance = balance + ? WHERE user_id = ?', (total_price, user_id))

        # 사용자 주식 보유 정보 업데이트
        new_quantity = existing_quantity - quantity
        if new_quantity == 0:
            cursor.execute('DELETE FROM user_stocks WHERE user_id = ? AND stock_code = ?', (user_id, stock_name))
        else:
            cursor.execute('''
                    UPDATE user_stocks SET quantity = ? WHERE user_id = ? AND stock_code = ?
                ''', (new_quantity, user_id, stock_name))

        conn.commit()
        await message.channel.send(f"{stock_data['name']} {quantity}주를 {total_price}원에 매도했습니다.")


    if message.content.startswith('팔돈추가'):
        if not is_admin(message.author):
            await message.channel.send("관리자 권한이 없습니다.")
            return

        parts = message.content.split()
        if len(parts) != 3:
            await message.channel.send("사용법: 팔돈추가 (사용자 ID) (금액)")
            return

        try:
            user_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            await message.channel.send("사용자 ID와 금액은 숫자로 입력해야 합니다.")
            return

        # 데이터베이스에서 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result:
            balance = result[0] + amount
            # 데이터베이스 업데이트
            cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (balance, user_id))
        else:
            # 데이터베이스에 사용자 돈 추가
            cursor.execute('INSERT INTO balances (user_id, balance) VALUES (?, ?)', (user_id, amount))

        conn.commit()
        await message.channel.send(f"사용자 {user_id}에게 {amount}원을 추가했습니다.")

    if message.content == '팔거지':
        user_id = message.author.id

        # 데이터베이스에서 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result:
            # 사용자 돈 0으로 설정
            cursor.execute('UPDATE balances SET balance = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            await message.channel.send(f"{message.author.mention}님은 거지가입니다")
        else:
            await message.channel.send(f"{message.author.mention}님은 이미 돈이 없습니다.")

    if message.content == '팔랭킹':
        # 데이터베이스에서 돈이 많은 순으로 사용자 정보 조회
        cursor.execute('SELECT user_id, balance FROM balances ORDER BY balance DESC')
        results = cursor.fetchall()

        embed = discord.Embed(title="돈 랭킹", color=discord.Color.gold())  # 임베드 색상 변경
        rank = 1
        for user_id, balance in results:
            user = await client.fetch_user(user_id)  # 사용자 정보 가져오기
            embed.add_field(name=f"{rank}위: {user.display_name}", value=f" {balance}원", inline=False)
            rank += 1
            if rank > 10:  # 10위까지만 표시
                break

        await message.channel.send(embed=embed)

    if message.content.startswith('팔도박'):
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("사용법: 팔도박 (배팅 금액 또는 ㅇㅇ)")
            return

        user_id = message.author.id

        # 사용자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0

        if parts[1].lower() == 'ㅇㅇ':
            bet_amount = balance
        else:
            try:
                bet_amount = int(parts[1])
            except ValueError:
                await message.channel.send("배팅 금액은 숫자로 입력해야 합니다.")
                return

        # 사용자 도박 성공 확률 조회 또는 초기화
        success_rate = user_success_rates.get(user_id, 0.5)

        # 도박 실행
        result_message, new_balance, new_success_rate = bet.gamble(user_id, bet_amount, balance, success_rate)

        # 데이터베이스 업데이트
        cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (new_balance, user_id))
        conn.commit()

        # 사용자 도박 성공 확률 업데이트
        user_success_rates[user_id] = new_success_rate

        await message.channel.send(f"{message.author.mention}님, {result_message} 현재 잔액: {new_balance}원")

    if message.content.startswith('팔송금'):
        parts = message.content.split()
        if len(parts) != 3:
            await message.channel.send("사용법: 팔송금 (사용자 ID) (금액)")
            return

        try:
            recipient_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            await message.channel.send("사용자 ID와 금액은 숫자로 입력해야 합니다.")
            return

        sender_id = message.author.id

        if sender_id == recipient_id:
            await message.channel.send("자신에게 송금할 수 없습니다.")
            return

        # 송금자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (sender_id,))
        sender_result = cursor.fetchone()
        sender_balance = sender_result[0] if sender_result else 0

        if sender_balance < amount:
            await message.channel.send("잔액이 부족합니다.")
            return

        # 수수료 계산
        fee = int(amount * 0.15)
        transfer_amount = amount - fee

        # 수신자 돈 조회
        cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (recipient_id,))
        recipient_result = cursor.fetchone()
        recipient_balance = recipient_result[0] if recipient_result else 0

        # 송금자 돈 차감
        new_sender_balance = sender_balance - amount
        cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (new_sender_balance, sender_id))

        # 수신자 돈 추가
        new_recipient_balance = recipient_balance + transfer_amount
        cursor.execute('UPDATE balances SET balance = ? WHERE user_id = ?', (new_recipient_balance, recipient_id))

        conn.commit()
        await message.channel.send(
            f"{message.author.mention}님이 <@{recipient_id}>님에게 {amount}원을 송금했습니다. (수수료: {fee}원, 송금액: {transfer_amount}원)")


@client.event
async def on_disconnect():
    conn.close()

client.run(TOKEN)
