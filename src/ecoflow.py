#!/usr/bin/env python
import hashlib
import hmac
import json
import random
import ssl
import time
import paho.mqtt.client as mqtt
import httpx
import logging
import os

logging.basicConfig(level=logging.DEBUG)

# Config
API_HOST = os.getenv("ECOFLOW_API_HOST")
API_ACCESS_KEY = os.getenv("ECOFLOW_API_ACCESS_KEY")
API_SECRET_KEY = os.getenv("ECOFLOW_API_SECRET_KEY")
SN = os.getenv("ECOFLOW_POWERSTREAM_SN")

# Globals
output_power_watts: float = float(0) # for example: 123.4 W
on_update = lambda : {}

# Utils
def sign(params: dict[str, str]):
    sorted_params = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(API_SECRET_KEY.encode('utf-8'), sorted_params.encode('utf-8'), hashlib.sha256).hexdigest()
    all_params = {
        **params,
        "sign": signature
    }
    return { key: all_params[key] for key in sorted(all_params) }

# Auth
params = {
    "accessKey": API_ACCESS_KEY,
    "nonce": str(random.randint(10000, 1000000)),
    "timestamp": str(int(time.time() * 1000))
}
r = httpx.get(
    API_HOST + "/iot-open/sign/certification",
    headers = sign(params)
)

print(r.request)
print(r.json())

data = r.json().get("data")
certificateAccount = data.get("certificateAccount")
certificatePassword = data.get("certificatePassword")
host = data.get("url")
port = int(data.get("port"))

# Define the callback functions
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribe to a topic
    client.subscribe(f"/open/{certificateAccount}/{SN}/quota")

def on_message(client, userdata, message):
    print(f"Received message: {message.payload.decode()} on topic {message.topic}")
    if message.topic == f"/open/{certificateAccount}/{SN}/quota":
        global output_power_watts
        output_power_watts = float(json.loads(message.payload).get("param").get("invOutputWatts"))/10
        on_update()

# Create an MQTT client instance
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.enable_logger()
client.username_pw_set(certificateAccount, certificatePassword)
client.tls_set(certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED)
client.tls_insecure_set(False)

# Assign the callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(host, port, 60)

# Publish a message
#client.publish("test/topic", "Hello, MQTT!")

# Start the loop to process network traffic and dispatch callbacks
print(f"Started looping")
#client.loop_forever()
client.loop_start()
