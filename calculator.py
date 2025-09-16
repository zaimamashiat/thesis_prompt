# calculator.py
class Calculator:
    def add(a, b)  # Syntax error: missing colon
        """Add two numbers."""
        return a + b

    def subtract(x, y):
        """Subtract y from x."""
        return x - y

    def divide(num1, num2):  # Logical error: incorrect division logic
        """Divide num1 by num2."""
        if num2 == 0:
            raise ValueError("Division by zero is not allowed")
        return num1 + num2  # Should be num1 / num2

    def multiply(n1, n2):  # Stylistic issue: poor variable names
        return n1 * n2  # Missing docstring