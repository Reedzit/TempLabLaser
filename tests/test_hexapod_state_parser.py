import unittest
import threading

from src.hexapod.SYM_HexaPy import API


class HexapodStateParserTests(unittest.TestCase):
    def make_api(self, response):
        api = API()
        api.executeCommand = lambda _command: response
        return api

    def test_state_ignores_echoed_command(self):
        values = ["8", "0"] + ["0"] * 47 + ["49"]
        response = "s_hexa,50,1\n" + "\n".join(values) + "\n"

        state = self.make_api(response).STATE()

        self.assertIn("s_hexa=8", state)
        self.assertIn("s_reserve_05=49", state)
        self.assertNotIn("s_hexa,50,1", state)

    def test_state_rejects_incomplete_payload(self):
        response = "s_hexa,50,1\n6\n0\n"

        with self.assertRaisesRegex(ValueError, "expected 50 values, received 2"):
            self.make_api(response).STATE()

    def test_state_cannot_interleave_with_command_completion(self):
        command_started = threading.Event()
        calls = []
        state_values = ["8", "0"] + ["0"] * 48

        class FakeSSH:
            verbose = False

            def execute_gpascii(self, command):
                calls.append(command)
                if command.endswith("c_cmd=C_MOVE_PTP"):
                    command_started.set()
                    return ""
                if command == "c_cmd":
                    return "0"
                if command == "s_hexa,50,1":
                    return "\n".join(state_values)
                raise AssertionError(f"Unexpected command: {command}")

        api = API()
        api.ssh_obj = FakeSSH()
        command_thread = threading.Thread(
            target=api.SendCommand,
            args=("MOVE_PTP", [2, 0, 0, 0, 0, 0, 0]),
        )
        state_thread = threading.Thread(target=api.STATE)

        command_thread.start()
        self.assertTrue(command_started.wait(timeout=1))
        state_thread.start()
        command_thread.join(timeout=2)
        state_thread.join(timeout=2)

        self.assertFalse(command_thread.is_alive())
        self.assertFalse(state_thread.is_alive())
        self.assertEqual(
            [
                "c_par(0)=2 c_par(1)=0 c_par(2)=0 c_par(3)=0 "
                "c_par(4)=0 c_par(5)=0 c_par(6)=0 c_cmd=C_MOVE_PTP",
                "c_cmd",
                "s_hexa,50,1",
            ],
            calls,
        )


if __name__ == "__main__":
    unittest.main()
