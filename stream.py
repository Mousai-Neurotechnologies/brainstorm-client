import sys
import os
from trace import Trace 
import numpy as np
import pickle

STREAM = 'SYNTHETIC' # 'OPENBCI' 
                        # Streams
                            # OPENBCI
                            # SYNTHETIC

                        # Ports
                            # Mac: '/dev/cu.usbserial-DM01N7AE'
                            # Windows: 'COM4'
                            # Synthetic: None
PORT = None # '/dev/cu.usbserial-DM01N7AE'

# Initialize the Trace
trace = Trace(id = 'User')

if STREAM == 'SYNTHETIC':
    trace.capture(stream=STREAM)
elif STREAM == 'OPENBCI':
    trace.capture(stream=STREAM,port=PORT)