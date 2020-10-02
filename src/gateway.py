import os
import socket
import sys
import time
import threading
import queue
import json

import usb_handler
import server_requests
import utils


class Gateway:
    """Gateway class"""

    def __init__(self, config):
        self.config_gateway = utils.read_config(config, 'GATEWAY')
        config_server = utils.read_config(config, 'SERVER')

        self.sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock_tcp.bind(('0.0.0.0', 0))
        self.sock_tcp.listen(5)
        self.sock_tcp.settimeout(1)
        self.server_addr = (config_server['ip'], int(config_server['port']))

        self.serial_q = queue.Queue()
        self._stop_thread_event = threading.Event()

        self.usb_handler = usb_handler.USBHandler(config, self.serial_q, self._stop_thread_event)
        self.usb_handler.start()

        self.server_requests = server_requests.ServerRequests(self.sock_tcp, self.usb_handler, config,
                                                              self._stop_thread_event)
        self.server_requests.start()

    def send_alive_and_debug_forever(self):
        alive_interval = int(self.config_gateway['alive_interval'])
        next_alive_timeout = time.time() + alive_interval
        try:
            while not self.stopped_thread():
                alive_timeout = next_alive_timeout - time.time()
                try:
                    data = self.serial_q.get(timeout=alive_timeout)
                    self.send_debug_data(data)
                    self.serial_q.task_done()
                except queue.Empty:
                    self.send_alive_msg()
                    next_alive_timeout = time.time() + alive_interval
        except KeyboardInterrupt:
            self.stop_thread()
            print('Waiting for usb_handler thread...')
            self.usb_handler.join()
            print('Waiting for server_requests thread...')
            self.server_requests.join()
            self.sock_tcp.close()
            sys.exit('Exiting. . .')

    def send_alive_msg(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            seed = self.usb_handler.get_seed()
            pck = utils.create_packet(utils.ACTION_ISALIVE, _id=self.config_gateway['id'],
                                      addr=(self.config_gateway['ip'], self.sock_tcp.getsockname()[1]),
                                      update_seed_number=seed)
            s.sendto(pck, self.server_addr)

    def send_debug_data(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(self.server_addr)
            pck = utils.create_packet(utils.DEBUG_GATEWAY, data=json.dumps(data).encode())
            s.sendall(pck)

    def stop_thread(self):
        self._stop_thread_event.set()

    def stopped_thread(self):
        return self._stop_thread_event.is_set()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--config', '-c', default=os.path.dirname(os.path.abspath(__file__)) + '/' + 'gateway.cfg',
                        help='Specify alternative config file')

    args = parser.parse_args()

    gateway = Gateway(config=args.config)
    gateway.send_alive_and_debug_forever()
