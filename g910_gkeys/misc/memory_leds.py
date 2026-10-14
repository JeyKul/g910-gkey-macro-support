import traceback

import usb
from g910_gkeys.lib.usb_device import USBDevice
from g910_gkeys.misc.logger import Logger


def change_profile(device: USBDevice, profile: str):
    log = Logger().logger(__name__)
    command = device.keyboard.events.memoryKeysLEDs.get(profile)
    if command is None:
        log.warning("No memory LED command for profile %s", profile)
        return False

    commands = command if isinstance(command, (list, tuple)) else [command]
    matched = True
    try:
        for packet in commands:
            device.dev.ctrl_transfer(
                0x21, 0x09, 0x0211, 1, packet, device.usb_timeout
            )
            try:
                response = device.dev.read(
                    device.endpoint, device.endpoint.wMaxPacketSize, device.usb_timeout
                )
            except usb.core.USBError as e:
                if e.errno == 110:
                    matched = False
                    continue
                raise
            matched = (bytes(response) == packet) and matched
        return matched
    except usb.core.USBError as e:
        log.exception("USB error updating LEDs for profile %s", profile)
        traceback.print_exc()
        return False
    except Exception:
        log.exception("Unexpected error updating LEDs for profile %s", profile)
        traceback.print_exc()
        return False
