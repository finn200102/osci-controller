# Basic Setup Commands
*IDN?                           # Query device identification
:CHANnel{n}:DISPlay ON         # Turn on channel n display
:CHANnel{n}:DISPlay?           # Query channel n display state
:CHANnel{n}:SCALe {value}      # Set vertical scale for channel n
:CHANnel{n}:SCALe?             # Query vertical scale for channel n
:CHANnel{n}:COUPling {mode}    # Set coupling mode (DC/AC) for channel n
:CHANnel{n}:COUPling?          # Query coupling mode for channel n

# Timebase Commands
:TIMebase:MAIN:SCALe {value}   # Set horizontal time scale
:TIMebase:MAIN:SCALe?          # Query horizontal time scale
:TIMebase:MAIN:OFFSet {value}  # Set horizontal offset
:TIMebase:MAIN:OFFSet?         # Query horizontal offset

# Acquisition Commands
:ACQuire:MDEPth {value}        # Set memory depth
:ACQuire:MDEPth?               # Query memory depth

# Waveform Commands
:WAV:XINC?                     # Query time increment between points
:WAV:SOUR CHAN{n}             # Set waveform source channel
:WAV:MODE {mode}              # Set waveform mode
:WAV:POIN {points}            # Set number of waveform points
:WAV:MODE?                    # Query waveform mode
:WAV:POIN?                    # Query number of waveform points
:WAV:FORM ASC                 # Set waveform format to ASCII
:WAV:DATA?                    # Query waveform data
:WAVeform:STARt?              # Query waveform start point
:WAVeform:STOP?               # Query waveform stop point

# Trigger Commands
:TRIG:EDGE:SOURce CHAN{n}     # Set trigger source channel
:TRIG:EDGE:LEV {value}        # Set trigger level
:TRIG:SWE SING               # Set trigger sweep mode to single
:TRIG:STAT?                  # Query trigger status
:SING                        # Set to single trigger mode
