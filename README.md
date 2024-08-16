# fronius_smart_meter_modbus_tcp_emulator
Emulate a Fronius  Modbus TCP Smart Meter 

Based on
https://www.photovoltaikforum.com/thread/185108-fronius-smart-meter-tcp-protokoll

Code is under develoment!

Just enter MQTT server data and send CONSUMPTION, TOTAL_IMPORT in Wh and TOTAL_EXPORT in Wh to the configured topics.

Was tested with fronius gen24 as primary counter

````shell
pip install -r requirements.txt
````
