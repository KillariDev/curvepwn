

from random import seed
from random import randint
from datetime import datetime

import price_calcs

import numpy as np

N_COINS = 3
PRECISION_MUL = [1, 1000000000000, 1000000000000]

FEE_DENOMINATOR = 10 ** 10
PRECISION = 10 ** 18

MAX_ADMIN_FEE = 10 * 10 ** 9
MAX_FEE = 5 * 10 ** 9

MAX_A = 10 ** 6
MAX_A_CHANGE = 10
A_PRECISION = 100

ADMIN_ACTIONS_DELAY = 3 * 86400
MIN_RAMP_TIME = 86400


def get_D(xp, amp):
    S = 0

    for _x in xp:
        S += _x
    if S == 0:
        return 0

    Dprev = 0
    D = S
    Ann = amp * N_COINS
    for _i in range(255):
        D_P = D
        for _x in xp:
            D_P = D_P * D // (_x * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D // ((Ann - 1) * D + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                return D
        else:
            if Dprev - D <= 1:
                return D
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    return D
def get_I(xp, amp):
    S = 0

    for _x in xp:
        S += _x
    if S == 0:
        return 0

    Dprev = 0
    D = S
    Ann = amp * N_COINS
    for _i in range(255):
        D_P = D
        for _x in xp:
            D_P = D_P * D // (_x * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D // ((Ann - 1) * D + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                return _i
        else:
            if Dprev - D <= 1:
                return _i
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    return 1000


#Expression of the invariant of the USDT pool in the contract code
def USDTpool(xp, amp, D):
    '''
    Return f(D)
    '''
    #amp is already A*n**(n-1)
    Ann = amp*N_COINS
    S = 0
    for _x in xp:
        S += _x
    if S == 0:
        return 0
    P = 1 #product of xi
    for _x in xp:
        P*= _x
    return Ann*S + (1-Ann)*D - (D**(N_COINS+1))/((N_COINS**N_COINS)*P)

amp = 2000
current_values = [int(351794.69*10**18),int(689185.73*10**18),int(382505.53*10**18)]

#Test that we get 0 for the current values in the pool
if False:
    D = get_D(current_values, amp)
    print(USDTpool(current_values, amp, D))

#Test that the spot prices are indeed 1 with the current values in the pool

if False:
    D = get_D(current_values, amp)
    invariant = lambda x : USDTpool(x, amp, D)
    spot1 = price_calcs.getSpotPrice(invariant, current_values, [0,1])
    spot2 = price_calcs.getSpotPrice(invariant, current_values, [0,2])
    spot3 = price_calcs.getSpotPrice(invariant, current_values, [2,1])
    spot_prices_list = [spot1, spot2, spot3]
    print("Spot prices: ", spot_prices_list)

#funds we have a available to try to modify the amounts
funds_avail = int(100000000*10**18)

seed(1452789)
best_val = 1e100
best_i = 0
while False:
    #try to guess a solution
    coins = [randint(0, current_values[0]+funds_avail), 
             randint(0, current_values[1]+funds_avail), 
             randint(0, current_values[2]+funds_avail)]
    #value = get_I(coins,amp)
    D = get_D(coins, amp)
    u = USDTpool(coins, amp, D)
    if abs(u)>0:
        print(coins)
        print(D)
        print(u)
        if abs(u)>0:
            diff = 0
            for i in range(0,3):
                diff += abs(coins[i]-current_values[i])
            if(diff<best_val):
                best_val = diff
                print('Solution found!')
                print(coins)
                print('USDTpool: ', USDTpool(coins, amp, D))
                print('Funds required: ', str(best_val/1e18) )
                print('Mod: ', str((coins[0]-current_values[0])/1e18), 'DAI' )
                print('Mod: ', str(( coins[1]-current_values[1])/1e18), 'USDC' )
                print('Mod: ', str(( coins[2]-current_values[2])/1e18), 'USDT' )

#Test all the values of balances found that result in a non zero invariant and see how the spot price and slippage are affected 

#List of the balances that create an issue
x_sols = [
    
    [2552132800774707953221343, 10954836975766391934268855, 6113261289102574864143845],

    [7383156777655277677397696, 5155991404625698646006209, 22062233463650651502213654],

    [8967941795019332620419554, 28138637197367895309556558, 17034664770329254888272019],

    [44592230509332193904618359, 92540796120217289407249535, 52517614521951134668905555],

    [6021622227921786133247673, 75552623271839259833403773, 30535944814071004252802378],

    [54910346171977265790353180, 47063522501931580992726383, 48715838319124038305979407],

    [55861715979112626728798628, 23288891084785364563789167, 27989134995153369213616087],

    [16335250935896498249124052, 42827395606463253065145007, 39735198056483082551992684]
    
    ]

#Spot price test
if False:
    #List storing all the spot prices pair for each pool that is a solution to our problem
    spot_prices_for_solutions = [] 
    for x in x_sols:
        D = get_D(x, amp)
        invariant = lambda x : USDTpool(x, amp, D)
        #Get all the spot prices of the different pairs with that new invariant
        spot1 = price_calcs.getSpotPrice(invariant, x, [0,1])
        spot2 = price_calcs.getSpotPrice(invariant, x, [0,2])
        spot3 = price_calcs.getSpotPrice(invariant, x, [2,1])
        spot_prices_list = [spot1, spot2, spot3]
        spot_prices_for_solutions.append(spot_prices_list)
    print("Max spot price: ", max(sublist[-1] for sublist in spot_prices_for_solutions))
    print("Min spot price: ", min(sublist[-1] for sublist in spot_prices_for_solutions))

#Slippage test with 
if False:
    #List storing all the slippage between the pairs for each pool that is a solution to our problem
    slippage_solutions = [] 
    for x in x_sols:
        D = get_D(x, amp)
        invariant = lambda x : USDTpool(x, amp, D)
        #Get all the spot prices of the different pairs with that new invariant
        spot1 = price_calcs.getSlippage(invariant, x, 10000000*1e18, [0,1])
        spot2 = price_calcs.getSlippage(invariant, x, 10000000*1e18, [0,2])
        spot3 = price_calcs.getSlippage(invariant, x, 10000000*1e18, [2,1])
        slippage_list = [spot1, spot2, spot3]
        slippage_solutions.append(slippage_list)
    print("Max slippage: ", max(sublist[-1] for sublist in slippage_solutions), "%")

#Verify how profitable a potential attack might be by comparing the new spot price with the slippage for a large order
if False:
    attack_balance = [2294228968411794745296753, 42782828621711901587047913, 7101142569280429938356188]
    D = get_D(attack_balance, amp)
    invariant = lambda x : USDTpool(x, amp, D)
    spot0 = price_calcs.getSpotPrice(invariant, attack_balance, [0,1])
    spot1 = price_calcs.getSpotPrice(invariant, attack_balance, [0,2])
    spot2 = price_calcs.getSpotPrice(invariant, attack_balance, [2,1])
    spot_prices_list = [spot0, spot1, spot2]
    max_spot_deviation = max([abs(x - 1) for x in spot_prices_list])
    index = np.argmax(np.array([abs(x - 1) for x in spot_prices_list]))
    if index == 0:
        slippage = price_calcs.getSlippage(invariant, attack_balance, 1000000*1e18, [0,1])
    elif index == 1: 
        slippage = price_calcs.getSlippage(invariant, attack_balance, 1000000*1e18, [0,2])
    elif index == 2: 
        slippage = price_calcs.getSlippage(invariant, attack_balance, 1000000*1e18, [2,1])
    print("Max spot price deviation: ", 100*max_spot_deviation)
    print("Corresponding slippage: ", slippage)