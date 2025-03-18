0/659
import pandas as pd
from itertools import combinations

def data():
    wip = pd.read_csv('WIP_merge.csv')
    xtime = pd.read_csv('XFER_TIME.csv').set_index(['FROM', 'TO'])
    cart = pd.read_csv('CART.csv').set_index('CART_ID')
    wip['R_time'] = wip['Remaining Q-Time'] - wip.apply(
        lambda row: xtime.get((row['FROM'], row['TO']), pd.Series({'XFER_TIME': 0}))['XFER_TIME'], 
        axis=1
    )
    return wip.sort_values(by='R_time'), xtime, cart

def route(mode, wip1, wip2, xtime, cart_loc):
    paths = {
        "PDPD": [cart_loc, wip1['FROM'], wip1['TO'], wip2['FROM'], wip2['TO']],
        "PPDD": [cart_loc, wip1['FROM'], wip2['FROM'], wip1['TO'], wip2['TO']]
    }
    route = paths[mode]
    
    times = [xtime.loc[(route[i], route[i+1]), 'XFER_TIME'] if (route[i], route[i+1]) in xtime.index else 0 
             for i in range(len(route) - 1)]
    total_time = sum(times)

    if mode == "PDPD":
        wip1_success = sum(times[:2]) <= wip1['Remaining Q-Time']
        wip2_success = total_time <= wip2['Remaining Q-Time']
    else:  # PPDD
        delivery_time1 = times[0] + times[1] + times[2]
        delivery_time2 = delivery_time1 + times[3]
        wip1_success = delivery_time1 <= wip1['Remaining Q-Time']
        wip2_success = delivery_time2 <= wip2['Remaining Q-Time']
    
    return total_time, bool(wip1_success), bool(wip2_success)

def best_pair(available_wips, xtime, cart):
    best_combination = None
    best_mode = None
    min_loss = float('inf')
    min_time = float('inf')

    for (idx1, wip1), (idx2, wip2) in combinations(available_wips.iterrows(), 2):
        for cart_id in cart.index:
            cart_loc = cart.loc[cart_id, 'INIT_LOC']
            for mode in ["PDPD", "PPDD"]:
                total_time, wip1_success, wip2_success = route(mode, wip1, wip2, xtime, cart_loc)
                loss = 2 - (wip1_success + wip2_success)

                if (loss < min_loss) or (loss == min_loss and total_time < min_time):
                    min_loss = loss
                    min_time = total_time
                    best_combination = (idx1, idx2, cart_id)
                    best_mode = mode

    return best_combination, best_mode, min_loss, min_time

def main():
    wip, xtime, cart = data()
    assigned_wips = set()
    results = []
    
    available_wips = wip.copy()
    
    while len(available_wips) >= 2:
        best_combination, mode, min_loss, min_time = best_pair(available_wips, xtime, cart)
        if not best_combination:
            break
        
        idx1, idx2, cart_id = best_combination
        wip1, wip2 = available_wips.loc[idx1], available_wips.loc[idx2]
        cart_loc = cart.loc[cart_id, 'INIT_LOC']

        # 執行最佳選擇的搬運模式
        total_time, wip1_success, wip2_success = route(mode, wip1, wip2, xtime, cart_loc)

        # 更新 cart 位置
        cart.at[cart_id, 'INIT_LOC'] = wip2['TO']

        assigned_wips.update([idx1, idx2])
        results.append((cart_id, wip1['WIP_ID'], wip2['WIP_ID'], mode, total_time, wip1_success, wip2_success))

        # 移除已分配的 WIP
        available_wips = available_wips.drop([idx1, idx2])

    success_count = sum(r[5] + r[6] for r in results)
    total_wips = len(assigned_wips)
    total_time_used = sum(r[4] for r in results)

    print(f"Total Loss: {total_wips - success_count}")
    print(f"Total Time: {total_time_used}")
    
    for r in results:
        print(f"Cart {r[0]} | WIP {r[1]} & {r[2]} | Mode: {r[3]} | Time: {r[4]} | Success: {r[5], r[6]}")

if __name__ == "__main__":
    main()
