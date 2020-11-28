import sys
import os
from trace import Trace 
import numpy as np
import pickle
import asyncio

async def beginStream(STREAM, PORT, URL):

    # Initialize the Trace
    trace = Trace(id = 'User')

    # Connect Websocket + EEG headset through Brainflow
    if STREAM == 'SYNTHETIC':
        await trace.capture(stream=STREAM,url=URL)
    elif STREAM == 'OPENBCI':
        await trace.capture(stream=STREAM,url=URL,port=PORT)

async def main():

    STREAM =  'SYNTHETIC' #'OPENBCI' # 
                            # Streams
                                # OPENBCI
                                # SYNTHETIC

                            # Ports
                                # Mac: '/dev/cu.usbserial-DM01N7AE'
                                # Windows: 'COM4'
                                # Synthetic: None
    PORT =     None #'/dev/cu.usbserial-DM01N7AE' #

    URL = 'https://brainsatplay.azurewebsites.net' # 'http://localhost' # 

    stream = asyncio.create_task(beginStream(STREAM, PORT, URL))
    await stream

if __name__ == "__main__":
    asyncio.run(main())