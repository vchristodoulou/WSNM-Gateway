import threading
import select
import time

import serial

import utils


class SerialHandler(threading.Thread):
    def __init__(self, serial_q, config, stop_thread_event):
        threading.Thread.__init__(self)
        self.serial_q = serial_q
        config_server = utils.read_config(config, 'SERVER')
        self.server_addr = (config_server['ip'], int(config_server['port']))
        self._stop_thread_event = stop_thread_event

        self.serials = []
        self.serials_locks = {}
        self.lock_serials = threading.Lock()
        self.serial_ports_buffer = {}

    def run(self):
        timeout = 1
        while not self.stopped_thread():
            with self.lock_serials:
                serial_filenos = []
                for _serial in self.serials:
                    try:
                        serial_filenos.append(_serial.fileno())
                    except serial.SerialException as e:
                        print('exception in append fileno')

            if serial_filenos:
                readable, _, exceptional = select.select(serial_filenos, [], serial_filenos, timeout)
                for serial_fileno in readable:
                    with self.lock_serials:
                        try:
                            _serial = next(_serial for _serial in self.serials if _serial.fileno() == serial_fileno)
                        except StopIteration as e:
                            print('EXC StopIteration =', e)
                            continue
                    try:
                        if _serial.in_waiting > 0:
                            locked = self.serials_locks[_serial.port].acquire(timeout=0.1)
                            if locked:
                                serial_data = _serial.read(1024)
                                self.serial_ports_buffer[_serial.port] += serial_data
                                pck = self.serial_ports_buffer[_serial.port]
                                self.serials_locks[_serial.port].release()
                            else:
                                break

                            start_pck_pos = pck.find(utils.DELIMITER)
                            if start_pck_pos > -1:
                                if len(pck) > (start_pck_pos + 2):
                                    frame_size = utils.get_serial_frame_size(pck[start_pck_pos+1:start_pck_pos+3])
                                    start_frame_pos = start_pck_pos + 3
                                    if len(pck) >= (start_frame_pos + frame_size):
                                        fmt = '!B' + str(frame_size - 3) + 's' + '2s'
                                        (_node_id, _data, _cs) = utils.get_serial_data(
                                            pck[start_frame_pos:start_frame_pos + frame_size],
                                            fmt)
                                        _node_id = str(_node_id)
                                        cs = utils.fletcher16_checksum(
                                            pck[start_frame_pos:start_frame_pos + frame_size - 2])
                                        if (cs[0] == _cs[0]) and (cs[1] == _cs[1]):
                                            timestamp = utils.get_cur_time()
                                            data = [timestamp, _node_id, _data.decode()]
                                            self.serial_q.put(data)
                                            self.serial_ports_buffer[_serial.port] = b''
                                        else:
                                            print('CHECKSUM BAD')
                                        self.serial_ports_buffer[_serial.port] = \
                                            self.serial_ports_buffer[_serial.port][:start_pck_pos] + \
                                            self.serial_ports_buffer[_serial.port][start_pck_pos + frame_size + 3:]
                    except serial.SerialException as e:
                        pass
                        # print('EXC SerialException =', e)
                    except OSError as e:
                        pass
                        # print('EXC OSError =', e)
                    except TypeError as e:
                        pass
                        # print('EXC TypeError =', e)
                    finally:
                        # _serial.close()
                        break
            else:
                time.sleep(timeout)
        print('Exiting from serial_handler. . .')

    def node_flash(self, port, command, image_path):
        with self.serials_locks[port]:
            res = utils.exec_command(port, command, image_path)
            if res == 0:
                ser = serial.Serial(port=port, baudrate=115200, timeout=0)
                self.serials.append(ser)
        return res

    def node_erase(self, port, command, image_path):
        if port in self.serials_locks:
            with self.serials_locks[port]:
                res = utils.exec_command(port, command, image_path)
                if res == 0:
                    with self.lock_serials:
                        self.serials = [_serial for _serial in self.serials if _serial.port != port]
        else:   # New serial connected. Erase memory!
            res = utils.exec_command(port, command, image_path)

        return res

    def node_reset(self, port, command, image_path):
        with self.serials_locks[port]:
            with self.lock_serials:
                self.serials = [_serial for _serial in self.serials if _serial.port != port]
            res = utils.exec_command(port, command, image_path)
            if res == 0:
                ser = serial.Serial(port=port, baudrate=115200, timeout=0)
                self.serials.append(ser)
        return res

    def add_serial_port(self, port):
        # ser = serial.Serial(port=port, baudrate=115200, timeout=0)
        with self.lock_serials:
            # self.serials.append(ser)
            self.serials_locks[port] = threading.Lock()
            self.serial_ports_buffer[port] = b''

    def delete_serial_port(self, port):
        with self.lock_serials:
            self.serials = [_serial for _serial in self.serials if _serial.port != port]
            del self.serials_locks[port]
            del self.serial_ports_buffer[port]

    def stopped_thread(self):
        return self._stop_thread_event.is_set()
