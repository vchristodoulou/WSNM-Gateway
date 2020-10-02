import curses
import curses.ascii
import json

import xml_handler


class Prompt:
    """Prompt to pass information about connected USB devices"""

    def __init__(self, ftp_path):
        self.ftp_path = ftp_path
        self.device_ids = []

    def device_info(self, device_path, device_serial_port):
        device_info = {}
        get_info = [self.device_id, self.device_platform_and_node_type, self.device_location, self.device_position]

        res = curses.wrapper(self.draw_ignore_prompt, device_path, device_serial_port)
        if res == 'IGNORE':
            return {}, False
        elif res == 'REFRESH':
            return {}, True

        i = 0
        while 0 <= i < len(get_info):
            info, back = get_info[i]()
            if back:
                i -= 1
            else:
                device_info.update(info)
                i += 1

        return device_info, False

    def device_id(self):
        info = {}
        _id, back = curses.wrapper(self.draw_input_prompt, 'id')
        if back:
            return {}, True
        else:
            info.update(_id)

        return info, False

    def device_platform_and_node_type(self):
        info = {}
        platform_nodetypes = xml_handler.get_platform_nodetypes(self.ftp_path)

        i = 0
        while 0 <= i < 2:
            _platform, back = curses.wrapper(self.draw_select_prompt, 'platform', list(platform_nodetypes.keys()))
            if back:
                return {}, True
            else:
                info.update(_platform)
                i += 1

            _node_type, back = curses.wrapper(self.draw_select_prompt, 'node type',
                                              platform_nodetypes[info['platform']])
            if back:
                i -= 1
            else:
                info.update(_node_type)
                i += 1

        return info, False

    def device_location(self):
        info = {}

        i = 0
        while 0 <= i < 3:
            buildings = xml_handler.get_buildings(self.ftp_path)
            location, back = curses.wrapper(self.draw_select_prompt, 'building', buildings)
            if back:
                i -= 1
                continue
            else:
                info.update(location)
                i += 1

            floors = xml_handler.get_floors_and_areas(self.ftp_path, location['building'])
            location, back = curses.wrapper(self.draw_select_prompt, 'floor', floors.keys())
            if back:
                i -= 1
                continue
            else:
                info.update(location)
                i += 1

            location, back = curses.wrapper(self.draw_select_prompt, 'area', floors[location['floor']])
            if back:
                i -= 1
                continue
            else:
                info.update(location)
                i += 1

        return info, False

    def device_position(self):
        _position, back = curses.wrapper(self.draw_input_prompt, 'position')
        if back:
            return {}, True
        else:
            return _position, False

    def add_id(self, _id):
        self.device_ids.append(_id)

    def remove_id(self, _id):
        self.device_ids.remove(_id)

    def check_id(self, _id):
        return False if _id in self.device_ids else True

    @staticmethod
    def init_colors():
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_WHITE)

    def draw_select_prompt(self, stdscr, attr, options):
        info = {}
        enum_options = {}
        k = 0
        cursor_x = 0
        answer = ''
        self.init_colors()

        # Loop where k is the last character pressed
        while True:
            stdscr.clear()

            error_msg = '-'
            height, width = stdscr.getmaxyx()
            question_mark = '[?]'[:width - 1]
            title = 'Select {}:'.format(attr)[:width - 1]
            status_info = 'Ctrl+[ to go back'
            status = ' | STATUS BAR | ' + status_info[:width - 1]

            if k == curses.KEY_ENTER or k == 10:
                if len(answer) > 0 and 0 < int(answer) <= len(enum_options):
                    info[attr] = enum_options[int(answer)]
                    return info, False
                else:
                    error_msg = 'Wrong option'
            elif k == curses.KEY_RIGHT:
                cursor_x += 1
            elif k == curses.KEY_LEFT:
                cursor_x -= 1
            elif k == curses.KEY_BACKSPACE or k == 127:
                answer = answer[:-1]
                cursor_x -= 1
            elif k == 0:
                pass
            elif k == 27:
                return {}, True
            elif 48 <= k <= 57:
                answer += chr(k)
                cursor_x += 1
            else:
                error_msg = 'Option should be number'

            cursor_x = max(len(question_mark) + len(title) + 2, cursor_x)
            cursor_x = min(width - 1, cursor_x)

            # Render question
            self.create_title(stdscr, title, 0, 0)

            # Render answer
            stdscr.addstr(0, len(question_mark) + len(title) + 2, answer[:width - 1], curses.color_pair(3))

            for count, option in enumerate(options, 1):
                option = option.strip()
                enum_options[count] = option
                stdscr.addstr(count + 1, 0, '[' + str(count) + ']', curses.color_pair(1))
                stdscr.addstr(count + 1, 5, option[:width - 1], curses.color_pair(3))

            # Render status bar
            self.create_status_bar(stdscr, error_msg, status)

            # Change cursor
            stdscr.move(0, cursor_x)

            # Refresh the screen
            stdscr.refresh()

            # Wait for next input
            k = stdscr.getch()

    def draw_input_prompt(self, stdscr, attr):
        info = {}
        k = 0
        cursor_x = 0
        answer = ''
        self.init_colors()

        # Loop where k is the last character pressed
        while True:
            stdscr.clear()

            error_msg = '-'
            height, width = stdscr.getmaxyx()
            question_mark = '[?]'[:width - 1]
            title = 'Give {}:'.format(attr)[:width - 1]
            status_info = 'Ctrl+[ to go back'
            status = ' | STATUS BAR | ' + status_info[:width - 1]

            if k == curses.KEY_ENTER or k == 10:
                if len(answer) == 0:
                    error_msg = 'Give {}'.format(attr)
                elif attr == 'id':
                    if self.check_id(answer):
                        info[attr] = answer
                        return info, False
                    else:
                        error_msg = 'ID already exists!'
                else:
                    info[attr] = answer
                    return info, False
            elif k == curses.KEY_RIGHT:
                cursor_x = cursor_x + 1
            elif k == curses.KEY_LEFT:
                cursor_x = cursor_x - 1
            elif k == curses.KEY_BACKSPACE or k == 127:
                answer = answer[:-1]
                cursor_x = cursor_x - 1
            elif k == 0:
                pass
            elif k == 27:
                return {}, True
            else:
                answer += chr(k)
                cursor_x = cursor_x + 1

            cursor_x = max(len(question_mark) + len(title) + 2, cursor_x)
            cursor_x = min(width - 1, cursor_x)

            # Render question
            self.create_title(stdscr, title, 0, 0)

            # Render answer
            stdscr.addstr(0, len(question_mark) + len(title) + 2, answer[:width - 1], curses.color_pair(3))

            # Render status bar
            self.create_status_bar(stdscr, error_msg, status)

            # Change cursor
            stdscr.move(0, cursor_x)

            # Refresh the screen
            stdscr.refresh()

            # Wait for next input
            k = stdscr.getch()

    def draw_ignore_prompt(self, stdscr, device_path, device_serial_port):
        k = 0
        cursor_x = 0
        answer = ''
        self.init_colors()

        # Loop where k is the last character pressed
        while True:
            stdscr.clear()

            error_msg = '-'
            height, width = stdscr.getmaxyx()
            device_info = 'Usb device connected. [{} {}]'.format(device_path, device_serial_port)
            question_mark = '[?]'[:width - 1]
            title = 'Ignore? [y/N]:'[:width - 1]
            status_info = 'Ctrl+r to refresh port'
            status_bar = ' | STATUS BAR | ' + status_info[:width - 1]

            if k == curses.KEY_ENTER or k == 10:
                if len(answer) == 0 or answer.lower() == 'n':
                    return ''
                elif answer.lower() == 'y':
                    return 'IGNORE'
                else:
                    error_msg = 'Wrong option'
            elif k == curses.KEY_RIGHT:
                cursor_x += 1
            elif k == curses.KEY_LEFT:
                cursor_x -= 1
            elif k == curses.KEY_BACKSPACE or k == 127:
                answer = answer[:-1]
                cursor_x -= 1
            elif k == 18:   # CTRL + R
                return 'REFRESH'
            elif k == 0:
                pass
            else:
                answer += chr(k)
                cursor_x += 1

            cursor_x = max(len(question_mark) + len(title) + 2, cursor_x)
            cursor_x = min(width - 1, cursor_x)

            # Render device info
            stdscr.addstr(0, 0, device_info, curses.color_pair(2))

            # Render question
            self.create_title(stdscr, title, 0, 1)

            # Render answer
            stdscr.addstr(1, len(question_mark) + len(title) + 2, answer[:width - 1], curses.color_pair(3))

            # Render status bar
            stdscr.addstr(height - 1, 0, error_msg, curses.color_pair(5))
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(height - 1, len(error_msg), status_bar)
            stdscr.addstr(height - 1, len(error_msg) + len(status_bar),
                          " " * (width - len(error_msg) - len(status_bar) - 1))
            stdscr.attroff(curses.color_pair(4))

            # Change cursor
            stdscr.move(1, cursor_x)

            # Refresh the screen
            stdscr.refresh()

            # Wait for next input
            k = stdscr.getch()

    @staticmethod
    def create_title(stdscr, title, x, y):
        height, width = stdscr.getmaxyx()
        question_mark = '[?]'[:width - 1]

        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(y, x, question_mark, curses.color_pair(1))
        stdscr.addstr(y, len(question_mark) + 1, title, curses.color_pair(2))
        stdscr.attroff(curses.A_BOLD)

    @staticmethod
    def create_status_bar(stdscr, error_msg, status):
        height, width = stdscr.getmaxyx()

        stdscr.addstr(height - 1, 0, error_msg, curses.color_pair(5))
        stdscr.attron(curses.color_pair(4))
        stdscr.addstr(height - 1, len(error_msg), status)
        stdscr.addstr(height - 1, len(error_msg) + len(status),
                      " " * (width - (len(error_msg) + len(status) + 1)))
        stdscr.attroff(curses.color_pair(4))
