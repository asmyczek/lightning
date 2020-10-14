# -*- coding: utf-8 -*-

from time import sleep
from lightning.DFRobotAS3935 import DFRobotAS3935, Location, Interrupt
import RPi.GPIO as GPIO
import logging
import paho.mqtt.client as mqtt
from json import dumps
from datetime import datetime


I2C_ADDRESS = 0X03  # 0X01, 0X02, 0X03
IRQ_PIN = 7  # GPIO input pin

GPIO.setmode(GPIO.BOARD)
GPIO.setup(IRQ_PIN, GPIO.IN)


def on_connect(client, user_data, flags, rc):
    if rc == 0:
        client.publish(f'{user_data["config"]("mqtt", "topic")}/status', payload='online', retain=False)
    else:
        logging.error(f'Unable to establish connection to mqtt server. Status {rc}')


def on_disconnect(client, user_data, rc):
    logging.info(f'Disconnected from mqtt broker. Status {rc}')


def on_publish(client, user_data, mid):
    logging.debug(f'Data published with mid {mid}.')


def create_client(config):
    client = mqtt.Client(config('mqtt', 'client_name'))
    client.username_pw_set(config('mqtt', 'user'), password=config.get('mqtt', 'password'))
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.will_set(f'{config("mqtt", "topic")}/status', 'offline', qos=0, retain=False)
    return client


def mk_callback_handler(sensor, mqtt, config):
    def handler(channel):
        sleep(0.005)
        timestamp = datetime.now().astimezone(tz=None).isoformat()
        interrupt = sensor.get_interrupt()
        if interrupt == Interrupt.LIGHTNING:
            distance = sensor.get_lightning_dist()
            intensity = sensor.get_strike_energy()
            logging.debug(f'Lightning occurs {distance} km away at intensity {intensity}.')

            message = dumps({'timestamp': timestamp,
                             'distance': distance,
                             'intensity': intensity})
            mqtt.publish(f'{config("mqtt", "topic")}/strike', payload=message, retain=True)

        elif interrupt == Interrupt.DISTURBANCE:
            logging.warning('Disturbance detected!')
            mqtt.publish(f'{config("mqtt", "topic")}/disturbance',
                         payload=dumps({'timestamp': timestamp}),
                         retain=True)
        elif interrupt == Interrupt.NOISE:
            logging.warning('Noise level too high!')
            mqtt.publish(f'{config("mqtt", "topic")}/noise',
                         payload=dumps({'timestamp': timestamp}),
                         retain=True)
        elif interrupt == Interrupt.ERROR:
            mqtt.publish(f'{config("mqtt", "topic")}/error',
                         payload=dumps({'timestamp': timestamp}),
                         retain=True)
        else:
            logging.debug('Unexpected result!')

    return handler


def start_sensor(config):

    sensor = DFRobotAS3935(I2C_ADDRESS,
                           bus=config('sensor', 'bus'),
                           capacitance=config('sensor', 'capacitance'),
                           location=Location[config('sensor', 'location').upper()],
                           disturber_detection=config('sensor', 'disturber_detection'))

    mqtt = create_client(config)
    try:
        logging.info('Starting MQTT notifier.')
        mqtt.connect(config('mqtt', 'broker'), config('mqtt', 'port'))

        if sensor.reset():
            logging.info('Sensor initialized.')
            GPIO.add_event_detect(IRQ_PIN, GPIO.RISING, callback=mk_callback_handler(sensor, mqtt, config))
            logging.info('Starting lightning detection...')
            mqtt.loop_forever()
        else:
            logging.fatal('Sensor initialization failed.')

    except Exception as e:
        logging.error(e)
        logging.exception('Unable to connect to MQTT broker!')
