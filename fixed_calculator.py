# calculator.py

"""
A module providing basic calculator functionality.
"""

class Calculator:
    """
    A class providing basic arithmetic operations.
    """

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, x, y):
        """Subtract y from x."""
        return x - y

    def divide(self, num1, num2):
        """Divide num1 by num2."""
        if num2 == 0:
            raise ValueError("Division by zero is not allowed")
        return num1 / num2

    def multiply(self, n1, n2):
        """Return the product of n1 and n2."""
        return n1 * n2