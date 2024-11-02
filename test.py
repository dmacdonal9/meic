from ib_insync import IB, Option
import cfg
from strategies import put_credit_spread
from qualify import qualify_contract
from options import get_closest_strike
from market_data import get_current_mid_price

# Initialize IB instance
ib = IB()
try:
    ib.connect('127.0.0.1', 7497, clientId=2)  # Adjust host, port, and clientId as needed
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

def test_put_credit_spread():
    """
    Test function to verify the put_credit_spread function.
    """
    # Define an example underlying contract (e.g., SPX Index)
    und_contract = qualify_contract(
        symbol='SPX',
        secType='IND',
        exchange='CBOE',
        currency='USD'
    )

    # Define PCS parameters
    opt_expiry = "20241104"  # Format: YYYYMMDD
    current_price = get_current_mid_price(und_contract)
    short_strike = get_closest_strike(und_contract, 'P', opt_expiry,current_price)
    print("Short strike is: ", short_strike)
    long_strike = get_closest_strike(und_contract,'P',opt_expiry, short_strike - cfg.long_put_width)
    print("Long strike is: ", long_strike)

    if short_strike is None or short_strike <= 0:
        print("Invalid short strike price received. Ensure get_current_mid_price returns a valid price.")
        return

    # Call the PCS function
    pcs_bag, pcs_legs = put_credit_spread(und_contract, short_strike, long_strike, opt_expiry)

    # Output results
    print("Put Credit Spread BAG Order:")
    print(pcs_bag)
    print("\nIndividual Qualified Legs:")
    for i, leg in enumerate(pcs_legs, start=1):
        print(f"Leg {i}: {leg}")

    # Verify that both pcs_bag and pcs_legs are returned
    assert pcs_bag is not None, "Failed: BAG order for PCS is None."
    assert isinstance(pcs_legs, list) and len(pcs_legs) == 2, "Failed: PCS legs are not properly returned."
    assert all(isinstance(leg, Option) for leg in pcs_legs), "Failed: PCS legs are not qualified Option contracts."

    print("\nTest Passed: Put Credit Spread created successfully.")

# Execute the test
test_put_credit_spread()
ib.disconnect()
# Execute the test
test_put_credit_spread()
ib.disconnect()