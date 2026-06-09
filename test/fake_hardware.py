import asyncio
import json
import math
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import websockets

HOST = "localhost"
PORT = 8765
OUTPUT_DIR = Path("recordings")


recording_enabled = False
recording_run_id = None
recording_label = None
recording_started_at = None
recording_samples = []
recording_packets = []


def generate_fake_ecg_samples(seq, num_samples=10):
    samples = []

    for i in range(num_samples):
        t = (seq * num_samples + i) * 0.01
        base_signal = math.sin(2 * math.pi * 1.2 * t)
        noise = random.uniform(-0.1, 0.1)
        ecg_value = round(base_signal + noise, 4)
        samples.append(ecg_value)

    return samples


def timestamp_for_filename():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_name(value):
    if not value:
        return "no_run_id"

    return "".join(
        char if char.isalnum() or char in ("-", "_") else "_"
        for char in str(value)
    )


def start_recording(run_id=None, label=None):
    global recording_enabled
    global recording_run_id
    global recording_label
    global recording_started_at
    global recording_samples
    global recording_packets

    recording_enabled = True
    recording_run_id = run_id or f"manual-{timestamp_for_filename()}"
    recording_label = label
    recording_started_at = datetime.now().isoformat()
    recording_samples = []
    recording_packets = []

    print("\n" + "=" * 72)
    print("[control] RECORDING STARTED")
    print(f"[control] runId     : {recording_run_id}")
    print(f"[control] label     : {recording_label}")
    print(f"[control] startedAt : {recording_started_at}")
    print("=" * 72 + "\n")

def stop_recording(reason=None):
    global recording_enabled
    global recording_run_id
    global recording_label
    global recording_started_at
    global recording_samples
    global recording_packets

    if not recording_enabled:
        print("[control] STOP ignored: recording was not active")
        return None

    recording_enabled = False
    finished_at = datetime.now().isoformat()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_id_safe = safe_name(recording_run_id)
    ts = timestamp_for_filename()

    file_id = f"{run_id_safe}_{ts}"

    ecg_path = OUTPUT_DIR / f"ecg_raw_{file_id}.npy"
    packets_path = OUTPUT_DIR / f"packets_{file_id}.npy"
    metadata_path = OUTPUT_DIR / f"metadata_{file_id}.json"

    ecg_array = np.asarray(recording_samples, dtype=np.float32)
    packets_array = np.asarray(recording_packets, dtype=object)

    np.save(ecg_path, ecg_array)
    np.save(packets_path, packets_array, allow_pickle=True)

    metadata = {
        "fileId": file_id,
        "runId": recording_run_id,
        "label": recording_label,
        "reason": reason,
        "startedAt": recording_started_at,
        "finishedAt": finished_at,
        "numSamples": int(ecg_array.size),
        "numPackets": int(len(recording_packets)),
        "ecgFile": str(ecg_path),
        "packetsFile": str(packets_path),
        "metadataFile": str(metadata_path),
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("[control] RECORDING STOPPED")
    print(f"[control] fileId    : {file_id}")
    print(f"[control] runId     : {recording_run_id}")
    print(f"[control] label     : {recording_label}")
    print(f"[control] startedAt : {recording_started_at}")
    print(f"[control] finishedAt: {finished_at}")
    print(f"[control] samples   : {int(ecg_array.size)}")
    print(f"[control] packets   : {int(len(recording_packets))}")
    print(f"[control] ECG       : {ecg_path}")
    print(f"[control] packets   : {packets_path}")
    print(f"[control] metadata  : {metadata_path}")
    print("=" * 72 + "\n")

    recording_run_id = None
    recording_label = None
    recording_started_at = None
    recording_samples = []
    recording_packets = []

    return metadata


async def stream_handler(websocket):
    global recording_samples
    global recording_packets

    print(f"[stream] Driver conectado de {websocket.remote_address}")

    seq = 0

    try:
        while True:
            samples = generate_fake_ecg_samples(seq)

            payload = {
                "seq": seq,
                "samples": samples,
                "sampleRateHz": 100,
                "metrics": {
                    "rr": round(random.uniform(0.75, 0.85), 3),
                    "hr": round(random.uniform(70, 80), 1),
                    "rmssd": round(random.uniform(30, 50), 1),
                    "sdnn": round(random.uniform(40, 60), 1),
                    "pnn50": round(random.uniform(0.10, 0.25), 3),
                    "lf_hf": round(random.uniform(1.2, 2.0), 2),
                },
            }

            if recording_enabled:
                recording_samples.extend(samples)
                recording_packets.append(payload)

            await websocket.send(json.dumps(payload))

            seq += 1
            await asyncio.sleep(0.2)

    except websockets.exceptions.ConnectionClosed:
        print(f"[stream] Driver desconectado de {websocket.remote_address}")


async def control_handler(websocket):
    print(f"[control] Cliente conectado de {websocket.remote_address}")

    try:
        async for message in websocket:
            try:
                command = json.loads(message)
            except json.JSONDecodeError:
                response = {
                    "ok": False,
                    "error": "invalid_json",
                }
                await websocket.send(json.dumps(response))
                continue

            print(f"[control] Received: {command}")

            if command.get("type") != "recording":
                response = {
                    "ok": False,
                    "error": "unsupported_type",
                    "received": command,
                }
                await websocket.send(json.dumps(response))
                continue

            action = command.get("action")

            if action == "start":
                start_recording(
                    run_id=command.get("runId"),
                    label=command.get("label"),
                )

                response = {
                    "ok": True,
                    "type": "recording",
                    "action": "start",
                    "runId": recording_run_id,
                    "recording": recording_enabled,
                }

            elif action == "stop":
                metadata = stop_recording(reason=command.get("reason"))

                response = {
                    "ok": True,
                    "type": "recording",
                    "action": "stop",
                    "recording": recording_enabled,
                    "metadata": metadata,
                }

            else:
                response = {
                    "ok": False,
                    "error": "unsupported_action",
                    "action": action,
                }

            await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed:
        print(f"[control] Cliente desconectado de {websocket.remote_address}")


async def router(websocket, path):
    if path == "/stream":
        await stream_handler(websocket)
    elif path == "/control":
        await control_handler(websocket)
    else:
        await websocket.close(4004, "Not Found")


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando hardware falso:")
    print(f"  stream : ws://{HOST}:{PORT}/stream")
    print(f"  control: ws://{HOST}:{PORT}/control")
    print(f"  output : {OUTPUT_DIR.resolve()}")

    async with websockets.serve(router, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServidor finalizado pelo usuário.")