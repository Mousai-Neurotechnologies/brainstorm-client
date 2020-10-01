
import socketio
import time

url = 'https://mousai.azurewebsites.net'
socket = socketio.Client()
socket.connect(url)
print('my sid is', socket.sid)
socket.emit('chat message', 'Hi')
time.sleep(1)

socket.disconnect()