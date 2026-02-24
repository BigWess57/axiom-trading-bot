import asyncio
import os
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from axiomtradeapi.websocket.client import AxiomTradeWebSocketClient
from src.pulse.tracker import PulseTracker, PulseToken
from src.config.pulse_filters import DEFAULT_PULSE_FILTERS
from src.utils.connection_helpers import connect_with_retry

class PulseTUI:
    """
    A simple TUI for the Pulse Tracker.
    """
    def __init__(self):
        self.console = Console()
        self.tracker = PulseTracker()
        self.layout = Layout()
        self.client: Optional[AxiomTradeWebSocketClient] = None
        self.running = False
        
        # Connect tracker callback
        self.tracker.on_update = self._on_token_update
        self.tracker.on_new_token = self._on_new_token
        self.tracker.on_token_removed = self._on_token_removed
        
        # State for UI
        self.status_msg = "Initializing..."
        self.msg_count = 0
        self.last_update = datetime.now()

    def _on_token_update(self, token: PulseToken):
        self.msg_count += 1
        self.last_update = datetime.now()
        # In a complex TUI we might optimize render, but Live handles it

    def _on_new_token(self, token: PulseToken):
        self.msg_count += 1
        self.status_msg = f"New Token: {token.ticker}!"

    def _on_token_removed(self, category: str, pair_address: str):
        self.msg_count += 1
        self.status_msg = f"Token Removed: {pair_address[:6]}... ({category})"

    def generate_header(self) -> Panel:
        """Create the header panel"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        title = Text("🔮 Axiom Pulse Tracker", style="bold magenta")
        status = Text(f"Status: {self.status_msg} | Msgs: {self.msg_count}", style="green")
        
        grid.add_row(title, status)
        return Panel(grid, style="white on blue")

    def generate_table(self) -> Table:
        """Create the main token table"""
        table = Table(expand=True, box=box.ROUNDED, header_style="bold cyan")
        
        table.add_column("Token", ratio=2)
        table.add_column("Price/MCap", justify="right", ratio=1)
        table.add_column("Vol (5m)", justify="right", ratio=1)
        table.add_column("Liq", justify="right", ratio=1)
        table.add_column("Dev %", justify="right", ratio=1)
        table.add_column("Insiders", justify="right", ratio=1)
        table.add_column("Holders", justify="right", ratio=1)
        table.add_column("Txns", justify="right", ratio=1)
        table.add_column("Smart Money", justify="right", ratio=1)
        
        # Get tokens and sort
        tokens = self.tracker.get_all_tokens()
        # Sort by creation time (newest first) by default
        # or maybe sort by MCap? Let's do newest first for "Pulse" feel
        tokens.sort(key=lambda x: x.created_at if x.created_at else "", reverse=True)
        
        for t in tokens[:20]: # Show top 20
            # Name & Ticker
            name_text = Text(f"{t.name} ", style="white")
            name_text.append(f"({t.ticker})", style="yellow")
            if t.website or t.twitter or t.telegram:
                name_text.append(" 🔗", style="blue")
            
            # MCap (Colorize nicely)
            mcap_style = "green" if t.market_cap > 100000 else "white"
            mcap_str = f"{t.market_cap:,.0f} SOL"
            
            # Vol
            vol_str = f"{t.volume_5m:,.0f} SOL"
            
            # Dev Holding (Red if high)
            dev_style = "red" if t.dev_holding_percent > 10 else "green"
            
            # Render Row
            table.add_row(
                name_text,
                Text(mcap_str, style=mcap_style),
                vol_str,
                f"${t.liquidity:,.0f}",
                Text(f"{t.dev_holding_percent:.1f}%", style=dev_style),
                f"{t.insiders_percent:.1f}%",
                str(t.holders),
                f"{t.txns_5m} ({t.buys_5m}/{t.sells_5m})",
                f"{t.kols_count} KOL | {t.pro_traders_count} Pro"
            )
            
        return table

    def generate_layout(self) -> Layout:
        """Generate the layout"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["header"].update(self.generate_header())
        self.layout["body"].update(self.generate_table())
        self.layout["footer"].update(Panel(Text(f"Last Update: {self.last_update.strftime('%H:%M:%S')} | Press Ctrl+C to quit"), style="dim"))
        return self.layout

    async def run(self):
        """Main run loop"""
        
        async def do_subscribe(ws_client):
            # Manually hook up new_pairs JSON callback
            # ws_client._callbacks["new_pairs"] = self.tracker.process_json_message
            
            return await ws_client.subscribe_to_pulse(
                filters=DEFAULT_PULSE_FILTERS, 
                data_callback=self.tracker.process_message
            )

        self.status_msg = "Connecting..."
        
        # Start Live Display
        with Live(self.generate_layout(), refresh_per_second=4, screen=True) as live:
            success, ws_client = await connect_with_retry(do_subscribe)
            
            if success:
                self.status_msg = "Connected"
                self.running = True
                
                # IMPORTANT: Start the handler task!
                handler_task = asyncio.create_task(ws_client.ensure_connection_and_listen())
                
                try:
                    while self.running:
                        # Update layout data
                        live.update(self.generate_layout())
                        await asyncio.sleep(0.25)
                except KeyboardInterrupt:
                    pass
                finally:
                    handler_task.cancel()
                    await ws_client.ws.close()
            else:
                self.status_msg = "Connection Failed"
                live.update(self.generate_layout())
                await asyncio.sleep(3)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    tui = PulseTUI()
    try:
        asyncio.run(tui.run())
    except KeyboardInterrupt:
        print("Goodbye!")
