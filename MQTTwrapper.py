import paho.mqtt.client as mqtt
import json
from dotenv import load_dotenv
import os

load_dotenv()

class MQTTSender:
    def __init__(self, topic, client_id):
        self.client = mqtt.Client(client_id=client_id)
        self.broker_address = os.getenv("MQTT_BROKER_ADDRESS", "localhost")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.topic = topic
        self.station_id = client_id
    
    def connect(self):
        try:
            self.client.connect(self.broker_address, self.broker_port)
            self.client.loop_start()
            print(f"Connected to MQTT broker at {self.broker_address}:{self.broker_port}")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def send_message(self, data_dict):
        try:
            if not self.client.is_connected():
                return False

            data_dict['station_id'] = self.station_id
            payload = json.dumps(data_dict)
            result = self.client.publish(self.topic, payload, qos=1)  
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Message queued for {self.topic}: {payload}")
                return True
            else:
                return False
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

class MQTTReceiver:
    def __init__(self, topic, client_id="WeatherDisplay"):
        self.client = mqtt.Client(client_id=client_id)
        self.broker_address = os.getenv("MQTT_BROKER_ADDRESS", "localhost")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.topic = topic
        self.on_message_callback = None
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker!")
            client.subscribe(self.topic, qos=1)  
        else:
            print(f"Connection failed: {rc}")
    
    def connect(self, on_message_callback):
        try:
            self.on_message_callback = on_message_callback
            self.client.on_connect = self._on_connect  
            self.client.on_message = self._internal_on_message
            
            self.client.connect(self.broker_address, self.broker_port)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def _internal_on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode('utf-8')
            data_dict = json.loads(payload)
            if self.on_message_callback:
                self.on_message_callback(data_dict)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Message processing error: {e}")
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print(f"Disconnected from MQTT broker")