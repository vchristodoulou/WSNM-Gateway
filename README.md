# WSNM-Gateway

## Installation
1) Install pip (pip3)
    - `sudo apt install python3-pip`
2) Install pipenv
    - `sudo -H pip3 install -U pipenv`
    - Install dependencies
        - `pipenv install` (from Pipfile)
3) Install FTP
    - `sudo apt install pure-ftpd`
    - `sudo groupadd ftpgroup`
    - `sudo useradd ftpuser -g ftpgroup -s /sbin/nologin -d /dev/null`
    - `sudo mkdir /home/(user)/FTP`
    - `sudo chown -R ftpuser:ftpgroup /home/(user)/FTP`
    - `sudo pure-pw useradd upload -u ftpuser -g ftpgroup -d /home/(user)/FTP -m`
    - `sudo pure-pw mkdb`
    - `sudo ln -s /etc/pure-ftpd/conf/PureDB /etc/pure-ftpd/auth/60puredb`
    - `sudo service pure-ftpd restart`
4) Install packages
    - Monitor USB devices/actions
        - `sudo apt install python3-pyudev`

    - Arduino support
        - `sudo apt install default-jre`
        - `sudo apt install snapd`
        - `sudo snap install arduino`
        - `sudo usermod -a -G dialout (user)`

    - TelosB support
        - `sudo install python-pip`
        - `sudo python2.7 -m pip install 'pyserial>=2.0,<=2.999'`
        - `git clone https://github.com/cetic/python-msp430-tools.git`
        - `cd python-msp430-tools`
        - `sudo make install`

## Configuration
- `gateway.cfg`
