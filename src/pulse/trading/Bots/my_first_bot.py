"""
This is a simple example of a trading bot that trades based on ?? (first test)
"""
import asyncio
import logging

from typing import Literal
from datetime import datetime

from src.pulse.trading.base_bot import BaseTradingBot
from src.pulse.tracker import PulseTracker
from src.pulse.types import PulseToken, SellReason, TradeResult, TradeTakenInformation, SellCategory, TokenState
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.pulse.trading.strategies.core_strategy import CoreStrategy
from src.pulse.trading.dashboard_connector import DashboardConnector
from src.pulse.trading.Bots.bot_extensions import BotExtensionsMixin


from src.utils.connection_helpers import connect_with_retry
from src.config.pulse_filters import DEFAULT_PULSE_FILTERS
from src.utils.async_utils import bridge_callback

from axiomtradeapi.websocket.client import AxiomTradeWebSocketClient

from src.config.default_strategy import get_whole_config, get_strategy_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



class ExampleTradingBot(BaseTradingBot, BotExtensionsMixin):
    """Trades based on ?? (first test)"""

    def __init__(self, config):
        super().__init__(config)
        self.tracker = PulseTracker()
        self.ws_client = None
        self.ws_client_sol_price = None
        self.current_sol_price = 0
        self.current_balance = config['starting_balance']
        
        # Concurrency Control
        self.api_semaphore = asyncio.Semaphore(4) # Limit concurrent background API calls

        self.tokens: dict[str, TokenState] = {}

        # Initialize strategy
        strategy_config_dict = get_strategy_config()
        self.strategy_config = StrategyConfig(strategy_config_dict)
        self.strategy = CoreStrategy(config=self.strategy_config, get_sol_price=lambda: self.current_sol_price)
        
        # TUI setup
        self.enable_tui = config.get('enable_tui', False)
        self.tui = None
        if self.enable_tui:
            from src.pulse.trading.terminal_ui.trading_bot_tui import TradingBotTUI
            self.tui = TradingBotTUI(self)

        # Dashboard Connector
        self.dashboard_connector = DashboardConnector()
        self.enable_dashboard = config['enable_dashboard']

    #### Analysis Methods
    def analyze_opportunity(self, state: TokenState):
        """Analyze token state for signals"""
        active_trades_count = sum(1 for t in self.tokens.values() if t.active_trade)
        
        should_buy, position_size_for_buy, confidence = self.strategy.should_buy(state)
        if should_buy and active_trades_count < 5:
            logger.info(f"🚀 BUY SIGNAL for {state.token.ticker} (Size: {position_size_for_buy:.2f} SOL, Confidence: {confidence:.2f})")
            self.execute_trade("BUY", state.token.pair_address, position_size_for_buy=position_size_for_buy)

    def manage_trade(self, trade_info: TradeTakenInformation, state: TokenState):
        """Manage current trades"""
        sell_reason = self.strategy.should_sell(trade_info, state)
        if sell_reason:
            self.execute_trade("SELL", trade_info.token_bought_snapshot.pair_address, sell_reason=sell_reason, sell_market_cap=trade_info.current_market_cap)


    #### Execution Method
    def execute_trade(self, signal: Literal["BUY", "SELL"], pair_address: str, sell_reason: SellReason = None, position_size_for_buy: float = 0.0, sell_market_cap: float = None):
        if self.is_currently_traded(pair_address) and signal == "BUY":
            print(f"Token {pair_address} is already traded. Not executing the trade.")
            return
        if not self.is_currently_traded(pair_address) and signal == "SELL":
            print(f"Token {pair_address} is not traded. Not executing the trade.")
            return

        print(f"🚀 Executing trade for token: {pair_address}")
        print(f"   Signal: {signal}")
        print()
        
        # Ensure TokenState exists (redundant check but safe)
        if pair_address not in self.tokens:
            logger.error(f"Token {pair_address} does not exist. Not executing the trade.")
            return
        state = self.tokens[pair_address]
        token = state.token
        
        if signal == "BUY":
            current_mc_usd = token.market_cap * self.current_sol_price
            state.active_trade = TradeTakenInformation(
                token_bought_snapshot=token,
                buy_market_cap=current_mc_usd,
                time_bought=datetime.now(),
                position_size=position_size_for_buy,
                current_market_cap=current_mc_usd
            )
            print(f"✅ Bought {token.pair_address} at ${current_mc_usd} MC at {datetime.now()} (Size: {position_size_for_buy} SOL)\n")
            
            buy_fees = self.calculate_fees(position_size_for_buy)
            self.current_balance -= (position_size_for_buy + buy_fees)
            
        elif signal == "SELL":
            if state.active_trade:
                # Use stored position size
                trade_position_size = state.active_trade.position_size
                
                # Calculate profit ratio
                if not sell_market_cap:
                    logger.warning(f"No sell market cap provided for {token.pair_address}. Using current market cap.")
                    sell_market_cap = token.market_cap * self.current_sol_price
                current_mc_usd = sell_market_cap
                profit_ratio = current_mc_usd / state.active_trade.buy_market_cap
                
                # Calculate Values
                gross_sell_value = trade_position_size * profit_ratio
                sell_fees = self.calculate_fees(gross_sell_value)
                net_sell_value = gross_sell_value - sell_fees
                
                self.current_balance += net_sell_value
                
                time_bought = state.active_trade.time_bought
                time_sold = datetime.now()
                print(f"✅ Sold {token.pair_address} at ${current_mc_usd} MC at {time_sold}")

                buy_fees = self.calculate_fees(trade_position_size)
                total_fees = buy_fees + sell_fees
                net_profit = net_sell_value - trade_position_size - buy_fees # Subtract original cost and buy fees

                result = TradeResult(
                    pair_address=token.pair_address,
                    token_ticker=token.ticker,
                    token_name=token.name,
                    profit=net_profit,
                    fees_paid=total_fees,
                    sell_reason=sell_reason,
                    time_bought=time_bought,
                    time_sold=time_sold,
                    buy_market_cap=state.active_trade.buy_market_cap,
                    sell_market_cap=current_mc_usd,
                    position_size=trade_position_size
                )
                state.past_trades.append(result)
                self.log_trade(result)
                
                # Clear active trade
                state.active_trade = None

    def is_currently_traded(self, pair_address: str):
        """Check if token is currently traded"""
        return pair_address in self.tokens and self.tokens[pair_address].active_trade is not None


    #### Callbacks
    async def on_token_update(self, token: PulseToken):
        """Emit token update event."""
        # Get or Create State
        if token.pair_address not in self.tokens:
            self.tokens[token.pair_address] = TokenState(token=token)
        state = self.tokens[token.pair_address]
        
        state.token = token
        
        # ATH Live Update
        current_mc_usd = token.market_cap * self.current_sol_price
        if current_mc_usd > state.ath_market_cap:
            state.ath_market_cap = current_mc_usd
            # print(f"🚀 New ATH for {token.ticker}: ${state.ath_market_cap:.2f}")
        
        # Snapshot
        self._record_snapshot(token, state)

        # Logic: Handle Trade or Analyze
        if state.active_trade:
            # Update active trade info with latest market cap data
            updated_trade_info = state.active_trade._replace(current_market_cap=current_mc_usd)
            state.active_trade = updated_trade_info
            self.manage_trade(updated_trade_info, state)
        else:
            self.analyze_opportunity(state)

    async def on_new_token(self, token: PulseToken):
        """Emit new token event."""
        print("TOKEN NEW : ", token.pair_address)
        
        # Ensure state exists or create it
        if token.pair_address not in self.tokens:
            self.tokens[token.pair_address] = TokenState(token=token)
        state = self.tokens[token.pair_address]
        
        # --- ATH Tracking: Initial Calculation ---
        asyncio.create_task(self._fetch_initial_ath(token, state))
        
        # --- Value Security Check (Holders) ---
        # We run this just for logging/scoring purposes now, not blocking
        asyncio.create_task(self._get_top_holders(token))
        
        self.analyze_opportunity(state)

    async def on_token_removed(self, category: str, pair_address: str):
        """Emit token removed event."""
        print("TOKEN REMOVED : ", category, pair_address)
        if self.is_currently_traded(pair_address):
            # We know it exists if is_currently_traded is true
            trade_taken_information = self.tokens[pair_address].active_trade
            if trade_taken_information:
                # Attempt to get the latest transaction to update the price before selling
                try:
                    print(f"📉 Rug/Removal detected for {pair_address}. Fetching latest price...")
                    loop = asyncio.get_running_loop()
                    last_tx = await loop.run_in_executor(None, self.client.get_last_transaction, pair_address)
                    
                    if last_tx and 'priceSol' in last_tx:
                        latest_price_sol = float(last_tx['priceSol'])
                        if latest_price_sol > 0:
                            trade_taken_information.current_market_cap = latest_price_sol * trade_taken_information.token.total_supply
                            print(f"Updated Market Cap to {trade_taken_information.current_market_cap:.4f} SOL based on latest tx price: {latest_price_sol:.10f} SOL")

                except Exception as e:
                    print(f"⚠️ Failed to fetch last transaction for {pair_address}: {e}")

                reason = SellReason(
                    category=SellCategory.TOKEN_REMOVED,
                    details=f"Removed from {category}"
                )
                self.execute_trade("SELL", trade_taken_information.token.pair_address, sell_reason=reason, sell_market_cap=trade_taken_information.current_market_cap)
                
    async def on_sol_price_update(self, price: float):
        """Emit SOL price update event."""
        self.current_sol_price = price
        logger.debug(f"SOL Price: ${price:.3f}")

    ##### WebSocket Connection
    async def handle_websocket_connection(self):
        """Handle websocket connection - runs both Pulse and SOL price as concurrent tasks."""
        # Setup Pulse tracker callbacks
        self.tracker.on_update = bridge_callback(self.on_token_update)
        self.tracker.on_new_token = bridge_callback(self.on_new_token)
        self.tracker.on_token_removed = bridge_callback(self.on_token_removed)

        # Pulse WebSocket subscription
        async def do_subscribe_pulse(ws_client: AxiomTradeWebSocketClient):
            return await ws_client.subscribe_to_pulse(
                filters=DEFAULT_PULSE_FILTERS,
                data_callback=self.tracker.process_message
            )

        # SOL Price WebSocket subscription
        async def do_subscribe_sol_price(ws_client: AxiomTradeWebSocketClient):
            return await ws_client.subscribe_sol_price(
                callback=self.on_sol_price_update
            )
        
        # Run Pulse connection
        async def run_pulse_connection():
            logger.info("Starting Pulse WebSocket connection...")
            success, self.ws_client, self.client = await connect_with_retry(do_subscribe_pulse)
            if success:
                logger.info("✅ Pulse connected!")
                await self.ws_client.ensure_connection_and_listen()
            else:
                logger.error("❌ Pulse connection failed.")
        
        # Run SOL Price connection
        async def run_sol_price_connection():
            logger.info("Starting SOL Price WebSocket connection...")
            success, self.ws_client_sol_price, _ = await connect_with_retry(do_subscribe_sol_price)
            if success:
                logger.info("✅ SOL Price connected!")
                await self.ws_client_sol_price.ensure_connection_and_listen()
            else:
                logger.error("❌ SOL Price connection failed.")

        # Run both connections concurrently
        await asyncio.gather(
            run_pulse_connection(),
            run_sol_price_connection()
        )

    async def broadcast_to_dashboard(self):
        """Background task to broadcast state to dashboard"""
        while True:
            try:
                if not self.enable_dashboard:
                    await asyncio.sleep(5)
                    continue

                stats = self.get_statistics()

                # Format active trades
                active_trades = [
                    self._format_active_trade(state.active_trade)
                    for state in self.tokens.values()
                    if state.active_trade is not None
                ]

                # Format recent trades
                recent_trades = [
                    {
                        "pair_address": trade.pair_address,
                        "token_ticker": trade.token_ticker,
                        "token_name": trade.token_name,
                        "profit": trade.profit,
                        "fees_paid": trade.fees_paid,
                        "sell_reason": {
                            "category": trade.sell_reason.category.value,
                            "details": trade.sell_reason.details
                        } if trade.sell_reason else None,
                        "time_bought": trade.time_bought.isoformat(),
                        "time_sold": trade.time_sold.isoformat(),
                        "buy_market_cap": trade.buy_market_cap,
                        "sell_market_cap": trade.sell_market_cap
                    }
                    for trade in reversed(self.trades_today[-50:])
                ]

                state = {
                    "stats": {
                        "total_trades": stats['total_trades'],
                        "winning_trades": stats['winning_trades'],
                        "losing_trades": stats['losing_trades'],
                        "win_rate": stats['win_rate'],
                        "total_profit": stats['total_profit'],
                        "total_fees_paid": stats['total_fees_paid'],
                        "runtime": stats['runtime'],
                        "balance": self.current_balance
                    },
                    "active_trades": active_trades,
                    "recent_trades": recent_trades
                }

                await self.dashboard_connector.send_update(state)
                await asyncio.sleep(1) # Update every second

            except Exception as e:
                logger.error(f"Error in dashboard broadcast: {e}")
                await asyncio.sleep(5)

    ##### Main Run Method
    async def run(self):
        """Start the example trading bot"""
        if not self.enable_tui:
            print("🚀 Example Trading Bot Started")
            print("🔍 Monitoring pulse and SOL price...")
            print("\nPress Ctrl+C to stop\n")

        try:
            tasks = [self.handle_websocket_connection()]
            
            if self.enable_tui and self.tui:
                tasks.append(self.tui.run())
            
            if self.enable_dashboard:
                tasks.append(self.broadcast_to_dashboard())
                
            await asyncio.gather(*tasks)
        finally:
            # Cleanup on shutdown
            if hasattr(self, 'ws_client') and self.ws_client and self.ws_client.ws:
                await self.ws_client.ws.close()
            if hasattr(self, 'ws_client_sol_price') and self.ws_client_sol_price and self.ws_client_sol_price.ws:
                await self.ws_client_sol_price.ws.close()
            
            await self.dashboard_connector.close()
            
            # Print trading stats
            print("\n\n FINAL BALANCE: ", self.current_balance)
            self.print_statistics()

# Run the bot
async def main():
    """Run the example trading bot"""
    
    config = get_whole_config()
    
    bot = ExampleTradingBot(config)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")