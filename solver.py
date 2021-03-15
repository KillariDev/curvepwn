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

def get_correct_D(xp, amp):
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
            D_P = D_P * D / (_x * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 0.000001:
                return D
        else:
            if Dprev - D <= 0.00001:
                return D
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    return D


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

def _xp_mem(rates, _balances):
    result= rates.copy()
    for i in range(N_COINS):
        result[i] = result[i] * _balances[i] // PRECISION
    return result

def USDTpool(xp, amp, D):
    '''
    Return f(D), takes xp in TokenPrecision units
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
    
def _exchangeWithUpdate(i, j, dx, rates, fee, amp, balances, admin_fee):
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

    xp = _xp(balances.copy(), rates)

    x = xp[i] + dx * rates[i] // PRECISION
    y = get_y(i, j, x, xp, amp)
    dy = xp[j] - y
    dy_fee = dy * fee // FEE_DENOMINATOR

    #Updates the balances, not needed to look for an appropriate dx
    dy_admin_fee = dy_fee * admin_fee // FEE_DENOMINATOR
    new_balances = balances.copy()
    new_balances[i] = x * PRECISION // rates[i]
    new_balances[j] = (y + (dy_fee - dy_admin_fee)) * PRECISION // rates[j]
    
    if(new_balances[i] < 0):
        raise 'traded too much'
    if(new_balances[j] < 0):
        raise 'traded too much'
    
    _dy = (dy - dy_fee) * PRECISION // rates[j]

    return (new_balances,_dy)

def exchange(i, j, dx, rates, fee, amp, balances, ourFunds, admin_fee):
    (new_balances,dy) = _exchangeWithUpdate(i, j, dx, rates, fee, amp, balances, admin_fee)

    ourFunds[i] -= dx
    if(ourFunds[i]<0):
        raise 'traded too much'
      
    ourFunds[j] += dy
    return (ourFunds,new_balances)


def remove_liquidity(_amount, min_amounts, balances, total_supply):
    amounts = [0,0,0]
    new_balances = balances.copy()
    for i in range(N_COINS):
        value = balances[i] * _amount // total_supply
        if(value < min_amounts[i]):
            raise Exception("Withdrawal resulted in fewer coins than expected")
        new_balances[i] -= value
        amounts[i] = value

    return(new_balances,amounts,total_supply-_amount)
     
def get_D_mem(rates, _balances,amp):
    return get_D(_xp_mem(rates, _balances),amp)
 
def add_liquidity(amounts, totalSupply, balances_c_tokens,fee, rates, admin_fee, amp):
    # Amounts is amounts of c-tokens

    fees= [0,0,0]
    _fee = fee * N_COINS // (4 * (N_COINS - 1))
    _admin_fee = admin_fee

    token_supply =totalSupply
    # Initial invariant
    D0 = 0
    balances = balances_c_tokens.copy()
    old_balances= balances_c_tokens.copy()
    if token_supply > 0:
        D0 = get_D_mem(rates.copy(), old_balances.copy(), amp)
    new_balances = old_balances.copy()

    for i in range(N_COINS):
        if token_supply == 0:
            if(amounts[i] <= 0):
                raise Exception("assert amounts[i] > 0")
        # balances store amounts of c-tokens
        new_balances[i] = old_balances[i] + amounts[i]

    # Invariant after change
    D1 = get_D_mem(rates.copy(), new_balances.copy(), amp)
    if(D1 <= D0):
        raise Exception("assert D1 > D0")

    # We need to recalculate the invariant accounting for fees
    # to calculate fair user's share
    D2 = D1
    if token_supply > 0:
        # Only account for fees if we are not the first to deposit
        for i in range(N_COINS):
            ideal_balance = D1 * old_balances[i] // D0
            difference = 0
            if ideal_balance > new_balances[i]:
                difference = ideal_balance - new_balances[i]
            else:
                difference = new_balances[i] - ideal_balance
            fees[i] = _fee * difference // FEE_DENOMINATOR
            balances[i] = new_balances[i] - fees[i] * _admin_fee // FEE_DENOMINATOR
            new_balances[i] -= fees[i]
        D2 = get_D_mem(rates.copy(), new_balances.copy(), amp)
    else:
        balances = new_balances.copy()

    # Calculate, how much pool tokens to mint
    mint_amount = 0
    if token_supply == 0:
        mint_amount = D1  # Take the dust if there was any
    else:
        mint_amount = token_supply * (D2 - D0) // D0

    # Mint pool tokens
    return(amounts,fees,D1,token_supply + mint_amount,mint_amount,balances)
    
def remove_liquidity_imbalance(amounts, token_supply, fee, admin_fee, rates, balances):
    assert token_supply > 0
    _fee = fee * N_COINS // (4 * (N_COINS - 1))
    _admin_fee = admin_fee

    old_balances = balances.copy()
    new_balances = old_balances.copy()
    D0 = get_D_mem(rates, old_balances, amp)
    for i in range(N_COINS):
        new_balances[i] -= amounts[i]
    D1 = get_D_mem(rates, new_balances, amp)
    for i in range(N_COINS):
        ideal_balance= D1 * old_balances[i] // D0
        difference = 0
        if ideal_balance > new_balances[i]:
            difference = ideal_balance - new_balances[i]
        else:
            difference = new_balances[i] - ideal_balance
        fees = _fee * difference // FEE_DENOMINATOR
        balances[i] = new_balances[i] - fees * _admin_fee // FEE_DENOMINATOR
        new_balances[i] -= fees
    D2 = get_D_mem(rates, new_balances, amp)

    token_amount = (D0 - D2) * token_supply // D0
    assert token_amount > 0
    return(token_amount,balances)

def USDTpool(xp, amp, D):
    '''
    Return f(D), takes xp in TokenPrecision units
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
    
rates = [ 210699862363827219553716955 ,  215918944268682000000000000 ,  1000000000000000000000000000000 ]
def CTokensToTokensIncreasedPrecision(amount, index):
    return rates[index] * amount// PRECISION
    
def isInvalidD(ctokens, amp):
    attack_balances_tokens_precision = [CTokensToTokensIncreasedPrecision(ctokens[0], 0), CTokensToTokensIncreasedPrecision(ctokens[1], 1), CTokensToTokensIncreasedPrecision(ctokens[2], 2)]
    D = get_D(attack_balances_tokens_precision, amp)
    u = USDTpool(attack_balances_tokens_precision, amp, D)
    if abs(u) > 0:
        return True
    return False
    
    
def get_virtual_price(balances,rates,token_supply,amp):
    return get_D(_xp(balances,rates),amp) * PRECISION // token_supply
