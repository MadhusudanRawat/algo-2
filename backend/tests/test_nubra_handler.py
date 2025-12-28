import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from nubra_handler import NubraHandler

@pytest.fixture
def nubra_handler():
    return NubraHandler()

@pytest.fixture
def mock_option_chain():
    class MockOption:
        def __init__(self, strike_price, open_interest):
            self.strike_price = strike_price
            self.open_interest = open_interest

    class MockOptionChain:
        def __init__(self):
            self.ce = [
                MockOption(100, 1000),
                MockOption(110, 1500),
                MockOption(120, 800),
            ]
            self.pe = [
                MockOption(100, 1200),
                MockOption(110, 1300),
                MockOption(120, 900),
            ]
    return MockOptionChain()

def test_calculate_pcr(nubra_handler, mock_option_chain):
    pcr = nubra_handler._calculate_pcr(mock_option_chain)
    assert pcr == (1200 + 1300 + 900) / (1000 + 1500 + 800)

def test_calculate_max_pain(nubra_handler, mock_option_chain):
    max_pain = nubra_handler.calculate_max_pain(mock_option_chain)
    assert max_pain == 110
