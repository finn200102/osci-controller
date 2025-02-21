import requests
import json
import matplotlib.pyplot as plt
import numpy as np

# API base URL
BASE_URL = "http://localhost:8000"

def connect_to_scope(ip_address):
    response = requests.post(f"{BASE_URL}/connect", 
                           json={"ip_address": ip_address})
    if response.status_code == 200:
        print("Successfully connected to oscilloscope")
        print(response.json())
    else:
        print(f"Failed to connect: {response.text}")
        exit(1)

def get_channel_data(channel_id):
    response = requests.get(f"{BASE_URL}/data/{channel_id}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get data: {response.text}")
        return None

def plot_data(data):
    time_step = data['time_step']
    waveform = data['data']
    
    # Create time array
    time = np.arange(len(waveform)) * time_step
    
    plt.figure(figsize=(10, 6))
    plt.plot(time, waveform)
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.title('Oscilloscope Channel Data')
    plt.grid(True)
    plt.show()

def main():
    # Connect to the oscilloscope
    scope_ip = "192.168.1.1"  # Replace with your scope's IP address
    connect_to_scope(scope_ip)
    
    # Get data from channel 1
    channel_data = get_channel_data(1)
    
    if channel_data:
        print(f"Received {len(channel_data['data'])} data points")
        plot_data(channel_data)

if __name__ == "__main__":
    main() 