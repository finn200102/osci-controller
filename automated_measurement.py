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
        date_folder.mkdir(parents=True, exist_ok=True)
        
        # Find the next available run number
        existing_runs = [d for d in date_folder.glob('run_*') if d.is_dir()]
        if not existing_runs:
            next_run = 1
        else:
            run_numbers = [int(run.name.split('_')[1]) for run in existing_runs]
            next_run = max(run_numbers) + 1
        
        # Create run subfolder
        self.current_measurement_path = date_folder / f"run_{next_run:03d}"
        self.current_measurement_path.mkdir(exist_ok=True)
        
        # Create data subfolder
        (self.current_measurement_path / "data").mkdir(exist_ok=True)

    def connect_scope(self):
        response = requests.post(
            f"{self.base_url}/connect",
            json={"ip_address": self.config['oscilloscope']['ip_address']}
        )
        response.raise_for_status()
        return response.json()

    def configure_scope(self):
        # Configure channels
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

        # Configure acquisition first (before trigger)
        response = requests.post(
            f"{self.base_url}/acquisition",
            json=self.config['acquisition']
        )
        response.raise_for_status()

        # Configure timebase
        response = requests.post(
            f"{self.base_url}/timebase",
            json=self.config['timebase']
        )
        response.raise_for_status()

        # Configure trigger last
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
        capture_data = {
            "timestamp": datetime.now().isoformat(),
            "channels": {}
        }
        
        for channel in self.config['channels']:
            if channel['display']:  # Only capture enabled channels
                try:
                    response = requests.get(
                        f"{self.base_url}/data/{channel['number']}",
                        params={"points": self.config['acquisition']['points']}
                    )
                    response.raise_for_status()
                    capture_data["channels"][f"channel_{channel['number']}"] = {
                        "data": response.json()['data'],
                        "time_step": response.json()['time_step'],
                        "scale": channel['scale'],
                        "coupling": channel['coupling']
                    }
                except Exception as e:
                    print(f"Warning: Failed to capture channel {channel['number']}: {str(e)}")

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
            
            # Validate channel configuration
            enabled_channels = [ch for ch in self.config['channels'] if ch['display']]
            if not enabled_channels:
                raise ValueError("No channels are enabled in the configuration")
            print(f"Configured channels: {[ch['number'] for ch in enabled_channels]}")
            
            print("Configuring scope...")
            self.configure_scope()
            
            print("Starting captures...")
            for capture_num in range(self.config['measurement']['captures']):
                print(f"\nCapture {capture_num + 1}/{self.config['measurement']['captures']}...")
                self.wait_for_trigger()
                
                print("Saving capture data...")
                self.save_capture(capture_num)
                
                # Wait for specified interval
                if capture_num < self.config['measurement']['captures'] - 1:  # Don't wait after last capture
                    time.sleep(self.config['measurement']['interval'])
            
            print("\nSaving configuration...")
            self.save_config()
            
        finally:
            print("Disconnecting from oscilloscope...")
            self.disconnect_scope()

if __name__ == "__main__":
    measurement = OscilloscopeMeasurement("config.yaml")
    measurement.run_measurement() 