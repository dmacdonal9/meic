import math
from qualify import get_front_month_contract_date, get_front_month_contract, qualify_contract
from options import get_atm_strike, get_today_expiry, get_closest_strike
from orders import submit_order
from strategies import iron_condor
from market_data import calc_combo_model_price
from ib_instance import ib

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

    front_month_contract_date = get_front_month_contract_date('ES', 'CME', '50', expiry=opt_expiry)
    front_month_contract = get_front_month_contract(symbol='ES', exchange='CME', multiplier='50', currency='USD', lastTradeDateOrContractMonth=front_month_contract_date)

    if front_month_contract:
        current_price = get_current_price(front_month_contract)

        if not math.isnan(current_price):
            atm_strike = get_atm_strike(front_month_contract, expiry=opt_expiry, current_price=current_price, secType='FOP')
            print("ATM Strike:", atm_strike)

            lower_strike_target = current_price - 75
            lower_strike = get_closest_strike(front_month_contract, sectype='FOP', right='P', expiry=opt_expiry, price=lower_strike_target)

            higher_strike_target = current_price + 75
            higher_strike = get_closest_strike(front_month_contract, sectype='FOP', right='C', expiry=opt_expiry, price=higher_strike_target)

            if not math.isnan(lower_strike):
                print("Lower Strike:", lower_strike)
            else:
                print("ERROR: Could not determine the lower_strike.")

            if not math.isnan(higher_strike):
                print("Higher Strike:", higher_strike)
            else:
                print("ERROR: Could not determine the higher_strike.")

            # now try to qualify all 4 contracts
            condor = iron_condor(front_month_contract,atm_strike,lower_strike,higher_strike,opt_expiry)
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