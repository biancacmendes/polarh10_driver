# polarh10_driver
Polar H10 Driver


polarh10_driver
│
├── main.py
├── config.yaml
│
├── config
│   └── config_loader.py
│
├── ble
│   ├── polar_client.py
│   └── polar_parser.py
│
├── pipeline
│   ├── data_queue.py
│   └── packet_builder.py
│
├── gateway
│   └── websocket_server.py
│
├── storage
│   └── csv_writer.py
│
└── models
    └── ecg_packet.py