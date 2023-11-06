import signal
import asyncio
import websockets
import socket
import json
import threading
from queue import Queue

# Configuration
command_server_address = "127.0.0.1"
command_server_port = 1337
websocket_port = 8766
command_queue = Queue()
canvas_max_x = 0
canvas_max_y = 0

# Global shutdown flag
shutdown_event = threading.Event()

def convert_coordinates(x, y):
    converted_x = (x + 250) * canvas_max_x / 500
    converted_y = (y + 180) * canvas_max_y / 360
    return converted_x, converted_y

def send_command_to_hardware(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((command_server_address, command_server_port))
            s.sendall(command.encode('utf-8'))
            response = s.recv(1024)
        return response.decode('utf-8')
    except socket.error as e:
        print(f"Socket error: {e}")
        return "error"

# Process commands in the queue
async def command_consumer(command_queue):
    global canvas_max_x, canvas_max_y
    calibrated = False
    while True:
        # Check if calibrated        
        if not calibrated:
            print("Checking if plottybot is calibrated")
            # Get hardware status
            status = json.loads(send_command_to_hardware("get_status"))
            # out put log for debuggin: output only calibration_done, canvas_max_x, canvas_max_y
            print("Hardware status: ", status["calibration_done"], status["canvas_max_x"], status["canvas_max_y"])
            # If not calibrated, keep checking
            if not status["calibration_done"]:
                await asyncio.sleep(5)  # Check every 5 seconds
                continue
            else:
                canvas_max_x = status["canvas_max_x"]
                canvas_max_y = status["canvas_max_y"]
                print("Hardware calibrated and ready to plot commands on canvas size: ({}, {})".format(canvas_max_x, canvas_max_y))
                calibrated = True

        # Process commands if calibrated
        while calibrated:
            command = command_queue.get()
            print("Sending command to hardware: {}".format(command))
            response = send_command_to_hardware(command)
            if response != "ok":
                print("Error sending command to hardware: {}".format(response))
                calibrated = False
                break


# Websocket Server Logic
async def websocket_server(websocket, path):
    oldX = 0
    oldY = 0
    print("New Scratch client connected.")
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"Received message: {data}")
            if data["type"] == "goToXY":
                if data["oldX"] != oldX or data["oldY"] == oldY:
                    # If oldX or oldY has changed, send a penUp command and move to the new 'old' location
                    command_queue.put("pen_up")
                    x, y = convert_coordinates(data["oldX"], data["oldY"])
                    command_queue.put(f"go_to({x},{y})")
                    oldX = data["oldX"]
                    oldY = data["oldY"]

                # Send a penDown command and move to the new location
                command_queue.put("pen_down")
                x, y = convert_coordinates(data["x"], data["y"])
                command_queue.put(f"go_to({x},{y})")
            if data["type"] == "penUp":
                command_queue.put("pen_up")
            await websocket.send("ok")
    except websockets.exceptions.ConnectionClosed:
        # When Scratch client disconnects
        while not command_queue.empty():
            command_queue.get()
        print("Scratch client disconnected. Queue cleared.")

async def start_websocket_server():
    async with websockets.serve(websocket_server, '0.0.0.0', websocket_port):
        print("WebSocket server started on port 8766")
        await asyncio.Future()  # run forever

def run_websocket_server():
    asyncio.run(start_websocket_server())

def run_command_consumer():
    asyncio.run(command_consumer(command_queue))

def command_consumer_thread_function():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(command_consumer())


# Main function to start servers
def main():
    # Create threads for websocket_server and command_consumer
    websocket_thread = threading.Thread(target=run_websocket_server, daemon=True)
    command_consumer_thread = threading.Thread(target=run_command_consumer, daemon=True)

    # Start threads
    websocket_thread.start()
    command_consumer_thread.start()

     # Main thread waits for "quit" command
    while True:
        user_input = input("Type 'quit' to stop the servers: ")
        if user_input == "quit":
            print("Shutting down...")
            shutdown_event.set()  # Signal all threads to shut down
            websocket_thread.join()
            command_consumer_thread.join()
            break

def shutdown_handler(signum, frame):
    print("Shutdown signal received. Cleaning up...")
    shutdown_event.set() # Signal the threads to close


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler) # For Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler) # For system kill command
    main()