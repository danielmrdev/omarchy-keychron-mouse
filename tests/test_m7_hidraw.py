import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from helper.m7_hidraw import (
    decode_button,
    decode_dpi_ack,
    decode_linked_mice,
    decode_protocol_version,
    build_shared_dpi_packet,
    decode_status,
    find_config_device,
    parse_hid_report_descriptor,
    read_mouse_state,
    verify_dpi_status,
    HidrawDevice,
    HidReportDescriptor,
    _drain_pending_reports,
    _exchange,
    main,
    run_dpi_smoke_test,
    set_dpi,
)


STATUS_CAPTURE = bytes.fromhex(
    "06 00 22 22 02 90 01 20 03 40 06 80 0c 88 13 15 05 04 0a 5d "
    "00 00 00 00 00 00 b7 00 00 00 04 04 04 04 04 04 04 04 04 04 "
    "00 00 00 00 01 02 03 04 05 06 05 00 00 00 00 00 00 00 00 00 "
    "00 00 00"
)


HID_DESCRIPTOR_CAPTURE = bytes.fromhex(
    "06 c1 ff 09 01 a1 01 15 00 26 ff 00 75 08 85 b4 09 02 95 3f "
    "81 02 85 b3 09 03 95 3f 91 02 85 b5 09 04 95 14 91 02 85 b6 "
    "09 07 95 14 81 02 c0"
)


class HidrawParserTests(unittest.TestCase):
    def test_decodes_captured_m7_status(self):
        status = decode_status(STATUS_CAPTURE)

        self.assertEqual(status["responseBytes"], 63)
        self.assertEqual(status["dpiStageCount"], 5)
        self.assertEqual(status["dpiPresets"], [400, 800, 1600, 3200, 5000])
        self.assertEqual(status["connections"], [
            {"name": "USB", "activeDpiStage": 3, "pollingHz": 1000},
            {"name": "2.4 GHz", "activeDpiStage": 3, "pollingHz": 1000},
            {"name": "Bluetooth", "activeDpiStage": 3, "pollingHz": 125},
        ])
        self.assertEqual(status["onboardProfile"], 1)
        self.assertEqual(status["onboardProfileCount"], 5)
        self.assertEqual(status["batteryPercent"], 93)
        self.assertFalse(status["batteryCharging"])
        self.assertEqual(status["rawHex"], " ".join(f"{byte:02x}" for byte in STATUS_CAPTURE))

    def test_decodes_battery_charging_bit(self):
        reply = bytearray(STATUS_CAPTURE)
        reply[19] |= 0x80

        status = decode_status(reply)

        self.assertEqual(status["batteryPercent"], 93)
        self.assertTrue(status["batteryCharging"])

    def test_marks_invalid_battery_level_unknown(self):
        reply = bytearray(STATUS_CAPTURE)
        reply[19] = 101

        status = decode_status(reply)

        self.assertIsNone(status["batteryPercent"])
        self.assertIsNone(status["batteryCharging"])

    def test_rejects_wrong_status_command(self):
        with self.assertRaisesRegex(ValueError, "status command"):
            decode_status(bytes([0x05]) + STATUS_CAPTURE[1:])

    def test_rejects_truncated_status(self):
        with self.assertRaisesRegex(ValueError, "63 bytes"):
            decode_status(STATUS_CAPTURE[:50])

    def test_rejects_unsupported_dpi_stage_count(self):
        reply = bytearray(STATUS_CAPTURE)
        reply[16] = 6

        with self.assertRaisesRegex(ValueError, "DPI stage count"):
            decode_status(reply)

    def test_rejects_active_stage_outside_reported_count(self):
        reply = bytearray(STATUS_CAPTURE)
        reply[2] = 0x05  # stage 6, while this reply advertises five stages

        with self.assertRaisesRegex(ValueError, "active DPI stage"):
            decode_status(reply)

    def test_decodes_default_button_even_with_nonzero_unused_tail(self):
        reply = bytes.fromhex("62 07 00 00 e9 00 00") + bytes(56)

        mapping = decode_button(reply, index=7, name="Page Down")

        self.assertEqual(mapping, {
            "name": "Page Down",
            "index": 7,
            "action": "Default (firmware)",
            "rawHex": "62 07 00 00 e9 00 00",
        })

    def test_decodes_media_action_from_button_reply(self):
        reply = bytes.fromhex("62 07 00 03 e9 00 00") + bytes(56)

        self.assertEqual(decode_button(reply, index=7, name="Page Down")["action"], "Volume Up")

    def test_builds_exact_temporary_800_dpi_packet(self):
        self.assertEqual(
            build_shared_dpi_packet(STATUS_CAPTURE, stage=1),
            bytes.fromhex("40 01 01 01 90 01 20 03 40 06 80 0c 88 13 05 00 00 00 00 00"),
        )

    def test_restore_packet_preserves_original_three_selectors(self):
        self.assertEqual(
            build_shared_dpi_packet(STATUS_CAPTURE, stage=None),
            bytes.fromhex("40 02 02 02 90 01 20 03 40 06 80 0c 88 13 05 00 00 00 00 00"),
        )

    def test_accepts_successful_shared_dpi_ack(self):
        self.assertEqual(decode_dpi_ack(bytes.fromhex("e4 00 40") + bytes(17)), "e4 00 40")
        self.assertEqual(decode_dpi_ack(bytes.fromhex("40 00 00") + bytes(17)), "40 00 00")

    def test_rejects_failed_shared_dpi_ack(self):
        with self.assertRaisesRegex(ValueError, "rejected"):
            decode_dpi_ack(bytes.fromhex("e4 01 40") + bytes(17))

    def test_verifies_only_dpi_selector_changed(self):
        changed = bytearray(STATUS_CAPTURE)
        for offset in (2, 3, 4):
            changed[offset] = (changed[offset] & 0xF0) | 1

        verify_dpi_status(STATUS_CAPTURE, changed, (1, 1, 1))

    def test_rejects_polling_change_during_dpi_test(self):
        changed = bytearray(STATUS_CAPTURE)
        changed[2] += 0x10

        with self.assertRaisesRegex(ValueError, "polling"):
            verify_dpi_status(STATUS_CAPTURE, changed, (1, 1, 1))

    def test_rejects_unrelated_status_change_during_dpi_test(self):
        changed = bytearray(STATUS_CAPTURE)
        changed[17] ^= 1

        with self.assertRaisesRegex(ValueError, "outside DPI selectors at offset 17"):
            verify_dpi_status(STATUS_CAPTURE, changed, (2, 2, 2))

    def test_decodes_protocol_v4_reply(self):
        reply = bytes.fromhex("02 04 00") + bytes(17)

        self.assertEqual(decode_protocol_version(reply), 4)

    def test_decodes_linked_m7_identity(self):
        reply = bytes.fromhex("03 01 34 34 56 d0 01") + bytes(13)

        self.assertEqual(decode_linked_mice(reply), [
            {"vendorId": 0x3434, "productId": 0xD056, "connected": True},
        ])

    def test_parses_receiver_configuration_reports(self):
        descriptor = parse_hid_report_descriptor(HID_DESCRIPTOR_CAPTURE)

        self.assertEqual(descriptor.usage_page, 0xFFC1)
        self.assertEqual(descriptor.usage, 0x01)
        self.assertEqual(descriptor.input_reports, {0xB4: 63, 0xB6: 20})
        self.assertEqual(descriptor.output_reports, {0xB3: 63, 0xB5: 20})

    def test_discovers_wired_m7_configuration_interface(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            sysfs = root / "sys"
            dev = root / "dev"
            entry = sysfs / "hidraw0"
            device_dir = entry / "device"
            device_dir.mkdir(parents=True)
            dev.mkdir()
            (device_dir / "uevent").write_text(
                "HID_ID=0003:00003434:0000D056" + chr(10)
                + "HID_NAME=Keychron Keychron M7 8K" + chr(10)
            )
            (device_dir / "report_descriptor").write_bytes(HID_DESCRIPTOR_CAPTURE)
            (dev / "hidraw0").touch()

            device = find_config_device(
                sysfs_root=sysfs,
                dev_root=dev,
                product_id=0xD056,
                allow_missing=True,
            )

        self.assertEqual(device.path, dev / "hidraw0")
        self.assertEqual(device.product_name, "Keychron Keychron M7 8K")

    def test_wired_status_reads_direct_device_without_receiver_or_writes(self):
        device = HidrawDevice(
            Path("/dev/hidraw-test"),
            "Keychron Keychron M7 8K",
            HidReportDescriptor(0xFFC1, 0x01, {0xB4: 63, 0xB6: 20}, {0xB3: 63, 0xB5: 20}),
        )
        button_replies = [
            bytes((0x62, index, 0, 0)) + bytes(59)
            for index in (0, 1, 2, 3, 4, 7, 13, 14)
        ]
        with (
            patch("helper.m7_hidraw.find_config_device", return_value=device) as find_device,
            patch("helper.m7_hidraw._open_verified_wired_mouse", return_value=(device, 99, 4)),
            patch("helper.m7_hidraw._open_verified_receiver") as open_receiver,
            patch("helper.m7_hidraw._command_query", side_effect=[STATUS_CAPTURE, *button_replies]) as query,
            patch("helper.m7_hidraw._write_shared_dpi") as write,
            patch("helper.m7_hidraw.os.close"),
        ):
            result = read_mouse_state()

        find_device.assert_called_once_with(product_id=0xD056, allow_missing=True)
        open_receiver.assert_not_called()
        self.assertEqual(result["transport"], "USB (cable)")
        self.assertEqual(result["device"]["productId"], "0xd056")
        self.assertIsNone(result["receiver"])
        self.assertEqual(result["status"]["batteryPercent"], 93)
        self.assertEqual(len(result["buttons"]), 8)
        self.assertEqual(query.call_count, 9)
        write.assert_not_called()

    def test_receiver_status_is_used_when_wired_mouse_is_absent(self):
        receiver = HidrawDevice(
            Path("/dev/hidraw-receiver"),
            "Keychron Ultra-Link 8K",
            HidReportDescriptor(0xFFC1, 0x01, {0xB4: 63, 0xB6: 20}, {0xB3: 63, 0xB5: 20}),
        )
        button_replies = [
            bytes((0x62, index, 0, 0)) + bytes(59)
            for index in (0, 1, 2, 3, 4, 7, 13, 14)
        ]
        with (
            patch("helper.m7_hidraw.find_config_device", return_value=None) as find_device,
            patch("helper.m7_hidraw._open_verified_receiver", return_value=(receiver, 99, 4)) as open_receiver,
            patch("helper.m7_hidraw._command_query", side_effect=[STATUS_CAPTURE, *button_replies]) as query,
            patch("helper.m7_hidraw.os.close"),
        ):
            result = read_mouse_state()

        find_device.assert_called_once_with(product_id=0xD056, allow_missing=True)
        open_receiver.assert_called_once()
        self.assertEqual(result["transport"], "2.4 GHz")
        self.assertEqual(result["device"]["productId"], "0xd028")
        self.assertEqual(result["receiver"]["productId"], "0xd028")
        self.assertEqual(query.call_count, 9)


class DpiSmokeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.device = HidrawDevice(
            Path("/dev/hidraw-test"),
            "Keychron Ultra-Link 8K",
            HidReportDescriptor(0xFFC1, 0x01, {0xB4: 63, 0xB6: 20}, {0xB3: 63, 0xB5: 20}),
        )

    @staticmethod
    def status_at_stage(stage):
        status = bytearray(STATUS_CAPTURE)
        for offset in (2, 3, 4):
            status[offset] = (status[offset] & 0xF0) | stage
        return bytes(status)

    def run_test_with_mocks(self, query_results, write_results):
        query_patch = patch("helper.m7_hidraw._command_query", side_effect=query_results)
        write_patch = patch("helper.m7_hidraw._write_shared_dpi", side_effect=write_results)
        open_patch = patch(
            "helper.m7_hidraw._open_verified_receiver",
            return_value=(self.device, 99, 4),
        )
        close_patch = patch("helper.m7_hidraw.os.close")
        return query_patch, write_patch, open_patch, close_patch

    def test_preflight_mismatch_refuses_all_writes(self):
        changed = bytearray(STATUS_CAPTURE)
        changed[2] = (changed[2] & 0xF0) | 1
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [bytes(changed)], []
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            with self.assertRaisesRegex(RuntimeError, "all three active stages"):
                run_dpi_smoke_test()

        query.assert_called_once()
        write.assert_not_called()

    def test_success_uses_temp_then_restore_and_confirms_two_reads(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, self.status_at_stage(1), STATUS_CAPTURE, STATUS_CAPTURE],
            ["e4 00 40", "e4 00 40"],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = run_dpi_smoke_test()

        self.assertTrue(result["ok"])
        self.assertEqual(result["restoredActiveDpi"], 1600)
        self.assertEqual(query.call_count, 4)
        self.assertEqual(write.call_count, 2)
        temporary_packet = write.call_args_list[0].args[2]
        restore_packet = write.call_args_list[1].args[2]
        self.assertEqual(temporary_packet, build_shared_dpi_packet(STATUS_CAPTURE, stage=1))
        self.assertEqual(restore_packet, build_shared_dpi_packet(STATUS_CAPTURE, stage=None))

    def test_failed_temporary_write_still_attempts_and_verifies_restore(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, STATUS_CAPTURE, STATUS_CAPTURE],
            [TimeoutError("temporary ACK timeout"), "e4 00 40"],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = run_dpi_smoke_test()

        self.assertFalse(result["ok"])
        self.assertIn("restaurado y verificado", result["result"])
        self.assertEqual(write.call_count, 2)
        self.assertEqual(query.call_count, 3)

    def test_failed_temporary_readback_still_attempts_restore(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, TimeoutError("temporary status timeout"), STATUS_CAPTURE, STATUS_CAPTURE],
            ["e4 00 40", "e4 00 40"],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = run_dpi_smoke_test()

        self.assertFalse(result["ok"])
        self.assertIn("temporary status timeout", result["testError"])
        self.assertEqual(write.call_count, 2)
        self.assertEqual(query.call_count, 4)

    def test_stale_baseline_reply_cannot_confirm_restore_by_itself(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, self.status_at_stage(1), STATUS_CAPTURE, self.status_at_stage(1)],
            ["e4 00 40", "e4 00 40"],
        )
        with query_patch as query, write_patch, open_patch, close_patch:
            result = run_dpi_smoke_test()

        self.assertFalse(result["ok"])
        self.assertEqual(result["result"], "Restauración no verificada; estado actual incierto")
        self.assertIn("active DPI stage changed unexpectedly", result["restoreError"])
        self.assertEqual(query.call_count, 4)

    def test_cli_requires_explicit_confirmation_before_hid_access(self):
        output = io.StringIO()
        with redirect_stdout(output), patch("helper.m7_hidraw._open_verified_receiver") as open_receiver:
            exit_code = main(["dpi-smoke-test"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue()), {
            "error": "temporary DPI write requires --confirm; no HID report sent",
        })
        open_receiver.assert_not_called()

    def test_set_dpi_requires_confirmation_before_hid_access(self):
        output = io.StringIO()
        with redirect_stdout(output), patch("helper.m7_hidraw._open_verified_receiver") as open_receiver:
            exit_code = main(["set-dpi", "--dpi", "800"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue()), {
            "error": "DPI write requires --confirm; no HID report sent",
        })
        open_receiver.assert_not_called()

    def test_set_dpi_rejects_unreported_preset_before_writing(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE], []
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            with self.assertRaisesRegex(RuntimeError, "not one of the receiver's reported presets"):
                set_dpi(1200)

        query.assert_called_once()
        write.assert_not_called()

    def test_set_dpi_applies_and_confirms_only_requested_shared_stage(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, self.status_at_stage(1), self.status_at_stage(1)],
            ["e4 00 40"],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = set_dpi(800)

        self.assertTrue(result["ok"])
        self.assertEqual(result["activeDpi"], [800, 800, 800])
        self.assertEqual(result["pollingHz"], [1000, 1000, 125])
        self.assertEqual(query.call_count, 3)
        write.assert_called_once()
        self.assertEqual(write.call_args.args[2], build_shared_dpi_packet(STATUS_CAPTURE, stage=1))

    def test_set_dpi_noop_does_not_write_when_all_modes_already_match(self):
        status = self.status_at_stage(1)
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [status], []
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = set_dpi(800)

        self.assertTrue(result["ok"])
        self.assertFalse(result["writeSent"])
        query.assert_called_once()
        write.assert_not_called()

    def test_set_dpi_reports_lost_ack_when_two_reads_confirm_target(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, self.status_at_stage(1), self.status_at_stage(1)],
            [TimeoutError("ACK timeout")],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = set_dpi(800)

        self.assertTrue(result["ok"])
        self.assertIn("ACK no recibido", result["result"])
        self.assertEqual(result["ackError"], "ACK timeout")
        self.assertEqual(query.call_count, 3)
        write.assert_called_once()

    def test_set_dpi_never_retries_after_unconfirmed_readback(self):
        query_patch, write_patch, open_patch, close_patch = self.run_test_with_mocks(
            [STATUS_CAPTURE, STATUS_CAPTURE],
            ["e4 00 40"],
        )
        with query_patch as query, write_patch as write, open_patch, close_patch:
            result = set_dpi(800)

        self.assertFalse(result["ok"])
        self.assertIn("estado actual incierto", result["result"])
        self.assertEqual(query.call_count, 2)
        write.assert_called_once()

    def test_persistent_input_queue_aborts_before_hid_write(self):
        ready = ([99], [], [])
        with patch("helper.m7_hidraw.select.select", return_value=ready), \
             patch("helper.m7_hidraw.os.read", return_value=bytes(65)), \
             patch("helper.m7_hidraw.os.write") as write:
            with self.assertRaisesRegex(RuntimeError, "queue did not drain"):
                _drain_pending_reports(99)

            with self.assertRaisesRegex(RuntimeError, "queue did not drain"):
                _exchange(99, 0xB5, 0xB6, bytes(20), 20, 20, lambda _: True, 1e9)

        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
