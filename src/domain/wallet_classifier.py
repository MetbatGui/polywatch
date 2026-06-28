from src.domain.wallet import Classification, WalletProfile


class WalletClassifier:
    @staticmethod
    def classify(p: WalletProfile) -> Classification:
        # insider: 신규 계정(<90일) + 집중 베팅 — 나이 먼저 체크
        if p.age_days < 90 and p.n_markets <= 3 and p.total_trades <= 5:
            return Classification.INSIDER

        # amm_bot: 중립 bias + 고빈도
        if 0.45 <= p.bias_up <= 0.55 and p.total_trades > 100 and p.win_rate >= 0.35:
            return Classification.AMM_BOT

        # arbitrager: 베테랑 + 극단적 승률 + 소수 마켓 집중
        if p.win_rate > 0.85 and p.n_markets <= 5 and p.total_trades < 20:
            return Classification.ARBITRAGER

        # expert: 베테랑(>=90일) + 꾸준한 고승률 + 다양한 마켓
        if p.age_days >= 90 and p.win_rate > 0.60 and p.n_markets > 5 and p.total_trades >= 20:
            return Classification.EXPERT

        # gambler: 저승률 + 고빈도 + 손실
        if p.win_rate < 0.2 and p.total_trades > 100 and p.total_pnl < -10_000:
            return Classification.GAMBLER

        return Classification.UNKNOWN
