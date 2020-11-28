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
import websockets
from urllib.parse import urlparse
import json
import requests
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
# import socketio
from brainflow.data_filter import DataFilter, FilterTypes


class Trace(object):
    def __init__(self, id='Default',tag=None):
        """
        This is the constructor for the Trace data object
        """

        self.id = id
        self.all_channels = True
        self.channels = [-1,-2,-3,-4,-5,-6,-7,-8] # Ignored
        self.date = datetime.datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p")
        s = requests.Session()
        s.headers['mode'] = 'cors'
        s.headers['credentials'] = 'include'
        self.session = s
        self.reader = []
        self.data = []
        self.details = {}

    def __repr__(self):
        return "Trace('{},'{}',{})".format(self.id, self.date)

    def __str__(self):
        return '{} _ {}'.format(self.id, self.date)

    def prime(self, attribute, value):
        self.details[attribute] = value

    async def capture(self, stream,url, port=None,plot=False, model=None,categories=None,details=None):

        # Authenticate
        res = self.session.post(url + '/login')

        cookies = ""
        cookieDict = res.cookies.get_dict()
        for cookie in (cookieDict):
            cookies += str(cookie + "=" + cookieDict[cookie] + "; ")
        
        o = urlparse(url)
        if (o.scheme == 'http'):
            uri = "ws://" + o.netloc
        elif (o.scheme == 'https'):
            uri = "wss://" + o.netloc
        else:
            print('not a valid url scheme')

        async with websockets.connect(uri,ping_interval=None, extra_headers=[('cookie', cookies)]) as websocket:
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

            # Get Data
            pass_data = []
            rate = DataFilter.get_nearest_power_of_two(self.board.rate)
            data = self.board.get_current_board_data(num_samples=rate)#1)
            t = data[self.board.time_channel]

            if self.all_channels:
                data = data[self.board.eeg_channels] # SCALED
            else:
                data = data[self.board.eeg_channels][self.channels] # SCALED

            for entry in data:
                DataFilter.perform_highpass(entry, self.board.rate, 3.0, 4, FilterTypes.BUTTERWORTH.value, 0)
                pass_data.append((entry).tolist())

            if len(t) > 0:
                t = t - self.start_time

            message = {
                'destination': 'bci', 
            'data': {'ts_filtered':pass_data}
            }
            message = json.dumps(message, separators=(',', ':'))
            
            
            # (Re)Open Websocket Connection
            if not websocket.open:
                try:
                    print('Websocket is NOT connected. Reconnecting...')
                    websocket = await websockets.connect(uri,ping_interval=None, extra_headers=[('cookie', cookies)])
                except:
                    print('Unable to reconnect, trying again.')

            await websocket.send(message)
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