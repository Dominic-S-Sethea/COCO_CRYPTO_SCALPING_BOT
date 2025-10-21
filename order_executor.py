# TARGET_FILE: order_executor.py
import logging
from binance import Client
from binance.exceptions import BinanceAPIException
import yaml
import os

logger = logging.getLogger("OrderExecutor")

def format_quantity(qty: float, symbol: str) -> str:
    """
    Format quantity as decimal string without scientific notation.
    Respect Binance step sizes.
    """
    if 'BTC' in symbol:
        # BTCUSDT: 5 decimal places
        return f"{qty:.5f}"
    elif 'ETH' in symbol:
        # ETHUSDT: 4 decimal places
        return f"{qty:.4f}"
    else:
        return f"{qty:.5f}"

class TestnetOrderExecutor:
    def __init__(self, config_path: str = "settings.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        api_key = config['binance']['api_key']
        api_secret = config['binance']['api_secret']
        
        self.client = Client(api_key, api_secret, testnet=True)
        self.client.API_URL = 'https://testnet.binance.vision/api'
        logger.info("Initialized Binance Testnet client")

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        try:
            qty_str = format_quantity(quantity, symbol)
            logger.info(f"Placing {side} market order: {qty_str} {symbol}")
            order = self.client.create_order(
                symbol=symbol,
                side=side.upper(),
                type='MARKET',
                quantity=qty_str
            )
            logger.info(f"Order filled: {order['orderId']} @ avgPrice={order.get('avgPrice', 'N/A')}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e.message} (code {e.code})")
            return None
        except Exception as e:
            logger.error(f"Order error: {e}")
            return None

    def get_account_balance(self, asset: str = "USDT") -> float:
        try:
            info = self.client.get_account()
            for bal in info['balances']:
                if bal['asset'] == asset:
                    return float(bal['free'])
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
        return 0.0

    def cancel_all_orders(self, symbol: str):
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            for order in orders:
                self.client.cancel_order(symbol=symbol, orderId=order['orderId'])
                logger.info(f"Cancelled order {order['orderId']}")
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")