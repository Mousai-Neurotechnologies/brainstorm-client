""" 
This module defines :class:'Trace'
"""

import sys
import imutils
import numpy as np
import time
import cv2
import os
import neo
from mneme.utils.utility_funcs import nan_helper
from mneme.utils.realtime_streams import initialize_board,start_stream,pull_data,stop_stream
from mneme.utils.realtime_viewer import EventManager,query_key
import quantities as pq
from math import cos,sin
import pickle
import datetime

import socketio


class Trace(object):
    def __init__(self, id='Default',tag=None):
        """
        This is the constructor for the Trace data object
        """

        self.id = id
        self.date = datetime.datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p")
        self.reader = []
        self.data = []
        self.details = {}
        self.socket = socketio.Client()

        @self.socket.event
        def connect():
            print('connection established')

        @self.socket.event
        def connect_error():
            print("The connection failed!")

        @self.socket.event
        def my_message(data):
            print('message received with ', data)
            sio.emit('my response', {'response': 'my response'})

        @self.socket.event
        def disconnect():
            print('disconnected from server')

        @self.socket.on('my message')
        def on_message(data):
            print('I received a message!')

    def __repr__(self):
        return "Trace('{},'{}',{})".format(self.id, self.date)

    def __str__(self):
        return '{} _ {}'.format(self.id, self.date)

    def prime(self, attribute, value):
        self.details[attribute] = value

    def capture(self, stream,port=None,model=None,categories=None,details=None):
        url = 'mousai.azurewebsites.net' #'localhost'
        self.socket.connect('https://' + url)
        print('my sid is', self.socket.sid)
        
        print('Initializing board')
        board = initialize_board(stream,port)
        print('Starting stream')
        start_time = start_stream(board)

        while True:
            data = pull_data(board,board.rate)
            t = data[board.time_channel]
            data = data[board.eeg_channels]
            try:
                t = t - start_time
                print(t[-1])
            except:
                pass
            
            # Scaling down the raw feed...
            self.socket.emit('real_bci', {'signal':(data[1]/100).tolist(),
            'time': (t*1000).tolist()})
        data = pull_data(board)

        nans, x= nan_helper(data)
        data[nans]= np.interp(x(nans), x(~nans), data[~nans])

        self.data = data[board.eeg_channels] * pq.uV
        self.details['time_channel'] = (data[board.time_channel] - data[board.time_channel][0])*pq.s
        self.details['voltage_units'] = 'uV'
        stop_stream(board,start_time)

        self.save(self.date,'traces')

    def save(self,label=None,datadir='traces'):
        datadir = "traces"
        if not os.path.exists(datadir):
            os.mkdir(datadir)

        print(f"Saving trace...")
        filename = os.path.join(datadir, f"{self.id}{label}")
        with open(filename, "wb") as fp:
            pickle.dump(self, fp)
        print(self.id + " saved!")

    
    def load(self):
        print('Loading ' + self.id + '...')
        self.reader = neo.get_io(filename=self.id)