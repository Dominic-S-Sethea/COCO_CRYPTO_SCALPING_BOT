import asyncio
import json
import logging
from collections import deque
from typing import Dict, Deque
import websockets

class BinanceKlineStream:
    def __init__(self, symbols: list, interval: str = '1s', maxlen: int = 60):
        """
        Stream 1s klines from Binance Mainnet (public data, no auth needed).
        Stores last `maxlen` klines per symbol in a deque.
        """
        self.symbols = [s.lower() for s in symbols]
        self.interval = interval
        self.klines: Dict[str, Deque[dict]] = {
            sym: deque(maxlen=maxlen) for sym in self.symbols
        }
        self.running = False
        self.logger = logging.getLogger("BinanceWS")

    async def _handle_message(self, msg: str, symbol: str):
        try:
            data = json.loads(msg)
            if 'k' in data:
                kline = data['k']
                # Store only essential fields for speed
                compact_kline = {
                    't': kline['t'],  # open time
                    'o': float(kline['o']),
                    'h': float(kline['h']),
                    'l': float(kline['l']),
                    'c': float(kline['c']),
                    'v': float(kline['v']),
                }
                self.klines[symbol].append(compact_kline)
        except Exception as e:
            self.logger.error(f"Error parsing kline for {symbol}: {e}")

    async def _stream_symbol(self, symbol: str):
        # ✅ Use MAINNET WebSocket (public, no auth, supports 1s klines)
        stream_url = f"wss://stream.binance.com:9443/ws/{symbol}@kline_{self.interval}"
        while self.running:
            try:
                async with websockets.connect(stream_url) as ws:
                    self.logger.info(f"Connected to {symbol} kline stream")
                    while self.running:
                        msg = await ws.recv()
                        await self._handle_message(msg, symbol)
            except Exception as e:
                self.logger.error(f"WS error for {symbol}: {e}, reconnecting in 2s...")
                await asyncio.sleep(2)

    async def start(self):
        self.running = True
        tasks = [self._stream_symbol(sym) for sym in self.symbols]
        await asyncio.gather(*tasks)

    def stop(self):
        self.running = False

    def get_latest_kline(self, symbol: str):
        """Get most recent kline (dict) or None."""
        dq = self.klines.get(symbol.lower())
        return dq[-1] if dq else None

    def get_klines_array(self, symbol: str, n: int = 10):
        """Get last n klines as list of dicts."""
        dq = self.klines.get(symbol.lower())
        return list(dq)[-n:] if dq else []