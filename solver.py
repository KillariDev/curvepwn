N_COINS = 3
PRECISION_MUL = [1, 1000000000000, 1000000000000]

FEE_DENOMINATOR = 10 ** 10
PRECISION = 10 ** 18

MAX_ADMIN_FEE = 10 * 10 ** 9
MAX_FEE = 5 * 10 ** 9

MAX_A = 10 ** 6
MAX_A_CHANGE = 10
A_PRECISION = 100
amp = 2000

ADMIN_ACTIONS_DELAY = 3 * 86400
MIN_RAMP_TIME = 86400

def get_D(xp, amp):
    '''
    xp = Balances in underlying tokens with increased precision = TokensPrecision unit
    '''
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

def _xp(current_balances, rates):
    '''
    Converts cTokens into Tokens by multiplying by their respective rates, read from the Compound contract
    '''
    result = rates.copy()
    for i in range(N_COINS):
        result[i] = result[i] * current_balances[i] // PRECISION
    return result

def get_y(i, j, x, _xp, amp):
    '''
    i = position of the token that we put in 
    j = position of the token that we want to get out 
    x = new balance after adding the amount of tokens we put in 
    xp = current balances of the pool
    amp = scaled amplification factor (A*n**(n-1))
    '''
    # x in the input is converted to the same price/precision

    assert (i != j) and (i >= 0) and (j >= 0) and (i < N_COINS) and (j < N_COINS)

    D = get_D(_xp, amp)
    c = D
    S_ = 0
    Ann = amp * N_COINS

    _x = 0
    for _i in range(N_COINS):
        if _i == i:
            _x = x
        elif _i != j:
            _x = _xp[_i]
        else:
            continue
        S_ += _x
        c = c * D // (_x * N_COINS)
    c = c * D // (Ann * N_COINS)
    b = S_ + D // Ann  # - D
    y_prev = 0
    y = D
    for _i in range(255):
        y_prev = y
        y = (y*y + c) // (2 * y + b - D)
        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                break
        else:
            if y_prev - y <= 1:
                break
    return y

def get_dy(i, j, xp, dx, amp, rates, fee):
    '''
    Slightly modified from the contracts, get the amount out from the amount given in. Removed precision stuff for now. See line 370. https://github.com/curvefi/curve-contract/blob/master/contracts/pools/usdt/StableSwapUSDT.vy

    i = position of the token that we put in 
    j = position of the token that we want to get out 
    x = new balance after adding the amount of tokens we put in 
    xp = current balances of the pool
    amp = scaled amplification factor (A*n**(n-1))
    '''
    # dx and dy in c-units
    #rates: uint256[N_COINS] = self._stored_rates()
    xp = _xp(xp, rates)

    x = xp[i] + dx * rates[i] // PRECISION
    y = get_y(i, j, x, xp, amp)
    dy = (xp[j] - y) * PRECISION // rates[j]
    _fee = fee * dy // FEE_DENOMINATOR
    return dy - _fee

def _exchange(i, j, xp, dx, rates, fee, amp):
    '''
    See Curve USDT pool contract line 425
    i = index of token in
    j = index of token out 
    xp = current balances
    dx = amount in (in cTokens)
    rates = current exchange rate of cTokens to Tokens
    returns: dy = amount out (in cTokens)
    '''
    # dx and dy are in c-tokens

    xp = _xp(xp.copy(), rates)

    x = xp[i] + dx * rates[i] // PRECISION
    y = get_y(i, j, x, xp, amp)
    dy = xp[j] - y
    dy_fee = dy * fee // FEE_DENOMINATOR

    #Updates the balances, not needed to look for an appropriate dx
    # dy_admin_fee = dy_fee * admin_fee // FEE_DENOMINATOR
    #self.balances[i] = x * PRECISION / rates[i]
    #self.balances[j] = (y + (dy_fee - dy_admin_fee)) * PRECISION / rates[j]

    _dy = (dy - dy_fee) * PRECISION // rates[j]

    return _dy
     