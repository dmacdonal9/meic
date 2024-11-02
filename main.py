import math
from qualify import qualify_contract
from options import get_atm_strike, get_today_expiry, get_closest_strike
from orders import submit_order, calc_combo_model_price
from strategies import iron_condor, put_credit_spread, call_credit_spread
from market_data import get_current_mid_price
from ib_instance import ib
import cfg

def get_current_price(qualified_contract):
    try:
        ticker = ib.reqMktData(qualified_contract, '', snapshot=True)
        ib.sleep(1)
        last_price = ticker.last
        if last_price is None:
            print("No market price available for this contract.")
            return float('nan')

        print(f"Current market price for {qualified_contract.symbol} is {last_price}")
        return last_price
    except Exception as e:
        print(f"Error fetching market price: {e}")
        return float('nan')

# Main program as test stub
if __name__ == '__main__':

    # Dynamically determine today's expiry date
    opt_expiry = get_today_expiry()

    # Qualify SPX and get the current price
    und_contract = qualify_contract(symbol='SPX',secType='IND',exchange='CBOE',currency='USD')

    if und_contract:
        current_mid = get_current_mid_price(und_contract)

        if not math.isnan(current_mid):
            atm_strike = get_atm_strike(und_contract, expiry=opt_expiry, current_price=current_mid, secType='OPT')
            print("ATM Strike:", atm_strike)

            lower_strike_target = current_mid - cfg.long_put_width
            lower_strike = get_closest_strike(und_contract, right='P', expiry=opt_expiry, price=lower_strike_target)

            higher_strike_target = current_mid + cfg.long_call_width
            higher_strike = get_closest_strike(und_contract, right='C', expiry=opt_expiry, price=higher_strike_target)

            if not math.isnan(lower_strike):
                print("Lower Strike:", lower_strike)
            else:
                print("ERROR: Could not determine the lower_strike.")

            if not math.isnan(higher_strike):
                print("Higher Strike:", higher_strike)
            else:
                print("ERROR: Could not determine the higher_strike.")

            # now setup the pcs side
            pcs = put_credit_spread(und_contract,atm_strike,higher_strike,opt_expiry)

            #print(condor)
            condor_price = calc_combo_model_price(condor)
            print(int(condor_price))

            ord_status = submit_order(order_contract=condor,
                                      limit_price=int(condor_price),
                                      action='BUY',
                                      is_live=False,
                                      quantity=1)
            print(ord_status)

    else:
        print("ERROR: Could not determine the front-month contract.")

    ib.disconnect()