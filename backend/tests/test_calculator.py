import pytest

from ai.tools.utility_tools import CalculatorError, calculate, calculator


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("2 + 3 * 4", 14),
        ("(2 + 3) * 4", 20),
        ("2^10", 1024),
        ("0.17 * 2450", 416.5),
        ("0.1 + 0.2", 0.3),
        ("sqrt(144) + factorial(5)", 132),
        ("1,234,567 + 1", 1234568),
        ("log(100, 10)", 2),
        ("max(3, 7, 5)", 7),
        ("sin(pi / 2)", 1),
        ("-(-5) % 3", 2),
        ("7 // 2", 3),
    ],
)
def test_calculate(expression, expected):
    assert calculate(expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('dir')",  # no code execution
        "9 ** 9 ** 9",                      # huge powers are refused
        "factorial(100000)",
        "x + 1",                            # unknown names
        "2 +",                              # invalid syntax
        "a" * 400,                          # too long
    ],
)
def test_calculate_rejects_unsafe_or_invalid(expression):
    with pytest.raises((CalculatorError, ValueError)):
        calculate(expression)


def test_calculator_tool_reports_errors_as_text():
    assert calculator.invoke({"expression": "1/0"}) == "Error: division by zero"
    assert calculator.invoke({"expression": "6*7"}) == "6*7 = 42"
