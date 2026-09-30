import json
import time


def write_heartbeat(path, cfg, state, prices):
    total_value = sum(a.capital_allocated - (a.qty * a.cost_basis - a.qty * prices.get(s, a.cost_basis))
                       for s, a in state.assets.items())
    mtm_value = sum(a.qty * prices.get(s, a.cost_basis) + (a.capital_allocated - a.qty * a.cost_basis)
                     for s, a in state.assets.items())
    payload = {
        "timestamp": time.time(),
        "mode": "DRY_RUN" if cfg.dry_run else "LIVE",
        "last_rebalance_ts": state.last_rebalance_ts,
        "total_realized_pnl": state.total_realized_pnl,
        "assets": {
            s: {
                "price": prices.get(s),
                "qty": a.qty,
                "exposure": a.current_exposure,
                "capital_allocated": a.capital_allocated,
                "mtm_value": a.qty * prices.get(s, 0.0) + (a.capital_allocated - a.qty * a.cost_basis),
                "realized_pnl": a.realized_pnl,
            } for s, a in state.assets.items()
        },
    }
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    import os
    os.replace(tmp, path)
