/****** Token ******/
export interface PulseToken {
  // Basic Identity (indices 0-7)
  pair_address: string;
  token_address: string;
  creator: string;
  name: string;
  ticker: string;
  image: string | null;
  chain_id: number;
  protocol: string | null;
  
  // Socials & Info (indices 9-11, 46)
  website: string | null;
  twitter: string | null;
  telegram: string | null;
  creator_name: string | null;
  
  // Holder Analysis (indices 13-17, 28)
  top10_holders_percent: number;
  dev_holding_percent: number;
  snipers_percent: number;
  insiders_percent: number;
  bundled_percent: number;
  holders: number;
  
  // Financial Metrics (indices 18-20, 27)
  volume_total: number;
  market_cap: number;
  fees_paid: number;
  total_supply: number;
  
  // Activity (indices 23-25, 29)
  txns_total: number;
  buys_total: number;
  sells_total: number;
  pro_traders_count: number;
  
  // Timestamps (indices 30, 34)
  migrated_at: string | null;
  created_at: string | null;
  
  // Dev Info (indices 33, 41)
  dev_tokens_migrated: number;
  dev_tokens_created: number;
  
  // Social Metrics (indices 40, 45, 47)
  famous_kols: number;
  active_users_watching: number;
  twitter_followers: number;
  
  // Category tracking
  category: string | null; // "newPairs", "finalStretch", or "migrated"
  
  // Debug fields for manual field mapping
  raw_fields?: Record<string, any>;
}

export type TokenCategory = "finalStretch" | "newPairs" | "migrated";

export interface TokenRemovedEvent {
  category: string;
  pair_address: string;
  token_address: string;
}

/****** Trades Info ******/
export interface TradeInfo {
  token: PulseToken;
  entry_mc: number;
  pnl_pct: number;
  pnl_absolute: number;
  time_bought: string;
}

export interface TradeResult {
  pair_address: string;
  token_ticker: string;
  token_name: string;
  profit: number;
  fees_paid: number;
  sell_reason?: SellReason;
  time_bought: string; // ISO format
  time_sold: string; // ISO format
  buy_market_cap?: number;
  sell_market_cap?: number;
}

export type SellCategory = 
  | "category_change" 
  | "security_failed" 
  | "stop_loss" 
  | "take_profit" 
  | "max_hold_time"
  | "token_removed";

export interface SellReason {
  category: SellCategory;
  details?: string;
}

export interface Candle {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
}


/****** Stats ******/
export interface BotStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit: number;
  total_fees_paid: number;
  runtime: number;
  balance: number;
}


/****** States ******/
export interface TokenState {
  token: PulseToken;
  active_trade?: TradeInfo;
  past_trades: TradeResult[];
}

export interface BotState {
  stats: BotStats;
  active_trades: TradeInfo[];
  recent_trades: TradeResult[];
}



