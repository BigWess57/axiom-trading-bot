import asyncio
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


class TradingBotTUI:
    """Terminal UI for monitoring trading bot activity"""
    
    def __init__(self, bot):
        """
        Initialize TUI with bot instance
        
        Args:
            bot: ExampleTradingBot instance to monitor
        """
        self.bot = bot
        self.console = Console()
        self.layout = Layout()
        self.running = False
        self.last_update = datetime.now()
    
    def generate_header(self) -> Panel:
        """Create the header panel with bot stats"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        # Left side: Bot name and status
        title = Text("🤖 Trading Bot Monitor", style="bold magenta")
        
        # Right side: Key stats
        stats = self.bot.get_statistics()
        balance_color = "green" if self.bot.current_balance >= self.bot.config['starting_balance'] else "red"
        pnl_color = "green" if self.bot.total_profit > 0 else "red"
        
        status_text = Text()
        status_text.append(f"Balance: ", style="white")
        status_text.append(f"{self.bot.current_balance:.3f} SOL", style=balance_color)
        status_text.append(f" | Trades: {stats['total_trades']}", style="white")
        status_text.append(f" | Win Rate: {stats['win_rate']:.1f}%", style="cyan")
        status_text.append(f" | Total P&L: ", style="white")
        status_text.append(f"{self.bot.total_profit:+.3f} SOL", style=pnl_color)
        
        grid.add_row(title, status_text)
        return Panel(grid, style="white on blue")
    
    def generate_active_trades_table(self) -> Table:
        """Create table showing currently active trades"""
        table = Table(
            expand=True, 
            box=box.ROUNDED, 
            header_style="bold cyan",
            title=f"[bold white]ACTIVE TRADES ({len(self.bot.token_currently_bought)})[/bold white]",
            title_style="bold white"
        )
        
        table.add_column("Token", ratio=2)
        table.add_column("Entry MC", justify="right", ratio=1)
        table.add_column("Current MC", justify="right", ratio=1)
        table.add_column("P&L", justify="right", ratio=1)
        table.add_column("Age", justify="right", ratio=1)
        table.add_column("Status", justify="center", ratio=1)
        
        if not self.bot.token_currently_bought:
            table.add_row("No active trades", "", "", "", "", "")
            return table
        
        for pair_address, trade_info in self.bot.token_currently_bought.items():
            token = trade_info.token
            entry_mc = trade_info.buy_market_cap
            current_mc = token.market_cap
            
            # Calculate P&L percentage
            pnl_pct = ((current_mc - entry_mc) / entry_mc * 100) if entry_mc > 0 else 0
            pnl_color = "green" if pnl_pct > 0 else "red" if pnl_pct < 0 else "white"
            pnl_text = Text(f"{pnl_pct:+.1f}%", style=pnl_color)
            if pnl_pct > 0:
                pnl_text.append(" ✅", style="green")
            elif pnl_pct < -10:
                pnl_text.append(" ⚠️", style="red")
            
            # Calculate age
            age_seconds = (datetime.now() - trade_info.time_bought).total_seconds()
            age_minutes = int(age_seconds // 60)
            age_secs = int(age_seconds % 60)
            age_str = f"{age_minutes}:{age_secs:02d}"
            
            # Token name with ticker
            token_text = Text(f"{token.name[:15]} ", style="white")
            token_text.append(f"({token.ticker})", style="yellow")
            
            table.add_row(
                token_text,
                f"{entry_mc:,.0f}",
                f"{current_mc:,.0f}",
                pnl_text,
                age_str,
                Text("HOLD", style="cyan")
            )
        
        return table
    
    def generate_closed_trades_table(self) -> Table:
        """Create table showing recent closed trades"""
        table = Table(
            expand=True,
            box=box.ROUNDED,
            header_style="bold cyan",
            title=f"[bold white]RECENT CLOSED TRADES ({len(self.bot.trades_today)})[/bold white]",
            title_style="bold white"
        )
        
        table.add_column("Token", ratio=2)
        table.add_column("P&L (SOL)", justify="right", ratio=1)
        table.add_column("P&L %", justify="right", ratio=1)
        table.add_column("Time", justify="right", ratio=1)
        
        if not self.bot.trades_today:
            table.add_row("No closed trades yet", "", "", "")
            return table
        
        # Show last 10 trades
        recent_trades = list(reversed(self.bot.trades_today[-10:]))
        
        for trade in recent_trades:
            # Extract token ticker from pair address (simplified)
            token_name = trade.pair_address[:8] + "..."
            
            # P&L coloring
            pnl_color = "green" if trade.profit > 0 else "red"
            pnl_text = Text(f"{trade.profit:+.4f}", style=pnl_color)
            if trade.profit > 0:
                pnl_text.append(" ✅", style="green")
            else:
                pnl_text.append(" ❌", style="red")
            
            # Calculate P&L percentage (approximate based on max_position_size)
            pnl_pct = (trade.profit / self.bot.config['max_position_size'] * 100) if self.bot.config['max_position_size'] > 0 else 0
            pnl_pct_text = Text(f"{pnl_pct:+.1f}%", style=pnl_color)
            
            # Time
            time_str = trade.time_sold.strftime("%H:%M:%S")
            
            table.add_row(
                token_name,
                pnl_text,
                pnl_pct_text,
                time_str
            )
        
        return table
    
    def generate_layout(self) -> Layout:
        """Generate the complete layout"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="active", ratio=2),
            Layout(name="closed", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["header"].update(self.generate_header())
        self.layout["active"].update(self.generate_active_trades_table())
        self.layout["closed"].update(self.generate_closed_trades_table())
        
        # Footer
        footer_text = Text()
        footer_text.append(f"Last Update: {self.last_update.strftime('%H:%M:%S')}", style="white")
        footer_text.append(" | SOL Price: ", style="dim")
        footer_text.append(f"${self.bot.current_sol_price:.2f}", style="green")
        footer_text.append(" | Press Ctrl+C to quit", style="dim")
        
        self.layout["footer"].update(Panel(footer_text, style="dim"))
        
        return self.layout
    
    async def run(self):
        """Main run loop for TUI"""
        self.running = True
        
        with Live(self.generate_layout(), refresh_per_second=4, screen=True) as live:
            try:
                while self.running:
                    self.last_update = datetime.now()
                    live.update(self.generate_layout())
                    await asyncio.sleep(0.25)
            except KeyboardInterrupt:
                self.running = False
