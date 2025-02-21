import os
import yaml
import time
import json
from datetime import datetime
import requests
from pathlib import Path

class OscilloscopeMeasurement:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.base_url = "http://localhost:8000"
        self.current_measurement_path = None

    def setup_folders(self):
        # Create base folder structure
        base_path = Path(self.config['oscilloscope']['save_path'])
        date_folder = base_path / datetime.now().strftime("%Y-%m-%d")
        
        # Create measurement subfolder with just the date
        self.current_measurement_path = date_folder
        self.current_measurement_path.mkdir(parents=True, exist_ok=True)
        
        # Create data subfolder
        (self.current_measurement_path / "data").mkdir(exist_ok=True)

    def connect_scope(self):
        response = requests.post(
            f"{self.base_url}/connect",
            json={"ip_address": self.config['oscilloscope']['ip_address']}
        )
        response.raise_for_status()
        return response.json()

    def configure_channels(self):
        for channel in self.config['channels']:
            response = requests.post(
                f"{self.base_url}/channel/{channel['number']}",
                json={
                    "channel": channel['number'],
                    "scale": channel['scale'],
                    "coupling": channel['coupling'],
                    "display": channel['display']
                }
            )
            response.raise_for_status()

    def configure_trigger(self):
        response = requests.post(
            f"{self.base_url}/trigger",
            json=self.config['trigger']
        )
        response.raise_for_status()

    def wait_for_trigger(self):
        while True:
            response = requests.get(f"{self.base_url}/trigger/status")
            status = response.json()['status']
            if status == "STOP":  # Triggered and acquired
                return True
            time.sleep(0.1)

    def save_capture(self, capture_num):
        # Save data for each configured channel
        capture_data = {}
        
        for channel in self.config['channels']:
            response = requests.get(f"{self.base_url}/data/{channel['number']}")
            response.raise_for_status()
            capture_data[f"channel_{channel['number']}"] = response.json()

        # Save capture data
        data_file = self.current_measurement_path / "data" / f"capture_{capture_num:04d}.json"
        with open(data_file, 'w') as f:
            json.dump(capture_data, f, indent=2)

    def save_config(self):
        # Save configuration and metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "configuration": self.config,
        }
        
        readme_file = self.current_measurement_path / "README.json"
        with open(readme_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def disconnect_scope(self):
        requests.post(f"{self.base_url}/disconnect")

    def run_measurement(self):
        try:
            print("Setting up measurement folders...")
            self.setup_folders()
            
            print("Connecting to oscilloscope...")
            self.connect_scope()
            
            print("Configuring channels...")
            self.configure_channels()
            
            print("Configuring trigger...")
            self.configure_trigger()
            
            print("Starting captures...")
            for capture_num in range(self.config['measurement']['captures']):
                print(f"Waiting for trigger {capture_num + 1}/{self.config['measurement']['captures']}...")
                self.wait_for_trigger()
                
                print("Saving capture data...")
                self.save_capture(capture_num)
                
                # Wait for specified interval
                time.sleep(self.config['measurement']['interval'])
                
                # Reconfigure trigger for next capture
                self.configure_trigger()
            
            print("Saving configuration...")
            self.save_config()
            
        finally:
            print("Disconnecting from oscilloscope...")
            self.disconnect_scope()

if __name__ == "__main__":
    measurement = OscilloscopeMeasurement("config.yaml")
    measurement.run_measurement() 