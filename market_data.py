import logging
from ib_insync import Contract, Ticker
from ib_instance import ib
import time
import math

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