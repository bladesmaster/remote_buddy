# remote_buddy
Volumio service for bluetooth and USB remotes support

This service is intended for Volumio boxes and provides universal support
 of various bluetooth based remotess and USB based devices
(remotes with USB dongle, volume knobs, multimedia keyboards e.t.c)

## Main features

1. It is universal, must work for all such devices without any code changes
   IR based remotes can work via Flirc USB dongle (https://flirc.tv)  

2. Multiple connected HID devices are supported, each of them will work

3. Hot plug/unplug of USB devices is supported, after hot plug new device
   will work immediately without restart

4. User can prepare file of favorites, they are assigned to  keys
   from 0 to 9 - they are present on lot of remote controls. To each such
   key a playlist element can be assigned. The example of this file is
   provided - it contains 3 radio stations. When appropriate key is pressed,
   playing will start immediately. When this file is edited, it will be
   reloaded automatically without need to restart

## Installation

This service requires some additional packages to be installed
Enter your volumio box with ssh and do following:

sudo apt install python3-pip
sudo apt install python3-evdev
sudo apt install python3-pyudev
pip3 install janus
pip3 install watchdog

Copy file remote_buddy.py  to /home/volumio and give execution permission:
 chmod +x remote_buddy.py

Prepare your file /home/volumio/favorites.json (the example is given)
To do so, enter your volumio station with ssh and issue requests:

curl http://localhost:3000/api/v1/search?query=KEYWORD_TO_SEARCH
This will bring the description of your favorite song/radio station e.t.c.

After you'll prepare your favorites.json, please verify that it is proper
 json file To do so, use this service: 
https://jsonformatter.curiousconcept.com/

Under sudo create file /lib/systemd/system/remote_buddy.service
sudo systemctl enable remote_buddy
sudo systemctl start remote_buddy



