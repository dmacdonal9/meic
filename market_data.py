import logging
import time
import math
from ib_insync import Contract, Ticker
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

            # Check for valid bid-ask; if bid and ask are -1, check if last price is valid
            if (ticker.bid == -1 or ticker.ask == -1) and ticker.last is not None and not math.isnan(ticker.last):
                logger.warning(f"Bid and ask are -1 for {my_contract}. Using last price as fallback: {ticker.last}")
                return ticker.last

            # Calculate midpoint if bid and ask are valid
            elif ticker.bid is not None and ticker.ask is not None and ticker.bid != -1 and ticker.ask != -1:
                mid_price = (ticker.bid + ticker.ask) / 2
                logger.debug(f"Midpoint price for {my_contract}: {mid_price} (bid: {ticker.bid}, ask: {ticker.ask})")
                return mid_price

            # Fallback to historical data
            elif ticker.last is None or math.isnan(ticker.last):
                hist_data = ib.reqHistoricalData(
                    my_contract, endDateTime='', durationStr='1 D',
                    barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                )
                if hist_data:
                    logger.info(f"Using historical trade price as fallback: {hist_data[-1].close}")
                    return hist_data[-1].close
                else:
                    logger.warning(f"No historical data available as fallback for {my_contract}.")
                    break  # Exit loop if historical data is also unavailable

        except Exception as e:
            logger.error(f"Error retrieving price for {my_contract} on attempt {attempt + 1}: {e}")

        attempt += 1
        time.sleep(retry_interval)  # Wait before retrying

    logger.error(f"Failed to retrieve price for {my_contract} after {max_retries} attempts.")
    return None


def calc_combo_model_price(strategy_legs, min_tick=0.01, max_wait_time=5) -> float:
    """
    Calculate the model price of a multi-leg option strategy based on the model option prices of each leg.
    Falls back to bid-ask midpoint or historical close price if necessary.

    Parameters:
    - strategy_legs: List of tuples, each containing:
        - leg (Contract): The option contract for the leg.
        - action (str): 'SELL' or 'BUY' indicating the action for the leg.
        - ratio (float): The ratio of this leg in the strategy.
    - min_tick (float): The minimum tick size for rounding, default is 0.01.
    - max_wait_time (int): Maximum wait time in seconds for modelGreeks data.

    Returns:
    - float: The calculated model price of the strategy, rounded to the nearest tick, or NaN if unavailable.
    """
    original_data_type = 1  # Assuming real-time data type as default
    ib.reqMarketDataType(4)  # Set to theoretical prices initially
    total_model_price = 0.0

    for leg_contract, action, ratio in strategy_legs:
        ib.qualifyContracts(leg_contract)
        ticker = ib.reqMktData(leg_contract, '', snapshot=True)

        logger.debug(f"Processing leg {leg_contract.conId} ({leg_contract.symbol}) with action {action} and ratio {ratio}.")

        # Wait for modelGreeks to populate with a timeout
        wait_time = 0
        while not ticker.modelGreeks and wait_time < max_wait_time:
            ib.sleep(0.5)
            wait_time += 0.5

        # Retrieve theoretical model price (optPrice)
        opt_price = ticker.modelGreeks.optPrice if ticker.modelGreeks else None

        # Fallback to real-time data for bid-ask midpoint if theoretical price is unavailable
        if opt_price is None:
            ib.reqMarketDataType(original_data_type)  # Switch to real-time data
            logger.info(f"Switching to real-time data for leg {leg_contract.conId}.")
            ticker = ib.reqMktData(leg_contract, '', snapshot=True)
            ib.sleep(1)  # Allow time for bid/ask data to populate

            bid = ticker.bid if ticker.bid is not None else 'N/A'
            ask = ticker.ask if ticker.ask is not None else 'N/A'

            # Check if both bid and ask are -1, indicating no data; if so, fallback to historical
            if bid == -1 and ask == -1:
                # Switch to historical data mode
                ib.reqMarketDataType(3)
                logger.info(f"Falling back to historical data for leg {leg_contract.conId}.")

                hist_data = ib.reqHistoricalData(
                    leg_contract, endDateTime='', durationStr='1 D',
                    barSizeSetting='1 day', whatToShow='TRADES', useRTH=True
                )
                if hist_data:
                    opt_price = hist_data[-1].close
                    logger.info(f"Using historical close price for leg {leg_contract.conId}: {opt_price}")
                else:
                    logger.error(f"No data available for leg: {leg_contract.conId}, skipping this leg.")
                    continue  # Skip this leg if no price data is available

                # Switch back to theoretical data for next leg
                ib.reqMarketDataType(4)

            elif isinstance(bid, float) and isinstance(ask, float):
                # If bid and ask are valid, calculate midpoint
                opt_price = (bid + ask) / 2
                logger.warning(f"Falling back to midpoint for leg {leg_contract.conId}: {opt_price}")
            else:
                # No valid data found even after attempting midpoint
                logger.error(f"No valid model price or bid/ask data available for leg: {leg_contract.conId}. Skipping this leg.")
                continue

        # Adjust based on action and ratio
        leg_price = opt_price * ratio
        if action == 'SELL':
            leg_price *= -1

        total_model_price += leg_price
        logger.debug(f"Leg {leg_contract.conId} contributes {'-' if action == 'SELL' else ''}{leg_price} to total.")

        # Cancel market data for each leg
        ib.cancelMktData(ticker)

    # Validate total_model_price to ensure it's a number
    if math.isnan(total_model_price):
        logger.error("Total model price is NaN. Check data sources for missing information.")
        return float('nan')

    rounded_price = round(total_model_price / min_tick) * min_tick
    logger.info(f"Total model price of strategy (rounded): {rounded_price}")

    return rounded_price
def test_calc_model_price():
    """
    Test function for calc_model_price to verify it calculates the correct model price for a multi-leg strategy.
    """
    leg1 = qualify_contract(symbol='SPX', secType='OPT', lastTradeDateOrContractMonth='20241104', exchange='CBOE',
                            currency='USD', strike=5700, right='P')
    leg2 = qualify_contract(symbol='SPX', secType='OPT', lastTradeDateOrContractMonth='20241104', exchange='CBOE',
                            currency='USD', strike=5750, right='P')
    leg3 = qualify_contract(symbol='SPX', secType='OPT', lastTradeDateOrContractMonth='20241104', exchange='CBOE',
                            currency='USD', strike=5800, right='C')
    leg4 = qualify_contract(symbol='SPX', secType='OPT', lastTradeDateOrContractMonth='20241104', exchange='CBOE',
                            currency='USD', strike=5850, right='C')

    strategy_legs = [
        (leg1, 'SELL', 1),
        (leg2, 'BUY', 1),
        (leg3, 'SELL', 1),
        (leg4, 'BUY', 1)
    ]

    model_price = calc_combo_model_price(strategy_legs)
    print(f"Calculated Model Price for Test Strategy: {model_price}")

    assert not math.isnan(model_price), "Model price should be calculated and not NaN."
    print("Test passed: Model price calculation works as expected.")


# Run the test
test_calc_model_price()