import asyncio
import websockets

async def echo(websocket, path):
    print("Client connected!")
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        print("Client disconnected.")

start_server = websockets.serve(echo, "0.0.0.0", 8766)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
