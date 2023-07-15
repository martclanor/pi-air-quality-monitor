import json
import os
import time
import datetime
import serial
import redis
from zoneinfo import ZoneInfo

redis_client = redis.StrictRedis(host=os.environ.get('REDIS_HOST'), port=6379, db=0)


class AirQualityMonitor():

    def __init__(self):
        self.ser = serial.Serial('/dev/ttyUSB0')

    def awaken_sensor(self):
        self.ser.write(bytes.fromhex('AA B4 06 01 00 00 00 00 00 00 00 00 00 00 00 FF FF 05 AB'))
        time.sleep(10)  # Allow some time for the sensor to wake up

    def sleep_sensor(self):
        self.ser.write(bytes.fromhex('AA B4 06 01 00 00 00 00 00 00 00 00 00 00 00 FF FF 06 AB'))

    def get_measurement(self):
        self.awaken_sensor()
        self.data = []
        for index in range(0,10):
            datum = self.ser.read()
            self.data.append(datum)
        self.pmtwo = int.from_bytes(b''.join(self.data[2:4]), byteorder='little') / 10
        self.pmten = int.from_bytes(b''.join(self.data[4:6]), byteorder='little') / 10
        self.meas = {
            "timestamp": datetime.datetime.now(ZoneInfo("Europe/Berlin")).strftime("%m-%d %H:%M"),
            "pm2.5": self.pmtwo,
            "pm10": self.pmten,
        }
        self.sleep_sensor()  # Put the sensor to sleep after getting the measurement
        return {
            'time': int(time.time()),
            'measurement': self.meas
        }

    def save_measurement_to_redis(self):
        """Saves measurement to redis db"""
        redis_client.lpush('measurements', json.dumps(self.get_measurement(), default=str))

    def get_last_n_measurements(self):
        """Returns the last n measurements in the list"""
        return [json.loads(x) for x in redis_client.lrange('measurements', 0, -1)]
