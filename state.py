import json
import os
from dataclasses import dataclass, field


@dataclass
class AssetState:
    symbol: str
    qty: float = 0.0
    cost_basis: float = 0.0  # avg price paid for current qty, 0 if flat
    capital_allocated: float = 0.0
    current_exposure: float = 0.0  # 0.0-1.0, last-set target
    realized_pnl: float = 0.0

    def to_dict(self):
        return {"symbol": self.symbol, "qty": self.qty, "cost_basis": self.cost_basis,
                "capital_allocated": self.capital_allocated,
                "current_exposure": self.current_exposure, "realized_pnl": self.realized_pnl}

    @staticmethod
    def from_dict(d):
        return AssetState(**d)


@dataclass
class BotState:
    assets: dict = field(default_factory=dict)  # symbol -> AssetState
    last_rebalance_ts: float = 0.0
    total_realized_pnl: float = 0.0

    def to_dict(self):
        return {"assets": {k: v.to_dict() for k, v in self.assets.items()},
                "last_rebalance_ts": self.last_rebalance_ts,
                "total_realized_pnl": self.total_realized_pnl}

    @staticmethod
    def from_dict(d):
        return BotState(
            assets={k: AssetState.from_dict(v) for k, v in d.get("assets", {}).items()},
            last_rebalance_ts=d.get("last_rebalance_ts", 0.0),
            total_realized_pnl=d.get("total_realized_pnl", 0.0),
        )


def load_state(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return BotState.from_dict(json.load(f))


def save_state(path: str, state: BotState):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)
    os.replace(tmp_path, path)
