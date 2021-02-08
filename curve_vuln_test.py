

from random import seed
from random import randint
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

def USDTpool(xp, amp, D):
    '''
    Return f(D)
    '''
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
coins = [int(351794.69*1e18),int(689185.73*1e18),int(382505.53*1e18)]
D = get_D(coins, amp)
print(coins)
print(D)
print(USDTpool(coins, amp, D))

if True:
    seed(1)
    best_val = 0
    while True:
        coins = [randint(0, 2**53-1),randint(0, 2**53-1),randint(0, 2**53-1)]
        value = get_I(coins,amp)
        if(value > best_val):
            best_val = value
            print(best_val)
        if(value > 255):
            D = get_D(coins, amp)
            print(coins, "diff:", USDTpool(coins, amp, D))
