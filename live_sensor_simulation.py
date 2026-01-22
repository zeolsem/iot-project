from WeatherDatabase import WeatherDatabase
import time
import random
from datetime import datetime

db = WeatherDatabase()
stations = ["station A", "station B", "station C"]


try:
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for station in stations:
            if station == "station A":
                base = 22.0
            elif station == "station B":
                base = 16.0
            else:
                base = 7.0 
            
            temp = round(base + random.uniform(-0.5, 0.5), 2)
            hum = round(random.uniform(40.0, 50.0), 2)
            
            db.insert_reading(station, temp, hum, now)
            print(f"[{now}] {station}: {temp}C")
        
        time.sleep(1) 
except KeyboardInterrupt:
    print("Symulacja zatrzymana.")