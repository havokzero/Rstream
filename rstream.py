import asyncio
import aiohttp
import random
import string
from termcolor import colored

# WebSocket URLs
CONTROL_WS_URL = 'wss://208-113-134-124.robotstreamer.com:8865/echo'
CONTROL_WS_URL_JIMBOT = 'wss://208-113-134-124.robotstreamer.com:8765/echo'

# Connection and ping message templates
connect_message = {
    "type": "connect",
    "token": "",  # Set as empty string
    "robot_id": None,  # Update this dynamically based on selection
    "owner_id": "53746"
}

ping_message = {"type": "RS_PING"}

# Command templates
commands = {
    '1': {"type": "command", "command": "F", "key_position": "down", "token": ""},
    '2': {"type": "command", "command": "B", "key_position": "down", "token": ""},
    '3': {"type": "command", "command": "L", "key_position": "down", "token": ""},
    '4': {"type": "command", "command": "R", "key_position": "down", "token": ""},
    'stop': {"type": "command", "command": "", "key_position": "up", "token": ""}
}

# Function to generate random strings for fuzzing
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Function to establish WebSocket connection
async def connect_and_send(session, ws_url, message):
    try:
        ws = await session.ws_connect(ws_url)
        print(colored(f"Connected to WebSocket at {ws_url}", 'green'))
        await ws.send_json(message)
        print(colored(f"Sent message: {message}", 'yellow'))
        asyncio.create_task(receive_messages(ws))  # Start receiving messages
        return ws
    except Exception as e:
        print(colored(f"Error connecting to WebSocket: {e}", 'red'))
        return None

# Function to send a command through an open WebSocket connection
async def send_command(ws, command, semaphore):
    if ws is None or ws.closed:
        print(colored("WebSocket is closed. Cannot send command.", 'red'))
        return
    try:
        async with semaphore:
            await ws.send_json(command)
            print(colored(f"Sent command: {command}", 'yellow'))
            # Send the "up" command after 0.1 seconds to simulate a key press release
            if command['key_position'] == 'down':
                await asyncio.sleep(0.1)
                up_command = command.copy()
                up_command['key_position'] = 'up'
                await ws.send_json(up_command)
                print(colored(f"Sent command: {up_command}", 'yellow'))
            # Receive response non-blocking
            try:
                response = await ws.receive(timeout=0.1)
                print(colored(f"Response received: {response.data}", 'green'))
            except asyncio.TimeoutError:
                pass  # Skip if no response received
    except aiohttp.ClientError as e:
        print(colored(f"WebSocket connection failed: {e}", 'red'))
    except Exception as e:
        print(colored(f"An unexpected error occurred: {e}", 'red'))

# Function to send a ping message to keep the connection alive
async def send_ping(ws):
    if ws is None or ws.closed:
        print(colored("WebSocket is closed. Cannot send ping.", 'red'))
        return
    try:
        await ws.send_json(ping_message)
        print(colored("Ping sent...", 'blue'))
    except Exception as e:
        print(colored(f"Ping failed: {e}", 'red'))

# Function to keep the connection alive with periodic pings
async def keep_alive(ws):
    while not ws.closed:
        await send_ping(ws)
        await asyncio.sleep(10)  # Adjust ping interval as needed

# Function to receive messages from WebSocket
async def receive_messages(ws):
    try:
        async for message in ws:
            if message.type == aiohttp.WSMsgType.TEXT:
                print(colored(f"Message received: {message.data}", 'cyan'))
            elif message.type == aiohttp.WSMsgType.ERROR:
                print(colored(f"WebSocket error: {ws.exception()}", 'red'))
                break
    except Exception as e:
        print(colored(f"Error while receiving messages: {e}", 'red'))

# Wiggle mode function
async def wiggle_mode(ws, semaphore):
    try:
        print(colored("Wiggle mode activated. Press 'Ctrl+C' to stop and return to the main menu.", 'yellow'))
        while True:
            await send_command(ws, commands['3'], semaphore)  # Left
            await asyncio.sleep(0.5)
            await send_command(ws, commands['4'], semaphore)  # Right
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        print(colored("Wiggle mode deactivated. Returning to main menu...", 'yellow'))

# Knock mode function
async def knock_mode(ws, semaphore):
    try:
        print(colored("Knock mode activated. Press 'Ctrl+C' to stop and return to the main menu.", 'yellow'))
        for _ in range(2):
            await send_command(ws, commands['2'], semaphore)  # Backward
            await asyncio.sleep(0.3)
        for _ in range(3):
            await send_command(ws, commands['1'], semaphore)  # Forward
            await asyncio.sleep(0.3)
    except KeyboardInterrupt:
        print(colored("Knock mode deactivated. Returning to main menu...", 'yellow'))

# Left 360 mode function
async def left_360_mode(ws, semaphore):
    try:
        print(colored("Left 360 mode activated. Press 'Ctrl+C' to stop and return to the main menu.", 'yellow'))
        while True:
            await send_command(ws, commands['3'], semaphore)  # Left
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print(colored("Left 360 mode deactivated. Returning to main menu...", 'yellow'))

# Right 360 mode function
async def right_360_mode(ws, semaphore):
    try:
        print(colored("Right 360 mode activated. Press 'Ctrl+C' to stop and return to the main menu.", 'yellow'))
        while True:
            await send_command(ws, commands['4'], semaphore)  # Right
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print(colored("Right 360 mode deactivated. Returning to main menu...", 'yellow'))

# Chat spam function
async def chat_spam(ws, semaphore, message):
    try:
        print(colored("Chat spam mode activated. Press 'Ctrl+C' to stop and return to the main menu.", 'yellow'))
        spam_message = {
            "type": "message",
            "message": message,
            "robot_id": connect_message["robot_id"],
            "owner_id": connect_message["owner_id"],
            "gre_token": "check-if-cached",
            "tts_price": 0,
            "sound_price": 0,
            "token": ""
        }
        while True:
            await send_command(ws, spam_message, semaphore)
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        print(colored("Chat spam deactivated. Returning to main menu...", 'yellow'))

# Function to control robots
async def control_robot(ws_url, robot_id):
    async with aiohttp.ClientSession() as session:
        connect_message["robot_id"] = robot_id
        ws = await connect_and_send(session, ws_url, connect_message)

        if ws is None:
            print(colored("Failed to establish WebSocket connection. Returning to main menu...", 'red'))
            return

        # Semaphore to limit concurrency
        semaphore = asyncio.Semaphore(1)

        # Keep sending pings periodically to maintain the connection
        asyncio.create_task(keep_alive(ws))

        while True:
            command = input(colored("Enter command (1: Forward, 2: Backward, 3: Left, 4: Right, 5: Wiggle, 6: Knock, 7: Left 360, 8: Right 360, 9: Chat, 10: Forward Indefinitely, 11: Reverse Indefinitely, stop, exit): ", 'cyan')).strip().lower()
            if command == 'exit':
                print(colored("Exiting...", 'yellow'))
                break
            elif command == '5':
                await wiggle_mode(ws, semaphore)
            elif command == '6':
                await knock_mode(ws, semaphore)
            elif command == '7':
                await left_360_mode(ws, semaphore)
            elif command == '8':
                await right_360_mode(ws, semaphore)
            elif command == '9':
                message = input(colored("Enter the message to spam: ", 'cyan')).strip()
                await chat_spam(ws, semaphore, message)
            elif command == '10':
                await send_command(ws, commands['1'], semaphore)
            elif command == '11':
                await send_command(ws, commands['2'], semaphore)
            elif command in commands:
                await send_command(ws, commands[command], semaphore)
            elif command == 'stop':
                await send_command(ws, commands['stop'], semaphore)
            else:
                print(colored("Invalid command. Please try again.", 'red'))

        if ws and not ws.closed:
            await ws.close()
            print(colored("WebSocket connection closed.", 'green'))

# Function to fuzz the WebSocket connection
async def fuzz_websocket():
    print(colored("Starting WebSocket fuzzing...", 'cyan'))
    async with aiohttp.ClientSession() as session:
        ws = await connect_and_send(session, CONTROL_WS_URL, connect_message)
        if ws is None:
            print(colored("Failed to establish WebSocket connection.", 'red'))
            return
        semaphore = asyncio.Semaphore(1)
        for _ in range(10):  # Adjust the range for more fuzzing iterations
            fuzz_data = generate_random_string(20)
            await send_command(ws, {"type": "fuzz", "data": fuzz_data}, semaphore)
            await asyncio.sleep(1)

        # Closing the WebSocket after fuzzing
        if ws and not ws.closed:
            await ws.close()
            print(colored("WebSocket connection closed after fuzzing.", 'green'))

# Function to fuzz the API and parse results
async def fuzz_api():
    print(colored("Starting API fuzzing...", 'cyan'))
    base_url = "https://api.robotstreamer.com/v1/get_endpoint/"
    endpoints = [
        "enduser_jsmpeg_audio_broadcast/100",
        "enduser_jsmpeg_audio_broadcast/546"
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                async with session.get(base_url + endpoint) as response:
                    data = await response.json()
                    print(colored(f"API Fuzzing Result for {endpoint}:", 'green'))
                    print(colored(f"Category: {data.get('category')}", 'yellow'))
                    print(colored(f"Host: {data.get('host')}", 'yellow'))
                    print(colored(f"Identifier: {data.get('identifier')}", 'yellow'))
                    print(colored(f"Port: {data.get('port')}", 'yellow'))
            except Exception as e:
                print(colored(f"Error fuzzing API endpoint {endpoint}: {e}", 'red'))

# Main function
async def main():
    while True:
        print(colored("Main Menu:", 'cyan'))
        print("1: Control Pippy")
        print("2: Control Jimbot")
        print("3: Control Both Bots")
        print("4: Fuzz API for keys")
        print("5: Fuzz WebSocket for keys")
        print("q: Quit")
        choice = input(colored("Choose an option: ", 'cyan')).strip().lower()

        if choice == 'q':
            print(colored("Exiting program...", 'yellow'))
            break
        elif choice == '1':
            await control_robot(CONTROL_WS_URL, "100")
        elif choice == '2':
            await control_robot(CONTROL_WS_URL_JIMBOT, "546")
        elif choice == '3':
            print(colored("Controlling both bots simultaneously.", 'green'))
            await asyncio.gather(
                control_robot(CONTROL_WS_URL, "100"),
                control_robot(CONTROL_WS_URL_JIMBOT, "546")
            )
        elif choice == '4':
            await fuzz_api()
        elif choice == '5':
            await fuzz_websocket()
        else:
            print(colored("Invalid choice. Please try again.", 'red'))

if __name__ == "__main__":
    asyncio.run(main())
