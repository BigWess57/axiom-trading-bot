import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("ShadowRecorder")

@dataclass
class ShadowTradeRecord:
    """
    Represents a single trade taken by a virtual bot.
    """
    strategy_id: str
    token_symbol: str
    token_address: str
    entry_price: float
    exit_price: float
    pnl_percent: float
    profit: float
    fees_paid: float
    duration_seconds: float
    exit_reason: str
    entry_confidence: float
    timestamp: str  # ISO format
    # token_snapshot_json: str = "" # Optional: JSON string of TokenSnapshot at entry

class ShadowRecorder:
    """
    Logs shadow trades to a CSV file.
    """
    def __init__(self, log_dir: str = "data/shadow_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a new log file for this session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(log_dir, f"shadow_trades_{timestamp}.csv")
        self._initialize_csv()

    def _initialize_csv(self):
        """Write header if file is empty"""
        try:
            with open(self.filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = [field for field in ShadowTradeRecord.__annotations__]
                writer.writerow(headers)
        except Exception as e:
            logger.error(f"Failed to init shadow log: {e}")

    def log_trade(self, record: ShadowTradeRecord):
        """Append a trade record"""
        try:
            with open(self.filepath, 'a', newline='') as f:
                writer = csv.writer(f)
                # Ensure values are in correct order matches dataclass
                values = [getattr(record, field) for field in ShadowTradeRecord.__annotations__]
                writer.writerow(values)
        except Exception as e:
            logger.error(f"Failed to log shadow trade: {e}")
