import threading
import socket
import json

import utils


class ServerRequests(threading.Thread):
    """ Server Requests handler class """

    def __init__(self, sock_tcp, usb_handler, config, stop_thread_event):
        threading.Thread.__init__(self)
        self.sock_tcp = sock_tcp
        self.usb_handler = usb_handler
        self._stop_thread_event = stop_thread_event

        server_info = utils.read_config(config, 'SERVER')
        self.server_addr = (server_info['ip'], int(server_info['port']))

    def run(self):
        req = dict()
        req[utils.NODES_FLASH] = self.nodes_flash_req
        req[utils.NODES_ERASE] = self.nodes_erase_req
        req[utils.NODES_RESET] = self.nodes_reset_req

        while not self.stopped_thread():
            try:
                (sock_server, address) = self.sock_tcp.accept()
                sock_server.settimeout(None)
            except socket.timeout:
                # Timeout to check for stopped_thread
                continue
            else:
                data = utils.read_data_from_socket(sock_server)
                action, data = utils.segment_packet(data)
                print(action, '===', data)
                req[action](data=data, sock_server=sock_server)
                sock_server.close()

        print('Exiting from server_requests. . .')

    def nodes_flash_req(self, data, sock_server, **kwargs):
        nodes_status = self.usb_handler.nodes_flash(data['node_ids'], data['image_name'])
        pck = utils.create_packet(utils.GATEWAY_NODES_FLASH, data=json.dumps(nodes_status).encode())
        sock_server.sendall(pck)

    def nodes_erase_req(self, data, sock_server, **kwargs):
        nodes_status = self.usb_handler.nodes_erase(data['node_ids'])
        pck = utils.create_packet(utils.GATEWAY_NODES_ERASE, data=json.dumps(nodes_status).encode())
        sock_server.sendall(pck)

    def nodes_reset_req(self, data, sock_server, **kwargs):
        nodes_status = self.usb_handler.nodes_reset(data['node_ids'])
        pck = utils.create_packet(utils.GATEWAY_NODES_RESET, data=json.dumps(nodes_status).encode())
        sock_server.sendall(pck)

    def stopped_thread(self):
        return self._stop_thread_event.is_set()
