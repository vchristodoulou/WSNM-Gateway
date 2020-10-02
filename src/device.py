class Device:
    """Device class"""

    def __init__(self, platform, nodetype_id, _id, location, properties, port, image_path):
        self.platform = platform
        self.nodetype_id = nodetype_id
        self.id = _id
        self.location = location
        self.properties = properties
        self.port = port
        self.image_path = image_path

    def print_added_device(self):
        print('++++++++++ DEVICE ADDED ++++++++++'
              '\n\tID\t\t%s\n\tPATH\t\t%s\n\tPLATFORM\t%s\n\tNODETYPE_ID\t%s\n\tPORT\t\t%s'
              % (self.id, self.properties['DEVPATH'], self.platform, self.nodetype_id, self.port))
        print('+' * 34, '\n')

    def print_removed_device(self):
        print('---------- DEVICE REMOVED ----------'
              '\n\tID\t\t%s\n\tPATH\t\t%s\n\tPLATFORM\t%s\n\tNODETYPE_ID\t%s\n\tPORT\t\t%s'
              % (self.id, self.properties['DEVPATH'], self.platform, self.nodetype_id, self.port))
        print('-' * 36, '\n')
