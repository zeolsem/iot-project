import paho.mqtt.client as mqtt
import json

class MQTTSender:
    def __init__(self, broker_address, topic):
        self.client = mqtt.Client(client_id="WeatherStation")
        self.broker_address = broker_address
        self.topic = topic
    
    def connect(self):
        try:
            self.client.connect(self.broker_address)
            self.client.loop_start()
            print(f"Connected to MQTT broker at {self.broker_address}")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def send_message(self, data_dict):
        try:
            payload = json.dumps(data_dict)
            result = self.client.publish(self.topic, payload, qos=1)
            result.wait_for_publish()  
            
            if result.is_published():
                print(f"Message sent to topic {self.topic}: {payload}")
                return True
            return False
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

class MQTTReceiver:
    def __init__(self, broker_address, topic):
        self.client = mqtt.Client(client_id="WeatherDisplay")
        self.broker_address = broker_address
        self.topic = topic
        self.on_message_callback = None
    
    def _on_connect(self, client, rc):
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
            
            self.client.connect(self.broker_address)
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