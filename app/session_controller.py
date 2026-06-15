class SessionController:
    def __init__(self):
        self.is_recording_fixed = False
        self.is_recording_hub = False

    def start_fixed(self):
        self.is_recording_fixed = True

    def stop_fixed(self):
        self.is_recording_fixed = False

    def start_hub(self):
        self.is_recording_hub = True

    def stop_hub(self):
        self.is_recording_hub = False

    def is_any_recording(self):
        return self.is_recording_fixed or self.is_recording_hub