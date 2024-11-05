import logging
import time
import math
from ib_insync import Contract, ComboLeg
from ib_instance import ib
from qualify import qualify_contract

# Configure logging for the module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()  # Outputs to console; use FileHandler to log to a file if needed
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_current_mid_price(my_contract: Contract, max_retries=3, retry_interval=1, refresh=False) -> float:
    attempt = 0
    ticker = None

    logger.info(f"Fetching midpoint price for contract: {my_contract}")

    while attempt < max_retries:
        try:
            # Request market data
            ticker = ib.reqMktData(my_contract, '', refresh, False)
            ib.sleep(retry_interval)

            if ticker.last is not None and not math.isnan(ticker.last):
                logger.warning(f"Invalid last_price: {ticker.last}")
                return ticker.last

        except Exception as e:
            logger.error(f"Error retrieving price for {my_contract} on attempt {attempt + 1}: {e}")

        attempt += 1
        time.sleep(retry_interval)  # Wait before retrying

    logger.error(f"Failed to retrieve price for {my_contract} after {max_retries} attempts.")
    return None

def round_to_tick(price, tick_size):
    return round(price / tick_size) * tick_size

def get_combo_prices(legs):
    """
    Function to retrieve bid, mid, and ask prices for a combo contract by summing individual leg prices.
    The logic has been corrected as per your specifications.

    Parameters:
    und_contract (Contract): The fully qualified underlying contract (e.g., SPX index).
    legs (list of tuples): Each tuple contains (Contract, action, ratio) for each option leg.

    Returns:
    tuple: (bid, mid, ask) prices or (None, None, None) if data is unavailable.
    """
    import math

    total_bid = 0.0
    total_ask = 0.0

    # Iterate over each leg
    for leg_contract, action, ratio in legs:
        # Ensure each leg contract is fully qualified
        leg_contract = ib.qualifyContracts(leg_contract)[0]

        # Request market data for the leg
        leg_ticker = ib.reqMktData(leg_contract, '', False, False)

        # Wait briefly for market data to populate
        ib.sleep(1)  # Adjust the sleep time as necessary
        print("LEG: ", action, leg_ticker.contract.strike, leg_ticker.bid, leg_ticker.ask)

        # Retrieve bid and ask prices
        bid = leg_ticker.bid
        ask = leg_ticker.ask

        # Cancel market data subscription for the leg
        ib.cancelMktData(leg_ticker)

        # Handle None or NaN values by assuming 0
        if bid is None or math.isnan(bid) or bid == -1.0:
            bid = 0.0
        if ask is None or math.isnan(ask) or ask == -1.0:
            ask = 0.0

        # For total bid price
        if action.upper() == 'BUY':
            # Add bid price of BUY leg
            total_bid -= bid * ratio
        elif action.upper() == 'SELL':
            # Subtract bid price of SELL leg
            total_bid += bid * ratio
        else:
            raise ValueError(f"Invalid action {action} for leg {leg_contract.localSymbol}")

        # For total ask price
        if action.upper() == 'BUY':
            # Add ask price of BUY leg
            total_ask -= ask * ratio
        elif action.upper() == 'SELL':
            # Subtract ask price of SELL leg
            total_ask += ask * ratio
        else:
            raise ValueError(f"Invalid action {action} for leg {leg_contract.localSymbol}")

    # Calculate mid price as average of total bid and total ask
    mid = (total_bid + total_ask) / 2.0

    # Round the mid price to the nearest tick size
    mid = round_to_tick(mid, 0.1)
    total_bid = round_to_tick(total_bid,0.1)
    total_ask = round_to_tick(total_ask,0.1)

    print("get_combo_prices(): Returning prices: ", total_bid, mid, total_ask)
    return total_bid, mid, total_ask