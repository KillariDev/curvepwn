

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

#Read by the attack contract from Compound
PRECISION_MUL = [1, 1000000000000, 1000000000000]

#Read from Etherscan for the USDT pool
fee = 4000000
admin_fee = 5000000000 

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

##########################
####MINING PARAMETERS#####
##########################

blockNumber = 11835041
current_ctokens = [ 2236520561601012 ,  3481287597858764 ,  200709219245 ]
LoanAmounts = [ 2000000000000000000000000 ,  2000000000000 ,  2000000000000 ]
funds_avail_ctokens = [ 9492175161208640 ,  9262735174877799 ,  2000000000000 ]
rates = [ 210699862363827219553716955 ,  215918944268682000000000000 ,  1000000000000000000000000000000 ]
totalSupply = 1366582863843277849699307 # total supply of pool tokens
##########################
##########################
##########################

current_ctokens = [ 1757662794027293 ,  3506962588474923 ,  324570592963 ]
totalSupply = 1366582863843277849699307
LoanAmounts = [ 15000000000000000000000000 ,  15000000000000 ,  6000000000000 ]
funds_avail_ctokens = [ 71986950757698170 ,  70250803567106466 ,  21094498755517 ]
rates = [ 210903268827652604936428979 ,  216115143722780000000000000 ,  1000000000000000000000000000000 ]
addLiquidity = [ 71986950757698170 ,  70250803567106466 ,  21094498755517 ]

contract_poolTokens = 0
our_poolTokens = 0
our_balance = []
contract_balance = []

def resetBalances():
    global contract_poolTokens,our_poolTokens,our_balance,contract_balance
    contract_poolTokens = totalSupply
    our_poolTokens = 0
    our_balance = funds_avail_ctokens.copy()
    contract_balance = current_ctokens.copy()

def simAddLiquidity(amounts):
    global contract_poolTokens,our_poolTokens,contract_balance
    (amounts,fees,D1,contract_poolTokens,mint_amount,contract_balance) = solver.add_liquidity(amounts, contract_poolTokens, contract_balance,fee, rates, admin_fee, amp)
    our_balance[0] -= amounts[0]
    our_balance[1] -= amounts[1]
    our_balance[2] -= amounts[2]
    our_poolTokens+=mint_amount
    
def simRemoveLiquidity(poolTokensToRemove):
    global our_balance,our_poolTokens,contract_poolTokens,contract_balance
    (contract_balance,amounts,contract_poolTokens) = solver.remove_liquidity(poolTokensToRemove, [0,0,0], contract_balance, contract_poolTokens)
    our_balance[0] += amounts[0]
    our_balance[1] += amounts[1]
    our_balance[2] += amounts[2]
    our_poolTokens -= poolTokensToRemove

def simTrade(i, j, dx):
    global our_balance,contract_balance
    (our_balance,contract_balance) = solver.exchange(i, j, dx, rates, fee, amp,contract_balance, our_balance,admin_fee)

seed(None)

bestProfit = 0
while(False):
    resetBalances()
    our_initial_balance = funds_avail_ctokens
    fundsIn = sum([CTokensToDollars(our_initial_balance[i],i) for i in range(N_COINS)])
    
    fundsToUseFrac = [uniform(0, 1),uniform(0, 1),uniform(0, 1)]
    fundsToUse = [int(fundsToUseFrac[i]*our_initial_balance[i]) for i in range(N_COINS)]
    add1 = [uniform(0, 1),uniform(0, 1),uniform(0, 1)]
    coinsLeft=[our_initial_balance[i]-fundsToUse[i] for i in range(N_COINS)]
    ti = randint(0,2)
    tj = randint(0,2)
    amountToTrade = randint(0,coinsLeft[ti])
    try:
        attackAdd1 = [int(fundsToUse[i]*add1[i]) for i in range(N_COINS)]
        attackAdd2 = [fundsToUse[i]-attackAdd1[i] for i in range(N_COINS)]
        
        simAddLiquidity(attackAdd1)
        if(ti!=tj and amountToTrade>0):
            simTrade(ti,tj,amountToTrade)
        
        simAddLiquidity(attackAdd2)
        simRemoveLiquidity(our_poolTokens)
        
        fundsOut = sum([CTokensToDollars(our_balance[i],i) for i in range(N_COINS)])
        profit = fundsOut-fundsIn
        if(profit>bestProfit):
            bestProfit=profit
            print('made profit!')
            print(profit)
            #print(attack_balances_c_tokens)
            file = open("profits.txt", "a")
            file.write("PROFIT!\n")
            file.write(str(fundsToUse[0])+', '+str(fundsToUse[1])+', '+str(fundsToUse[2])+'\n')
            
            file.write("add:\n")
            file.write(str(attackAdd1[0])+', '+str(attackAdd1[1])+', '+str(attackAdd1[2])+'\n')
            
            file.write("trade:\n")
            file.write(str(ti)+', '+str(tj)+', '+str(amountToTrade)+'\n')
            
            file.write("add:\n")
            file.write(str(attackAdd2[0])+', '+str(attackAdd2[1])+', '+str(attackAdd2[2])+'\n')
           
            file.write("calc:\n")
            file.write('Funds In: '+str(fundsIn) + '$\n')
            file.write('Funds Out: '+str(fundsOut) + '$\n')
            file.write('profit'+str(profit) + '$\n')
            file.close()
            
    except KeyboardInterrupt:
        exit()
    except:
        continue

#Test: find invalid D for very unbalanced pool, trade on that pool and then trade back. 
iteration = 0
while True: 

    resetBalances()

    our_initial_balance = funds_avail_ctokens
    fundsIn = sum([CTokensToDollars(our_initial_balance[i],i) for i in range(N_COINS)])

    #Current balance of the USDT pool in CTokens

    cdai = current_ctokens[0]
    cusdc = current_ctokens[1]
    cusdt = current_ctokens[2]

    #For easily understandable adjustments
    attack_balances_usd = [1000000,10000000,5000000]

    #Convert to CTokens
    attack_balances_c_tokens = [DollarsToCTokens(attack_balances_usd[0], 0), DollarsToCTokens(attack_balances_usd[1], 1), DollarsToCTokens(attack_balances_usd[2], 2)]

    #Perturb to find an invalid D
    attack_balances_c_tokens = [int(uniform(0.8,1)*attack_balances_c_tokens[0]), int(uniform(0.8,1)*attack_balances_c_tokens[1]), int(uniform(0.8,1)*attack_balances_c_tokens[2])]

    #Convert to TokensPrecision
    attack_balances_tokens_precision = [CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[0], 0), CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[1], 1), CTokensToTokensIncreasedPrecision(attack_balances_c_tokens[2], 2)]

    #Get D for this pool composition
    D = solver.get_D(attack_balances_tokens_precision, amp)
    
    #Check if the D found breaks the invariant
    u = USDTpool(attack_balances_tokens_precision, amp, D)

    #If D doesn't verify the invariant relationship
    if abs(u) > 0:
        try:
            #Find liquidity to add to get the invalid D found

            liquidityToAdd = [attack_balances_c_tokens[i] - current_ctokens[i] for i in range(N_COINS)]

            #Add liquidity into the original pool to get to the exact attack balances found 

            simAddLiquidity(liquidityToAdd)

            #Perform a swap of 40% the original amount of (c)USDC for (c)DAI into that new pool

            #Get amount in
            amountToTradeCUSDC = int(cusdc*0.4)

            #Get the amount out before changing the state of the pool
            amountOutCDAI = solver._exchange(1, 0, current_ctokens, amountToTradeCUSDC, rates, fee, amp)

            #Change state of the pool
            simTrade(1, 0, amountToTradeCUSDC) 

            #Trade the exact amount of (c)DAI obtained back to (c)USDC

            amountBackCUSDC = solver._exchange(0, 1, contract_balance, amountOutCDAI, rates, fee, amp)

            simTrade(0, 1, amountOutCDAI)

            # if iteration % 1000000 == 0:
            #     file = open("check_cdai_in_out.txt", "a")
            #     file.write("CDAI in: " + str(amountToTradeCDAI) + "\n")
            #     file.write("CDAI out " + str(amountBackCDAI) + "\n")
            #     if amountBackCDAI > amountToTradeCDAI:
            #         file.write("OUT/IN: " + str(amountBackCDAI/amountToTradeCDAI) + "\n \n")
            #     elif amountToTradeCDAI > amountBackCDAI: 
            #         file.write("IN/OUT: " + str(amountToTradeCDAI/amountBackCDAI) + "\n \n")
            #     file.close()

            if (amountBackCUSDC > 1.009*amountToTradeCUSDC or amountToTradeCUSDC > 1.009*amountBackCUSDC):

                print("Solution found!")
                
                #Save solution found

                file = open("unbalanced_back_and_forth_trade_attack.txt", "a")
                file.write("Solution found! Swap CUSDC to CDAI back to CUSDC \n")
                if amountBackCUSDC > amountToTradeCUSDC:
                    file.write("OUT/IN: " + str(amountBackCUSDC/amountToTradeCUSDC) + "\n \n")
                elif amountToTradeCUSDC > amountBackCUSDC: 
                    file.write("IN/OUT: " + str(amountToTradeCUSDC/amountBackCUSDC) + "\n \n")
                file.write("Required attack balances: \n \n")
                file.write("CDAI: " + str(attack_balances_c_tokens[0]) + "\n")
                file.write("CUSDC: " + str(attack_balances_c_tokens[1]) + "\n")
                file.write("USDT: " + str(attack_balances_c_tokens[2]) + "\n \n")
                file.write("Amounts to add: \n \n")
                file.write("CDAI: " + str(liquidityToAdd[0]) + "\n")
                file.write("CUSDC: " + str(liquidityToAdd[1]) + "\n") 
                file.write("USDT: " + str(liquidityToAdd[2]) + "\n") 
                simRemoveLiquidity(our_poolTokens)
                fundsOut = sum([CTokensToDollars(our_balance[i],i) for i in range(N_COINS)])
                profit = fundsOut-fundsIn
                file.write("profit: " + str(profit) + "$\n")
                
                file.write("\n_____________________________________________________________ \n \n")
                
                file.close()

                #LATER: Withdraw liquidity and do absolute profit calculations, but if we find a case where we get 1% more out than we put in it's already good enough
        except KeyboardInterrupt:
            exit()
        except:
            continue    
        iteration += 1 