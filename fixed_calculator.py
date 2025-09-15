"This module provides a simple calculator class with basic arithmetic operations."

class Calculator:
    """A simple calculator class with basic arithmetic operations."""
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
        """Multiply two numbers."""
        return n1 * n2