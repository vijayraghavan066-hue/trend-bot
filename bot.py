"""Weekly, volatility-targeted trend-following across BTC/ETH/SOL.

Not a grid bot -- no price levels. Once a week (REBALANCE_INTERVAL_DAYS),
for each symbol: if the trailing FORMATION_WEEKS return is positive, target
an exposure fraction sized to hit TARGET_VOL of realized weekly volatility
(clipped MIN_EXPOSURE-MAX_EXPOSURE, spot-only so never >1.0x); otherwise
target 0 (flat, in cash). Trades the delta between current and target
holdings via a single market order per symbol per rebalance.

Backtested and validated in PROJECT_STATUS.md before this was written --
see "Different asset class research: BTC/ETH/SOL weekly trend-following".
This is a risk-reduction/drawdown-protection tool, not an alpha strategy:
it consistently cut drawdown in the 2020 COVID crash and 2022 crypto
winter across BTC/ETH/SOL, at the cost of capping upside in monster bull
runs (no leverage available spot-only).
"""
import logging
import math
import time

from binance.client import Client
from binance_client import BinanceUSTrader
from config import load_config
from health import write_heartbeat
from state import AssetState, BotState, load_state, save_state

log = logging.getLogger("trend-bot")


def fetch_weekly_closes(client, symbol, n_weeks):
    days_needed = (n_weeks + 2) * 7
    raw = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, f"{days_needed} day ago UTC")
    daily = [float(k[4]) for k in raw]
    return daily[::7]


def realized_weekly_vol(weekly_closes):
    rets = [weekly_closes[i] / weekly_closes[i - 1] - 1 for i in range(1, len(weekly_closes))]
    if len(rets) < 2:
        return None
    m = sum(rets) / len(rets)
    return math.sqrt(sum((r - m) ** 2 for r in rets) / len(rets))


def target_exposure(weekly_closes, formation_weeks, vol_lookback_weeks, target_vol, min_exp, max_exp):
    if len(weekly_closes) < formation_weeks + 2:
        return 0.0
    formation_ret = weekly_closes[-1] / weekly_closes[-1 - formation_weeks] - 1
    if formation_ret <= 0:
        return 0.0
    vol_window = weekly_closes[-(vol_lookback_weeks + 1):]
    vol = realized_weekly_vol(vol_window)
    if not vol or vol <= 0:
        return min_exp
    return max(min_exp, min(max_exp, target_vol / vol))


def rebalance(cfg, state, traders):
    now_prices = {}
    for symbol in cfg.symbols:
        trader = traders[symbol]
        filters = trader.filters
        price = trader.get_price()
        now_prices[symbol] = price

        weekly = fetch_weekly_closes(trader._client, symbol, cfg.formation_weeks + cfg.vol_lookback_weeks)
        exposure = target_exposure(weekly, cfg.formation_weeks, cfg.vol_lookback_weeks,
                                    cfg.target_vol, cfg.min_exposure, cfg.max_exposure)

        asset = state.assets[symbol]
        target_value = asset.capital_allocated * exposure
        target_qty = filters.round_qty(target_value / price) if price > 0 else 0.0
        current_qty = asset.qty
        delta_qty = target_qty - current_qty

        min_notional = filters.min_notional or 1.0
        if abs(delta_qty) * price < min_notional:
            log.info(f"{symbol}: exposure {exposure:.2f}, target_qty={target_qty}, "
                     f"current={current_qty}, delta too small to trade, skipping")
            asset.current_exposure = exposure
            continue

        if delta_qty > 0:
            order_id, fill_price = trader.place_market_buy(delta_qty)
            new_qty = current_qty + delta_qty
            asset.cost_basis = ((current_qty * asset.cost_basis) + (delta_qty * fill_price)) / new_qty if new_qty > 0 else 0.0
            asset.qty = new_qty
            log.info(f"{symbol}: BUY {delta_qty} @ ~{fill_price} -> {order_id} "
                     f"(exposure {asset.current_exposure:.2f} -> {exposure:.2f})")
        else:
            sell_qty = min(-delta_qty, current_qty)
            order_id, fill_price = trader.place_market_sell(sell_qty)
            realized = (fill_price - asset.cost_basis) * sell_qty
            asset.realized_pnl += realized
            state.total_realized_pnl += realized
            asset.qty = current_qty - sell_qty
            if asset.qty <= 0:
                asset.cost_basis = 0.0
            log.info(f"{symbol}: SELL {sell_qty} @ ~{fill_price} -> {order_id}, "
                     f"realized {realized:+.2f} (exposure {asset.current_exposure:.2f} -> {exposure:.2f})")
        asset.current_exposure = exposure

    state.last_rebalance_ts = time.time()
    return now_prices


def run():
    cfg = load_config()
    logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO),
                         format="%(asctime)s [%(levelname)s] %(message)s")
    log.info(f"Starting trend-bot | symbols={cfg.symbols} dry_run={cfg.dry_run}")
    if not cfg.dry_run:
        log.warning("LIVE TRADING ENABLED — real orders will be placed on Binance.US")

    state = load_state(cfg.state_file)
    if state is None:
        per_asset_capital = cfg.total_capital_usdt / len(cfg.symbols)
        state = BotState(assets={s: AssetState(symbol=s, capital_allocated=per_asset_capital) for s in cfg.symbols})
        log.info(f"Fresh state: {len(cfg.symbols)} assets, ${per_asset_capital:.2f} each "
                 f"(${cfg.total_capital_usdt:.2f} total)")
    else:
        log.info(f"Resumed prior state: last_rebalance={state.last_rebalance_ts}, "
                 f"total_realized_pnl={state.total_realized_pnl:.2f}")

    traders = {}
    for symbol in cfg.symbols:
        trader = BinanceUSTrader(cfg.api_key, cfg.api_secret, symbol, cfg.dry_run)
        trader.get_symbol_filters()
        traders[symbol] = trader

    while True:
        now = time.time()
        due = state.last_rebalance_ts == 0.0 or (now - state.last_rebalance_ts) >= cfg.rebalance_interval_days * 86400
        if due:
            try:
                prices = rebalance(cfg, state, traders)
                save_state(cfg.state_file, state)
            except Exception:
                log.exception("Rebalance failed, will retry next poll")
                prices = {s: traders[s].get_price() for s in cfg.symbols}
        else:
            prices = {s: traders[s].get_price() for s in cfg.symbols}

        write_heartbeat(cfg.heartbeat_file, cfg, state, prices)
        time.sleep(cfg.poll_interval_seconds)


if __name__ == "__main__":
    run()
