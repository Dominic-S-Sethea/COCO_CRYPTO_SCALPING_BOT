# TARGET_FILE: trading_engine.py
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.binance_ws import BinanceKlineStream
from strategies.scalping_features import compute_scalping_features
from strategies.scalping_model import load_scalping_model, predict_signal
from risk_management import MicroScalpingRiskManager
from order_executor import TestnetOrderExecutor
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TradingEngine")

def save_latest_klines(klines: list, symbol: str, filepath: str = "latest_klines.json"):
    """Save last N klines to JSON for dashboard."""
    try:
        data = {
            "symbol": symbol,
            "klines": klines[-100:],  # Keep last 100
            "updated_at": time.time()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.debug(f"Failed to save klines: {e}")

class ScalpingEngine:
    def __init__(self, config_path: str = "settings.yaml"):
        with open(config_path) as f:
            self.settings = yaml.safe_load(f)
        self.risk_mgr = MicroScalpingRiskManager(self.settings)
        self.ws_client = BinanceKlineStream(
            symbols=self.settings['trading']['symbols'],
            interval='1s',
            maxlen=60
        )
        self.model = load_scalping_model(self.settings['model']['path'])
        self.order_executor = TestnetOrderExecutor(config_path)
        self.running = True

    async def trade_loop(self):
        symbol = self.settings['trading']['symbols'][0]  # Start with first symbol
        logger.info(f"Starting scalping engine for {symbol} on Testnet")

        while self.running:
            try:
                # Get latest data
                klines = self.ws_client.get_klines_array(symbol, n=15)
                if len(klines) < 10:
                    await asyncio.sleep(0.5)
                    continue

                # Save klines for dashboard
                save_latest_klines(klines, symbol)

                # Compute features
                features = compute_scalping_features(klines)
                confidence, side = predict_signal(self.model, features)

                # Update state for dashboard
                self.risk_mgr.load_state()
                current_price = klines[-1]['c']
                self.risk_mgr.state["last_signal"] = {
                    "side": side,
                    "confidence": confidence,
                    "price": current_price,
                    "time": time.time()
                }
                self.risk_mgr.save_state()

                # Check for exit if in position
                exit_reason = self.risk_mgr.check_exit_conditions(current_price)
                if exit_reason:
                    logger.info(f"Closing position due to {exit_reason}")
                    pos = self.risk_mgr.state["active_position"]
                    close_side = 'SELL' if pos["side"] == "buy" else 'BUY'
                    order_result = self.order_executor.place_market_order(
                        symbol, close_side, pos["quantity"]
                    )
                    if order_result:
                        avg_price = float(order_result.get('avgPrice', current_price))
                        self.risk_mgr.update_portfolio_after_close(
                            close_price=avg_price,
                            side=pos["side"],
                            qty=pos["quantity"],
                            entry_price=pos["entry_price"]
                        )
                        # Set cooldown to prevent immediate re-entry
                        self.risk_mgr.state["last_close_time"] = time.time()
                        self.risk_mgr.save_state()
                    else:
                        logger.error("Failed to close position")

                # Open new position if signal is strong AND no cooldown
                elif (side in ['buy', 'sell'] 
                      and confidence > 0.7  # Increased threshold
                      and self.risk_mgr.can_open_position(symbol)):
                    
                    # Check cooldown (3 seconds after close)
                    last_close = self.risk_mgr.state.get("last_close_time", 0)
                    if time.time() - last_close < 3.0:
                        logger.debug("Skipping signal due to cooldown")
                    else:
                        qty = self.risk_mgr.calculate_position_size(current_price)
                        order_side = 'BUY' if side == 'buy' else 'SELL'
                        order_result = self.order_executor.place_market_order(symbol, order_side, qty)
                        
                        if order_result:
                            avg_price = float(order_result.get('avgPrice', current_price))
                            self.risk_mgr.state["active_position"] = {
                                "symbol": symbol,
                                "side": side,
                                "quantity": qty,
                                "entry_price": avg_price,
                                "open_time": time.time(),
                                "order_id": order_result['orderId']
                            }
                            logger.info(f"Opened {side} position: {qty} @ {avg_price} (conf: {confidence:.2%})")
                            self.risk_mgr.save_state()
                        else:
                            logger.error("Failed to place order")

                await asyncio.sleep(1.0)  # Evaluate every 1 second

            except Exception as e:
                logger.error(f"Error in trade loop: {e}")
                await asyncio.sleep(1)

    async def run(self):
        # Start WebSocket stream
        ws_task = asyncio.create_task(self.ws_client.start())
        await asyncio.sleep(2)  # Let WS connect

        # Start trading logic
        try:
            await self.trade_loop()
        except asyncio.CancelledError:
            logger.info("Trade loop cancelled.")
        finally:
            self.running = False
            self.ws_client.stop()
            ws_task.cancel()
            try:
                await ws_task
            except asyncio.CancelledError:
                pass

    def shutdown(self):
        logger.info("Shutting down engine...")
        self.running = False

if __name__ == "__main__":
    engine = ScalpingEngine()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        logger.info("Received Ctrl+C. Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")