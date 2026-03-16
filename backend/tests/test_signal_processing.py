import unittest
from backend.signal_processing import critical_function_1, critical_function_2

class TestSignalProcessing(unittest.TestCase):
    def test_critical_function_1(self):
        self.assertEqual(critical_function_1(input_data), expected_output)

    def test_critical_function_2(self):
        self.assertEqual(critical_function_2(input_data), expected_output)

if __name__ == '__main__':
    unittest.main()