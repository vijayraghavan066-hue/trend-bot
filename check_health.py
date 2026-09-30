import json
import time

with open("heartbeat.json") as f:
    hb = json.load(f)

age = time.time() - hb["timestamp"]
print(f"Last update:    {time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(hb['timestamp']))} UTC ({age:.0f}s ago)")
print(f"Mode:           {hb['mode']}")
print(f"Last rebalance: {time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(hb['last_rebalance_ts'])) if hb['last_rebalance_ts'] else 'never yet'}")
print(f"Total realized: {hb['total_realized_pnl']:+.4f} USDT")
for sym, a in hb["assets"].items():
    print(f"  {sym:<10} price={a['price']:<12.4f} exposure={a['exposure']:.2f} "
          f"qty={a['qty']:.6f} mtm=${a['mtm_value']:.2f} realized={a['realized_pnl']:+.2f}")

if age > 7200:
    print(f"\nWARNING: heartbeat is {age:.0f}s old (>2h) — bot may be stuck")
else:
    print("\nOK: bot is alive and updating on schedule")
