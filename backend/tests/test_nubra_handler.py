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

@pytest.fixture
def mock_option_chain_with_none():
    class MockOption:
        def __init__(self, strike_price, open_interest):
            self.strike_price = strike_price
            self.open_interest = open_interest

    class MockOptionChain:
        def __init__(self):
            self.ce = [
                MockOption(100, 1000),
                MockOption(110, None),
                MockOption(120, 800),
                MockOption(None, 500),
            ]
            self.pe = [
                MockOption(100, 1200),
                MockOption(110, 1300),
                MockOption(120, None),
                MockOption(None, 600),
            ]
    return MockOptionChain()

def test_calculate_pcr_with_none(nubra_handler, mock_option_chain_with_none):
    pcr = nubra_handler._calculate_pcr(mock_option_chain_with_none)
    assert pcr == (1200 + 1300 + 600) / (1000 + 800 + 500)

def test_calculate_max_pain_with_none(nubra_handler, mock_option_chain_with_none):
    max_pain = nubra_handler.calculate_max_pain(mock_option_chain_with_none)
    assert max_pain == 110

@pytest.fixture
def mock_options_for_filtering():
    class MockOption:
        def __init__(self, strike_price):
            self.strike_price = strike_price

    options = [MockOption(i * 10 + 100) for i in range(20)] # 100, 110, ..., 290
    return options

def test_filter_strikes_from_top(nubra_handler, mock_options_for_filtering):
    # Test when ATM strike is high in the list
    atm_strike = 250
    count = 5
    filtered_list = nubra_handler._filter_strikes(mock_options_for_filtering, atm_strike, count)
    assert len(filtered_list) == 10 # 5 below, ATM, 4 above
    assert filtered_list[0].strike_price == 200
    assert filtered_list[-1].strike_price == 290

def test_filter_strikes_from_bottom(nubra_handler, mock_options_for_filtering):
    # Test when ATM strike is low in the list
    atm_strike = 150
    count = 5
    filtered_list = nubra_handler._filter_strikes(mock_options_for_filtering, atm_strike, count)
    assert len(filtered_list) == 11 # 5 below, ATM, 5 above
    assert filtered_list[0].strike_price == 100
    assert filtered_list[-1].strike_price == 200

def test_filter_strikes_in_middle(nubra_handler, mock_options_for_filtering):
    # Test with ATM strike in the middle
    atm_strike = 200
    count = 5
    filtered_list = nubra_handler._filter_strikes(mock_options_for_filtering, atm_strike, count)
    assert len(filtered_list) == 11 # 5 below, ATM, 5 above
    assert filtered_list[0].strike_price == 150
    assert filtered_list[-1].strike_price == 250
