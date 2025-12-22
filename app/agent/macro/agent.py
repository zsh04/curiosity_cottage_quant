class MacroAgent:
    """
    Stub for the Macro Agent (The Consultant).
    """

    def __init__(self):
        pass

    def analyze_regime(self, state: dict) -> dict:
        """
        Stub method returning a safe default regime.
        """
        return {"status": "Neutral", "alpha": 2.5, "macro_correlation": 0.0}
