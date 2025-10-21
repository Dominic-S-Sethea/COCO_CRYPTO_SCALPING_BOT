# TARGET_FILE: data_collector.py
import asyncio
import csv
import logging
import os
import yaml
from data.binance_ws import BinanceKlineStream
from strategies.scalping_features import compute_scalping_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataCollector")

class ScalpingDataCollector:
    def __init__(self, config_path: str = "settings.yaml", output_dir: str = "datasets"):
        with open(config_path) as f:
            self.settings = yaml.safe_load(f)
        self.symbol = self.settings['trading']['symbols'][0].lower()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.ws_client = BinanceKlineStream([self.symbol], interval='1s', maxlen=30)
        self.running = True
        self.save_count = 0

    async def collect_loop(self):
        output_file = os.path.join(self.output_dir, f"{self.symbol}_1s_scalping_data.csv")
        file_exists = os.path.exists(output_file)
        if not file_exists:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'close', 'price_change_1s', 'price_change_5s',
                    'volatility_10s', 'volume_10s', 'price_acceleration'
                    # We'll add 'label' later during relabeling
                ])

        logger.info(f"Collecting raw features for {self.symbol} → {output_file}")

        while self.running:
            try:
                klines = self.ws_client.get_klines_array(self.symbol, n=20)
                if len(klines) >= 10:
                    # Compute features on latest 10 klines
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
                            logger.info(f"Collected {self.save_count} samples")
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
    collector = ScalpingDataCollector()
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")