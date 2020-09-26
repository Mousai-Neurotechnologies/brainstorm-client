import sys
import mneme
import os
from mneme.core import Trace
from mneme.utils import realtime_streams, features, plots
import quantities as pq
import numpy as np
import pickle

STREAM = 'OPENBCI' 
                        # Streams
                            # OPENBCI
                            # SYNTHETIC

                        # Ports
                            # Mac: '/dev/cu.usbserial-DM01N7AE'
                            # Windows: 'COM4'
                            # Synthetic: None
PORT = '/dev/cu.usbserial-DM01N7AE'

# Initialize the Trace
trace = Trace(id = 'User')

if STREAM == 'SYNTHETIC':
    trace.capture(stream=STREAM)
elif STREAM == 'OPENBCI':
    trace.capture(stream=STREAM,port=PORT)