import argparse
import fcntl
import importlib.metadata
import os
import signal
import time
import traceback
import uinput
from g910_gkeys.misc.helper import Helper
from g910_gkeys.misc.layers import Config, LayerState
from g910_gkeys.lib.usb_device import USBDevice
from g910_gkeys.lib.keyboard import Keyboard
from g910_gkeys.misc import notify, memory_leds
from g910_gkeys.misc.logger import Logger

config = Config()
log = Logger().logger(__name__)
notifier = notify.Notification(config)
program_running = True
layers = LayerState()
device = None
keyboard = None


def signal_handler(sig, frame):
    global program_running
    log.debug('Got signal %s, terminating', signal.Signals(sig).name)
    program_running = False


def config_changed_handler(sig, frame):
    time.sleep(0.5)
    config.update_config()


def reload_handler(sig, frame):
    config.update_config()


def change_profile(dev, event):
    keyboard.release()
    profile = layers.select(event)
    config.profile = profile
    log.info('Change profile to %s', profile)
    memory_leds.change_profile(dev, layers.bank)
    if layers.shifted:
        memory_leds.change_profile(dev, 'MEMORY_RECORD')
    notifier.send_notification(profile)


def main():
    global device
    parser = argparse.ArgumentParser(description=importlib.metadata.metadata('g910-gkeys')['summary'])
    parser.add_argument('--create-config', action='store_true', help='Create configuration')
    parser.add_argument('-s', '--set-config', default='', dest='config_file')
    parser.add_argument('-v', '--version', action='version',
                        version=f'%(prog)s {Helper.get_version()} by {Helper.get_author()}')
    args = parser.parse_args()
    if args.config_file:
        config.config_path = args.config_file
    if args.create_config:
        device = USBDevice()
        try:
            config.create(device.keyboard)
        finally:
            device.__exit__()
    else:
        start()


def start():
    global device, keyboard, layers
    layers = LayerState()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(sig, signal_handler)
    signal.signal(signal.SIGIO, config_changed_handler)
    signal.signal(signal.SIGUSR1, reload_handler)
    fd = None
    try:
        device = USBDevice()
        config.check_paths(config, device)
        fd = os.open(config.config_dir, os.O_RDONLY)
        fcntl.fcntl(fd, fcntl.F_SETSIG, 0)
        fcntl.fcntl(fd, fcntl.F_NOTIFY, fcntl.DN_MODIFY | fcntl.DN_CREATE | fcntl.DN_MULTISHOT)
        config.read()
        device.disable_fkey_to_gkey_binding()
        keyboard = Keyboard(config)
        keyboard.set_keyboard(device.keyboard)
        change_profile(device, 'MEMORY_1')
        while program_running:
            loop()
    finally:
        try:
            if keyboard is not None:
                keyboard.release()
                keyboard.__exit__()
        finally:
            try:
                if device is not None:
                    device.__exit__()
            finally:
                if fd is not None:
                    os.close(fd)


def loop():
    try:
        control = device.read()
        if not control:
            return
        b = bytes(control)
        events = device.keyboard.events
        if b in events.memoryKeys:
            change_profile(device, events.memoryKeys[b])
        elif b in events.macroKeys:
            key = events.macroKeys[b]
            if key == 'MEMORY_RECORD':
                change_profile(device, key)
            else:
                keyboard.emit_keys(key)
        elif b in events.mediaKeys:
            keyboard.device.emit_click(getattr(uinput, events.mediaKeys[b]))
        elif b in events.releaseEvents:
            keyboard.release()
        elif b[:3] not in (b'\x11\xff\x0f', b'\x11\xff\x10', b'\x11\xff\xff'):
            log.debug('Unmapped USB report: %r', b)
    except SystemExit:
        signal.raise_signal(signal.SIGQUIT)
    except Exception:
        log.exception('Event handling failed')
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
