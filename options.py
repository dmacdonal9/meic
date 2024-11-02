from datetime import datetime
from ib_insync import Contract
from ib_instance import ib

def get_closest_strike(contract, right, expiry, price):
    """
    Finds the closest strike price in the options chain to the given price and right (call or put).

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

        # Find the closest strike to the target price
        closest_strike = None
        min_difference = float('inf')

        for detail in option_chain:
            strike = detail.contract.strike
            difference = abs(strike - price)
            if difference < min_difference:
                min_difference = difference
                closest_strike = strike

        if closest_strike is not None:
            print(f"Closest strike for price {price} and right {right} is {closest_strike}")
            return closest_strike
        else:
            print("No matching strike found.")
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