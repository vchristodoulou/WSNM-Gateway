import sys
import os
from datetime import datetime
import configparser
import struct
import json
import subprocess
import socket


NODETYPES_FILE = 'nodetypes.xml'
LOCATIONS_FILE = 'locations.xml'

ACTION_ISALIVE = 'ISALIVE'
NODES_FLASH = 'NFL'.encode()
NODES_RESET = 'NRS'.encode()
NODES_ERASE = 'NER'.encode()

GATEWAY_NODES_FLASH = 'GNF'.encode()
GATEWAY_NODES_RESET = 'GNR'.encode()
GATEWAY_NODES_ERASE = 'GNE'.encode()

DEBUG_GATEWAY = 'DGA'.encode()

NODE_ID = 'node_id'
FLASHED = 'FLASHED'
ERASED = 'ERASED'
ERROR = 'ERROR'

SIZE_ID = 8
SIZE_IP = 16
SIZE_ACTION = 3
SIZE_OF_DATA = 2
SIZE_PORT = 2
SIZE_SEED = 2

DELIMITER = 0x7F        # 127

TIME_FMT = '%d/%m/%Y %H:%M:%S.%f'

SOCK_BUFSIZE = 1024


def segment_packet(pck):
    """Segment a packet"""

    pck_action = struct.unpack('!' + str(SIZE_ACTION) + 's', bytes(pck[:SIZE_ACTION]))
    pck_size = struct.unpack('!H', bytes(pck[SIZE_ACTION:SIZE_ACTION + SIZE_OF_DATA]))
    return (pck_action[0],
            json.loads(pck[SIZE_ACTION + SIZE_OF_DATA:
                           SIZE_ACTION + SIZE_OF_DATA + pck_size[0]]))


def create_packet(action, _id=None, addr=None, update_seed_number=None, data=None):
    """Create a packet"""
    pck = bytearray()

    if action == ACTION_ISALIVE:
        pck.extend(struct.pack('!' + str(SIZE_ID) + 's', _id.encode()))
        pck.extend(struct.pack('!' + str(SIZE_IP) + 's', addr[0].encode()))
        pck.extend(struct.pack('!H', addr[1]))
        pck.extend(struct.pack('!H', update_seed_number))
    else:
        pck.extend(struct.pack('!' + str(SIZE_ACTION) + 's', action))
        pck.extend(struct.pack('!H', len(data)))
        pck.extend(data)

    return pck


def read_data_from_socket(s):
    buffer = b''

    while True:
        try:
            data = s.recv(SOCK_BUFSIZE)
            if data:
                buffer = buffer + data
                if len(buffer) >= SIZE_ACTION + SIZE_OF_DATA:
                    data_size = struct.unpack('!H', bytes(buffer[SIZE_ACTION:SIZE_ACTION + SIZE_OF_DATA]))[0]
                    while data_size + SIZE_ACTION + SIZE_OF_DATA > len(buffer):
                        data = s.recv(SOCK_BUFSIZE)
                        if data:
                            buffer = buffer + data
                        else:
                            break
                    return buffer
            else:
                break
        except socket.timeout as e:
            print('Socket timeout', e)
            break
        except BlockingIOError as e:
            print(e)
            break

    return buffer


def get_serial_frame_size(pck):
    return struct.unpack('!H', pck)[0]


def get_serial_data(pck, fmt):
    return struct.unpack(fmt, pck)


def fletcher16_checksum(bytestring):
    modulus = 255
    bytes_read = 1
    c0 = 0
    c1 = 0

    if type(bytestring) != bytes:
        bytestring = str.encode(bytestring)
    bytestring = bytearray(bytestring)

    iterations = ((len(bytestring) - 1) // bytes_read) + 1

    for i in range(0, iterations):
        start = bytes_read * i
        end = bytes_read * (i + 1)

        bytepart = int.from_bytes(bytestring[start:end], byteorder="little")
        c0 = (c0 + bytepart) % modulus
        c1 = (c1 + c0) % modulus

    return c1, c0


def get_cur_time():
    now = datetime.utcnow()
    # Return string representation DAY/MONTH/YEAR HOURS:MINUTES:SECONDS.MICROSECONDS
    return now.strftime('%d/%m/%Y %H:%M:%S.%f')


def exec_command(port, command, image_path):
    command = command.replace('PORT', port)
    if image_path:
        command = command.replace('IMAGE', image_path)
    command = command.split(' ')

    print('\t', command)
    res = subprocess.run(command)
    print('\tEXEC_END', res.returncode)
    if res.returncode != 0:
        print('\tEXEC_ERROR', res)
    return res.returncode


def get_flash_image_path(ftp_path, platform, nodetype_id, image_name):
    if platform == 'ARDUINO':
        if nodetype_id == 'UNO':
            return ftp_path + '/images/' + image_name.split('.')[0] + '/' + image_name

    return ftp_path + '/images/' + image_name


def get_erase_image_path(ftp_path, platform, nodetype_id):
    if platform == 'ARDUINO':
        if nodetype_id == 'UNO':
            return ftp_path + '/images/erase/arduino_uno/arduino_uno.ino'

    return None


def read_config(config_file, name):
    info = {}
    config = configparser.ConfigParser()

    if not os.path.isfile(config_file):
        sys.exit('Config file not exists\n\tFile path given: ' + config_file)
    else:
        config.read(config_file)

    try:
        for key in config[name]:
            info[key] = config[name][key]
    except KeyError as e:
        sys.exit('Error in config file\n\tKey Error: ' + str(e))

    return info


def to_bytes(data):
    if isinstance(data, str):
        res = data.encode()     # uses 'utf-8' for encoding
    elif isinstance(data, int):
        res = data.to_bytes(2, byteorder='big')
    else:
        print('to_bytes -> data %s' % data,  'is type of %s' % type(data))
        res = data

    return res
