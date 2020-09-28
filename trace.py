""" 
This module defines :class:'Trace'
"""

import sys, signal
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import pickle
import datetime
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
import socketio


class Trace(object):
    def __init__(self, id='Default',tag=None):
        """
        This is the constructor for the Trace data object
        """

        self.id = id
        self.channel = 0
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
        self.board = initialize_board(stream,port)
        print('Starting stream')
        self.board.start_stream(num_samples=450000)
        self.start_time = time.time()
        signal.signal(signal.SIGINT, self.signal_handler)

        while True:
            data = self.board.get_current_board_data(num_samples=self.board.rate)
            t = data[self.board.time_channel]
            data = data[self.board.eeg_channels]
            if len(t) > 0:
                t = t - self.start_time
                print(t[-1])
            # Scaling down the raw feed...
            self.socket.emit('real_bci', {'signal':(data[self.channel]/100).tolist(),
            'time': (t*1000).tolist()})
            
    def save(self,label=None,datadir='traces'):
        datadir = "traces"
        if not os.path.exists(datadir):
            os.mkdir(datadir)

        print(f"Saving " + self.id + "'s trace...")
        filename = os.path.join(datadir, f"{self.id}{label}")
        with open(filename, "wb") as fp:
            pickle.dump(self, fp)
        print(self.id + " saved!")

    def plot(self):
        plt.figure()
        print('Only for channel #' + str(self.channel))
        data = self.board.get_current_board_data(num_samples=450000)
        t = data[self.board.time_channel] - self.start_time
        eeg_data = data[self.board.eeg_channels][self.channel]
        plt.plot(t, eeg_data)
        plt.title('OpenBCI Stream History')
        plt.ylabel('Voltage')
        plt.xlabel('Time (s)')

        plt.show()
        
        return data

    
    def signal_handler(self, signal, frame):

        print('\nStopping data stream.')
        flag = True

        # Disconnect socket
        self.socket.disconnect()
        delattr(self, 'socket')

        # Stop stream
        self.board.stop_stream()

        data = self.plot()

        while flag:
        # Give the option to save data locally
            save_choice = input("\nWould you like to save your data locally? (y/n) ")
            if save_choice == 'y':
                # nans, x= nan_helper(data)
                # data[nans]= np.interp(x(nans), x(~nans), data[~nans])
                self.data = data[self.board.eeg_channels]
                self.details['time_channel'] = (data[self.board.time_channel] - data[self.board.time_channel][0])
                self.details['voltage_units'] = 'uV'
                self.save(self.date,'traces')
                flag = False
            if save_choice == 'n': 
                flag = False
            else: 
                print("Invalid input.")

        self.board.release_session()

        sys.exit('Exiting brainstorm-client...')

def initialize_board(name='SYNTHETIC',port = None):
    if name == 'SYNTHETIC':
        BoardShim.enable_dev_board_logger()

        # use synthetic board for demo
        params = BrainFlowInputParams()
        board_id = BoardIds.SYNTHETIC_BOARD.value
        board = BoardShim(board_id, params)
        board.rate = BoardShim.get_sampling_rate(board_id)
        board.channels = BoardShim.get_eeg_channels(board_id)
        board.time_channel = BoardShim.get_timestamp_channel(board_id)
        board.eeg_channels = BoardShim.get_eeg_channels(board_id)
        board.accel_channels = BoardShim.get_accel_channels(board_id)

    elif name == 'OPENBCI':

        board_id = BoardIds.CYTON_DAISY_BOARD.value
        params = BrainFlowInputParams()
        params.serial_port = port
        board_id = BoardIds.CYTON_DAISY_BOARD.value
        board = BoardShim(board_id, params)
        board.rate = BoardShim.get_sampling_rate(board_id)
        board.channels = BoardShim.get_eeg_channels(board_id)
        board.time_channel = BoardShim.get_timestamp_channel(board_id)
        board.eeg_channels = BoardShim.get_eeg_channels(board_id)
        board.accel_channels = BoardShim.get_accel_channels(board_id)

    board.prepare_session()
    return board