from ib_instance import ib
from ib_insync import Option


def find_spreads_for_symbol(symbol: str, expiry: str):
    # Retrieve all positions and filter by symbol and expiration date
    positions = ib.positions()
    spx_positions = [pos for pos in positions
                     if pos.contract.symbol == symbol
                     and pos.contract.lastTradeDateOrContractMonth == expiry]

    # Organize positions by option type and long/short position
    short_calls = []
    long_calls = []
    short_puts = []
    long_puts = []

    for pos in spx_positions:
        contract = pos.contract
        if contract.right == 'C':  # Call option
            if pos.position < 0:
                short_calls.append((contract, pos.position))
            elif pos.position > 0:
                long_calls.append((contract, pos.position))
        elif contract.right == 'P':  # Put option
            if pos.position < 0:
                short_puts.append((contract, pos.position))
            elif pos.position > 0:
                long_puts.append((contract, pos.position))

    # Identify bull call spreads (short call with a lower strike, long call with a higher strike)
    bull_call_spreads = []
    for short_call, _ in short_calls:
        for long_call, _ in long_calls:
            if short_call.strike < long_call.strike:
                bull_call_spreads.append((short_call, long_call))
                break  # Avoid matching the same short leg to multiple long legs

    # Identify bear put spreads (short put with a higher strike, long put with a lower strike)
    bear_put_spreads = []
    for short_put, _ in short_puts:
        for long_put, _ in long_puts:
            if short_put.strike > long_put.strike:
                bear_put_spreads.append((short_put, long_put))
                break  # Avoid matching the same short leg to multiple long legs

    # Output results
    print(f"Total Short Bull Call Spreads Found: {len(bull_call_spreads)}")
    print(f"Total Short Bear Put Spreads Found: {len(bear_put_spreads)}\n")

    print("Short Bull Call Spreads:")
    for short_call, long_call in bull_call_spreads:
        print(f"Short Call: {short_call.localSymbol}, Long Call: {long_call.localSymbol}")

    print("\nShort Bear Put Spreads:")
    for short_put, long_put in bear_put_spreads:
        print(f"Short Put: {short_put.localSymbol}, Long Put: {long_put.localSymbol}")


# Example call
find_spreads_for_symbol('SPX', '20241108')