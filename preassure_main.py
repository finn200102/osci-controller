# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyvisa
from typing import List, Optional
import uvicorn
from datetime import datetime
import time

app = FastAPI()

# Global pressure device connection
pressure_connection = None

# Data Models
class ConnectRequest(BaseModel):
    port: str = "/dev/ttyS0"
    baudrate: int = 9600

class PressureCommand(BaseModel):
    command: str

class ContinuousModeConfig(BaseModel):
    interval: int  # interval in seconds

@app.post("/connect")
async def connect_pressure_device(request: ConnectRequest):
    global pressure_connection
    try:
        rm = pyvisa.ResourceManager()
        resource_name = f'ASRL{request.port}::INSTR'
        pressure_connection = rm.open_resource(resource_name)

        # Configure the serial settings
        pressure_connection.baud_rate = request.baudrate
        pressure_connection.data_bits = 8
        pressure_connection.parity = pyvisa.constants.Parity.none
        pressure_connection.stop_bits = pyvisa.constants.StopBits.one
        pressure_connection.read_termination = None
        pressure_connection.write_termination = '\r'
        pressure_connection.timeout = 1000  # timeout in milliseconds

        # Stop any continuous output that might be running
        pressure_connection.write_raw(b'x')
        time.sleep(0.5)

        # Clear any remaining data
        if pressure_connection.bytes_in_buffer > 0:
            pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)

        return {"status": "connected", "device": f"Pressure device at {request.port}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/command")
async def send_command(command: PressureCommand):
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        # Send command
        pressure_connection.write(command.command)
        time.sleep(0.2)

        # Read response if available
        response = None
        if pressure_connection.bytes_in_buffer > 0:
            response = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)
            response = response.decode('ascii', errors='replace')

        return {"status": "success", "command": command.command, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pressure")
async def get_pressure():
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        # Request pressure measurement
        pressure_connection.write("PR1")
        time.sleep(0.2)

        # Read acknowledgment
        if pressure_connection.bytes_in_buffer > 0:
            ack = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)

        # Send ENQ to get data
        pressure_connection.write_raw(b'\x05')  # ENQ character
        time.sleep(0.2)

        # Read pressure data
        pressure_data = None
        if pressure_connection.bytes_in_buffer > 0:
            pressure_data = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)
            pressure_data = pressure_data.decode('ascii', errors='replace').strip()

        return {
            "timestamp": datetime.now().isoformat(),
            "pressure": pressure_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/error")
async def get_error_status():
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        # Request error status
        pressure_connection.write("ERR")
        time.sleep(0.2)

        # Read acknowledgment
        if pressure_connection.bytes_in_buffer > 0:
            ack = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)

        # Send ENQ to get data
        pressure_connection.write_raw(b'\x05')  # ENQ character
        time.sleep(0.2)

        # Read error data
        error_data = None
        if pressure_connection.bytes_in_buffer > 0:
            error_data = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)
            error_data = error_data.decode('ascii', errors='replace').strip()

        return {
            "timestamp": datetime.now().isoformat(),
            "error_code": error_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/continuous")
async def set_continuous_mode(config: ContinuousModeConfig):
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        # Set continuous mode with specified interval
        pressure_connection.write(f"COM,{config.interval}")
        time.sleep(0.2)

        # Read acknowledgment
        response = None
        if pressure_connection.bytes_in_buffer > 0:
            response = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)
            response = response.decode('ascii', errors='replace')

        return {
            "status": "success", 
            "mode": "continuous", 
            "interval": config.interval,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop_continuous")
async def stop_continuous_mode():
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        # Send any character to stop continuous output
        pressure_connection.write_raw(b'x')
        time.sleep(0.5)

        # Clear any remaining data
        if pressure_connection.bytes_in_buffer > 0:
            data = pressure_connection.read_bytes(pressure_connection.bytes_in_buffer)
            data = data.decode('ascii', errors='replace')
        else:
            data = None

        return {"status": "continuous mode stopped", "remaining_data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/disconnect")
async def disconnect_pressure_device():
    global pressure_connection
    if not pressure_connection:
        raise HTTPException(status_code=400, detail="Pressure device not connected")
    try:
        pressure_connection.close()
        pressure_connection = None
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
