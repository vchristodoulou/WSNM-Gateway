import xml.etree.ElementTree as ET
from xml.dom import minidom
import configparser

import utils


class XmlBuilder:
    """XML uilder class"""

    def __init__(self, config):
        self.config = config
        self.config_gateway = utils.read_config(self.config, 'GATEWAY')
        self.ftp_path = self.config_gateway['ftp_path']
        self.gateway_id = self.config_gateway['id']
        self.root = None
        self.nodes_el = None

    def create_xml(self):
        self.root = ET.Element('gateway')
        self.root.set('id', self.gateway_id)
        location_el = ET.SubElement(self.root, 'location')
        location = self.get_config_location()
        for key, value in location.items():
            temp = ET.SubElement(location_el, key)
            temp.text = value
        self.nodes_el = ET.SubElement(self.root, 'nodes')
        try:
            self.write()
        except (PermissionError, FileNotFoundError):
            print('Check gateway.cfg for ftp_path')
            raise

    def get_config_location(self):
        location = {}
        config = configparser.ConfigParser()
        config.read(self.config)

        for key in config['LOCATION']:
            location[key] = config['LOCATION'][key]

        return location

    def write(self):
        xml_str = minidom.parseString(ET.tostring(self.root)).toprettyxml(indent="  ")
        with open(self.ftp_path + '/' + str(self.gateway_id) + '.xml', "w") as f:
            f.write(xml_str)

    def add_node(self, nodetype_id, _id, locations):
        new_node = ET.SubElement(self.nodes_el, 'node')
        new_node.set('id', _id)

        _nodetype_id = ET.SubElement(new_node, 'nodetype_id')
        _nodetype_id.text = nodetype_id

        location = ET.SubElement(new_node, 'location')
        for key, value in locations.items():
            temp = ET.SubElement(location, key)
            temp.text = value
        try:
            self.write()
        except (PermissionError, FileNotFoundError):
            raise

    def remove_node(self, _id):
        for child in self.nodes_el:
            if _id == child.attrib['id']:
                self.nodes_el.remove(child)
                try:
                    self.write()
                except (PermissionError, FileNotFoundError):
                    raise


def get_buildings(ftp_path):
    tree = ET.parse(ftp_path + '/' + utils.LOCATIONS_FILE)
    root = tree.getroot()

    buildings = []
    for location in root:
        buildings.append(location[1].text)

    return buildings


def get_floors_and_areas(ftp_path, _building):
    tree = ET.parse(ftp_path + '/' + utils.LOCATIONS_FILE)
    root = tree.getroot()

    for location in root:
        building_name = location[1].text
        if building_name == _building:
            floors = {}
            j = 0
            for i in range(int(len(location[2]) / 2)):
                areas = []
                for area in location[2][i + j + 1]:
                    areas.append(area.text)

                floors[location[2][i+j].text] = areas
                j = j + 1

            return floors


def get_nodetype_commands(ftp_path, nodetype_id):
    tree = ET.parse(ftp_path + '/' + utils.NODETYPES_FILE)
    root = tree.getroot()

    nodetype_commands = {}
    for key in root:
        if key[0].text == nodetype_id:
            commands = key[6]
            for command in commands:
                nodetype_commands[command.tag] = command.text
            break

    return nodetype_commands


def get_platform_nodetypes(ftp_path):
    tree = ET.parse(ftp_path + '/' + utils.NODETYPES_FILE)
    root = tree.getroot()

    platform_nodetypes = {}
    for key in root:
        _id = key[0]
        platform = key[1]
        try:
            platform_nodetypes[platform.text].append(_id.text)
        except KeyError:
            platform_nodetypes[platform.text] = [_id.text]

    return platform_nodetypes
