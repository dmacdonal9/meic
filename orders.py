from ib_insync import LimitOrder, ComboLeg, Contract
from ib_instance import ib
from datetime import datetime, timedelta
import cfg
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Define the minimum tick sizes for various symbols
minTick: dict[str, float] = {
    "ES": 0.05,
    "SPX": 0.1
}


def submit_order(order_contract, limit_price: float, action: str, is_live: bool, quantity: int):
    order = LimitOrder(action=action, lmtPrice=limit_price, transmit=is_live, totalQuantity=quantity)
    print("submit_order: ", limit_price, action, is_live, quantity)
    # Set the orderRef field
    order.orderRef = cfg.myStrategyTag

    print("Placing order for ", order_contract.symbol)
    try:
        trade = ib.placeOrder(order_contract, order)
        ib.sleep(2)

        # Check the status of the order
        if trade.orderStatus.status in ('Submitted', 'PendingSubmit', 'PreSubmitted', 'Filled'):
            status = f"Order sent with status: {trade.orderStatus.status}\n"
        else:
            status = f"Order failed with status: {trade.orderStatus.status}\n"
        return status
    except Exception as e:
        error_message = f': Order placement failed with error: {str(e)}\n'
        return error_message

def create_bag(und_contract: Contract, legs: list, actions: list, ratios: list) -> Contract:
    """
    Creates a BAG contract with multiple legs.

    Parameters:
    und_contract (Contract): The underlying contract (e.g., SPX for an iron condor).
    legs (list): A list of Contract objects representing each leg of the combo.
    actions (list): A list of strings ("BUY" or "SELL") corresponding to each leg.
    ratios (list): A list of integers representing the ratio for each leg.

    Returns:
    Contract: A fully qualified BAG contract with specified legs.
    """
    # Initialize the combo contract as a BAG
    bag_contract = Contract()
    bag_contract.symbol = und_contract.symbol
    bag_contract.secType = 'BAG'
    bag_contract.currency = und_contract.currency
    bag_contract.exchange = und_contract.exchange

    # Add each leg to the contract
    bag_contract.comboLegs = []
    for leg, action, ratio in zip(legs, actions, ratios):
        combo_leg = ComboLeg()
        combo_leg.conId = leg.conId       # Contract ID of the leg
        combo_leg.action = action         # BUY or SELL
        combo_leg.ratio = ratio           # Ratio for the leg (e.g., 1 or 2)
        combo_leg.exchange = leg.exchange # Exchange for the leg
        combo_leg.openClose = 0           # Open the position (0=open, 1=close)

        # Append each configured ComboLeg to the contract
        bag_contract.comboLegs.append(combo_leg)

    return bag_contract

def get_active_orders():
    """
    Fetches and returns a list of all active orders in the IB account.

    Returns:
    - List of active orders (list of `Order` objects)
    """
    try:
        # Log the action
        logger.debug("Requesting active orders from IB account...")

        # Retrieve active orders
        active_orders = ib.reqAllOpenOrders()

        # Log the number of active orders found
        logger.debug(f"Number of active orders retrieved: {len(active_orders)}")

        # Iterate and log each order for detailed debugging
        for order in active_orders:
            logger.debug(f"Active Order - ID: {order.orderId}, Symbol: {order.contract.symbol}, "
                         f"Type: {order.orderType}, Quantity: {order.totalQuantity}, "
                         f"Status: {order.status}")

        return active_orders

    except Exception as e:
        logger.error(f"Failed to retrieve active orders: {e}")
        return []

# Test stub to call `get_active_orders` function
def test_get_active_orders():
    """
    Test function to verify retrieval of active orders.
    """
    logger.info("Running test for get_active_orders function.")
    active_orders = get_active_orders()

    if active_orders:
        print(f"Retrieved {len(active_orders)} active orders.")
    else:
        print("No active orders found.")


def get_recently_filled_orders(timeframe='today'):
    """
    Retrieves a list of recently filled orders based on the specified timeframe.

    Parameters:
    - timeframe (str): 'today', 'yesterday', or a specific date range in 'YYYY-MM-DD' format.

    Returns:
    - List of filled orders (list of `Trade` objects)
    """
    try:
        # Log the action
        logger.debug(f"Requesting filled orders for timeframe: {timeframe}")

        # Fetch all completed trades
        all_trades = ib.reqExecutions()

        # Define date boundaries based on timeframe
        if timeframe == 'today':
            start_time = datetime.combine(datetime.today(), datetime.min.time())
        elif timeframe == 'yesterday':
            start_time = datetime.combine(datetime.today() - timedelta(days=1), datetime.min.time())
        else:
            # Parse custom date format if specified
            try:
                start_time = datetime.strptime(timeframe, '%Y-%m-%d')
            except ValueError:
                logger.error("Invalid date format. Use 'today', 'yesterday', or 'YYYY-MM-DD'.")
                return []

        end_time = start_time + timedelta(days=1)

        # Filter for filled orders within the timeframe
        filled_orders = [trade for trade in all_trades if start_time <= trade.time < end_time]

        # Log the number of filled orders found
        logger.debug(f"Number of filled orders retrieved: {len(filled_orders)}")

        # Log each filled order in detail
        for trade in filled_orders:
            logger.debug(f"Filled Order - ID: {trade.order.orderId}, Symbol: {trade.contract.symbol}, "
                         f"Type: {trade.order.orderType}, Quantity: {trade.order.totalQuantity}, "
                         f"Time: {trade.time}, Fill Price: {trade.execution.avgPrice}")

        return filled_orders

    except Exception as e:
        logger.error(f"Failed to retrieve filled orders: {e}")
        return []

# Test stub to call `get_recently_filled_orders` function
def test_get_recently_filled_orders():
    """
    Test function to verify retrieval of filled orders within a specified timeframe.
    """
    logger.info("Running test for get_recently_filled_orders function.")

    # Testing with 'today'
    filled_orders_today = get_recently_filled_orders('today')
    print(f"Filled orders today: {len(filled_orders_today)}")

    # Testing with 'yesterday'
    filled_orders_yesterday = get_recently_filled_orders('yesterday')
    print(f"Filled orders yesterday: {len(filled_orders_yesterday)}")

    # Testing with a specific date
    filled_orders_specific = get_recently_filled_orders('2024-11-01')
    print(f"Filled orders on 2024-11-01: {len(filled_orders_specific)}")

# Run the test
if __name__ == '__main__':
    # Ensure IB connection
    if not ib.isConnected():
        ib.connect('127.0.0.1', 7497, clientId=1)  # Adjust client ID and port as needed

    test_get_recently_filled_orders()

    # Disconnect after the test
    ib.disconnect()
