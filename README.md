# Python Code Fixer Thesis

This repository contains a Python pipeline for analyzing, testing, and fixing code files using the Groq API. It performs syntax validation with AST, style/logical checks with Pylint, unit test generation, and code fixing.

## Files
- `thesis.py`: The main script. Run with `python thesis.py <code_file>`.
- `calculator.py`: Sample input code with syntax errors for testing.
- `fixed_calculator.py`: Expected fixed output from the pipeline.

## Setup
1. Install dependencies: `pip install requests pylint python-dotenv`.
2. Set `GROQ_API_KEY` environment variable (obtain from https://console.groq.com).
3. Run: `python thesis.py calculator.py`.

## Dependencies
- Groq API key for LLM calls.
- Python 3.6+.

## License
MIT License.