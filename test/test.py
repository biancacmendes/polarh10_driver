import asyncio
import json
import websockets

HOST = "ws://localhost:8765/stream"


async def main():

    async with websockets.connect(HOST) as ws:

        print("Connected to gateway")

        while True:

            msg = await ws.recv()

            data = json.loads(msg)

            print(data)


if __name__ == "__main__":
    asyncio.run(main())