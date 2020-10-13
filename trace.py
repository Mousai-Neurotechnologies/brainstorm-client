""" 
This module defines :class:'Trace'
"""

import sys, signal
import matplotlib.pyplot as plt
import numpy as np
import time
import matplotlib.animation as animation
import os
import pickle
import datetime
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
import socketio
from brainflow.data_filter import DataFilter, FilterTypes


class Trace(object):
    def __init__(self, id='Default',tag=None):
        """
        This is the constructor for the Trace data object
        """

        self.id = id
        self.all_channels = False
        self.channels = [-2] # Ignored if all_channels is True
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

    def capture(self, stream,port=None,plot=False, model=None,categories=None,details=None):
        url = 'https://mousai.azurewebsites.net' 
        self.socket.connect(url)
        print('my sid is', self.socket.sid)
        
        print('Initializing board')
        self.board = initialize_board(stream,port)
        print('Starting stream')
        self.board.start_stream(num_samples=450000)
        self.start_time = time.time()
        signal.signal(signal.SIGINT, self.signal_handler)

        # # initialise plot and line
        # fig = plt.figure()
        # ax = fig.add_subplot(1, 1, 1)
        # xs = []
        # ys = []

        # def animate(i, xs, ys): 
        #     data = self.board.get_current_board_data(num_samples=DataFilter.get_nearest_power_of_two(self.board.rate))#1)
        #     t = data[self.board.time_channel]
        #     data = data[self.board.eeg_channels][self.channel]
        #     if len(t) > 0:
        #         t = t - self.start_time
        #     DataFilter.perform_highpass(data, self.board.rate, 3.0, 4, FilterTypes.BUTTERWORTH.value, 0)
        #     self.socket.emit('bci', {'signal':(data).tolist(),
        #     'time': (t*1000).tolist()})

        #     xs.append(t[-1])
        #     ys.append(data[-1])

        #     # Limit x and y lists to 20 items
        #     xs = xs[-20:]
        #     ys = ys[-20:]

        #     # Draw x and y lists
        #     ax.clear()
        #     ax.plot(xs, ys)

        #     # Format plot
        #     plt.xticks(rotation=45, ha='right')
        #     plt.subplots_adjust(bottom=0.30)
        #     plt.title('OpenBCI Live Stream')
        #     plt.ylabel('Voltage')
        
        # ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=1)
        # plt.show()   

        while True:
            pass_data = []
            rate = DataFilter.get_nearest_power_of_two(self.board.rate)
            data = self.board.get_current_board_data(num_samples=rate)#1)
            t = data[self.board.time_channel]

            if self.all_channels:
                data = data[self.board.eeg_channels] / 5 # SCALED
            else:
                data = data[self.board.eeg_channels][self.channels] / 5 # SCALED

            for entry in data:
                pass_data.append(entry.tolist())

            if len(t) > 0:
                t = t - self.start_time

            # DataFilter.perform_highpass(data, self.board.rate, 3.0, 4, FilterTypes.BUTTERWORTH.value, 0)
            self.socket.emit('bci', {'signal':pass_data,
            'time': (t*1000).tolist()})
            time.sleep(.01)

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
        print('Only for channel #' + str(self.channels[0]))
        data = self.board.get_current_board_data(num_samples=450000)
        t = data[self.board.time_channel] - self.start_time
        data = data[self.board.eeg_channels][self.channels[0]]
        DataFilter.perform_highpass(data, self.board.rate, 3.0, 4, FilterTypes.BUTTERWORTH.value, 0)

        plt.plot(t, data)
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