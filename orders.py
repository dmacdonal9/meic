from ib_insync import LimitOrder, ComboLeg, Contract, Order, TagValue
from ib_instance import ib
from datetime import datetime, timedelta
from typing import Optional
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


def submit_adaptive_order_trailing_stop(
        order_contract: Contract,
        limit_price: float,
        order_type: str,
        action: str,
        is_live: bool,
        quantity: int,
        stop_loss_amt: float
    ) -> Optional[Order]:
    """
    Submit an adaptive order (market or limit) with a linked trailing stop loss as a bracket order in TWS.

    Parameters:
        order_contract (Contract): The contract to trade.
        limit_price (float): The limit price for the order (ignored if order_type is 'MKT').
        order_type (str): 'MKT' or 'LMT'.
        action (str): 'BUY' or 'SELL'.
        is_live (bool): Whether to submit as a live order (True) or paper (False).
        quantity (int): Number of units to trade.
        stop_loss_amt (float): The trailing amount for the stop loss order.

    Returns:
        Optional[Order]: The primary order object if successful, else None.
    """

    # Update contract to use SMART exchange
    order_contract.exchange = 'SMART'

    # Ensure valid action
    if action not in ["BUY", "SELL"]:
        logger.error(f"Invalid action: {action}. Must be 'BUY' or 'SELL'.")
        return None

    # Ensure valid order_type
    if order_type not in ["MKT", "LMT"]:
        logger.error(f"Invalid order type: {order_type}. Must be 'MKT' or 'LMT'.")
        return None

    # Create the primary adaptive order
    primary_order = Order(
        orderType=order_type,
        action=action,
        totalQuantity=quantity,
        tif='DAY',
        algoStrategy='Adaptive',
        algoParams=[TagValue('adaptivePriority', 'Normal')],
        transmit=False  # Hold transmission until child is set up
    )

    # Set limit price if order_type is 'LMT'
    if order_type == 'LMT':
        primary_order.lmtPrice = limit_price

    # Place the primary order to get the orderId
    ib.placeOrder(order_contract, primary_order)
    ib.sleep(1)  # Allow time for the order ID to populate

    # Verify the primary order has an ID
    if not primary_order.orderId:
        logger.error("Primary order failed to generate an order ID.")
        return None

    # Create the trailing stop order as a child of the primary order
    trailing_stop_order = Order(
        orderType='TRAIL',
        action='SELL' if action == 'BUY' else 'BUY',
        totalQuantity=quantity,
        auxPrice=stop_loss_amt,
        parentId=primary_order.orderId,  # Link to the primary order
        tif='DAY',
        transmit=is_live  # This will transmit both orders together
    )

    # Place the trailing stop order
    ib.placeOrder(order_contract, trailing_stop_order)

    # Log success or failure
    if primary_order.orderId and trailing_stop_order.orderId:
        logger.info("Adaptive order with linked trailing stop submitted successfully")
    else:
        logger.error("Order submission failed")

    return primary_order

def submit_limit_order(order_contract, limit_price: float, action: str, is_live: bool, quantity: int):
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
