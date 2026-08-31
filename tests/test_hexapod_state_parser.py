import unittest

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


if __name__ == "__main__":
    unittest.main()
