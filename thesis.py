from dotenv import load_dotenv
load_dotenv()
import ast
import os
import unittest
import sys
import json
import requests
from io import StringIO
from pylint.lint import Run
from pylint.reporters.text import TextReporter

class WritableObject:
    def __init__(self):
        self.content = []
    def write(self, st):
        self.content.append(st)
    def read(self):
        return ''.join(self.content)

def clean_code(content):
    """Remove Markdown formatting and extra whitespace from code."""
    content = content.strip()
    if content.startswith('```python'):
        content = content[10:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()
    return content

def update_test_import(test_file, current_module, original_module="calculator"):
    """Update the import statement in the test file to match the current module name."""
    with open(test_file, "r") as f:
        test_code = f.read()
    test_code = test_code.replace(f"from {original_module} import", f"from {current_module} import")
    with open(test_file, "w") as f:
        f.write(test_code)

def fix_syntax(code, syntax_error, api_key):
    """Fix syntax errors using Groq API."""
    syntax_fix_prompt = (
        f"The following Python code has a syntax error: {syntax_error}\n\n"
        f"Code:\n{code}\n\n"
        f"Provide a detailed natural language explanation of how to fix the syntax error. "
        f"Do not include code snippets or Markdown formatting.\n"
    )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": syntax_fix_prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fix_explanation = response.json()["choices"][0]["message"]["content"]
        print("Syntax Fix Explanation:\n", fix_explanation)
    except requests.RequestException as e:
        print(f"Error generating syntax fix explanation with Groq API: {e}")
        return None, None
    
    # Generate corrected code
    code_fix_prompt = (
        f"Based on the following syntax error and fix explanation, generate the corrected Python code. "
        f"Output only the fixed code, without additional text, explanations, Markdown formatting such as ```python or ```, "
        f"example usage, instantiation, or print statements.\n\n"
        f"Original Code:\n{code}\n\nSyntax Error:\n{syntax_error}\n\nFix Explanation:\n{fix_explanation}"
    )
    
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": code_fix_prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fixed_code = clean_code(response.json()["choices"][0]["message"]["content"])
        return fix_explanation, fixed_code
    except requests.RequestException as e:
        print(f"Error generating fixed code with Groq API: {e}")
        return None, None

def generate_unit_tests(code, module_name, api_key):
    """Generate a unit test file for any Python codebase using Groq API."""
    test_prompt = (
        f"Analyze the following Python code and generate a complete, valid unit test file using the `unittest` framework. "
        f"The code may contain classes, standalone functions, or a mix of both. For each public function or method "
        f"(excluding those starting with '_'), create test cases that cover:\n"
        f"- Normal cases (typical inputs and expected outputs).\n"
        f"- Edge cases (e.g., zero, negative, empty, or boundary inputs).\n"
        f"- Exception cases (e.g., invalid inputs that raise errors).\n"
        f"Infer the functionality of each function/method based on its name, parameters, docstring (if available), and code body. "
        f"Include a `setUp` method for classes to initialize instances. Ensure the output is formatted as executable Python code "
        f"with proper imports and a `Test{module_name.capitalize()}` class. Include a docstring for each test method. "
        f"Output only the test file content, without additional explanations or Markdown formatting such as ```python or ```.\n\n"
        f"Code:\n{code}\n\n"
        f"Module name: {module_name}"
    )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": test_prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        test_code = clean_code(response.json()["choices"][0]["message"]["content"])
    except requests.RequestException as e:
        print(f"Error generating unit tests with Groq API: {e}")
        return None
    
    # Write test file
    test_file = f"test_{module_name}.py"
    try:
        with open(test_file, "w") as f:
            f.write(test_code)
        return test_file
    except Exception as e:
        print(f"Error writing test file {test_file}: {e}")
        return None

def run_pipeline(code_file):
    # Validate input file
    if not os.path.isfile(code_file):
        print(f"Error: File {code_file} does not exist.")
        sys.exit(1)
    
    # Extract module name without extension
    original_module = os.path.splitext(os.path.basename(code_file))[0]
    module_name = original_module
    syntax_fixed = False
    
    # Step 1: Syntax check with AST
    try:
        with open(code_file, "r") as f:
            code = f.read()
    except Exception as e:
        print(f"Error reading code file {code_file}: {e}")
        sys.exit(1)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    
    syntax_errors = ""
    try:
        ast.parse(code)
        print("Syntax validation successful.")
    except SyntaxError as e:
        syntax_errors = str(e)
        print("Syntax error detected:", syntax_errors)
        
        # Step 2: Fix syntax errors using Groq API
        print("Attempting to fix syntax errors with Groq API...")
        fix_explanation, fixed_code = fix_syntax(code, syntax_errors, api_key)
        if not fixed_code:
            print("Failed to fix syntax errors. Exiting.")
            sys.exit(1)
        
        # Save syntactically corrected code to a temporary file
        temp_file = f"temp_{original_module}.py"
        try:
            with open(temp_file, "w") as f:
                f.write(fixed_code)
            print(f"Syntactically corrected code saved to: {temp_file}")
            code = fixed_code
            code_file = temp_file
            module_name = os.path.splitext(os.path.basename(code_file))[0]
            syntax_fixed = True
        except Exception as e:
            print(f"Error writing temporary file {temp_file}: {e}")
            sys.exit(1)
    
    # Step 3: Logical and style check with Pylint
    pylint_output = WritableObject()
    try:
        Run([code_file], reporter=TextReporter(pylint_output))
    except SystemExit as e:
        if e.code != 0:
            print(f"Pylint completed with issues (exit code: {e.code})")
    except Exception as e:
        print(f"Pylint error: {str(e)}")
    pylint_result = pylint_output.read()
    print("Pylint analysis results:\n", pylint_result if pylint_result else "No Pylint issues detected.")
    
    # Compile issues
    issues = ""
    if syntax_errors:
        issues += f"Syntax errors:\n{syntax_errors}\n\n"
    if pylint_result:
        issues += f"Pylint issues:\n{pylint_result}\n"
    
    if not issues.strip():
        print("No issues detected. Proceeding to unit testing.")
    
    # Step 4: Generate unit tests using Groq API
    print("Generating unit test file with Groq API...")
    test_file = generate_unit_tests(code, original_module, api_key)  # Use original_module for prompt
    if not test_file:
        print("Unit test generation failed. Skipping unit testing.")
        return
    
    print(f"Generated test file: {test_file}")
    
    # Step 5: Run unit tests on (corrected) original code
    print("Running unit tests on" + (" syntax-corrected code..." if syntax_fixed else " original code..."))
    current_module = os.path.splitext(os.path.basename(code_file))[0]
    update_test_import(test_file, current_module, original_module)
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.dirname(code_file), pattern=f"test_{original_module}.py")
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    print("Original Code Unit Test Summary:", test_result)
    
    # Step 6: Obtain fix explanation for logical/style issues from Groq API
    explanation_prompt = (
        f"Provide a detailed natural language explanation of how to fix the following issues "
        f"in this Python code. Focus on clarity and step-by-step guidance. Do not include code snippets or Markdown formatting.\n\n"
        f"Code:\n{code}\n\nIssues:\n{issues}"
    )
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": explanation_prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fix_explanation = response.json()["choices"][0]["message"]["content"]
        print("Fix Explanation in Natural Language:\n", fix_explanation)
    except requests.RequestException as e:
        print(f"Error generating fix explanation with Groq API: {e}")
        return
    
    # Step 7: Generate fixed code for logical/style issues using Groq API
    fix_prompt = (
        f"Based on the following fix explanation, generate the corrected Python code. "
        f"Output only the fixed code, without additional text, explanations, Markdown formatting such as ```python or ```, "
        f"example usage, instantiation, or print statements.\n\n"
        f"Original Code:\n{code}\n\nFix Explanation:\n{fix_explanation}\n\nIssues:\n{issues}"
    )
    
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": fix_prompt}]
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fixed_code = clean_code(response.json()["choices"][0]["message"]["content"])
        print("Fixed Code:\n", fixed_code)
    except requests.RequestException as e:
        print(f"Error generating fixed code with Groq API: {e}")
        return
    
    # Write fixed code to a new file
    fixed_file = f"fixed_{original_module}.py"
    try:
        with open(fixed_file, "w") as f:
            f.write(fixed_code)
        print(f"Fixed code saved to: {fixed_file}")
    except Exception as e:
        print(f"Error writing fixed code to {fixed_file}: {e}")
        return
    
    # Step 8: Run unit tests on fixed code
    print("Running unit tests on fixed code...")
    fixed_module = os.path.splitext(os.path.basename(fixed_file))[0]
    update_test_import(test_file, fixed_module, original_module)
    suite = loader.discover(start_dir=os.path.dirname(fixed_file), pattern=f"test_{original_module}.py")
    test_result = runner.run(suite)
    print("Fixed Code Unit Test Summary:", test_result)

# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python thesis.py <code_file>")
        sys.exit(1)
    run_pipeline(sys.argv[1])