from qualify import qualify_contract
from orders import create_bag


def iron_condor(und_contract, mid_strike, lower_strike, higher_strike, opt_expiry):
    """
    Creates an Iron Condor using four option legs on the specified underlying contract.

    Parameters:
    - und_contract: The underlying contract for which the options are created.
    - mid_strike: The strike price for the short call and put options (center of the iron condor).
    - lower_strike: The lower strike price for the long put option.
    - higher_strike: The higher strike price for the long call option.
    - opt_expiry: The expiration date for the options (YYYYMMDD format).

    Returns:
    - A tuple containing:
        1. A BAG order for the iron condor.
        2. A list of the qualified contracts (legs) used in the iron condor.
    """
    # Determine secType for option contract based on underlying secType
    option_secType = 'FOP' if und_contract.secType == 'FUT' else 'OPT'

    # Short put
    sell_put = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=mid_strike,
        right='P',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Long put
    buy_put = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=lower_strike,
        right='P',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Short call
    sell_call = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=mid_strike,
        right='C',  # 'C' for Call
        multiplier=und_contract.multiplier
    )

    # Long call
    buy_call = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=higher_strike,
        right='C',  # 'C' for Call
        multiplier=und_contract.multiplier
    )

    # Define legs, actions, and ratios for the iron condor
    legs = [sell_put, buy_put, sell_call, buy_call]
    actions = ['SELL', 'BUY', 'SELL', 'BUY']
    ratios = [1, 1, 1, 1]

    # Create the BAG order for the iron condor
    condor = create_bag(und_contract, legs, actions, ratios)

    # Return both the BAG order and the individual legs
    return condor, legs


def put_credit_spread(und_contract, short_strike, long_strike, opt_expiry):
    """
    Creates a Put Credit Spread (PCS) using two option legs on the specified underlying contract.

    Parameters:
    - und_contract: The underlying contract for which the options are created.
    - short_strike: The strike price of the short put option.
    - long_strike: The strike price of the long put option.
    - opt_expiry: The expiration date for the options (YYYYMMDD format).

    Returns:
    - A tuple containing:
        1. A BAG order for the put credit spread.
        2. A list of the qualified contracts (legs) used in the spread.
    """
    # Determine secType for option contract based on underlying secType
    option_secType = 'FOP' if und_contract.secType == 'FUT' else 'OPT'

    # Short put
    sell_put = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=short_strike,
        right='P',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Long put
    buy_put = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=long_strike,
        right='P',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Define legs, actions, and ratios for the PCS
    legs = [sell_put, buy_put]
    actions = ['BUY', 'SELL']
    ratios = [1, 1]

    # Construct a list of tuples, each containing a leg contract, action, and ratio
    strategy_legs = [(leg, action, ratio) for leg, action, ratio in zip(legs, actions, ratios)]

    pcs = create_bag(und_contract, legs, actions, ratios)

    return pcs, strategy_legs


def call_credit_spread(und_contract, short_strike, long_strike, opt_expiry):
    """
    Creates a Put Credit Spread (PCS) using two option legs on the specified underlying contract.

    Parameters:
    - und_contract: The underlying contract for which the options are created.
    - short_strike: The strike price of the short put option.
    - long_strike: The strike price of the long put option.
    - opt_expiry: The expiration date for the options (YYYYMMDD format).

    Returns:
    - A tuple containing:
        1. A BAG order for the put credit spread.
        2. A list of the qualified contracts (legs) used in the spread.
    """
    # Determine secType for option contract based on underlying secType
    option_secType = 'FOP' if und_contract.secType == 'FUT' else 'OPT'

    # Short call
    sell_call = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=short_strike,
        right='C',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Long call
    buy_call = qualify_contract(
        und_contract.symbol,
        secType=option_secType,
        lastTradeDateOrContractMonth=opt_expiry,
        exchange=und_contract.exchange,
        strike=long_strike,
        right='C',  # 'P' for Put
        multiplier=und_contract.multiplier
    )

    # Define legs, actions, and ratios for the PCS
    legs = [sell_call, buy_call]
    actions = ['BUY', 'SELL']
    ratios = [1, 1]

    # Construct a list of tuples, each containing a leg contract, action, and ratio
    strategy_legs = [(leg, action, ratio) for leg, action, ratio in zip(legs, actions, ratios)]

    ccs = create_bag(und_contract, legs, actions, ratios)

    return ccs, strategy_legs