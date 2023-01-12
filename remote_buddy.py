#!/usr/bin/python3
"""

This is a service for Volumio, that supports
bluetooth and USB dongle based remote controls,
airmouses, volume knobs, multimedia keyboards e.t.c.

Autor: Vitaly Margolin (vitaly_mar@yahoo.com)


"""

import asyncio, evdev, evdev.ecodes as ecodes
from evdev import InputDevice
from evdev.eventio_async import ReadIterator
from pyudev import Context, Monitor, MonitorObserver
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer as FileObserver
import janus
import requests
import json
from pathlib import Path

devs = []
tasks = {}
favorites = {}
queue: janus.Queue[int] or None = None
queue_f: janus.Queue[int] or None = None

URL_BASE = 'http://localhost:3000/api/v1/commands/'
FAVORITES_FILE = '/home/volumio/favorites.json'
URL_FAVORITE = 'http://localhost:3000/api/v1/replaceAndPlay'

commands = {
    'PLAYPAUSE': {
                     'cmd': 'toggle'
                 },
    'VOLUMEDOWN': {
                      'cmd': 'volume',
                      'volume': 'minus'
                  },
    'VOLUMEUP': {
                    'cmd': 'volume',
                    'volume': 'plus'
                },
    'PREVIOUSSONG': {
                        'cmd': 'prev'
                    },
    'NEXTSONG': {
                    'cmd': 'next'
                },
    'MUTE': {
                'cmd': 'volume',
                'volume': 'toggle'
          }
}

class SafeReadIterator():

    def __init__(self, read_it):
        self.read_it = read_it

    def __iter__(self):
        return self

    def __next__(self):
        return self.read_it.__next__()

    def __aiter__(self):
        return self

    def __anext__(self):
        future = asyncio.Future()
        try:
            future.set_result(next(self.read_it.current_batch))
        except StopIteration:
            def next_batch_ready(batch):
                try:
                    self.read_it.current_batch = batch.result()
                    future.set_result(next(self.read_it.current_batch))
                except Exception as e:
                    try:
                        future.set_exception(e)
                    except asyncio.base_futures.InvalidStateError as e:
                        pass

            self.read_it.device.async_read().add_done_callback(next_batch_ready)
        return future


def is_suitable(dev) -> bool:
    capabilities = dev.capabilities()
    if ecodes.EV_KEY in capabilities:
        supported_keys = capabilities[ecodes.EV_KEY]
        return ecodes.KEY_VOLUMEDOWN in supported_keys or ecodes.KEY_0 in supported_keys
    return False

class FavoritesFileEventHandler(PatternMatchingEventHandler):

    def on_any_event(self, event):
        queue_f.sync_q.put(event)

async def refresh_devices():
    global queue
    global devs
    if queue is None:
        queue = janus.Queue()
    asyncio.create_task(read_active_devices())
    while True:
        plug_event = await  queue.async_q.get()
        asyncio.create_task(read_active_devices())

 
def usbEventCallback(action, device):
    tokens = device.sys_path.split('/')
    dev_path = '/dev/input/' + tokens[len(tokens)-1]
    if action != 'add' and action != 'remove':
        return
    queue.sync_q.put(action + ':' + dev_path)


def startListener():

    context = Context()
    monitor = Monitor.from_netlink(context)
    monitor.filter_by(subsystem='input')

    observer = MonitorObserver(monitor, usbEventCallback, name="usbdev")
    observer.setDaemon(False)
    observer.start()

    return observer

def stopListener(observer):
    observer.stop()

async def read_active_devices():
    devs.clear()
    for task in tasks:
        try:
            tasks[task].cancel()
        except Exception as e:
            pass
    tasks.clear()
    paths =[path for path in evdev.list_devices()]
    paths = list(dict.fromkeys(paths))

    for path in paths:
        input_dev = evdev.InputDevice(path)
        if is_suitable(input_dev):
            devs.append(input_dev)
    for dev in devs:
        tasks[dev.path] = asyncio.create_task(print_events(dev))

async def refresh_favorites():
    global queue_f

    if queue_f is None:
        queue_f = janus.Queue()
    asyncio.create_task(read_favorites())
    while True:
        modified_event = await  queue_f.async_q.get()
        asyncio.create_task(read_favorites())

async def read_favorites():
    global favorites

    favorites.clear()
    try:
        favorites = json.loads(Path(FAVORITES_FILE).read_text())
    except Exception as e:
        pass

async def print_events(device):
    try:
        async for event in SafeReadIterator(device.async_read_loop()):
            key = evdev.ecodes.KEY[event.code][4:]
            if event.type ==  evdev.ecodes.EV_KEY:
                data = evdev.categorize(event)
                if data.keystate == 0:
                    continue
                if len(key) == 0:
                    key = 'MUTE'
                #print(f'EVENT:   {device.path}      Key:  {key} ')
                if key in commands:
                    url_params =  commands[key]
                    try:
                        requests.get(url=URL_BASE, params=url_params, timeout=0.000000001)
                    except requests.exceptions.ReadTimeout:
                        pass
                elif key in favorites:
                     try:
                         requests.post(url=URL_FAVORITE,  json =favorites[key], timeout=0.000000001)
                     except requests.exceptions.ReadTimeout:
                        pass

    except BaseException:
        pass
    return 0

asyncio.ensure_future(refresh_devices())
asyncio.ensure_future(refresh_favorites())

favorites_event_handler = FavoritesFileEventHandler(patterns=['favorites.json'],
                                                    ignore_patterns = [],
                                                    ignore_directories = True)
favorites_file_observer = FileObserver()
favorites_file_observer.schedule(favorites_event_handler, '/home/volumio', recursive = True)
favorites_file_observer.start()

observer = startListener()

loop = asyncio.get_event_loop()
loop.run_forever()


