from datetime import datetime
from ib_insync import Contract, Option
from ib_instance import ib
import math
import logging

def get_closest_strike(contract, right, expiry, price):
    """
    Finds the closest strike price in the options chain to the given price and right (call or put),
    filtering out any strikes where the bid price is None or NaN.

    Parameters:
    - contract: The underlying contract (e.g., future or stock) for which options are to be fetched.
    - right: 'C' for calls or 'P' for puts.
    - expiry: The expiry date for the options (YYYYMMDD format).
    - price: The target price to find the closest strike to.

    Returns:
    - The closest strike price, or NaN if no matching options are found.
    """
    try:
        # Determine secType for option contract based on underlying secType
        option_secType = 'FOP' if contract.secType == 'FUT' else 'OPT'

        # Define the base option contract with the derived secType
        option_contract = Contract()
        option_contract.symbol = contract.symbol
        option_contract.secType = option_secType
        option_contract.exchange = contract.exchange
        option_contract.currency = contract.currency
        option_contract.lastTradeDateOrContractMonth = expiry
        option_contract.right = right  # 'C' for Call, 'P' for Put

        # Request the options chain for the given expiry
        option_chain = ib.reqContractDetails(option_contract)
        if not option_chain:
            print("No options found for the specified parameters.")
            return float('nan')

        # Extract contracts from the option chain
        option_contracts = [detail.contract for detail in option_chain]

        # Request market data for all option contracts
        tickers = ib.reqTickers(*option_contracts)

        # Initialize variables for finding the closest strike
        closest_strike = None
        min_difference = float('inf')

        # Loop over the contracts and their tickers
        for contract, ticker in zip(option_contracts, tickers):
            bid_price = ticker.bid

            # Filter out contracts with None or NaN bid prices
            if bid_price is None or math.isnan(bid_price):
                continue

            strike = contract.strike
            difference = abs(strike - price)
            if difference < min_difference:
                min_difference = difference
                closest_strike = strike

        if closest_strike is not None:
            print(f"Closest strike for price {price} and right {right} is {closest_strike}")
            return closest_strike
        else:
            print("No matching strike found with valid bid prices.")
            return float('nan')
    except Exception as e:
        print(f"Error fetching closest strike: {e}")
        return float('nan')

def get_today_expiry():
    """Returns today's date in YYYYMMDD format."""
    return datetime.today().strftime('%Y%m%d')

def get_atm_strike(qualified_contract, expiry, current_price, secType):
    try:
        option_contract = Contract()
        option_contract.symbol = qualified_contract.symbol
        option_contract.secType = secType
        option_contract.exchange = qualified_contract.exchange
        option_contract.currency = qualified_contract.currency
        option_contract.lastTradeDateOrContractMonth = expiry

        option_details = ib.reqContractDetails(option_contract)
        if not option_details:
            print("No options found for the given expiry.")
            return float('nan')

        closest_strike = None
        min_difference = float('inf')

        for detail in option_details:
            strike = detail.contract.strike
            difference = abs(strike - current_price)
            if difference < min_difference:
                min_difference = difference
                closest_strike = strike

        if closest_strike is not None:
            print(f"Closest ATM strike for price {current_price} is {closest_strike}")
            return closest_strike
        else:
            print("No ATM strike found.")
            return float('nan')
    except Exception as e:
        print(f"Error fetching ATM strike: {e}")
        return float('nan')



def get_option_by_target_price(und_contract, right, expiry, target_price):
    """
    Find the option (put or call) whose ask price is closest to the target ask price.
    If multiple options have the same ask price, return the one with the highest strike price.

    Parameters:
    ib (IB): An instance of the IB class from ib_insync, already connected.
    und_contract (Contract): The underlying contract (e.g., Stock or Future).
    right (str): 'P' for put or 'C' for call.
    expiry (str): The expiration date in 'YYYYMMDD' format.
    target_ask_price (float): The target ask price.

    Returns:
    Option: The option contract that meets the criteria.
    """
    logging.info(f"Starting search for option on {und_contract.symbol} with right '{right}', expiry '{expiry}', and target ask price {target_price}.")

    # Get option chain parameters for the underlying contract
    try:
        chains = ib.reqSecDefOptParams(
            und_contract.symbol, '', und_contract.secType, und_contract.conId)
        logging.debug(f"Option chains retrieved: {chains}")
    except Exception as e:
        logging.error(f"Error retrieving option chains: {e}")
        return None, None

    # Collect all strikes and trading classes for the given expiry
    all_strikes = set()
    trading_classes = set()
    for chain in chains:
        if expiry in chain.expirations:
            all_strikes.update(chain.strikes)
            trading_classes.add(chain.tradingClass)
    logging.debug(f"Filtered strikes matching expiry: {sorted(all_strikes)}")
    logging.debug(f"Trading classes: {trading_classes}")

    if not all_strikes:
        logging.warning("No strikes found for the given expiry.")
        return None, None

    # Sort strikes in ascending order
    strikes = sorted(all_strikes)
    logging.debug(f"Sorted strikes: {strikes}")

    # Create option contracts for each strike with the desired right
    contracts = []
    for strike in strikes:
        for trading_class in trading_classes:
            option = Option(
                symbol=und_contract.symbol,
                lastTradeDateOrContractMonth=expiry,
                strike=strike,
                right=right,
                exchange='SMART',  # Use 'SMART' or specify an exchange like 'CBOE'
                currency=und_contract.currency,
                tradingClass=trading_class)
            contracts.append(option)
    logging.debug(f"Created {len(contracts)} option contracts with right '{right}'.")

    # Qualify contracts to get conIds
    qualified_contracts = ib.qualifyContracts(*contracts)
    logging.debug(f"Qualified contracts: {qualified_contracts}")

    if not qualified_contracts:
        logging.warning("No qualified contracts found.")
        return None, None

    # Request market data for all qualified contracts
    tickers = ib.reqTickers(*qualified_contracts)
    ib.sleep(2)  # Increase sleep time as needed
    logging.debug(f"Market data tickers retrieved: {tickers}")

    # Filter out options without valid ask prices
    valid_options = []
    for ticker in tickers:
        if right == 'P':
            if ticker.ask != float('inf') and ticker.ask > 0:
                valid_options.append((ticker.contract, ticker.ask))
        else:
            if ticker.bid != float('inf') and ticker.bid > 0:
                valid_options.append((ticker.contract, ticker.bid))

    logging.debug(f"Options with valid ask prices: {valid_options}")

    if not valid_options:
        logging.warning("No options with valid ask prices found.")
        return None, None

    # Find the options whose ask price is closest to the target ask price
    if right == 'P':
        min_diff = min(abs(ask - target_price) for _, ask in valid_options)
        closest_options = [(contract, ask) for contract, ask in valid_options if abs(ask - target_price) == min_diff]
    else:
        min_diff = min(abs(bid - target_price) for _, bid in valid_options)
        closest_options = [(contract, bid) for contract, bid in valid_options if abs(bid - target_price) == min_diff]

    logging.debug(f"Options with minimum price difference: {closest_options}")

    # If multiple options have the same minimum difference, select the one with the highest strike price
    closest_options.sort(key=lambda x: x[0].strike, reverse=True)
    selected_option = closest_options[0][0]
    selected_price = closest_options[0][1]

    logging.info(f"Option closest to target price found: {selected_option} with bid/ask price {selected_price}")

    return selected_option, selected_price