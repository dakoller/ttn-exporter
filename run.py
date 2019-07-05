# https://www.thethingsnetwork.org/forum/t/a-python-program-to-listen-to-your-devices-with-mqtt/9036/6
# Get data from MQTT server
# Run this with python 3, install paho.mqtt prior to use

import paho.mqtt.client as mqtt
import json
import base64
from prometheus_client import start_http_server, Summary, Gauge
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from pprint import pprint
import os
import logging
import sys
from datetime import datetime, timezone
from dateutil import tz, parser



formatter = logging.Formatter('%(asctime)-15s %(name)-12s: %(levelname)-8s %(message)s')

logger = logging.getLogger()
handler = logging.StreamHandler()   # by default writes to STDERR when stream is None
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

port = 8765

logger.info('*** TTN-Prometheus Exporter starting up')
APPEUI = os.environ['APPEUI']
if APPEUI:
    logger.info('*** Using APPEUI %s for access to TTN' % APPEUI)
else:
    logger.critical('*** No AppEUI found. Please grab it from TTN Console.')
    exit(1)

APPID = os.environ['APPID']
if APPID:
    logger.info('*** Using APPID %s for access to TTN' % APPID)
else:
    logger.critical('*** No application ID given. Please get it from TTN Console.')
    exit(1)

PSW    = os.environ['PSW']
if PSW:
    logger.info('*** PSW was provided.')
else: 
    logger.critical('*** No access key (PSW) was provided. Please get one from TTN Console.')
    exit(1)

timeout = os.environ.get('TIMEOUT',240)
logger.info('*** Devices will get deleted, if they did not not send messages for %d seconds. ' % timeout)

labels = [
    'appid',
    'device'
]

metrics = []

data = { 
    }

rssi = {}

device_last_ts = {}

#Call back functions

# gives connection message
def on_connect(mqttc, mosq, obj,rc):
    print("Connected with result code:"+str(rc))
    # subscribe for all devices of user
    mqttc.subscribe('+/devices/+/up')

# gives message from device
@REQUEST_TIME.time()
def on_message(mqttc,obj,msg):
    try:
        #print(msg.payload)
        x = json.loads(msg.payload.decode('utf-8'))
        device = x["dev_id"]
        counter = x["counter"]
        payload_raw = x["payload_raw"]
        payload_fields = x["payload_fields"]
        dt2 = x["metadata"]["time"]
        gateways = x["metadata"]["gateways"]

        gw_id = gateways[0]['gtw_id']

        if device not in device_last_ts.keys():
            device_last_ts[device] = dt2
        else:
            device_last_ts[device] = dt2

        #pprint(device_last_ts)

        # process payload fields
        for field_key in payload_fields.keys():
        #    g = Gauge('%s' % (field_key), 'Description of gauge', labels)
        #    g.labels(appid= APPID, device= device).set(payload_fields[field_key])
            if field_key not in data.keys():
                data[field_key] = {}
                metrics.append(field_key)
            
            if device not in data[field_key].keys():
                data[field_key][device] = {}

                rssi[device] = {}
        
            if gw_id not in rssi.keys():
                rssi[device][gw_id] = 0.0

            rssi[device][gw_id] = gateways[0]['rssi']

            values = (
                payload_fields[field_key],
                gateways[0]['gtw_id']
                )
            data[field_key][device] = values

            


        
        # print for every gateway that has received the message and extract RSSI
        for gw in gateways:
            gateway_id = gw["gtw_id"]
            rssi2 = gw["rssi"]
            #logger.debug(datetime + ", " + device + ", " + str(counter) + ", "+ gateway_id + ", "+ str(rssi2) + ", " + str(payload_fields))
    except Exception as e:
        print(e)
        pass

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mqttc,obj,level,buf):
    print("message:" + str(buf))
    print("userdata:" + str(obj))


class CustomCollector(object):
    def collect(self):

        removed_devices = []

        for device in device_last_ts:
            t1 = parser.parse(device_last_ts[device])
            diff = (datetime.now(timezone.utc)-t1)
            pprint('%s: last seen %d seconds ago' % (device,diff.total_seconds()))

            if diff.total_seconds() > timeout:
                logger.info('*** Deleting device %s since no new messages since %d seconds from it.(Threshold: %d sceonds)' % (device, diff.total_seconds(), timeout ))

                for field_key in data.keys():
                    data[field_key].pop(device, None)

                rssi.pop(device, None)

                removed_devices.append(device)


                logger.info('*** Device %s deleted.' % device)

        for device in removed_devices:
            device_last_ts.pop(device,None)


        for field_key in data.keys():
            c = GaugeMetricFamily('ttn_%s_%s' % (APPID, field_key), 'Help text', labels=labels)
            for device in data[field_key].keys():
                c.add_metric([
                    APPID,  
                    device], 
                    data[field_key][device][0])
            yield c

        c2 = GaugeMetricFamily('ttn_rssi', 'Help text', labels=['device','gateway'])
        for device in rssi.keys():
            for gw in rssi[device].keys():
                c2.add_metric(
                    [device,gw],
                    rssi[device][gw]
                )

        yield c2


REGISTRY.register(CustomCollector())

if __name__== '__main__':
    mqttc= mqtt.Client()
    # Assign event callbacks
    mqttc.on_connect=on_connect
    mqttc.on_message=on_message

    mqttc.username_pw_set(APPID, PSW)
    mqttc.connect("eu.thethings.network",1883,60)

    start_http_server(port)
    logger.info('*** Exporter exposes data localhost:%d' % port)

    # and listen to server
    run = True
    while run:
        mqttc.loop()
