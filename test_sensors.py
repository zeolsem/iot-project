#!/usr/bin/env python3
import time
import board
import adafruit_dht
from w1thermsensor import W1ThermSensor

# --- KONFIGURACJA (CONSTANTS) ---
DHT_PIN_ID = board.D16  # GPIO 16 (Pin 36) dla DHT11
LOOP_DELAY = 2.0  # Opóźnienie pętli (DHT11 wymaga min 2s)


# --- WARSTWA SPRZĘTOWA (HARDWARE ABSTRACTION) ---
def init_dht():
    """Inicjalizuje czujnik DHT11."""
    try:
        # use_pulseio=False pomaga na RPi 4/5 przy problemach z timingiem
        return adafruit_dht.DHT11(DHT_PIN_ID, use_pulseio=False)
    except Exception as e:
        print(f"[ERROR] Nie można zainicjować DHT11: {e}")
        return None


def init_ds18b20():
    """
    Inicjalizuje czujnik DS18B20.
    UWAGA: Pin jest obsługiwany przez kernel (domyślnie GPIO 4/Pin 7).
    Python szuka urządzenia w /sys/bus/w1/devices/.
    """
    try:
        return W1ThermSensor()
    except Exception:
        # Zwraca None, jeśli czujnik nie jest wykryty (nie przerywa programu)
        return None


def read_dht_sensor(dht_device):
    """
    Bezpieczny odczyt z DHT11 z obsługą typowych błędów (RuntimeError).
    Zwraca krotkę: (temperatura, wilgotność) lub (None, None).
    """
    if not dht_device:
        return None, None

    try:
        t = dht_device.temperature
        h = dht_device.humidity
        return t, h
    except RuntimeError as _:
        # DHT często zwraca błędy sumy kontrolnej - to normalne zachowanie
        return None, None
    except Exception as e:
        print(f"[DHT CRITICAL] Błąd odczytu: {e}")
        return None, None


def read_ds18b20_sensor(ds_device):
    """Odczytuje temperaturę z DS18B20."""
    if not ds_device:
        return None
    try:
        return ds_device.get_temperature()
    except Exception as e:
        print(f"[DS18B20 ERROR] Błąd odczytu: {e}")
        return None


# --- WARSTWA LOGIKI (BUSINESS LOGIC) ---


def print_telemetry(ds_temp, dht_temp, dht_hum):
    """Formatuje i wyświetla dane w konsoli."""
    parts = []

    # Priorytet dla DS18B20 (jest dokładniejszy)
    if ds_temp is not None:
        parts.append(f"DS18B20: {ds_temp:.2f}°C")

    if dht_temp is not None:
        parts.append(f"DHT11: {dht_temp}°C")

    if dht_hum is not None:
        parts.append(f"Wilgotność: {dht_hum}%")

    if not parts:
        print("... Oczekiwanie na dane ...")
    else:
        print(" | ".join(parts))


# --- GŁÓWNA PĘTLA (ORCHESTRATION) ---


def main():
    print("--- URUCHAMIANIE SYSTEMU MONITORINGU ---")

    # 1. Inicjalizacja zasobów
    dht = init_dht()
    ds18 = init_ds18b20()

    if not ds18:
        print("[WARN] Nie wykryto DS18B20. Upewnij się, że 1-Wire jest włączone.")

    print("Naciśnij Ctrl+C, aby zakończyć.\n")

    try:
        while True:
            # 2. Akwizycja danych
            ds_temp = read_ds18b20_sensor(ds18)
            dht_temp, dht_hum = read_dht_sensor(dht)

            # 3. Prezentacja danych
            print_telemetry(ds_temp, dht_temp, dht_hum)

            # 4. Decyzja sterująca
            # Wybieramy temperaturę z DS jako główną, fallback do DHT
            reference_temp = ds_temp if ds_temp is not None else dht_temp

            # 5. Oczekiwanie
            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n[STOP] Zatrzymywanie systemu przez użytkownika...")
    finally:
        # 6. Sprzątanie (Graceful Shutdown)
        if dht:
            dht.exit()
        print("Zasoby zwolnione. Do widzenia.")


if __name__ == "__main__":
    main()
