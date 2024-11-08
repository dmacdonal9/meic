import math
from qualify import qualify_contract, get_front_month_contract, get_front_month_contract_date
from options import get_atm_strike, get_today_expiry, get_closest_strike, get_option_by_target_price
from strategies import put_credit_spread, call_credit_spread
from market_data import get_current_mid_price, get_combo_prices
from ib_instance import ib
from orders import submit_adaptive_order_trailing_stop
import cfg
import sys


# Main program as test stub
if __name__ == '__main__':

    # Dynamically determine today's expiry date
    opt_expiry = get_today_expiry()

    # Qualify SPX and get the current price
    #und_contract = qualify_contract(symbol='SPX',secType='IND',exchange='CBOE',currency='USD')
    und_contract = qualify_contract(symbol='SPX',secType='IND',exchange='CBOE',currency='USD')


    if und_contract:
        current_mid = get_current_mid_price(und_contract)
        print("Current Price:", current_mid)

        contract_details = ib.reqContractDetails(und_contract)
        min_tick = contract_details[0].minTick

        if not math.isnan(current_mid):
            atm_strike = get_atm_strike(und_contract, expiry=opt_expiry, current_price=current_mid, secType='OPT')
            print("ATM Strike:", atm_strike)

            lower_contract, lower_put_opt_price = get_option_by_target_price(und_contract=und_contract, right='P',
                                                                             expiry=opt_expiry,
                                                                             target_price=float('0.05'),
                                                                             atm_strike=atm_strike)
            lower_strike = lower_contract.strike

            higher_contract, higher_call_opt_price = get_option_by_target_price(und_contract=und_contract, right='C',
                                                                                expiry=opt_expiry,
                                                                                target_price=float('0.05'),
                                                                                atm_strike=atm_strike)

            higher_strike = higher_contract.strike

            if not math.isnan(lower_strike):
                print("Lower Strike:", lower_strike)
            else:
                print("ERROR: Could not determine the lower_strike.")

            if not math.isnan(higher_strike):
                print("Higher Strike:", higher_strike)
            else:
                print("ERROR: Could not determine the higher_strike.")

            # PCS
            pcs, pcs_legs = put_credit_spread(und_contract,atm_strike,lower_strike,opt_expiry)
            print("PCS LEGS: ", pcs_legs)
            pcs_bid, pcs_mid, pcs_ask = get_combo_prices(pcs_legs)
            print("PRICES: ", pcs_bid, pcs_mid, pcs_ask)
            pcs_stop_loss_amt = round(abs(pcs_mid) / cfg.spx_min_tick) * cfg.spx_min_tick
            print("STOP LOSS AMT: ", pcs_stop_loss_amt)

            # CCS
            ccs, ccs_legs = call_credit_spread(und_contract,atm_strike,higher_strike,opt_expiry)
            print("CCS LEGS: ", ccs_legs)
            ccs_bid, ccs_mid, ccs_ask = get_combo_prices(ccs_legs)
            print("PRICES: ", ccs_bid, ccs_mid, ccs_ask)
            ccs_stop_loss_amt = round(abs(ccs_mid) / cfg.spx_min_tick) * cfg.spx_min_tick
            print("STOP LOSS AMT: ", ccs_stop_loss_amt)

            # ok, now let's submit a sell order for the pcs side
            pcs_order_status = submit_adaptive_order_trailing_stop(order_contract=pcs,
                                                                     limit_price=abs(pcs_bid),
                                                                     order_type = 'LMT',
                                                                     action='SELL',
                                                                     is_live=True,
                                                                     quantity=1,
                                                                     stop_loss_amt=pcs_stop_loss_amt
                                                                     )
            # ok, now let's submit a sell order for the ccs
            ccs_order_status = submit_adaptive_order_trailing_stop(order_contract=ccs,
                                                                     limit_price=abs(ccs_bid),
                                                                     order_type='LMT',
                                                                     action='SELL',
                                                                     is_live=True,
                                                                     quantity=1,
                                                                     stop_loss_amt=ccs_stop_loss_amt
                                                                     )

    else:
        print("ERROR: Could not qualify the underlying contract.")

    ib.disconnect()