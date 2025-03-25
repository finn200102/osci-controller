import yaml
import json
import time
import copy
from pathlib import Path
from automated_measurement import OscilloscopeMeasurement

def run_multi_timebase_measurements(config_path):
    # Load the multi-timebase configuration
    with open(config_path, 'r') as f:
        multi_config = yaml.safe_load(f)
    
    # Validate that we have timebase runs defined
    if 'timebase_runs' not in multi_config or not multi_config['timebase_runs']:
        raise ValueError("No timebase runs defined in configuration file")
    
    # Get a list of all timebase configurations
    timebase_runs = multi_config['timebase_runs']
    print(f"Found {len(timebase_runs)} timebase configurations to run")
    
    # Create a base configuration for each run
    base_config = copy.deepcopy(multi_config)
    if 'timebase_runs' in base_config:
        del base_config['timebase_runs']  # Remove the runs list from the base config
    
    # Run each timebase configuration as a separate measurement
    for i, timebase_config in enumerate(timebase_runs):
        print(f"\n=== Running timebase configuration {i+1}/{len(timebase_runs)} ===")
        print(f"Timebase scale: {timebase_config['scale']} seconds/div")
        if 'description' in timebase_config:
            print(f"Description: {timebase_config['description']}")
        
        # Create a temporary config file for this run
        run_config = copy.deepcopy(base_config)
        
        # Update the timebase configuration for this run
        run_config['timebase'] = run_config.get('timebase', {})
        run_config['timebase']['scale'] = timebase_config['scale']
        
        # Add the timebase description to the measurement metadata if available
        if 'description' in timebase_config:
            run_config['measurement'] = run_config.get('measurement', {})
            run_config['measurement']['timebase_description'] = timebase_config['description']
        
        # Save the temporary config file
        temp_config_path = f"temp_config_{i+1}.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(run_config, f)
        
        # Run the measurement with this config
        print(f"Starting measurement with timebase scale {timebase_config['scale']} s/div")
        measurement = OscilloscopeMeasurement(temp_config_path)
        measurement.run_measurement()
        
        # Optionally wait between runs to let things settle
        if i < len(timebase_runs) - 1:  # Don't wait after the last run
            wait_time = 5  # seconds to wait between runs, adjust as needed
            print(f"Waiting {wait_time} seconds before next run...")
            time.sleep(wait_time)
        
        # Cleanup temporary config file
        Path(temp_config_path).unlink(missing_ok=True)
    
    print("\nAll multi-timebase measurements completed!")

if __name__ == "__main__":
    run_multi_timebase_measurements("multi_timebase_config.yaml") 