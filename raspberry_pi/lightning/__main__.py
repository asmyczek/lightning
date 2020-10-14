# -*- coding: utf-8 -*-

from lightning.config import Config
from lightning.lightning import start_sensor
import logging
import argparse


parser = argparse.ArgumentParser(description='Lightning Sensor')
parser.version = "Lightining Sensor v0.1"
parser.add_argument('-v', '--version',
                    action='version',
                    help='Print current service version.')
parser.add_argument('-c', '--config',
                    action='store',
                    type=str,
                    default='config.json',
                    help='Config file name')
args = parser.parse_args()


if __name__ == '__main__':

    config = Config(args.config)

    logging.basicConfig(filename=config('logging', 'file'),
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.getLevelName(config('logging', 'level')))

    start_sensor(config)


