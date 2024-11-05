from ib_insync import *
from ib_instance import ib
import logging

# Set up logging configuration
#logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# Suppress INFO messages from 'ib_insync.wrapper'
#logging.getLogger('ib_insync.wrapper').setLevel(logging.ERROR)

# If you want to suppress all INFO messages from 'ib_insync'
#logging.getLogger('ib_insync').setLevel(logging.ERROR)

def get_option_by_target_price(und_contract, right, expiry, target_ask_price):
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
    logging.info(f"Starting search for option on {und_contract.symbol} with right '{right}', expiry '{expiry}', and target ask price {target_ask_price}.")

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
        if ticker.ask != float('inf') and ticker.ask > 0:
            valid_options.append((ticker.contract, ticker.ask))
    logging.debug(f"Options with valid ask prices: {valid_options}")

    if not valid_options:
        logging.warning("No options with valid ask prices found.")
        return None, None

    # Find the options whose ask price is closest to the target ask price
    min_diff = min(abs(ask - target_ask_price) for _, ask in valid_options)
    closest_options = [(contract, ask) for contract, ask in valid_options if abs(ask - target_ask_price) == min_diff]

    logging.debug(f"Options with minimum price difference: {closest_options}")

    # If multiple options have the same minimum difference, select the one with the highest strike price
    closest_options.sort(key=lambda x: x[0].strike, reverse=True)
    selected_option = closest_options[0][0]
    selected_ask_price = closest_options[0][1]

    logging.info(f"Option closest to target ask price found: {selected_option} with ask price {selected_ask_price}")

    return selected_option, selected_ask_price

# Define the underlying contract (e.g., Apple stock)
und_contract = Stock('SPY', 'SMART', 'USD')
# Qualify the contract to ensure it has a valid conId
und_contract = ib.qualifyContracts(und_contract)[0]

# Call the function to get the cheapest put option for the given expiry
cheapest_option, opt_price = get_option_by_target_price(und_contract=und_contract, right='P', expiry='20241106', target_ask_price=float('0.02'))

if cheapest_option:
    print(f"Cheapest Option: {cheapest_option} is available for price: {opt_price}")
else:
    print("No suitable option found.")

# Disconnect IB connection
ib.disconnect()