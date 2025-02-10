def hello(n: int) -> str:
    """Greet the sum from 0 to n (exclusive end)."""
    sum_n = sum(range(n))
    return f"Hello {sum_n}!"
