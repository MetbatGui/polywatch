"""MarketFilter Domain Service 단위 테스트"""
from src.domain.market_filter import MarketFilter


def test_macro_keywords_pass():
    assert MarketFilter.is_macro("Will Iran develop nuclear weapons before 2027?")
    assert MarketFilter.is_macro("Federal Reserve rate cut in September?")
    assert MarketFilter.is_macro("Will Trump win the 2024 election?")
    assert MarketFilter.is_macro("Russia ceasefire agreement in 2025?")
    assert MarketFilter.is_macro("Will inflation exceed 3% in June?")


def test_sports_excluded():
    assert not MarketFilter.is_macro("Will Real Madrid win the Champions League?")
    assert not MarketFilter.is_macro("Wimbledon 2025 winner")
    assert not MarketFilter.is_macro("NBA finals game 7 winner")
    assert not MarketFilter.is_macro("FIFA World Cup 2026 champion")


def test_crypto_excluded():
    assert not MarketFilter.is_macro("Will BTC reach $100K?")
    assert not MarketFilter.is_macro("ETH price above $5000 by end of year")


def test_entertainment_excluded():
    assert not MarketFilter.is_macro("Oscar best picture winner 2025")
    assert not MarketFilter.is_macro("Grammy award for best album")


def test_ambiguous_defaults_to_excluded():
    """매크로 키워드 없으면 제외"""
    assert not MarketFilter.is_macro("Will it rain in London tomorrow?")
