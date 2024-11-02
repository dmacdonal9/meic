from ib_insync import LimitOrder, ComboLeg, Contract
from ib_instance import ib
import cfg

# Define the minimum tick sizes for various symbols
minTick: dict[str, float] = {
    "ES": 0.05,
    "SPX": 0.1
}


def calc_combo_model_price(bag_contract: Contract) -> float:
    """
    Calculate the model price of a BAG contract based on the model option prices of each leg.
    The final price is rounded to conform to the minimum tick size.

    Parameters:
    ib (IB): The connected IB instance to fetch contract details and market data.
    bag_contract (Contract): The BAG contract containing multiple legs with option contracts.

    Returns:
    float: The calculated model price of the BAG contract, rounded to the nearest tick.
    """
    # Set IB market data type to 'theoretical' for model prices
    ib.reqMarketDataType(4)  # 4 represents theoretical prices

    # Initialize the model price of the BAG combo
    total_model_price = 0.0

    # Get the min tick size based on the underlying symbol
    min_tick = minTick.get(bag_contract.symbol, 0.01)  # Default to 0.01 if symbol not found

    # Loop through each leg in the combo
    for combo_leg in bag_contract.comboLegs:
        # Create the contract object for the leg using its conId
        leg_contract = Contract(conId=combo_leg.conId, exchange=combo_leg.exchange)

        # Request market data for this leg to obtain modelGreeks
        ib.qualifyContracts(leg_contract)
        ticker = ib.reqMktData(leg_contract, '', False, False)

        # Wait until modelGreeks are available
        while not ticker.modelGreeks:
            ib.sleep(0.1)  # Short sleep to allow model data to populate

        # Retrieve the model price (optPrice) of the leg
        opt_price = ticker.modelGreeks.optPrice if ticker.modelGreeks else 0.0

        # Adjust based on action and ratio
        leg_price = opt_price * combo_leg.ratio
        if combo_leg.action == 'SELL':
            leg_price *= -1

        # Add to the total model price
        total_model_price += leg_price

    # Cancel market data to clean up
    #ib.cancelMktData(ticker)

    # Round total model price to the nearest minimum tick size
    rounded_price = round(total_model_price / min_tick) * min_tick

    return rounded_price


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

def showOrders():
    global orderbox

    ord_string = ""
    if ib.isConnected():

        #print("Checking for open orders to show")
        open_orders = ib.reqAllOpenOrders()

        for trade in open_orders:
            # print(trade)
            ticker = ib.reqMktData(trade.contract)
            ib.sleep(1)
            ord_string += f"{trade.order.account}: {trade.contract.symbol}: limit: {trade.order.lmtPrice}, market: {ticker.marketPrice()}\n"
        ord_string += f"----------------------------\n"

        return ord_string
