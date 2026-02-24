"""
Base class for all trading bots
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from src.pulse.types import PulseToken, TradeResult, TokenState

logger = logging.getLogger(__name__)


class BaseTradingBot(ABC):
    """Base class for all trading bots"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        
        # Risk management
        self.max_position_size = config.get('max_position_size', 1.0)
        self.max_daily_trades = config.get('max_daily_trades', 50)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.05)
        
        # Statistics
        self.trades_today : list[TradeResult] = []
        self.total_profit = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees_paid = 0
        self.start_time = datetime.now()
        
        logger.info(f"✅ {self.__class__.__name__} initialized")
    
    @abstractmethod
    def analyze_opportunity(self, state: TokenState):
        """
        Analyze trading opportunity and generate signal
        Returns: dict with 'action' ('buy'/'sell'/'hold') and 'confidence' (0-1)
        """
        pass
    
    @abstractmethod
    def execute_trade(self, signal: Literal["BUY", "SELL"], token: PulseToken):
        """Execute the trade based on signal"""
        pass
    
    async def check_risk_limits(self, proposed_trade):
        """Verify trade doesn't violate risk limits"""
        
        # Check daily trade limit
        if len(self.trades_today) >= self.max_daily_trades:
            logger.warning("⚠️  Daily trade limit reached")
            return False
        
        # Check position size
        if proposed_trade['size'] > self.max_position_size:
            logger.warning(f"⚠️  Position size {proposed_trade['size']} exceeds limit")
            return False
        
        # Check wallet balance
        if self.client is None:
            logger.warning("⚠️  Client not initialized")
            return False
        else:
            balance = self.client.GetBalance(proposed_trade['wallet'])
            if balance['sol'] < proposed_trade['size']:
                logger.warning("⚠️  Insufficient balance")
                return False
        
        return True
    
    def log_trade(self, trade_result: TradeResult):
        """Log trade execution and update statistics"""
        self.trades_today.append(trade_result)
        
        if trade_result.profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.total_profit += trade_result.profit
        self.total_fees_paid += trade_result.fees_paid
        
        logger.debug(f"📝 Trade logged: {trade_result}")
    
    def get_statistics(self):
        """Get bot performance statistics"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'total_fees_paid': self.total_fees_paid,
            'runtime': (datetime.now() - self.start_time).total_seconds()
        }
    
    def print_statistics(self):
        """Print bot statistics"""
        stats = self.get_statistics()
        
        print(f"\n📊 BOT STATISTICS")
        print(f"   Total Trades: {stats['total_trades']}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total Profit: {stats['total_profit']:.6f} SOL")
        print(f"   Total Fees Paid: {stats['total_fees_paid']:.6f} SOL")
        print(f"   Runtime: {stats['runtime']:.0f}s")
        # self.print_trades_today()
    
    def print_trades_today(self):
        """Print trades taken today"""
        print(f"\n📝 TRADES TODAY")
        for trade in self.trades_today:
            print(f"   {trade}")
    
    @abstractmethod
    async def run(self):
        """Main bot loop"""
        pass