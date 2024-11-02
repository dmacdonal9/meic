from ib_insync import IB

import cfg
from strategies import put_credit_spread
from qualify import qualify_contract
from market_data import get_current_mid_price

# Initialize IB instance
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=2)  # Adjust host, port, and clientId as needed

def test_put_credit_spread():
    """
    Test stub function to call and verify the put_credit_spread function.
    """
    # Define an example underlying contract (e.g., /ES Future)
    und_contract = qualify_contract(
        symbol='SPX',
        secType='IND',
        exchange='CBOE',
        currency='USD'
    )

    # Define parameters for the PCS
    short_strike = get_current_mid_price(und_contract)
    long_strike = short_strike - cfg.short_put_offset
    opt_expiry = "20241104"  # Format: YYYYMMDD

    # Call the put_credit_spread function
    pcs_bag, pcs_legs = put_credit_spread(und_contract, short_strike, long_strike, opt_expiry)

    # Check and print the results
    print("Put Credit Spread BAG Order:")
    print(pcs_bag)
    print("\nIndividual Qualified Legs:")
    for leg in pcs_legs:
        print(leg)

    # Verify that both pcs_bag and pcs_legs are returned
    assert pcs_bag is not None, "Failed: BAG order for PCS is None."
    assert isinstance(pcs_legs, list) and len(pcs_legs) == 2, "Failed: PCS legs are not properly returned."
    assert all(isinstance(leg, type(und_contract)) for leg in pcs_legs), "Failed: PCS legs are not qualified contracts."

    print("\nTest Passed: Put Credit Spread created successfully.")

# Call the test function
test_put_credit_spread()