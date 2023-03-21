import ccxt
import time
import pandas as pd
import pprint

access = "a0jHcrmK92pZCZgPSuewXSENHyeI3Ko9QFlH6kXNo5bYN8reNtj6MkNnFPrgOg1p"      # 본인 값으로 변경
secret = "4GMCE5Vy7LTtV7nm85flNFLtVAp8S7XR0npxBtmXxqLVXWpqL4xnMYnh8eoHjyPb"      # 본인 값으로 변경

# binanceX   생성
binanceX = ccxt.binance(config={
    'apiKey': access, 
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

#RSI지표 수치를 구해준다. 첫번째: 분봉/일봉 정보, 두번째: 기간, 세번째: 기준 날짜
def GetRSI(ohlcv,period,st):
    ohlcv["close"] = ohlcv["close"]
    delta = ohlcv["close"].diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] =0
    down[down > 0] = 0
    _gain = up.ewm(com=(period - 1), min_periods=period).mean()
    _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    return float(pd.Series(100 - (100 / (1 + RS)), name="RSI").iloc[st])

#이동평균선 수치를 구해준다 첫번째: 분봉/일봉 정보, 두번째: 기간, 세번째: 기준 날짜
def GetMA(ohlcv,period,st):
    close = ohlcv["close"]
    ma = close.rolling(period).mean()
    return float(ma[st])

#분봉/일봉 캔들 정보를 가져온다 첫번째: 바이낸스 객체, 두번째: 코인 티커, 세번째: 기간 (1d,4h,1h,15m,10m,1m ...)
def GetOhlcv(binance, Ticker, period):
    btc_ohlcv = binance.fetch_ohlcv(Ticker, period)
    df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df


#스탑로스를 걸어놓는다. 해당 가격에 해당되면 바로 손절한다. 첫번째: 바이낸스 객체, 두번째: 코인 티커, 세번째: 손절 수익율 (1.0:마이너스100% 청산, 0.9:마이너스 90%, 0.5: 마이너스 50%)
def SetStopLoss(binance, Ticker, cut_rate):
    time.sleep(0.1)
    #주문을 읽어온다.
    orders = binance.fetch_orders(Ticker)

    StopLossOk = False
    for order in orders:

        if order['status'] == "open" and order['type'] == 'stop_market':
            #print(order)
            StopLossOk = True
            break
 
    #스탑로스 주문이 없다면 주문을 건다
    if StopLossOk == False:

        time.sleep(10.0)

        #잔고 데이터를 가지고 온다.
        balance = binance.fetch_balance(params={"type": "future"})
        time.sleep(0.1)
                                
        amt = 0
        entryPrice = 0
        leverage = 0
        #평균 매입단가와 수량을 가지고 온다.
        for posi in balance['info']['positions']:
            if posi['symbol'] == Ticker.replace("/", ""):
                entryPrice = float(posi['entryPrice'])
                amt = float(posi['positionAmt'])
                leverage = float(posi['leverage'])


        #롱일땐 숏을 잡아야 되고
        side = "sell"
        #숏일땐 롱을 잡아야 한다.
        if amt < 0:
            side = "buy"

        danger_rate = ((100.0 / leverage) * cut_rate) * 1.0

        #롱일 경우의 손절 가격을 정한다.
        stopPrice = entryPrice * (1.0 - danger_rate*0.01)

        #숏일 경우의 손절 가격을 정한다.
        if amt < 0:
            stopPrice = entryPrice * (1.0 + danger_rate*0.01)

        params = {
            'stopPrice': stopPrice,
            'closePosition' : True
        }

        print("side:",side,"   stopPrice:",stopPrice, "   entryPrice:",entryPrice)
        #스탑 로스 주문을 걸어 놓는다.
        print(binance.create_order(Ticker,'STOP_MARKET',side,abs(amt),stopPrice,params))

        print("############### STOPLOSS SETTING DONE ##################")

#구매할 수량을 구한다.  첫번째: 돈(USDT), 두번째:코인 가격, 세번째: 비율 1.0이면 100%, 0.5면 50%
def GetAmount(usd, coin_price, rate):

    target = usd * rate 

    amout = target/coin_price

    if amout < 0.001:
        amout = 0.001

    #print("amout", amout)
    return amout

#거래할 코인의 현재가를 가져온다. 첫번째: 바이낸스 객체, 두번째: 코인 티커
def GetCoinNowPrice(binance,Ticker):
    coin_info = binance.fetch_ticker(Ticker)
    coin_price = coin_info['last'] # coin_info['close'] == coin_info['last'] 

    return coin_price 

#시장가 taker 0.04, 지정가 maker 0.02

#시장가 숏 포지션 잡기 
#print(binance.create_market_sell_order(Target_Coin_Ticker, 0.002))
#print(binance.create_order(Target_Coin_Ticker, 'market', 'sell', 0.002, None))
 
#시장가 롱 포지션 잡기 
#print(binance.create_market_buy_order(Target_Coin_Ticker, 0.   001))
#print(binance.create_order(Target_Coin_Ticker, 'market', 'bu   y', 0.002, None))
    
#지정가 숏 포지션 잡기 
#print(binance.create_limit_sell_order(Target_Coin_Ticker, abs_amt, entryPrice))
#print(binance.create_order(Target_Coin_Ticker, 'limit', 'sell', abs_amt, entryPrice))
#지정가 롱 포지션 잡기 
#print(binance.create_limit_buy_order(Target_Coin_Ticker, abs_amt, btc_price))
#print(binance.create_order(Target_Coin_Ticker, 'limit', 'buy', abs_amt, entryPrice))

#거래할 코인 티커와 심볼
Target_Coin_Ticker = "BTC/USDT"
Target_Coin_Symbol = "BTCUSDT"

#캔들 정보 가져온다
df_15 = GetOhlcv(binanceX,Target_Coin_Ticker, '15m')

#최근 3개의 종가 데이터
print("Price: ",df_15['close'][-3], "->",df_15['close'][-2], "->",df_15['close'][-1] )
#최근 3개의 7일선 데이터
#일선 데이터
print("7ma: ",GetMA(df_15, 5, -3), "->",GetMA(df_15, 5, -2), "->",GetMA(df_15, 5, -1))
#최근 3개의 RSI14 데이터
print("RSI14: ",GetRSI(df_15, 14, -3), "->",GetRSI(df_15, 14, -2), "->",GetRSI(df_15, 14, -1))

#최근 7일선 3개를 가지고 와서 변수에 넣어준다.
ma7_before3 = GetMA(df_15, 5, -4)
ma7_before2 = GetMA(df_15, 5, -3)
ma7 = GetMA(df_15, 5, -2)

#31일선을 가지고 와서 변수에 넣어준다.
ma31 = GetMA(df_15, 20, -2)

#RSI14 정보를 가지고 온다.
rsi14 = GetRSI(df_15, 14, -1)

#잔고 데이터 가져오기 
balance = binanceX.fetch_balance(params={"type": "future"})
time.sleep(0.1)
#pprint.pprint(balance)

print(balance['USDT'])
print("Total Money:",float(balance['USDT']['total']))
print("Remain Money:",float(balance['USDT']['free']))

#레버리지 설정 5배 설정
try:
    print(binanceX.fapiPrivate_post_leverage({'symbol': Target_Coin_Symbol, 'leverage': 5}))
except Exception as e:
    print("error:", e)

amt = 0 #수량 정보 0이면 포지션 없는 상태, 음수면 Short 양수면 Long
entryPrice = 0 #평균 매입 단가
leverage = 1   #레버리지, 앱이나 웹에서 설정된 값을 가져온다.
unrealizedProfit = 0 #미 실현 손익 = 이익,손해

isolated = True #격리모드

#실제로 잔고 데이ㅌ의 포지션 정보 부분에서 해당 코인에 해당되는 정보를 넣어준다.
for posi in balance['info']['positions']:
    if posi['symbol'] == Target_Coin_Symbol:
        amt = float(posi['positionAmt'])
        entryPrice = float(posi['entryPrice'])
        leverage = float(posi['leverage'])
        unrealizedProfit = float(posi['unrealizedProfit'])
        isolated = posi['isolated']
        break
        
if isolated == False:
    try:
        print(binanceX.fapiPrivate_post_margintype({'symbol': Target_Coin_Symbol, 'marginType': 'ISOLATED'}))
    except Exception as e:
        print("error:", e)

print("amt:",amt)
print("entryPrice:",entryPrice)
print("leverage:",leverage)
print("unrealizedProfit:",unrealizedProfit)

#해당 코인 가격을 가져온다.
coin_price = GetCoinNowPrice(binanceX, Target_Coin_Ticker)

#레버리지에 따른 최대 매수 가능 수량
Max_Amount = round(GetAmount(float(balance['USDT']['total']),coin_price,0.5),3) * leverage 

#최대 매수수량의 1%에 해당하는 수량을 구한다.
one_percent_amount = Max_Amount / 10.0

print("one_percent_amount : ", one_percent_amount) 

#첫 매수 비중을 구한다.. 기본 5%
first_amount = one_percent_amount * 5.0

if first_amount < 0.001:
    first_amount = 0.001

print("first_amount : ", first_amount) 

'''
5  + 5
10  + 10
20   + 20
40   + 40
80

'''

#음수를 제거한 절대값 수량 예)  -0.1 -> 0.1 로 바꿔준다.
abs_amt = abs(amt)

#0이면 포지션 잡기전
if amt == 0:
    print("-----No Position")

    #7일선이 31일선 위에 있는데 7일선이 하락추세로 꺾였을때 
    if ma7 > ma31 and ma7_before3 < ma7_before2 and ma7_before2 > ma7 and rsi14 >= 30.0:
        print("sell/shot")

#모든주문 취소
        binanceX.cancel_all_orders(Target_Coin_Ticker)
        time.sleep(0.1)

        #포지션 진입
       # print(binanceX.create_limit_sell_order(Target_Coin_Ticker, first_amount, coin_price))
        print(binanceX.create_order(Target_Coin_Ticker, 'limit', 'sell', first_amount, coin_price))
        
        #스탑 로스 설정
        SetStopLoss(binanceX,Target_Coin_Ticker,0.5)

    #7일선이 31일선 아래에 있는데 7일선이 상승추세로 꺾였을때 
    if ma7 < ma31 and ma7_before3 > ma7_before2 and ma7_before2 < ma7 and rsi14 <= 65.0:
        print("buy/long")

        #모든 주문 취소
        binanceX.cancel_all_orders(Target_Coin_Ticker)
        time.sleep(0.1)

        #포지션 진입
        #print(binanceX.create_limit_buy_order(Target_Coin_Ticker, first_amount, coin_price))
        print(binanceX.create_order(Target_Coin_Ticker, 'limit', 'buy', first_amount, coin_price))

        #스탑 로스 설정.
        SetStopLoss(binanceX,Target_Coin_Ticker,0.5)

#0이 아니라면 포지션 잡은 상태
else:

    #음수면 숏 포지션 상태
    if amt < 0:
        print("-----Short Position")

    #양수면 롱 포지션 상태
    else:
        print("-----Long Position")

SetStopLoss(binanceX,Target_Coin_Ticker,0.5)

