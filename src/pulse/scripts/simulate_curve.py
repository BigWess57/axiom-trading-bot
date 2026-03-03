# Pump.fun CPAMM Simulation

# Constants
INITIAL_VIRTUAL_SOL = 30.0
INITIAL_VIRTUAL_TOKEN = 1_073_000_000.0
K = INITIAL_VIRTUAL_SOL * INITIAL_VIRTUAL_TOKEN # 32.19 Billion

# Graduation Target
GRADUATION_REAL_SOL = 85.0
GRADUATION_VIRTUAL_SOL = INITIAL_VIRTUAL_SOL + GRADUATION_REAL_SOL # 115.0

print(f"K Constant: {K}")
print(f"--- Curve Simulation ---")

# Simulate points along the curve
for real_sol in [0, 10, 20, 30, 42.5, 50, 60, 70, 80, GRADUATION_REAL_SOL]:
    virtual_sol = INITIAL_VIRTUAL_SOL + real_sol
    virtual_token = K / virtual_sol
    
    # Price is (virtual_sol_reserves / virtual_token_reserves)
    price_in_sol = virtual_sol / virtual_token
    
    # Total supply is always 1_000_000_000
    market_cap_sol = price_in_sol * 1_000_000_000
    
    # The curve percentage is the ratio of real SOL added vs graduation goal
    curve_pct = (real_sol / GRADUATION_REAL_SOL) * 100
    
    print(f"Curve: {curve_pct:5.1f}% | Real SOL diff: {real_sol:4.1f} | Tokens in Curve: {virtual_token:13.1f} | Price (SOL): {price_in_sol:.10f} | MC (SOL): {market_cap_sol:6.1f}")
SOL = 88.0 # usd per sol
# What happens to MC as we approach the end?
print("\nLet's map Curve % to MC(SOL):")
for curve_pct in [10, 20, 30, 40, 50, 60, 70, 80, 90, 98, 100]:
    real_sol = GRADUATION_REAL_SOL * (curve_pct / 100.0)
    virtual_sol = INITIAL_VIRTUAL_SOL + real_sol
    virtual_token = K / virtual_sol
    price_in_sol = virtual_sol / virtual_token
    market_cap_sol = price_in_sol * 1_000_000_000
    print(f"{curve_pct:3.0f}% Curve = {market_cap_sol:6.1f} SOL MC ({market_cap_sol * SOL:6.1f} USD)")
