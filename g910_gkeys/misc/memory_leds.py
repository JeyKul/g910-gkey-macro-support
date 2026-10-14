import traceback

import usb
from g910_gkeys.lib.usb_device import USBDevice
from g910_gkeys.misc.logger import Logger


def change_profile(device: USBDevice, profile: str):
    log = Logger().logger(__name__)
    led_commands = device.keyboard.events.memoryKeysLEDs
    command = led_commands.get(profile)
    if command is None:
        log.warning("No memory LED command for profile %s", profile)
        return False

    commands = list(command) if isinstance(command, (list, tuple)) else [command]
    record_commands = led_commands.get("MEMORY_RECORD")
    # The G910 record LED has its own off/on packets, separate from M1-M3.
    if profile in ("MEMORY_1", "MEMORY_2", "MEMORY_3"):
        if isinstance(record_commands, (list, tuple)) and record_commands:
            commands.insert(0, record_commands[0])

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
