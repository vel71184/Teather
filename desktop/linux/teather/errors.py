class TeatherError(RuntimeError):
    """Expected, user-actionable Teather failure."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category
