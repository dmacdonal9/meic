from ib_insync import TagValue, Contract, Order, IB
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize IB connection (assuming `ib` is connected globally)
ib = IB()

def submit_adaptive_limit_sell_order_with_trailing_stop():
    """
    Submits an adaptive limit sell order for the SPX 5700 put option expiring on 2024-11-04,
    with an attached buy-to-cover trailing stop order set at 10% below the current price.
    """
    try:
        # Define the SPX option contract with SMART exchange for adaptive orders
        option_contract = Contract(
            symbol='SPX',
            secType='OPT',
            lastTradeDateOrContractMonth='20241104',
            strike=5700,
            right='P',
            multiplier='100',
            exchange='SMART',
            currency='USD'
        )

        # Qualify the contract to ensure it’s recognized by IB
        ib.qualifyContracts(option_contract)
        logger.debug("SPX option contract qualified successfully.")

        # Retrieve the current price to calculate the trailing stop price
        ticker = ib.reqMktData(option_contract, '', snapshot=True)
        ib.sleep(1)  # Wait for data to populate
        current_price = ticker.last if ticker.last is not None else (ticker.bid + ticker.ask) / 2

        # Calculate the trailing amount (10% of current price) for buy-to-cover stop
        trailing_amount = current_price * 0.10
        logger.debug(f"Current price: {current_price}, Trailing amount: {trailing_amount}")

        # Define the adaptive limit sell order (primary order) to open the short
        limit_price = 10.0  # Initial limit price, adjust as needed
        adaptive_order = Order(
            action='SELL',
            orderType='LMT',
            totalQuantity=1,
            lmtPrice=limit_price,
            tif='DAY',
            algoStrategy='Adaptive',
            algoParams=[TagValue(tag='adaptivePriority', value='Normal')],
            transmit=False  # Set transmit to False for pending status
        )

        # Define the trailing stop order (child order) as a buy-to-cover
        trailing_stop_order = Order(
            action='BUY',  # Buy-to-cover to close the short position
            orderType='TRAIL',
            auxPrice=trailing_amount,  # Trailing amount
            totalQuantity=1,
            parentId=adaptive_order.orderId,  # Link to the parent order
            tif='GTC',  # Good-Till-Cancelled for trailing stop
            transmit=True  # Transmit both orders together when parent is ready
        )

        # Submit the primary order with the attached trailing stop
        trade = ib.placeOrder(option_contract, adaptive_order)
        ib.placeOrder(option_contract, trailing_stop_order)  # Attach and submit trailing stop

        logger.info(f"Adaptive limit sell order submitted with trailing stop at 10% below current price. "
                    f"Order ID: {trade.order.orderId}")

        # Log order details for both orders
        logger.debug(f"Primary Order - Type: {adaptive_order.orderType}, Limit Price: {adaptive_order.lmtPrice}, "
                     f"Quantity: {adaptive_order.totalQuantity}, Algo Strategy: {adaptive_order.algoStrategy}")
        logger.debug(f"Trailing Stop Order - Type: {trailing_stop_order.orderType}, Trailing Amount: {trailing_amount}")

        return trade

    except Exception as e:
        logger.error(f"Failed to submit adaptive limit sell order with trailing stop: {e}")
        return None

# Test stub to call `submit_adaptive_limit_sell_order_with_trailing_stop`
def test_submit_adaptive_limit_sell_order_with_trailing_stop():
    """
    Test function to verify adaptive limit sell order with attached trailing stop.
    """
    logger.info("Running test for submit_adaptive_limit_sell_order_with_trailing_stop function.")
    trade = submit_adaptive_limit_sell_order_with_trailing_stop()

    if trade:
        print(f"Order submitted successfully with trailing stop: Order ID = {trade.order.orderId}")
    else:
        print("Order submission failed.")

# Run the test
if __name__ == '__main__':
    # Ensure IB connection
    if not ib.isConnected():
        ib.connect('127.0.0.1', 7497, clientId=1)  # Adjust client ID and port as needed

    test_submit_adaptive_limit_sell_order_with_trailing_stop()

    # Disconnect after the test
    ib.disconnect()