"""
    In this game, you act as a market maker against four players. Each player (including you) has a number 
    between 1 and 10 (inclusive) and your job is to make markets on the SUM of the all five numbers.

    There are ten rounds of markets, and they happen FAST! So incorporate new information as you receive and quote
    as quickly as possible before time runs out.  

    Your quote is sent to all opponents SIMULTANEOUSLY and their response is sent back to you SIMULTANEOUSLY and PUBLICALLY. 
    This means opponents can see ALL transactions in previous rounds (but not in the current round). 

    Opponents trade exactly one unit at a time and are allowed to not trade (should your quote be bad). 

    At the end of the game, the numbers are revealed and your score is set. 

    Original game: https://github.com/sameerlal/OMakeMeAMarket

"""
from ctypes.wintypes import HINSTANCE
from multiprocessing.pool import MapResult
import random
from time import sleep
from uuid import RESERVED_FUTURE
from anyio import open_cancel_scope

from yaml import parse
import constants
from strats import *



class Player:
    def __init__(self, name):
        ## Attributes Unique to Each Player
        self.identifier = name
        self.secret = random.randrange(constants.MIN_SECRET,constants.MAX_SECRET+1)
        ## Pnl related        
        self.cash  = 0 # Current Cash Balance
        self.stock = 0 # Current Stock Balance
        self.pnl   = 0 # Realized pnl
        ## Record Keeping
        self.past_transactions = []

    def transact(self, price, qty, ctpy):
        self.past_transactions.append({"ctpy": ctpy, "price": price, "qty":qty})
        self.cash += -price*qty
        self.stock += qty
        if(self.stock == 0):
            self.pnl  += self.cash
            self.cash = 0
        return True
    
    def get_balance(self, stringify=False):
        data =  {"cash": self.cash, "stock": self.stock, "pnl": self.pnl}
        if(stringify):
            return f"cash: {self.cash}\tstock: {self.stock}\tpnl: {self.pnl}"
        return data


class MarketMaker(Player):
    def __init__(self, name):
        super().__init__(name)

class History:
    """"
        All past transactions, useful for opponents.
        
        TODO!
    """
    def __init__(self):
        self.past_transactions = []


def parse_quote(quote):
    try:
        bid, ask = quote.strip().split("@")
        return int(bid), int(ask)
    except:
        print("Malformed quote...no quote")
    return

def update_mm(market_maker : MarketMaker, response, bid, ask):
    if(response == Response.HIT):
        # mm is BUYING
        return market_maker.transact(price=bid, qty=1, ctpy=opp.identifier)
    elif(response == Response.LIFT):
        # mm is SELLING
        return market_maker.transact(price=ask, qty=-1,  ctpy=opp.identifier)
    else:
        return True

def update_opp(opp, response, bid, ask):
    if(response == Response.HIT):
        # opp is SELLING
        opp.transact(price=bid, qty=-1, ctpy=opp.identifier)
    elif(response == Response.LIFT):
        # opp is BUYING
        opp.transact(price=ask, qty=1, ctpy=opp.identifier)
    else:
        return True


if __name__ == "__main__":
    ## Set Up Players
    market_maker = MarketMaker(name="User")
    opponents = [] 
    for opp in range(constants.NUM_OPPONENTS):
        opponents.append( BaselineStrat(f"{opp}") )
    history = History()

    ## Preamble
    print("Secret numbers have been assigned!")
    

    print(f"There are a total of {constants.NUM_OPPONENTS} opponents and {constants.NUM_ROUNDS} rounds")
    print(f"Secret numbers are between {constants.MIN_SECRET} and {constants.MAX_SECRET} inclusive. ")
    print("Your secret number is below: ")
    print(f">>>>>>>>>>{market_maker.secret}<<<<<<<<<<")
    print(f"Make a market on: {market_maker.secret} + SUM(all {constants.NUM_OPPONENTS} opponents secret numbers)")
    ack = input("Press enter when you are ready")

    print("Game starting in 3")
    sleep(1)
    print("Game starting in 2")
    sleep(1)
    print("Game starting in 1")
    sleep(1)

    prompt = """Enter a quote in "bid@ask" format """
    prompt2 = f"Market Make: {market_maker.secret} + SUM({constants.NUM_OPPONENTS} opponent secret numbers)"

    print("-"*90)
    print("|", " "*88, "|")
    print("|", " "*88, "|")
    spacing = (86 - len(prompt) ) // 2
    print("|", " "*spacing, prompt ," "*spacing, "|")
    print("|", " "*88, "|")
    print("|", " "*88, "|")
    spacing2 = (86 - len(prompt2) ) // 2
    print("|", " "*spacing2, prompt2 ," "*spacing2, "|")
    print("|", " "*88, "|")
    print("-"*90)
    

    ## Begin Game 
    for i in range(1, constants.NUM_ROUNDS+1):
        print("\n", "*"*25, f"Round {i}", "*"*25)
        quote = input("Enter a quote>")
        bid, ask = parse_quote(quote)

        ## Present quote to opponents
        for opp in opponents:
            response = opp.get_action(bid,ask, history)
            ## Do transaction
            update_mm(market_maker, response, bid, ask)
            update_opp(opp, response, bid, ask)
            ## Print player
            if(constants.HARD_MODE):
                o_stock = "Hidden"
                o_price = "Hidden"
            else:
                o_stock = opp.stock
                o_price = opp.cash / abs(o_stock) if o_stock != 0 else 0
            pp =  bid if(response == Response.HIT) else ask if response == Response.LIFT else "--"
            print(f"|\tPlayer: {opp.identifier} {response} @ {pp} \t\t Current position: {o_stock}@{o_price}")
            
        print("-" * 47)
        
        print("Your stats:\t", market_maker.get_balance(stringify=True))
    
    ## End Game
    print("*"*20, "Statistics", "*"*20)
    print("Revealing secret numbers...")
    sleep(1)
    fv = market_maker.secret
    for opp in opponents:
        print(f"Player {opp.identifier}: {opp.secret}")
        fv += opp.secret
        sleep(0.5)
    print(f"This means the fair value is:  {fv} ")
    print("Computing your total pnl....")
    sleep(2)
    if(market_maker.stock > 0):
        print(f"You have {market_maker.stock} stocks")
        print(f"Exchanging your stock for cash...")
        market_maker.cash += market_maker.stock*fv
        market_maker.stock -= market_maker.stock
        market_maker.pnl += market_maker.cash
    if(market_maker.stock < 0):
        print(f"You are short {market_maker.stock} stock")
        print(f"Covering your short position...")
        market_maker.cash += market_maker.stock*fv
        market_maker.stock -= market_maker.stock
        market_maker.pnl += market_maker.cash
    sleep(0.5)
    print(f"Total pnl: >>>||  {market_maker.pnl}  ||<<<")
    # print("+"*60)
    # print("+", " " * 12, "coming soon!", " " * 12, "+")
    # print("+"*60)