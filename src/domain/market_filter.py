_MACRO_INCLUDE = frozenset({
    "election", "president", "prime minister", "chancellor",
    "senate", "congress", "parliament", "governor",
    "federal reserve", "fed ", "interest rate", "gdp",
    "inflation", "recession", "ipo ",
    "nuclear", "nuke", "war", "peace", "nato", "sanctions",
    "iran", "russia", "china", "taiwan", "ukraine", "israel",
    "trump", "biden", "harris", "macron", "modi", "erdogan",
    "zelensky", "zelenskyy", "canal", "gulf", "geopolit",
    "referendum", "vote", "ballot", "primary", "runoff",
    "nominee", "leadership", "cabinet", "ceasefire", "treaty",
})

_EXCLUDE = frozenset({
    "formula", "grand prix", "world cup", "fifa", "wimbledon",
    "premier league", "bundesliga", "serie a", "la liga", "champions league",
    " nba ", " nfl ", " nhl ", " mlb ", " f1 ",
    "tour de", " pga ", " t20 ", "cricket", "rugby",
    "bitcoin", "ethereum", "crypto", "solana", " btc ", " eth ",
    "oscar", "emmy", "grammy", "golden globe",
    "temperature", "weather",
})


class MarketFilter:
    @staticmethod
    def is_macro(question: str) -> bool:
        # 양쪽 공백 패딩 — 단어 경계 없는 substring 충돌 방지 (예: nfl ⊂ inflation)
        q = f" {question.lower()} "
        if any(kw in q for kw in _EXCLUDE):
            return False
        return any(kw in q for kw in _MACRO_INCLUDE)
