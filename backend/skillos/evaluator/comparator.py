def compare(actual: str, expected: str, mode: str = "exact") -> bool:
    if mode == "exact":
        return actual.strip() == expected.strip()
    elif mode == "float":
        try:
            return abs(float(actual.strip()) - float(expected.strip())) < 1e-6
        except ValueError:
            return False
    elif mode == "multiline":
        actual_lines   = [l.strip() for l in actual.strip().splitlines()]
        expected_lines = [l.strip() for l in expected.strip().splitlines()]
        return actual_lines == expected_lines
    return False  # fail closed on unknown mode
