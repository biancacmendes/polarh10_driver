# Polar H10 ECG WebSocket Gateway

This project provides a **Python gateway for streaming ECG data from a Polar H10 chest strap over the network**.

The gateway connects to the Polar H10 via **Bluetooth Low Energy (BLE)** and broadcasts ECG data through a **WebSocket endpoint**. Other applications (VR systems, analytics pipelines, monitoring dashboards, etc.) can subscribe to this stream and receive ECG packets in real time.

---

# Architecture

The system implements the following pipeline:

```
Polar H10
   ↓
BLE (bleak)
   ↓
polar-python driver
   ↓
PolarClient
   ↓
Async Queue
   ↓
WebSocketGateway
   ↓
Network Clients
```

The Polar device is read asynchronously, packets are queued internally, and then streamed to all connected WebSocket clients.

---

# Repository Structure

```
polarh10_driver
│
├── main.py
├── requirements.txt
├── venv_setup.sh
├── README.md
│
├── config
│   ├── config.yaml
│   └── data_loader.py
│
├── core
│   ├── polar_client.py
│   └── websocket_gateway.py
│
└── test
    └── test.py
```

Description of the main components:

| Path | Description |
|-----|-------------|
| `main.py` | Entry point that initializes the Polar client and WebSocket gateway |
| `config/` | Configuration loading and YAML configuration |
| `core/polar_client.py` | Handles BLE communication with the Polar H10 |
| `core/websocket_gateway.py` | WebSocket server that broadcasts ECG packets |
| `test/test.py` | Simple WebSocket client used to test the stream |
| `venv_setup.sh` | Script that creates the Python virtual environment |
| `requirements.txt` | Python dependencies |

---

# Requirements

Hardware:

- Polar H10 chest strap
- Bluetooth support on the host machine

Software:

- Python 3.14
- macOS or Linux

---

# Installation

## 1. Clone the repository

```
git clone <repository-url>
cd polarh10_driver
```

## 2. Setup the Python environment

Run the provided setup script:

```
sh venv_setup.sh
```

This script will:

- create a `.venv` virtual environment
- install all required dependencies

Activate the environment:

```
source .venv/bin/activate
```

---

# Dependencies

Main dependencies used by the project:

```
bleak
polar-python==0.0.5
fastapi
uvicorn
pyyaml
numpy
pandas
matplotlib
websockets
```

Install manually if needed:

```
pip install -r requirements.txt
```

---

# Configuration

Configuration is defined in:

```
config/config.yaml
```

Example:

```
bluetooth:
  device_address: "D6531279-6A6E-DDA8-C1D5-13D102E3EA9A"

gateway:
  host: "0.0.0.0"
  port: 8765
  websocket_path: "/stream"
```

Parameters:

| Field | Description |
|------|-------------|
| `device_address` | Bluetooth MAC address of the Polar H10 |
| `host` | Network interface for the gateway |
| `port` | WebSocket server port |
| `websocket_path` | WebSocket endpoint path |

---

# Running the Gateway

Start the gateway with:

```
python main.py
```

Expected output:

```
Searching Polar device...
Polar device resolved
Starting ECG stream
Starting WebSocket server
```

The WebSocket endpoint will be available at:

```
ws://localhost:8765/stream
```

---

# Testing the Stream

A simple test client is provided.

Run in a second terminal:

```
python test/test.py
```

The client will connect to the gateway and print incoming packets.

Example output:

```
{'type': 'ecg', 'seq': 8, 'timestamp': 1773524298.720088, 'samples': [...]}
```

---

# ECG Packet Format

Each WebSocket message has the structure:

```
{
  "type": "ecg",
  "seq": 8,
  "timestamp": 1773524298.720088,
  "samples": [-141, -134, -127, ...]
}
```

Field description:

| Field | Meaning |
|------|--------|
| `type` | Packet type (`ecg`) |
| `seq` | Sequential packet number |
| `timestamp` | Host timestamp when packet was generated |
| `samples` | Raw ECG samples received from the Polar device |

Notes:

- Samples are **raw ECG integer values** from the sensor.
- Each packet contains a **block of ECG samples**.

---

# Typical Workflow

Terminal 1:

```
python main.py
```

Terminal 2:

```
python test/test.py
```

You should observe ECG packets arriving in real time.

---

# Future Improvements

Potential future features:

- RR interval extraction
- Heart rate calculation
- HRV metrics
- Live ECG visualization via HTTP dashboard
- Session recording
- Integration with VR experiment pipelines

---

# License

This project is intended for **research and experimental use**.