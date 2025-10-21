# TARGET_FILE: smart_data_collector.py
import asyncio
import csv
import logging
import os
import time
import yaml
import numpy as np
from data.binance_ws import BinanceKlineStream
from strategies.scalping_features import compute_scalping_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SmartCollector")

class VolatilityOptimizedCollector:
    def __init__(self, config_path: str = "settings.yaml", output_dir: str = "datasets"):
        with open(config_path) as f:
            self.settings = yaml.safe_load(f)
        self.symbol = self.settings['trading']['symbols'][0].lower()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.ws_client = BinanceKlineStream([self.symbol], interval='1s', maxlen=200)
        self.running = True
        self.save_count = 0
        self.volatility_window = 60
        self.last_volatile_sample = time.time()
        self.fallback_mode = False

    async def is_high_volatility(self, klines: list) -> bool:
        if len(klines) < self.volatility_window:
            return False
        closes = np.array([k['c'] for k in klines[-self.volatility_window:]])
        returns = np.diff(closes) / closes[:-1]
        current_vol = np.std(returns)
        return current_vol > 0.0005

    async def collect_loop(self):
        output_file = os.path.join(self.output_dir, f"{self.symbol}_volatile_1s_data.csv")
        file_exists = os.path.exists(output_file)
        if not file_exists:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'close', 'price_change_1s', 'price_change_5s',
                    'volatility_10s', 'volume_10s', 'price_acceleration'
                ])

        logger.info(f"Smart collector started for {self.symbol} → {output_file}")
        logger.info("Primary mode: high volatility only. Fallback after 10 min silence.")

        while self.running:
            try:
                klines = self.ws_client.get_klines_array(self.symbol, n=100)
                if len(klines) < 20:
                    await asyncio.sleep(1)
                    continue

                # Check volatility
                if await self.is_high_volatility(klines):
                    self.fallback_mode = False
                    self.last_volatile_sample = time.time()
                    should_save = True
                else:
                    # Fallback: save all if no volatility for 10 minutes
                    if time.time() - self.last_volatile_sample > 600:  # 10 minutes
                        if not self.fallback_mode:
                            logger.info("Switching to fallback mode (low volatility)")
                            self.fallback_mode = True
                        should_save = True
                    else:
                        should_save = False

                if should_save and len(klines) >= 10:
                    features = compute_scalping_features(klines[-10:])
                    if features is not None:
                        row = [
                            klines[-1]['t'],
                            klines[-1]['c'],
                            float(features[0]),
                            float(features[1]),
                            float(features[2]),
                            float(features[3]),
                            float(features[4])
                        ]
                        with open(output_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(row)
                        self.save_count += 1
                        if self.save_count % 10 == 0:
                            mode = "fallback" if self.fallback_mode else "volatile"
                            logger.info(f"Collected {self.save_count} samples ({mode} mode)")

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(1)

    async def run(self):
        ws_task = asyncio.create_task(self.ws_client.start())
        await asyncio.sleep(2)
        try:
            await self.collect_loop()
        finally:
            self.ws_client.stop()
            ws_task.cancel()

if __name__ == "__main__":
    collector = VolatilityOptimizedCollector()
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")