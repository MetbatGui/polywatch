from src.domain.wallet import Classification, WalletProfile


class WalletClassifier:
    @staticmethod
    def classify(p: WalletProfile) -> Classification:
        # amm_bot: 중립 bias + 고빈도 + 중립 승률 (gambler와 구분)
        if 0.45 <= p.bias_up <= 0.55 and p.total_trades > 100 and p.win_rate >= 0.35:
            return Classification.AMM_BOT

        # arbitrager: 극단적 승률 + 소수 마켓 + 저거래
        if p.win_rate > 0.85 and p.n_markets <= 3 and p.total_trades < 10:
            return Classification.ARBITRAGER

        # insider: 탐색 모드 — 낮은 임계값, 재현율 우선
        if p.win_rate > 0.6 and p.n_markets < 10 and p.total_pnl > 5_000:
            return Classification.INSIDER

        # gambler: 저승률 + 고빈도 + 손실
        if p.win_rate < 0.2 and p.total_trades > 100 and p.total_pnl < -10_000:
            return Classification.GAMBLER

        return Classification.UNKNOWN
