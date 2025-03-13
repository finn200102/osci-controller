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
        self.pressure_url = "http://localhost:8001"
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
    
    def connect_pressure_device(self):
        try:
            response = requests.post(
                f"{self.pressure_url}/connect",
                json={
                    "port": self.config.get('pressure', {}).get('port', "/dev/ttyS0"),
                    "baudrate": self.config.get('pressure', {}).get('baudrate', 9600)
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Failed to connect to pressure device: {str(e)}")
            return None
        

    def get_pressure_reading(self):
        try:
            response = requests.get(f"{self.pressure_url}/pressure")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Failed to get pressure reading: {str(e)}")
            return None


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
        # First, re-arm the trigger
        requests.post(
            f"{self.base_url}/trigger",
            json=self.config['trigger']
        )
        while True:
            response = requests.get(f"{self.base_url}/trigger/status")
            status = response.json()['status']
            if status == "STOP":  # Triggered and acquired
                return True
            time.sleep(0.1)

    def save_capture(self, capture_num):
        # Create a metadata dictionary
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "channels": {}
        }

        # Get pressure reading for this capture
        pressure_data = self.get_pressure_reading()
        if pressure_data:
            metadata["pressure"] = pressure_data
        
        # Dictionary to store data for all channels
        all_channel_data = {}
        max_points = 0
        
        # First collect all data and metadata
        for channel in self.config['channels']:
            if channel['display']:  # Only capture enabled channels
                try:
                    response = requests.get(
                        f"{self.base_url}/data/{channel['number']}",
                        params={"points": self.config['acquisition']['points']}
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    
                    # Store channel metadata
                    metadata["channels"][f"channel_{channel['number']}"] = {
                        "time_step": response_data['time_step'],
                        "scale": channel['scale'],
                        "coupling": channel['coupling']
                    }
                    
                    # Store channel data
                    all_channel_data[channel['number']] = response_data['data']
                    max_points = max(max_points, len(response_data['data']))
                    
                except Exception as e:
                    print(f"Warning: Failed to capture channel {channel['number']}: {str(e)}")
        
        # Save metadata to JSON
        metadata_file = self.current_measurement_path / "data" / f"capture_{capture_num:04d}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save waveform data to CSV
        csv_file = self.current_measurement_path / "data" / f"capture_{capture_num:04d}.csv"
        with open(csv_file, 'w') as f:
            # Write header
            header = ['Time']
            for channel_num in sorted(all_channel_data.keys()):
                header.append(f'Channel_{channel_num}')
            f.write(','.join(header) + '\n')
            
            # Write data rows
            time_step = metadata["channels"]["channel_1"]["time_step"]  # Use first channel's time step
            for i in range(max_points):
                row = [f"{i * time_step:.9e}"]  # Time in seconds
                for channel_num in sorted(all_channel_data.keys()):
                    data = all_channel_data[channel_num]
                    value = data[i] if i < len(data) else ''
                    row.append(f"{value:.6e}" if value != '' else '')
                f.write(','.join(row) + '\n')

    def save_config(self):
        # Get final pressure reading for the measurement series
        pressure_data = self.get_pressure_reading()
        # Save configuration and metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "configuration": self.config,
        }

        # Add pressure data to the README
        if pressure_data:
            metadata["pressure"] = pressure_data

        
        readme_file = self.current_measurement_path / "README.json"
        with open(readme_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def disconnect_scope(self):
        requests.post(f"{self.base_url}/disconnect")

    def disconnect_pressure_device(self):
        try:
            requests.post(f"{self.pressure_url}/disconnect")
        except Exception as e:
            print(f"Warning: Failed to disconnect pressure device: {str(e)}")


    def run_measurement(self):
        try:
            print("Setting up measurement folders...")
            self.setup_folders()
            
            print("Connecting to oscilloscope...")
            self.connect_scope()

            print("Connecting to pressure device...")
            self.connect_pressure_device()
            
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

            print("Disconnecting from pressure device...")
            self.disconnect_pressure_device()

if __name__ == "__main__":
    measurement = OscilloscopeMeasurement("config.yaml")
    measurement.run_measurement() 