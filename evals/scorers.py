from src.models import Classification


def severity_accuracy(expected: Classification, actual: Classification) -> float:
    """1.0 if severity matches exactly, 0.0 otherwise."""
    return 1.0 if expected.severity == actual.severity else 0.0


def category_accuracy(expected: Classification, actual: Classification) -> float:
    """1.0 if category matches exactly, 0.0 otherwise."""
    return 1.0 if expected.category == actual.category else 0.0


def overall_score(
    expected: Classification,
    actual: Classification,
    severity_weight: float = 0.4,
    category_weight: float = 0.6,
) -> float:
    """Weighted combination of severity and category accuracy."""
    return (
        severity_weight * severity_accuracy(expected, actual)
        + category_weight * category_accuracy(expected, actual)
    )
