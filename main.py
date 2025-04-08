from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyvisa
from typing import List, Optional
import uvicorn
from datetime import datetime

app = FastAPI()

# Global oscilloscope connection
osci_connection = None

# Data Models
class ConnectRequest(BaseModel):
    ip_address: str

class ChannelConfig(BaseModel):
    channel: int
    scale: float
    coupling: str = "DC"
    display: bool = True

class TriggerConfig(BaseModel):
    source: int
    level: float
    mode: str = "SING"

class TimebaseConfig(BaseModel):
    scale: float  # seconds/div
    offset: float = 0.0  # seconds from center

class AcquisitionConfig(BaseModel):
    points: int  # memory depth points

@app.post("/connect")
async def connect_oscilloscope(request: ConnectRequest):  # Changed to use request body
    global osci_connection
    try:
        rm = pyvisa.ResourceManager('@py')
        osci_connection = rm.open_resource(f'TCPIP::{request.ip_address}::INSTR')
        osci_connection.timeout = 5000
        osci_connection.read_termination = '\n'
        osci_connection.write_termination = '\n'
        idn = osci_connection.query('*IDN?')
        return {"status": "connected", "device": idn}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/channel/{channel_id}")
async def configure_channel(channel_id: int, config: ChannelConfig):
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.write(f":CHANnel{channel_id}:DISPlay {'ON' if config.display else 'OFF'}")
        osci_connection.write(f":CHANnel{channel_id}:SCALe {config.scale}")
        osci_connection.write(f":CHANnel{channel_id}:COUPling {config.coupling}")
        return {"status": "success", "channel": channel_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger")
async def configure_trigger(config: TriggerConfig):
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.write(f':TRIG:EDGE:SOURce CHAN{config.source}')
        osci_connection.write(f':TRIG:EDGE:LEV {config.level}')
        osci_connection.write(f':TRIG:SWE {config.mode}')
        if config.mode == "SING":
            osci_connection.write(':SING')
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trigger/status")
async def get_trigger_status():
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        status = osci_connection.query(':TRIG:STAT?').strip()
        return {"status": status}
    except Exception as e:
        if "socket.timeout" in str(e):
            raise HTTPException(status_code=500, detail="Timeout error: Oscilloscope not responding. Check network connection and oscilloscope status.")
        else:
            raise HTTPException(status_code=500, detail=f"Error getting trigger status: {str(e)}")

@app.post("/timebase")
async def configure_timebase(config: TimebaseConfig):
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.write(f':TIMebase:MAIN:SCALe {config.scale}')
        osci_connection.write(f':TIMebase:MAIN:OFFSet {config.offset}')
        return {
            "status": "success",
            "scale": config.scale,
            "offset": config.offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/acquisition")
async def configure_acquisition(config: AcquisitionConfig):
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.write(f':ACQuire:MDEPth {config.points}')
        return {
            "status": "success",
            "points": config.points
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/{channel_id}")
async def get_channel_data(channel_id: int, points: Optional[str] = "max"):
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.write(f':WAV:SOUR CHAN{channel_id}')
        osci_connection.write(':WAV:MODE RAW')
        osci_connection.write(f':WAV:POIN {points}')
        osci_connection.write(':WAV:FORM ASC')

        data = osci_connection.query(':WAV:DATA?')
        time_step = float(osci_connection.query(':WAV:XINC?'))

        return {
            "time_step": time_step,
            "data": [float(x) for x in data.split(',') if x.strip()]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/disconnect")
async def disconnect_oscilloscope():
    global osci_connection
    if not osci_connection:
        raise HTTPException(status_code=400, detail="Oscilloscope not connected")
    try:
        osci_connection.close()
        osci_connection = None
        return {"status": "disconnected"}
    except Exception as e:
        if "socket.timeout" in str(e):
            raise HTTPException(status_code=500, detail="Timeout error: Oscilloscope not responding. Check network connection and oscilloscope status.")
        else:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
