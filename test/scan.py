import asyncio
from bleak import BleakScanner
from polar_python import PolarDevice
from polar_python.models import ACCData, ECGData, HRData

async def main():
    # 1. Find a Polar H10 device
    print("Scanning for Polar H10...")
    device = await BleakScanner.find_device_by_filter(lambda bd, ad: bd.name and "Polar H10" in bd.name, timeout=5)
    if not device:
        print("Device not found. Please ensure your Polar device is awake and nearby.")
        return
    print(f"Found {device.name}, connecting...")

    # 2. Connect and manage the device session
    async with PolarDevice(device) as polar_device:
        # 3. Define your callback functions
        def ecg_callback(data: ECGData):
            print(f"ECG Data: {data}")
        def acc_callback(data: ACCData):
            print(f"ACC Data: {data}")
        def hr_callback(data: HRData):
            print(f"HR Data: {data}")

        # 4. Start data streams with desired configurations
        await polar_device.start_ecg_stream(ecg_callback=ecg_callback, sample_rate=130, resolution=14)
        await polar_device.start_acc_stream(acc_callback=acc_callback, sample_rate=25, resolution=16, range=2)
        await polar_device.start_hr_stream(hr_callback=hr_callback)

        # 5. Keep the main loop running to receive data
        print("Streaming data for 10 seconds...")
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())