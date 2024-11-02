from ib_insync import Contract
from ib_instance import ib
from ib_insync import Contract
from ib_instance import ib

def get_real_time_price():
    """
    Attempts to fetch real-time data for the specified SPX option as a fallback.
    """
    option_contract = Contract(
        symbol='SPX',
        secType='OPT',
        lastTradeDateOrContractMonth='20241104',
        strike=5700,
        right='P',
        multiplier='100',
        exchange='CBOE',  # or 'SMART'
        currency='USD'
    )

    # Qualify the contract
    ib.qualifyContracts(option_contract)

    # Request market data
    ticker = ib.reqMktData(option_contract, '', snapshot=True)
    ib.sleep(1)  # Allow time for data to populate

    if ticker.last is not None:
        print(f"Real-time last price: {ticker.last}")
    elif ticker.bid is not None and ticker.ask is not None:
        mid_price = (ticker.bid + ticker.ask) / 2
        print(f"Real-time midpoint (bid/ask): {mid_price}")
    else:
        print("No real-time price data available.")

# Run the function to get real-time data
get_real_time_price()