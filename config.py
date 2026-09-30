import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _get(key, default=None):
    return os.environ.get(key, default)


@dataclass
class Config:
    api_key: str
    api_secret: str
    symbols: list
    formation_weeks: int
    vol_lookback_weeks: int
    target_vol: float
    min_exposure: float
    max_exposure: float
    total_capital_usdt: float
    rebalance_interval_days: int
    poll_interval_seconds: int
    dry_run: bool
    state_file: str
    log_file: str
    log_level: str
    heartbeat_file: str
    ledger_file: str


def load_config() -> Config:
    symbols = [s.strip() for s in _get("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if s.strip()]
    cfg = Config(
        api_key=_get("BINANCE_US_API_KEY", ""),
        api_secret=_get("BINANCE_US_API_SECRET", ""),
        symbols=symbols,
        formation_weeks=int(_get("FORMATION_WEEKS", "4")),
        vol_lookback_weeks=int(_get("VOL_LOOKBACK_WEEKS", "8")),
        target_vol=float(_get("TARGET_VOL", "0.05")),
        min_exposure=float(_get("MIN_EXPOSURE", "0.2")),
        max_exposure=float(_get("MAX_EXPOSURE", "1.0")),
        total_capital_usdt=float(_get("TOTAL_CAPITAL_USDT", "0.0")),
        rebalance_interval_days=int(_get("REBALANCE_INTERVAL_DAYS", "7")),
        poll_interval_seconds=int(_get("POLL_INTERVAL_SECONDS", "3600")),
        dry_run=_get("DRY_RUN", "true").lower() == "true",
        state_file=_get("STATE_FILE", "state.json"),
        log_file=_get("LOG_FILE", "logs/bot.log"),
        log_level=_get("LOG_LEVEL", "INFO"),
        heartbeat_file=_get("HEARTBEAT_FILE", "heartbeat.json"),
        ledger_file=_get("LEDGER_FILE", "trades.csv"),
    )
    if not (0.0 < cfg.min_exposure <= cfg.max_exposure <= 1.0):
        raise RuntimeError("Require 0 < MIN_EXPOSURE <= MAX_EXPOSURE <= 1.0 (spot-only, no leverage)")
    if not cfg.symbols:
        raise RuntimeError("SYMBOLS must list at least one symbol")
    return cfg
