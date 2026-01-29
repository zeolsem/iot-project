from WeatherDatabase import WeatherDatabase
import time
import random
from datetime import datetime

BATCH_SIZE = 10         
GENERATE_INTERVAL = 1   

stations_config = {
    "RPI-1": ["bme280", "ds18b20"],  
    "RPI-2": ["bme280", "ds18b20"],  
    "RPI-3": ["bme280", "ds18b20"]   
}

db = WeatherDatabase()
temp_buffer = []
hum_buffer = []

try:
    counter = 0
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for station_id, sensors in stations_config.items():
            
            if station_id == "RPI-1": 
                base_temp = 18.0 
                base_hum = 40.0
            elif station_id == "RPI-2": 
                base_temp = 24.0 
                base_hum = 30.0
            else: 
                base_temp = 21.0
                base_hum = 50.0

            variation = (counter % 20) * 0.05
            current_temp = base_temp + variation + random.uniform(-0.05, 0.05)
            
            for sensor_type in sensors:
                sensor_id = f"{station_id}-{sensor_type}"
                
                read_temp = current_temp
                
                if sensor_type == "ds18b20":
                    read_temp += 1.5 
                
                temp_buffer.append({
                    "station_id": station_id,
                    "sensor_id": sensor_id,
                    "value": round(read_temp, 2),
                    "timestamp": now  
                })
                
                if sensor_type == "bme280":
                    read_hum = round(base_hum + random.uniform(-1, 1), 1)
                    hum_buffer.append({
                        "station_id": station_id,
                        "sensor_id": sensor_id,
                        "value": read_hum,
                        "timestamp": now
                    })
        
        threshold = BATCH_SIZE * 6 
        
        if len(temp_buffer) >= threshold: 
            print(f" >>> ZAPIS BATCHA DO BAZY ({len(temp_buffer)} odczytów) <<<")
            db.insert_temps_bulk(temp_buffer)
            db.insert_hums_bulk(hum_buffer)
            
            temp_buffer.clear()
            hum_buffer.clear()
            
        counter += 1
        time.sleep(GENERATE_INTERVAL)

except KeyboardInterrupt:
    print("\nSymulacja zatrzymana.")
