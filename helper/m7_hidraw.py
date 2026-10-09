"""Keychron M7 8K HID queries and guarded shared-DPI writes."""

import argparse
import json
import os
import select
import sys
import time
from dataclasses import dataclass
from pathlib import Path


VENDOR_ID = 0x3434
RECEIVER_PRODUCT_ID = 0xD028
MOUSE_PRODUCT_ID = 0xD056
CONFIG_USAGE_PAGE = 0xFFC1
CONFIG_USAGE = 0x01
STATUS_COMMAND = 0x06
BUTTON_COMMAND = 0x62
WRITE_SHARED_DPI_COMMAND = 0x40
STATUS_LENGTH = 63
SETTINGS_LENGTH = 20
POLLING_RATES = (125, 500, 1000, 2000, 4000, 8000)
CONNECTION_NAMES = ("USB", "2.4 GHz", "Bluetooth")
DPI_OFFSETS = (5, 7, 9, 11, 13)
BUTTONS = (
    (0, "Left"),
    (1, "Middle"),
    (2, "Right"),
    (3, "Back"),
    (4, "Forward"),
    (7, "Page Down"),
    (13, "Scroll Down"),
    (14, "Scroll Up"),
)
REPORT_TIMEOUT_SECONDS = 2.0
TOTAL_TIMEOUT_SECONDS = 12.0


@dataclass(frozen=True)
class HidReportDescriptor:
    usage_page: int | None
    usage: int | None
    input_reports: dict[int, int]
    output_reports: dict[int, int]


@dataclass(frozen=True)
class HidrawDevice:
    path: Path
    product_name: str
    descriptor: HidReportDescriptor


def decode_status(payload: bytes) -> dict:
    """Decode one 63-byte B4 payload for status command 0x06."""
    if len(payload) != STATUS_LENGTH:
        raise ValueError(f"status reply must contain exactly {STATUS_LENGTH} bytes")
    if payload[0] != STATUS_COMMAND:
        raise ValueError("unexpected status command marker")

    stage_count = payload[16]
    if not 1 <= stage_count <= len(DPI_OFFSETS):
        raise ValueError(f"unsupported DPI stage count: {stage_count}")

    dpi_presets = [payload[offset] | (payload[offset + 1] << 8) for offset in DPI_OFFSETS]
    connections = []
    for index, name in enumerate(CONNECTION_NAMES):
        value = payload[2 + index]
        active_stage = (value & 0x0F) + 1
        if active_stage > stage_count:
            raise ValueError(f"active DPI stage {active_stage} exceeds reported stage count {stage_count}")
        rate_index = value >> 4
        polling_hz = POLLING_RATES[rate_index] if rate_index < len(POLLING_RATES) else f"code {rate_index}"
        connections.append({
            "name": name,
            "activeDpiStage": active_stage,
            "pollingHz": polling_hz,
        })

    profile = payload[1] + 1
    profile_count = payload[50]
    if profile_count == 0 or profile > profile_count:
        raise ValueError(f"onboard profile {profile} exceeds reported profile count {profile_count}")

    raw_battery = payload[19]
    battery_level = raw_battery & 0x7F
    battery_valid = battery_level <= 100

    return {
        "result": "Respuesta de estado válida",
        "reportId": "0xb4",
        "responseBytes": len(payload),
        "dpiStageCount": stage_count,
        "dpiPresets": dpi_presets,
        "connections": connections,
        "onboardProfile": profile,
        "onboardProfileCount": profile_count,
        "batteryPercent": battery_level if battery_valid else None,
        "batteryCharging": bool(raw_battery & 0x80) if battery_valid else None,
        "rawHex": " ".join(f"{byte:02x}" for byte in payload),
    }


def build_shared_dpi_packet(status: bytes, stage: int | None) -> bytes:
    """Build the v4 shared-DPI packet; stage is zero-based, None restores selectors."""
    decoded = decode_status(status)
    if stage is not None and not 0 <= stage < decoded["dpiStageCount"]:
        raise ValueError("requested DPI stage is outside reported stage count")

    packet = bytearray(SETTINGS_LENGTH)
    packet[0] = WRITE_SHARED_DPI_COMMAND
    for mode in range(3):
        packet[1 + mode] = (status[2 + mode] & 0x0F) if stage is None else stage
    packet[4:14] = status[5:15]
    packet[14] = status[16]
    return bytes(packet)


def decode_dpi_ack(payload: bytes) -> str:
    """Validate the v4 shared-DPI write ACK on B6."""
    if len(payload) != SETTINGS_LENGTH:
        raise ValueError("malformed shared-DPI acknowledgement")
    if payload[0] == WRITE_SHARED_DPI_COMMAND:
        return " ".join(f"{byte:02x}" for byte in payload[:3])
    if payload[0] == 0xE4 and payload[2] == WRITE_SHARED_DPI_COMMAND:
        if payload[1] != 0:
            raise ValueError(f"receiver rejected shared-DPI write with code {payload[1]}")
        return " ".join(f"{byte:02x}" for byte in payload[:3])
    raise ValueError("unexpected shared-DPI acknowledgement")


def verify_dpi_status(baseline: bytes, actual: bytes, expected_stages: tuple[int, int, int]) -> None:
    """Require only the three active DPI selectors to differ from baseline."""
    decode_status(baseline)
    decode_status(actual)
    if len(expected_stages) != 3:
        raise ValueError("three expected connection stages are required")
    if actual[1] != baseline[1]:
        raise ValueError("onboard profile changed")
    if actual[16] != baseline[16]:
        raise ValueError("DPI stage count changed")
    if actual[50] != baseline[50]:
        raise ValueError("onboard profile count changed")
    if actual[5:15] != baseline[5:15]:
        raise ValueError("DPI presets changed")

    for mode, expected_stage in enumerate(expected_stages):
        before = baseline[2 + mode]
        after = actual[2 + mode]
        if (after >> 4) != (before >> 4):
            raise ValueError("polling rate changed")
        if (after & 0x0F) != expected_stage:
            raise ValueError(f"active DPI stage changed unexpectedly in mode {mode}")

    allowed_offsets = {2, 3, 4}
    for offset, (before, after) in enumerate(zip(baseline, actual)):
        if offset not in allowed_offsets and before != after:
            raise ValueError(f"status byte changed outside DPI selectors at offset {offset}")


def decode_protocol_version(payload: bytes) -> int:
    """Decode the 20-byte B6 reply to settings query 0x02."""
    if len(payload) != SETTINGS_LENGTH or payload[0] != 0x02:
        raise ValueError("unexpected protocol-version reply")
    return payload[1] | (payload[2] << 8)


def decode_linked_mice(payload: bytes) -> list[dict]:
    """Decode the 20-byte B6 reply to linked-device query 0x03."""
    if len(payload) != SETTINGS_LENGTH or payload[0] != 0x03:
        raise ValueError("unexpected linked-device reply")
    count = payload[1]
    capacity = (len(payload) - 2) // 5
    if count > capacity:
        raise ValueError("linked-device count exceeds reply capacity")

    mice = []
    for index in range(count):
        offset = 2 + index * 5
        mice.append({
            "vendorId": payload[offset] | (payload[offset + 1] << 8),
            "productId": payload[offset + 2] | (payload[offset + 3] << 8),
            "connected": payload[offset + 4] == 1,
        })
    return mice


def decode_button(payload: bytes, index: int, name: str) -> dict:
    """Decode one 63-byte B4 reply to button query 0x62."""
    if len(payload) != STATUS_LENGTH:
        raise ValueError(f"button reply must contain exactly {STATUS_LENGTH} bytes")
    if payload[0] != BUTTON_COMMAND or payload[1] != index:
        raise ValueError("unexpected button reply command or index")

    action_type = payload[3]
    if action_type == 0:
        action = "Default (firmware)"
    elif action_type == 4:
        action = "Macro"
    elif action_type == 9:
        action = "Disabled"
    elif action_type == 1:
        value = (payload[4] << 16) | (payload[5] << 8) | payload[6]
        action = {
            0x010000: "Left Click",
            0x020000: "Right Click",
            0x040000: "Middle Click",
            0x080000: "Back",
            0x100000: "Forward",
            0x800000: "Double Click",
            0x000200: "Scroll Up",
            0x00FE00: "Scroll Down",
            0x0000FE: "Scroll Left",
            0x000002: "Scroll Right",
        }.get(value, f"Custom mouse code {value:x}")
    elif action_type == 3:
        value = payload[4] | (payload[5] << 8)
        action = {
            0xE9: "Volume Up",
            0xEA: "Volume Down",
            0xE2: "Mute",
            0xCD: "Play/Pause",
            0xB5: "Next Track",
            0xB6: "Previous Track",
        }.get(value, f"Custom media code 0x{value:x}")
    elif action_type == 5:
        action = {1: "DPI Loop", 2: "DPI +", 3: "DPI -"}.get(payload[4], "Custom DPI action")
    else:
        action = f"Custom action type {action_type}"

    return {
        "name": name,
        "index": index,
        "action": action,
        "rawHex": " ".join(f"{byte:02x}" for byte in payload[:7]),
    }


def parse_hid_report_descriptor(descriptor: bytes) -> HidReportDescriptor:
    """Read top-level usage and input/output report sizes from HID items."""
    if not descriptor:
        raise ValueError("empty HID report descriptor")

    usage_page = None
    top_level_usage_page = None
    top_level_usage = None
    report_size = None
    report_count = None
    report_id = 0
    global_stack = []
    local_usages = []
    collection_depth = 0
    input_bits: dict[int, int] = {}
    output_bits: dict[int, int] = {}

    offset = 0
    while offset < len(descriptor):
        prefix = descriptor[offset]
        offset += 1

        if prefix == 0xFE:
            if offset + 2 > len(descriptor):
                raise ValueError("truncated long HID item")
            data_length = descriptor[offset]
            offset += 2  # length byte and long-item tag
            if offset + data_length > len(descriptor):
                raise ValueError("truncated long HID item data")
            offset += data_length
            continue

        size_code = prefix & 0x03
        data_length = 4 if size_code == 3 else size_code
        item_type = (prefix >> 2) & 0x03
        item_tag = (prefix >> 4) & 0x0F
        if offset + data_length > len(descriptor):
            raise ValueError("truncated short HID item")
        data_bytes = descriptor[offset:offset + data_length]
        offset += data_length
        value = int.from_bytes(data_bytes, "little") if data_bytes else 0

        if item_type == 1:  # Global items.
            if item_tag == 0:  # Usage Page
                usage_page = value
            elif item_tag == 7:  # Report Size
                report_size = value
            elif item_tag == 8:  # Report ID
                if value == 0 or value > 0xFF:
                    raise ValueError("invalid HID report ID")
                report_id = value
            elif item_tag == 9:  # Report Count
                report_count = value
            elif item_tag == 10:  # Push
                global_stack.append((usage_page, report_size, report_count, report_id))
            elif item_tag == 11:  # Pop
                if not global_stack:
                    raise ValueError("unmatched HID global Pop")
                usage_page, report_size, report_count, report_id = global_stack.pop()
            continue

        if item_type == 2 and item_tag == 0:  # Local Usage.
            local_usages.append(value)
            continue

        if item_type != 0:
            continue

        if item_tag == 10:  # Collection
            if collection_depth == 0 and top_level_usage is None:
                top_level_usage_page = usage_page
                top_level_usage = local_usages[0] if local_usages else None
            collection_depth += 1
        elif item_tag in (8, 9, 11):  # Input, Output, Feature
            if report_size is None or report_count is None:
                raise ValueError("HID report has no size or count")
            bits = report_size * report_count
            target = input_bits if item_tag == 8 else output_bits if item_tag == 9 else None
            if target is not None:
                target[report_id] = target.get(report_id, 0) + bits
        elif item_tag == 12:  # End Collection
            if collection_depth == 0:
                raise ValueError("unmatched HID End Collection")
            collection_depth -= 1

        local_usages.clear()

    if collection_depth != 0:
        raise ValueError("unterminated HID Collection")
    if global_stack:
        raise ValueError("unmatched HID global Push")

    return HidReportDescriptor(
        usage_page=top_level_usage_page,
        usage=top_level_usage,
        input_reports={report: (bits + 7) // 8 for report, bits in input_bits.items()},
        output_reports={report: (bits + 7) // 8 for report, bits in output_bits.items()},
    )


def find_config_device(
    sysfs_root: Path = Path("/sys/class/hidraw"),
    dev_root: Path = Path("/dev"),
    product_id: int = RECEIVER_PRODUCT_ID,
    allow_missing: bool = False,
) -> HidrawDevice | None:
    """Find one M7/receiver FFC1 interface by its USB product ID."""
    labels = {
        RECEIVER_PRODUCT_ID: ("Keychron Ultra-Link receiver", "Keychron Ultra-Link 8K"),
        MOUSE_PRODUCT_ID: ("wired Keychron M7 8K", "Keychron M7 8K"),
    }
    label, default_name = labels.get(product_id, ("Keychron HID device", "Keychron HID device"))
    candidates = []
    matching_device_seen = False

    for entry in sorted(sysfs_root.glob("hidraw*")):
        device_dir = entry / "device"
        try:
            uevent = dict(
                line.split("=", 1)
                for line in (device_dir / "uevent").read_text().splitlines()
                if "=" in line
            )
            hid_id = uevent.get("HID_ID", "").split(":")
            if len(hid_id) != 3:
                continue
            vendor_id, found_product_id = int(hid_id[1], 16), int(hid_id[2], 16)
            if (vendor_id, found_product_id) != (VENDOR_ID, product_id):
                continue
            matching_device_seen = True
            descriptor = parse_hid_report_descriptor((device_dir / "report_descriptor").read_bytes())
        except (OSError, ValueError):
            continue

        expected = (
            descriptor.usage_page == CONFIG_USAGE_PAGE
            and descriptor.usage == CONFIG_USAGE
            and descriptor.input_reports.get(0xB4) == STATUS_LENGTH
            and descriptor.input_reports.get(0xB6) == SETTINGS_LENGTH
            and descriptor.output_reports.get(0xB3) == STATUS_LENGTH
            and descriptor.output_reports.get(0xB5) == SETTINGS_LENGTH
        )
        if expected:
            node = dev_root / entry.name
            if node.exists():
                candidates.append(HidrawDevice(
                    path=node,
                    product_name=uevent.get("HID_NAME", default_name),
                    descriptor=descriptor,
                ))

    if len(candidates) > 1:
        raise RuntimeError("multiple matching Keychron config interfaces; refusing to guess")
    if candidates:
        return candidates[0]
    if matching_device_seen:
        raise RuntimeError(f"{label} found, but no matching 0xFFC1 config interface")
    if allow_missing:
        return None
    raise RuntimeError(f"{label} 3434:{product_id:04x} not found")


def _drain_pending_reports(fd: int) -> None:
    """Discard queued reports, refusing to transact if the queue stays busy."""
    for _ in range(32):
        readable, _, _ = select.select([fd], [], [], 0)
        if not readable:
            return
        os.read(fd, 65)

    readable, _, _ = select.select([fd], [], [], 0)
    if readable:
        raise RuntimeError("HID input queue did not drain; refusing to send another report")


def _exchange(
    fd: int,
    output_report_id: int,
    input_report_id: int,
    packet: bytes,
    output_payload_length: int,
    input_payload_length: int,
    matches,
    deadline: float,
) -> bytes:
    if len(packet) != output_payload_length:
        raise ValueError("outgoing HID payload length does not match descriptor")

    _drain_pending_reports(fd)
    frame = bytes([output_report_id]) + packet
    written = os.write(fd, frame)
    if written != len(frame):
        raise OSError(f"short hidraw write: {written}/{len(frame)} bytes")

    while True:
        remaining = min(REPORT_TIMEOUT_SECONDS, deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError(f"no matching HID reply on report 0x{input_report_id:02x}")
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            continue
        frame = os.read(fd, 65)
        if not frame or frame[0] != input_report_id:
            continue
        if len(frame) != input_payload_length + 1:
            raise ValueError(f"malformed HID report 0x{input_report_id:02x}: {len(frame) - 1} payload bytes")
        payload = frame[1:]
        if matches(payload):
            return payload


def _settings_query(fd: int, device: HidrawDevice, command: int, args: tuple[int, ...], deadline: float) -> bytes:
    packet = bytearray(SETTINGS_LENGTH)
    packet[0] = command
    packet[1:1 + len(args)] = bytes(args)
    return _exchange(
        fd, 0xB5, 0xB6, bytes(packet),
        device.descriptor.output_reports[0xB5],
        device.descriptor.input_reports[0xB6],
        lambda payload: payload[0] == command,
        deadline,
    )


def _command_query(fd: int, device: HidrawDevice, command: int, args: tuple[int, ...], deadline: float) -> bytes:
    packet = bytearray(STATUS_LENGTH)
    packet[0] = command
    packet[1:1 + len(args)] = bytes(args)
    expected_index = args[0] if command == BUTTON_COMMAND else None
    return _exchange(
        fd, 0xB3, 0xB4, bytes(packet),
        device.descriptor.output_reports[0xB3],
        device.descriptor.input_reports[0xB4],
        lambda payload: payload[0] == command and (expected_index is None or payload[1] == expected_index),
        deadline,
    )


def _open_verified_receiver() -> tuple[HidrawDevice, int, int]:
    device = find_config_device()
    try:
        fd = os.open(device.path, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    except PermissionError as error:
        raise PermissionError(
            f"cannot access {device.path}; check the receiver's uaccess ACL"
        ) from error

    try:
        deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        version_reply = _settings_query(fd, device, 0x02, (1,), deadline)
        protocol_version = decode_protocol_version(version_reply)
        linked_reply = _settings_query(fd, device, 0x03, (), deadline)
        linked_mice = decode_linked_mice(linked_reply)
        mouse = next((
            item for item in linked_mice
            if item["vendorId"] == VENDOR_ID
            and item["productId"] == MOUSE_PRODUCT_ID
            and item["connected"]
        ), None)
        if mouse is None:
            raise RuntimeError("connected M7 8K (3434:d056) not confirmed; no further queries sent")
        if protocol_version != 4:
            raise RuntimeError(f"unsupported receiver protocol v{protocol_version}; expected v4")
        return device, fd, protocol_version
    except Exception:
        os.close(fd)
        raise


def _open_verified_wired_mouse(device: HidrawDevice | None = None) -> tuple[HidrawDevice, int, int]:
    if device is None:
        device = find_config_device(product_id=MOUSE_PRODUCT_ID)
    if device is None:
        raise RuntimeError("wired Keychron M7 8K config interface not found")
    try:
        fd = os.open(device.path, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    except PermissionError as error:
        raise PermissionError(
            f"cannot access {device.path}; check the wired M7's uaccess ACL"
        ) from error

    try:
        deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        version_reply = _settings_query(fd, device, 0x02, (1,), deadline)
        protocol_version = decode_protocol_version(version_reply)
        if protocol_version != 4:
            raise RuntimeError(f"unsupported wired M7 protocol v{protocol_version}; expected v4")
        return device, fd, protocol_version
    except Exception:
        os.close(fd)
        raise


def _write_shared_dpi(fd: int, device: HidrawDevice, packet: bytes, deadline: float) -> str:
    reply = _exchange(
        fd, 0xB5, 0xB6, packet,
        device.descriptor.output_reports[0xB5],
        device.descriptor.input_reports[0xB6],
        lambda payload: payload[0] == WRITE_SHARED_DPI_COMMAND
        or (payload[0] == 0xE4 and payload[2] == WRITE_SHARED_DPI_COMMAND),
        deadline,
    )
    return decode_dpi_ack(reply)


def set_dpi(dpi: int) -> dict:
    """Apply one firmware-reported DPI preset across all three connection modes."""
    device, fd, protocol_version = _open_verified_receiver()
    try:
        deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        baseline = _command_query(fd, device, STATUS_COMMAND, (), deadline)
        decoded = decode_status(baseline)
        if dpi not in decoded["dpiPresets"]:
            raise RuntimeError(f"DPI {dpi} is not one of the receiver's reported presets; no write sent")

        stage = decoded["dpiPresets"].index(dpi)
        expected_stages = (stage, stage, stage)
        previous_dpi = [decoded["dpiPresets"][item["activeDpiStage"] - 1] for item in decoded["connections"]]
        if all(item["activeDpiStage"] == stage + 1 for item in decoded["connections"]):
            return {
                "ok": True,
                "result": "DPI ya estaba activo; no se escribió nada",
                "dpi": dpi,
                "previousDpi": previous_dpi,
                "activeDpi": previous_dpi,
                "pollingHz": [item["pollingHz"] for item in decoded["connections"]],
                "writeSent": False,
            }

        ack = None
        ack_error = None
        write_deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        try:
            ack = _write_shared_dpi(
                fd, device, build_shared_dpi_packet(baseline, stage=stage), write_deadline
            )
        except Exception as error:
            ack_error = str(error)

        verification_deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        observed_reply = None
        try:
            observed_reply = _command_query(fd, device, STATUS_COMMAND, (), verification_deadline)
            verify_dpi_status(baseline, observed_reply, expected_stages)
            confirmed_reply = _command_query(fd, device, STATUS_COMMAND, (), verification_deadline)
            verify_dpi_status(baseline, confirmed_reply, expected_stages)
            observed = decode_status(confirmed_reply)
        except Exception as error:
            observed = None
            if observed_reply is not None:
                try:
                    observed = decode_status(observed_reply)
                except ValueError:
                    pass
            return {
                "ok": False,
                "result": "No se pudo confirmar el DPI solicitado; estado actual incierto",
                "dpi": dpi,
                "previousDpi": previous_dpi,
                "observedStatus": observed,
                "ack": ack,
                "ackError": ack_error,
                "error": str(error),
                "instruction": "Consulta el estado antes de volver a aplicar el DPI; no se reintentó la escritura.",
            }

        return {
            "ok": True,
            "result": "DPI aplicado y confirmado por dos lecturas" if ack_error is None
                else "DPI confirmado por dos lecturas; ACK no recibido",
            "dpi": dpi,
            "previousDpi": previous_dpi,
            "activeDpi": [observed["dpiPresets"][item["activeDpiStage"] - 1] for item in observed["connections"]],
            "pollingHz": [item["pollingHz"] for item in observed["connections"]],
            "dpiPresets": observed["dpiPresets"],
            "ack": ack,
            "ackError": ack_error,
            "writeSent": True,
            "operation": "Actualiza solo etapa DPI activa compartida; sin cambiar presets, polling, perfil, botones ni firmware.",
        }
    finally:
        os.close(fd)


def read_mouse_state() -> dict:
    """Read M7 status over direct USB or the linked 2.4 GHz receiver."""
    wired_device = find_config_device(product_id=MOUSE_PRODUCT_ID, allow_missing=True)
    if wired_device is not None:
        device, fd, protocol_version = _open_verified_wired_mouse(wired_device)
        transport = "USB (cable)"
        receiver = None
        device_product_id = MOUSE_PRODUCT_ID
        operation = "Solo consultas 0x02, 0x06 y 0x62; sin comandos de escritura de configuración."
    else:
        device, fd, protocol_version = _open_verified_receiver()
        transport = "2.4 GHz"
        receiver = {
            "productName": device.product_name,
            "vendorId": "0x3434",
            "productId": "0xd028",
            "hidraw": str(device.path),
            "configCollection": "0xffc1 / reportes 0xb3↔0xb4, 0xb5↔0xb6",
        }
        device_product_id = RECEIVER_PRODUCT_ID
        operation = "Solo consultas 0x02, 0x03, 0x06 y 0x62; sin comandos de escritura de configuración."

    try:
        deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        status_reply = _command_query(fd, device, STATUS_COMMAND, (), deadline)
        status = decode_status(status_reply)
        buttons = []
        for index, name in BUTTONS:
            reply = _command_query(fd, device, BUTTON_COMMAND, (index,), deadline)
            buttons.append(decode_button(reply, index, name))

        return {
            "result": "Estado y asignaciones leídos; sin escrituras de configuración",
            "transport": transport,
            "device": {
                "productName": device.product_name,
                "vendorId": "0x3434",
                "productId": f"0x{device_product_id:04x}",
                "hidraw": str(device.path),
            },
            "receiver": receiver,
            "mouse": "Keychron M7 8K (3434:d056)",
            "protocolVersion": protocol_version,
            "status": status,
            "buttons": buttons,
            "operation": operation,
        }
    finally:
        os.close(fd)


def run_dpi_smoke_test() -> dict:
    """Temporarily select 800 DPI on all modes, then restore and verify baseline."""
    device, fd, protocol_version = _open_verified_receiver()
    baseline = None
    attempted_write = False
    temporary_ack = None
    temporary_status = None
    test_error = None
    restore_ack = None
    restore_ack_error = None
    restored_status = None
    restore_error = None

    try:
        deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        baseline = _command_query(fd, device, STATUS_COMMAND, (), deadline)
        decoded = decode_status(baseline)
        if decoded["dpiPresets"] != [400, 800, 1600, 3200, 5000]:
            raise RuntimeError("DPI presets differ from the authorized test baseline; no write sent")
        if [item["activeDpiStage"] for item in decoded["connections"]] != [3, 3, 3]:
            raise RuntimeError("all three active stages must be 1600 DPI; no write sent")
        if [item["pollingHz"] for item in decoded["connections"]] != [1000, 1000, 125]:
            raise RuntimeError("polling differs from the authorized baseline; no write sent")
        if decoded["onboardProfile"] != 1 or decoded["onboardProfileCount"] != 5:
            raise RuntimeError("onboard profile differs from the authorized baseline; no write sent")

        test_deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
        try:
            attempted_write = True
            temporary_ack = _write_shared_dpi(
                fd, device, build_shared_dpi_packet(baseline, stage=1), test_deadline
            )
            temporary_reply = _command_query(fd, device, STATUS_COMMAND, (), test_deadline)
            temporary_status = decode_status(temporary_reply)
            verify_dpi_status(baseline, temporary_reply, (1, 1, 1))
        except Exception as error:
            test_error = str(error)
        finally:
            if attempted_write:
                restore_deadline = time.monotonic() + 6.0
                try:
                    restore_ack = _write_shared_dpi(
                        fd, device, build_shared_dpi_packet(baseline, stage=None), restore_deadline
                    )
                except Exception as error:
                    restore_ack_error = str(error)
                try:
                    restored_reply = _command_query(fd, device, STATUS_COMMAND, (), restore_deadline)
                    verify_dpi_status(baseline, restored_reply, (2, 2, 2))
                    confirmed_reply = _command_query(fd, device, STATUS_COMMAND, (), restore_deadline)
                    verify_dpi_status(baseline, confirmed_reply, (2, 2, 2))
                    restored_status = decode_status(confirmed_reply)
                except Exception as error:
                    restore_error = str(error)

        if restore_error:
            return {
                "ok": False,
                "result": "Restauración no verificada; estado actual incierto",
                "mouse": "Keychron M7 8K (3434:d056)",
                "protocolVersion": protocol_version,
                "testError": test_error,
                "restoreAck": restore_ack,
                "restoreAckError": restore_ack_error,
                "restoreError": restore_error,
                "instruction": "Mantén ratón y receptor conectados; consulta el estado antes de volver a usarlo.",
            }

        if restore_ack_error:
            result = "Lectura confirma estado original; ACK de restauración no confirmado"
            ok = False
        elif test_error:
            result = "Prueba fallida; estado original restaurado y verificado"
            ok = False
        else:
            result = "Prueba correcta; DPI original restaurado y verificado"
            ok = True

        return {
            "ok": ok,
            "result": result,
            "receiver": str(device.path),
            "mouse": "Keychron M7 8K (3434:d056)",
            "protocolVersion": protocol_version,
            "dpiLayout": "shared",
            "writeRoute": "0x40 por B5; ACK B6",
            "profile": decoded["onboardProfile"],
            "temporaryAck": temporary_ack,
            "temporaryActiveDpi": 800 if temporary_status else None,
            "restoredActiveDpi": 1600 if restored_status else None,
            "pollingHzRestored": [item["pollingHz"] for item in restored_status["connections"]],
            "dpiPresetsUnchanged": restored_status["dpiPresets"],
            "restoreAck": restore_ack,
            "testError": test_error,
            "restoreAckError": restore_ack_error,
            "operation": "Solo selección temporal de etapa activa; sin cambios a presets, polling, perfil, botones ni firmware.",
        }
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keychron M7 8K hidraw probe")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="read identity, status, and button mappings")
    dpi_parser = subparsers.add_parser(
        "dpi-smoke-test", help="temporary 1600→800→restore test across all connection modes"
    )
    dpi_parser.add_argument("--confirm", action="store_true", help="confirm the temporary DPI change")
    set_parser = subparsers.add_parser("set-dpi", help="apply one reported DPI preset across all connection modes")
    set_parser.add_argument("--dpi", type=int, required=True, help="DPI value from the receiver's reported presets")
    set_parser.add_argument("--confirm", action="store_true", help="confirm the persistent DPI change")
    args = parser.parse_args(argv)

    if args.command == "dpi-smoke-test" and not args.confirm:
        print(json.dumps({"error": "temporary DPI write requires --confirm; no HID report sent"}))
        return 2
    if args.command == "set-dpi" and not args.confirm:
        print(json.dumps({"error": "DPI write requires --confirm; no HID report sent"}))
        return 2

    try:
        if args.command == "status":
            result = read_mouse_state()
            success = True
        elif args.command == "dpi-smoke-test":
            result = run_dpi_smoke_test()
            success = result["ok"]
        else:
            result = set_dpi(args.dpi)
            success = result["ok"]
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
