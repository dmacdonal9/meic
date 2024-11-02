from ib_insync import Contract
from ib_instance import ib


def get_current_mid_price(my_contract: Contract) -> float:
    """
    Retrieves the midpoint of the bid-ask spread for the specified contract.

    Parameters:
        my_contract (Contract): The contract for which to fetch the current midpoint price.

    Returns:
        float: The current midpoint price of the contract. If bid/ask are unavailable, returns None.
    """
    try:
        # Request market data
        ticker = ib.reqMktData(my_contract, '', False, False)
        # Wait briefly for data to be received
        ib.sleep(1)
        # Calculate midpoint price if both bid and ask are available
        current_mid_price = (ticker.bid + ticker.ask) / 2 if ticker.bid is not None and ticker.ask is not None else None
        return current_mid_price
    except Exception as e:
        print(f"Error retrieving price for {my_contract}: {e}")
        return None