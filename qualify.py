from ib_insync import Contract, Future, FuturesOption, Stock, Index, Option
from operator import attrgetter
from ib_instance import ib


def qualify_contract(symbol: str, secType: str, lastTradeDateOrContractMonth: str = '', exchange: str = 'SMART', currency: str = 'USD', strike: float = 0.0, right: str = '', multiplier: str = ''):
    # Determine the type of contract to qualify
    if secType.upper() == 'STK':
        contract = Stock(symbol=symbol, exchange=exchange, currency=currency)
    elif secType.upper() == 'FUT':
        if not lastTradeDateOrContractMonth:
            raise ValueError("lastTradeDateOrContractMonth must be provided for future contracts.")
        contract = Future(symbol=symbol, lastTradeDateOrContractMonth=lastTradeDateOrContractMonth, currency=currency, exchange=exchange, multiplier=multiplier)
    elif secType.upper() == 'FOP':
        if not all([lastTradeDateOrContractMonth, strike, right]):
            raise ValueError("lastTradeDateOrContractMonth, strike, and right must be provided for future options.")
        contract = FuturesOption(symbol=symbol, lastTradeDateOrContractMonth=lastTradeDateOrContractMonth, strike=strike, right=right, currency=currency, exchange=exchange, multiplier=multiplier)
    elif secType.upper() == 'OPT':
        if not all([lastTradeDateOrContractMonth, strike, right]):
            raise ValueError("lastTradeDateOrContractMonth, strike, and right must be provided for stock options.")
        contract = Option(symbol=symbol, lastTradeDateOrContractMonth=lastTradeDateOrContractMonth, strike=strike, right=right, currency=currency, exchange=exchange, multiplier=multiplier)
    elif secType.upper() == 'IND':
        # Index contracts like SPX or NDX
        contract = Index(symbol=symbol, exchange=exchange, currency=currency)
    else:
        raise ValueError("Unsupported contract type. Supported types are STK, FUT, FOP, OPT, IND.")

    try:
        print(f"Attempting to qualify: {contract}")
        ib.qualifyContracts(contract)
        print(f"Contract qualified successfully: {contract}")
        return contract
    except Exception as e:
        print(f"Failed to qualify contract: {e}")
        raise
def test_option_chain(contract, exchange, expiry):
    try:
        chain = ib.reqSecDefOptParams(underlyingSymbol=contract.symbol,
                                      futFopExchange=exchange,
                                      underlyingSecType=contract.secType,
                                      underlyingConId=contract.conId)
        for c in chain:
            if expiry in c.expirations:
                return chain
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

    return None

def get_front_month_contract_date(future_symbol, exchange, mult, expiry):
    contract = Future(symbol=future_symbol, exchange=exchange, multiplier=mult)
    contract_details_list = ib.reqContractDetails(contract)

    contracts = [cd.contract for cd in contract_details_list]
    sorted_contracts = sorted(contracts, key=attrgetter('lastTradeDateOrContractMonth'))

    # Get contracts that have a valid option chain
    for contract in sorted_contracts:
        option_chain = test_option_chain(contract, exchange=exchange, expiry=expiry)
        if option_chain:
            return str(contract.lastTradeDateOrContractMonth)

def get_front_month_contract(symbol, exchange, multiplier, currency, lastTradeDateOrContractMonth):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'FUT'
    contract.exchange = exchange
    contract.lastTradeDateOrContractMonth = lastTradeDateOrContractMonth
    contract.currency = currency
    contract.multiplier = multiplier

    print(f"Requesting all available contracts for symbol: {symbol}")
    possible_contracts = ib.reqContractDetails(contract)
    if not possible_contracts:
        print("No contracts found for the given parameters.")
        return None

    possible_contracts.sort(key=lambda x: x.contract.lastTradeDateOrContractMonth)
    front_month_contract = possible_contracts[0].contract
    print("Selected front-month contract:", front_month_contract)

    return front_month_contract

