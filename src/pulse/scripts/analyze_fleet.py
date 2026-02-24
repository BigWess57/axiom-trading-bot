import csv
import argparse
import json
from typing import Dict, List, Any
from pathlib import Path

def analyze_fleet_logs(csv_path: str, min_trades: int = 10, top_n: int = 20, configs_path: str = None):
    """
    Analyzes the Shadow Fleet trade logs.
    Groups trades by strategy_id and calculates key performance metrics.
    """
    path = Path(csv_path)
    if not path.exists():
        print(f"Error: Log file not found at {csv_path}")
        return

    # Load configs if provided
    configs_data = {}
    if configs_path:
        cp = Path(configs_path)
        if cp.exists():
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    configs_data = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load configs from {configs_path}: {e}")
        else:
            print(f"Warning: Config file not found at {configs_path}")
            
    # strategy_id -> list of trades
    strategies_data: Dict[str, List[Dict[str, Any]]] = {}
    
    # Read CSV
    try:
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                strat_id = row['strategy_id']
                if strat_id not in strategies_data:
                    strategies_data[strat_id] = []
                strategies_data[strat_id].append(row)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    # Calculate metrics
    results = []
    
    for strat_id, trades in strategies_data.items():
        trade_count = len(trades)
        
        # Apply Statistical Significance Filter
        if trade_count < min_trades:
            continue
            
        total_pnl = 0.0
        winning_trades = 0
        total_fees = 0.0
        max_loss = 0.0
        max_win = 0.0
        
        for trade in trades:
            profit = float(trade['profit'])
            total_pnl += profit
            total_fees += float(trade['fees_paid'])
            
            if profit > 0:
                winning_trades += 1
                max_win = max(max_win, profit)
            else:
                max_loss = min(max_loss, profit)
                
        win_rate = (winning_trades / trade_count) * 100 if trade_count > 0 else 0
        
        results.append({
            'strategy_id': strat_id,
            'trades': trade_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'max_win': max_win,
            'max_loss': max_loss,
            'avg_pnl_per_trade': total_pnl / trade_count if trade_count > 0 else 0
        })

    # Sort primarily by Total PnL (descending)
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    # Print Results
    print(f"\n{'='*90}")
    print(f"FLEET ANALYTICS REPORT ({len(strategies_data)} Total Strategies evaluated)")
    print(f"Showing Top {top_n} strategies with at least {min_trades} trades.")
    print(f"{'='*90}")
    
    header = f"{'Strategy ID':<15} | {'Trades':<8} | {'Win Rate':<10} | {'Total PnL':<10} | {'Max Win':<10} | {'Max Loss':<10}"
    print(header)
    print("-" * 90)
    
    displayed = 0
    for res in results:
        if displayed >= top_n:
            break
            
        print(f"{res['strategy_id']:<15} | {res['trades']:<8} | {res['win_rate']:>6.1f}%   | {res['total_pnl']:>10.4f} | {res['max_win']:>10.4f} | {res['max_loss']:>10.4f}")
        
        # Print Config if available
        if configs_data and res['strategy_id'] in configs_data:
            c = configs_data[res['strategy_id']]
            # Format some key parameters in a readable way
            print(f"    ↳ SL: {int(c.get('stop_loss_pct', 0)*100)}% | TP: {int(c.get('take_profit_pct', 0)*100)}% | Max Hold: {int(c.get('max_holding_time', 0)/60)}m | Min MC: {c.get('min_market_cap', 0):.0f} | Base Conf: {c.get('baseline_confidence_score', 0)}")
            print(f"    ↳ T_High: {c.get('holder_safety_threshold_high', 0)} | T_Low: {c.get('holder_safety_threshold_low', 0)} | Penalty (LHS): {c.get('confidence_penalty_low_holder_safety', 0)}")
            print(f"    ↳ Boost (HA): {c.get('confidence_boost_high_activity', 0)} | Boost (BP): {c.get('confidence_boost_buying_pressure', 0)} | TxnsReq: {c.get('min_txns_for_boost', 0)} | LB(s): {c.get('activity_lookback_seconds', 0)}")
            print("-" * 90)
            
        displayed += 1
        
    if displayed == 0:
        print("No strategies met the minimum trade count criteria.")
    print(f"{'='*90}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Shadow Fleet trading logs.")
    parser.add_argument("csv_path", help="Path to the shadow_trades.csv log file")
    parser.add_argument("--min_trades", type=int, default=10, help="Minimum number of trades to be included in ranking")
    parser.add_argument("--top_n", type=int, default=20, help="Number of top strategies to display")
    parser.add_argument("--configs_path", default="src/pulse/trading/fleet/logs/fleet_configs.json", help="Path to the JSON configs mapping file")
    
    args = parser.parse_args()
    analyze_fleet_logs(args.csv_path, args.min_trades, args.top_n, args.configs_path)
