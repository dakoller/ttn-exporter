# ttn-exporter
Prometheus Exporter of TheThingsNetwork sensor data

This repo exposes messages from IoT devices (sensors etc.) following the LoRaWan standard from TheThingsNetwork as data consumable by prometheus for data collection & visualization.

The image at https://cloud.docker.com/repository/docker/dakoller/ttn-exporter can be started like:

Docker run -e APPEUI="*" -e APPID="*" -e PSW="***" -p 8765:8765 --name ttn01 dakoller/ttn-exporter:latest

APPEUI, APPID & PSW (=Application Access Key) need to be taken from TTN Console.

Now all numerical fields from all devices in the given TTN application are processed and exposed.

OPEN TODO/BUG:

Data from sensors, which don't send data anymore, are currently repeated (until restart of the container). --> The plan is to remove devices from the prometheus output, once a configurable duration after last message has passed
