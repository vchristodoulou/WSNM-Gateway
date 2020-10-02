import threading
from functools import partial

import pyudev

import serial_handler
import prompt
import xml_handler
import device
import utils


class USBHandler(threading.Thread):
    """ Monitor udev for detection of usb """

    def __init__(self, config, serial_q, stop_thread_event):
        threading.Thread.__init__(self)
        config_gateway = utils.read_config(config, 'GATEWAY')
        self.ftp_path = config_gateway['ftp_path']
        self._stop_thread_event = stop_thread_event
        self.devices = {}
        self.seed = 1
        # Synchronization between USB_ACTIONS and IS_ALIVE_MSG
        self.lock_seed = threading.Lock()

        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb', device_type='usb_device')

        self.prompt = prompt.Prompt(self.ftp_path)
        self.xml_builder = xml_handler.XmlBuilder(config)
        self.create_init_xml(config_gateway['id'])

        self.serial_handler = serial_handler.SerialHandler(serial_q, config, stop_thread_event)
        self.serial_handler.start()

    def create_init_xml(self, gateway_id):
        try:
            self.xml_builder.create_xml()
        except PermissionError:
            print('Permission denied to', self.ftp_path, '\nUse sudo?')
            raise
        except FileNotFoundError:
            print('File [ %s ] not found in [ %s ]'
                  % ('gateway' + gateway_id, self.ftp_path))
            raise

    def run(self):
        while not self.stopped_thread():
            for usb_device in iter(partial(self.monitor.poll, 1), None):
                refresh = True
                device_properties = dict(usb_device.properties)
                if usb_device.get('ACTION') == 'bind':
                    device_path = usb_device.get('DEVPATH')
                    while refresh:
                        device_serial_port = self.get_device_serial_port(device_path)
                        res_prompt, refresh = self.prompt.device_info(device_path, device_serial_port)
                        if res_prompt:
                            self.add_device(res_prompt, device_properties, device_serial_port)
                elif usb_device.get('ACTION') == 'remove':
                    self.remove_device(usb_device.get('DEVPATH'))
        print('Exiting from usb_handler. . .')

    def get_device_serial_port(self, device_path):
        serial_port = None
        for tty_device in self.context.list_devices(subsystem='tty', ID_BUS='usb'):
            print(tty_device)
            if tty_device.get('DEVPATH').startswith(device_path):
                serial_port = tty_device.get('DEVNAME')
                return serial_port

        # Not found, return None
        return serial_port

    def add_device(self, prompt_info, properties, port):
        platform = prompt_info.pop('platform')
        nodetype_id = prompt_info.pop('node type')
        _id = prompt_info.pop('id')
        location = prompt_info

        # print(properties)
        image_path = None
        if port:
            image_path = utils.get_erase_image_path(self.ftp_path, platform, nodetype_id)
            commands = xml_handler.get_nodetype_commands(self.ftp_path, nodetype_id)
            res = self.serial_handler.node_erase(port, commands['erase'], image_path)
            self.serial_handler.add_serial_port(port)

        self.devices[_id] = device.Device(platform, nodetype_id, _id, location, properties, port, image_path)
        self.devices[_id].print_added_device()
        self.xml_builder.add_node(nodetype_id, _id, location)
        self.prompt.add_id(_id)
        self.update_seed()

    def remove_device(self, device_path):
        for _id in self.devices:
            if self.devices[_id].properties['DEVPATH'] == device_path:
                self.xml_builder.remove_node(_id)
                self.devices[_id].print_removed_device()
                if self.devices[_id].port:
                    self.serial_handler.delete_serial_port(self.devices[_id].port)
                del self.devices[_id]
                self.prompt.remove_id(_id)
                self.update_seed()
                return

    def nodes_flash(self, node_ids, image_name):
        result = {'nodes': []}
        for node_id in node_ids:
            platform = self.devices[node_id].platform
            port = self.devices[node_id].port
            nodetype_id = self.devices[node_id].nodetype_id

            image_path = utils.get_flash_image_path(self.ftp_path, platform, nodetype_id, image_name)
            commands = xml_handler.get_nodetype_commands(self.ftp_path, nodetype_id)
            res = self.serial_handler.node_flash(port, commands['flash'], image_path)
            if res == 0:
                result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.FLASHED})
                self.devices[node_id].image_path = image_path
            else:
                result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.ERROR})

        return result

    def nodes_erase(self, node_ids):
        result = {'nodes': []}
        for node_id in node_ids:
            platform = self.devices[node_id].platform
            port = self.devices[node_id].port
            nodetype_id = self.devices[node_id].nodetype_id

            image_path = utils.get_erase_image_path(self.ftp_path, platform, nodetype_id)
            commands = xml_handler.get_nodetype_commands(self.ftp_path, nodetype_id)
            res = self.serial_handler.node_erase(port, commands['erase'], image_path)
            if res == 0:
                result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.ERASED})
                self.devices[node_id].image_path = image_path
            else:
                result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.ERROR})

        return result

    def nodes_reset(self, node_ids):
        result = {'nodes': []}
        for node_id in node_ids:
            port = self.devices[node_id].port
            image_path = self.devices[node_id].image_path
            nodetype_id = self.devices[node_id].nodetype_id
            platform = self.devices[node_id].platform

            erase_image_path = utils.get_erase_image_path(self.ftp_path, platform, nodetype_id)

            commands = xml_handler.get_nodetype_commands(self.ftp_path, nodetype_id)
            res = self.serial_handler.node_reset(port, commands['reset'], image_path)
            if res == 0:
                if image_path != erase_image_path:
                    result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.FLASHED})
                else:
                    result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.ERASED})
            else:
                result['nodes'].append({utils.NODE_ID: node_id, 'status': utils.ERROR})

        return result

    def get_seed(self):
        with self.lock_seed:
            return self.seed

    def update_seed(self):
        with self.lock_seed:
            self.seed += 1

    def stopped_thread(self):
        return self._stop_thread_event.is_set()
