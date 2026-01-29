## To run the project on a raspberry pi:

##### 0. To check if the Pi is compliant, run setup_pi.sh:

#### 1. Install uv python package manager
#### 2. run `uv sync`

#### 3.for the database-writing script, run: 
`MQTT_BROKER_ADDRESS=<central_node_ip> uv run ingest.py`

#### 4. on edge nodes (and optionally the central node), run:
`MQTT_BROKER_ADDRESS=<central_node_ip> STATION_ID=<arbitrary_name_for_station> SENSOR_COMBO=bme280_ds18 uv run sender.py`

#### 5. for the web app, run:
`uv run app.py`
