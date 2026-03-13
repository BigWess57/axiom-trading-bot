import sqlite3
import argparse
import json
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime

def analyze_fleet_logs(db_path: str, min_trades_per_hour: float = 5.0, top_n: int = 20, configs_path: str = None, baseline_mode: bool = False):
    """
    Analyzes the Shadow Fleet trade logs.
    Groups trades by strategy_id and calculates key performance metrics.
    """
    path = Path(db_path)
    if not path.exists():
        print(f"Error: Database file not found at {db_path}")
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
    
    # Read SQLite
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate duration
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trades")
        min_ts_str, max_ts_str = cursor.fetchone()
        
        total_hours = 0.0
        if min_ts_str and max_ts_str:
            try:
                # Timestamps are ISO formatted
                min_ts = datetime.fromisoformat(min_ts_str.replace('Z', '+00:00'))
                max_ts = datetime.fromisoformat(max_ts_str.replace('Z', '+00:00'))
                total_hours = (max_ts - min_ts).total_seconds() / 3600.0
            except Exception as e:
                print(f"Warning: Failed to parse timestamps for duration: {e}")
        
        # If run was extremely short or parsing failed, default to at least 1 hour for rate calculation
        effective_hours = max(total_hours, 1.0)
        min_trades = max(1, int(min_trades_per_hour * effective_hours))
        
        cursor.execute("SELECT strategy_id, profit, fees_paid, exit_reason FROM trades")
        for row in cursor.fetchall():
            strat_id = row['strategy_id']
            if strat_id not in strategies_data:
                strategies_data[strat_id] = []
            strategies_data[strat_id].append({
                'profit': row['profit'], 
                'fees_paid': row['fees_paid'],
                'exit_reason': row['exit_reason']
            })
        conn.close()
    except Exception as e:
        print(f"Failed to read SQLite DB: {e}")
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
        exit_reasons_count: Dict[str, int] = {}
        
        for trade in trades:
            profit = float(trade['profit'])
            total_pnl += profit
            total_fees += float(trade['fees_paid'])
            
            # Extract main category from exit reason (e.g., "SellCategory.STOP_LOSS: hit -25%" -> "STOP_LOSS")
            raw_reason = trade.get('exit_reason', 'UNKNOWN')
            if raw_reason and ':' in raw_reason:
                category = raw_reason.split(':')[0].replace('SellCategory.', '')
            else:
                category = str(raw_reason).replace('SellCategory.', '')
            
            exit_reasons_count[category] = exit_reasons_count.get(category, 0) + 1
            
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
            'avg_pnl_per_trade': total_pnl / trade_count if trade_count > 0 else 0,
            'exit_reasons': exit_reasons_count
        })

    # Sort primarily by Total PnL (descending)
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    # Print Results
    print(f"\n{'='*120}")
    print(f"FLEET ANALYTICS REPORT ({len(strategies_data)} Total Strategies evaluated)")
    print("BASELINE MODE" if baseline_mode else "CORE MODE")
    print(f"Run Duration: {total_hours:.2f} hours")
    print(f"Showing Top {top_n} strategies with at least {min_trades} trades ({min_trades_per_hour} trades/hr).")
    print(f"{'='*120}")
    
    header = f"{'Strategy ID':<15} | {'Trades':<8} | {'Win Rate':<10} | {'Total PnL':<10} | {'Max Win':<10} | {'Max Loss':<10} | {'Total Fees':<10}"
    print(header)
    print("-" * 120)
    
    displayed = 0
    for res in results:
        if displayed >= top_n:
            break
            
        print(f"{res['strategy_id']:<15} | {res['trades']:<8} | {res['win_rate']:>6.1f}%   | {res['total_pnl']:>10.4f} | {res['max_win']:>10.4f} | {res['max_loss']:>10.4f} | {res['total_fees']:>10.4f}")
        
        # Print Exit Reasons
        reasons_str = " | ".join([f"{k}: {v}" for k, v in sorted(res['exit_reasons'].items(), key=lambda item: item[1], reverse=True)])
        print(f"    [EXITS] {reasons_str}")
        
        # Print Config if available
        if configs_data and res['strategy_id'] in configs_data:
            c = configs_data[res['strategy_id']]
            if baseline_mode:
                print(f"    [RISK] SL: {int(c.get('initial_stop_loss_pct', 0)*100)}% | TP: {int(c.get('max_take_profit_pct', 0)*100)}% | Max Hold: {int(c.get('max_holding_time', 0)/60)}m | Min MC: {c.get('min_market_cap', 0):.0f}")
                print(f"    [MOMENTUM] Min Txns/min: {c.get('min_txns_per_min', 0)} | Min B/S Ratio: {c.get('min_buy_sell_ratio', 0):.1f} | Min Users Watch Inc: {c.get('min_users_watching_increase', 0)} | Lookback(s): {c.get('activity_lookback_seconds', 0)}")
                print(f"    [SAFETY] Holder Min SOL: {c.get('min_holder_sol_balance', 0)} | Safe Threshold: {c.get('holder_safe_threshold', 0)}")
            else:
                # Format some key parameters in a readable way
                print(f"    [RISK] SL: {int(c.get('initial_stop_loss_pct', 0)*100)}% | TP: {int(c.get('max_take_profit_pct', 0)*100)}% | Max Hold: {int(c.get('max_holding_time', 0)/60)}m | Min MC: {c.get('min_market_cap', 0):.0f} | Base Buy Conf: {c.get('baseline_confidence_score', 0)}")
                print(f"    [HOLDING] Min Hold Conf: {c.get('min_hold_confidence_score', 0)} | Vel Penalty: {c.get('hold_penalty_velocity_death', 0)} | Hype Pen: {c.get('hold_penalty_hype_death', 0)} | Esc Pen: {c.get('hold_penalty_holder_exodus', 0)}")
                print(f"    [SAFETY] T_High: {c.get('holder_safety_threshold_high', 0)} | T_Low: {c.get('holder_safety_threshold_low', 0)} | Penalty (LHS): {c.get('confidence_penalty_low_holder_safety', 0)}")
                print(f"    [BOOSTS] Boost (HA): {c.get('confidence_boost_high_activity', 0)} | Boost (BP): {c.get('confidence_boost_buying_pressure', 0)} | Txns/mReq: {c.get('min_txns_per_min_for_boost', 0)} | LB(s): {c.get('activity_lookback_seconds', 0)}")
            print("-" * 120)
            
        displayed += 1
        
    if displayed == 0:
        print("No strategies met the minimum trade count criteria.")
    print(f"{'='*120}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Shadow Fleet tracking logs.")
    parser.add_argument("db_path", help="Path to the shadow_run_*.db SQLite file")
    parser.add_argument("--min_trades_per_hour", type=float, default=5.0, help="Minimum number of trades per hour to be included in ranking")
    parser.add_argument("--top_n", type=int, default=20, help="Number of top strategies to display")
    parser.add_argument("--configs_path", default="data/config_logs/fleet_configs.json", help="Path to the JSON configs mapping file")
    
    parser.add_argument("--baseline", action="store_true", help="Format output for baseline strategies")
    
    args = parser.parse_args()
    analyze_fleet_logs(args.db_path, args.min_trades_per_hour, args.top_n, args.configs_path, args.baseline)
