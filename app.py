from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import ast
import os
import unittest
import sys
import json
import requests
from io import StringIO
import tempfile
import shutil
from pylint.lint import Run
from pylint.reporters.text import TextReporter
import logging
import importlib.util
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Python Code Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return content.strip()


def clean_module_cache(module_patterns):
    """Clean module cache for given patterns."""
    modules_to_remove = []
    for pattern in module_patterns:
        modules_to_remove.extend([name for name in sys.modules if pattern in name])
    
    for module in modules_to_remove:
        if module in sys.modules:
            del sys.modules[module]
            logger.info(f"Removed {module} from module cache")


def fix_syntax(code, syntax_error, api_key):
    """Fix syntax errors using Groq API."""
    syntax_fix_prompt = (
        f"There's a small error in this code. Explain what's wrong in simple terms. "
        f"Keep it short and friendly - no technical jargon.\n\n"
        f"Error: {syntax_error}\nCode:\n{code}"
    )

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role": "user", "content": syntax_fix_prompt}]}

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fix_explanation = response.json()["choices"][0]["message"]["content"]
        logger.info("Syntax fix explanation generated successfully")
    except requests.RequestException as e:
        logger.error(f"Error generating syntax fix explanation: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        raise HTTPException(status_code=500, detail=f"Error generating syntax fix explanation with Groq API: {str(e)}")

    # Generate corrected code
    code_fix_prompt = (
        f"Fix this code and make it work properly. Return only the corrected code.\n\n"
        f"Code with error:\n{code}\n\nWhat to fix:\n{fix_explanation}"
    )

    payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role": "user", "content": code_fix_prompt}]}

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        fixed_code = clean_code(response.json()["choices"][0]["message"]["content"])
        if not fixed_code:
            logger.error("Generated fixed code is empty")
            raise ValueError("Invalid fixed code generated")
        
        # Validate the fixed code
        try:
            ast.parse(fixed_code)
        except SyntaxError as e:
            logger.error(f"Generated fixed code has syntax errors: {e}")
            raise ValueError(f"Invalid fixed code generated: {e}")
            
        logger.info("Syntax fixed code generated successfully")
        return fix_explanation, fixed_code
    except (requests.RequestException, ValueError, SyntaxError) as e:
        logger.error(f"Error generating fixed code: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        raise HTTPException(status_code=500, detail=f"Error generating fixed code with Groq API: {str(e)}")


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
        f"Methods are instance methods, so use a class instance (e.g., self.calc.method()) in test cases. "
        f"IMPORTANT: Only test for TypeError exceptions if the method actually validates input types and raises TypeError. "
        f"If the method doesn't have type validation, do not create TypeError test cases. "
        f"Test only the actual behavior of the methods as implemented. "
        f"Include a `setUp` method to initialize an instance (e.g., self.calc = Calculator()). "
        f"Ensure the output is formatted as executable Python code with proper imports and a `Test{module_name.capitalize()}` class. "
        f"Include a docstring for each test method. Output only the test file content, without additional explanations or Markdown formatting.\n\n"
        f"Code:\n{code}\n\nModule name: {module_name}"
    )

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role": "user", "content": test_prompt}]}

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        test_code = clean_code(response.json()["choices"][0]["message"]["content"])
        if not test_code:
            logger.error("Generated test code is empty")
            raise ValueError("Invalid test code generated")
        
        # Validate the test code
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            logger.error(f"Generated test code has syntax errors: {e}")
            raise ValueError(f"Invalid test code generated: {e}")
            
        logger.info("Unit tests generated successfully")
        return test_code
    except (requests.RequestException, ValueError, SyntaxError) as e:
        logger.error(f"Error generating unit tests: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        raise HTTPException(status_code=500, detail=f"Error generating unit tests with Groq API: {str(e)}")


def run_unit_tests(test_code, code_file, module_name, temp_dir):
    """Run unit tests and capture results with improved module isolation."""
    # Generate unique module names to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    unique_module_name = f"{module_name}_{unique_id}"
    unique_test_module = f"test_{unique_module_name}"
    
    # Create unique file names
    unique_code_file = os.path.join(temp_dir, f"{unique_module_name}.py")
    test_file_path = os.path.join(temp_dir, f"{unique_test_module}.py")
    
    try:
        # Copy the code file with unique name
        with open(code_file, 'r') as src:
            code_content = src.read()
        with open(unique_code_file, 'w') as dst:
            dst.write(code_content)
        
        # Update test code to import the uniquely named module
        updated_test_code = test_code.replace(f"from {module_name} import", f"from {unique_module_name} import")
        updated_test_code = updated_test_code.replace(f"import {module_name}", f"import {unique_module_name}")
        
        # Write the test file
        with open(test_file_path, "w") as f:
            f.write(updated_test_code)
        logger.info(f"Test file written to: {test_file_path}")

        # Clean module cache for all related modules
        clean_module_cache([module_name, unique_module_name, unique_test_module])
        
        # Save current directory and change to temp directory
        original_dir = os.getcwd()
        original_sys_path = sys.path.copy()
        
        try:
            os.chdir(temp_dir)
            if temp_dir not in sys.path:
                sys.path.insert(0, temp_dir)
                logger.info(f"Added {temp_dir} to sys.path")

            # Verify the module can be imported
            try:
                spec = importlib.util.spec_from_file_location(unique_module_name, unique_code_file)
                if spec is None:
                    raise ImportError(f"Could not load spec for {unique_module_name}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[unique_module_name] = module
                spec.loader.exec_module(module)
                logger.info(f"Successfully imported module {unique_module_name}")
            except Exception as e:
                logger.error(f"Failed to import module {unique_module_name}: {e}")
                return f"Failed to import module {unique_module_name}: {e}", False

            # Run the tests
            try:
                loader = unittest.TestLoader()
                suite = loader.discover(start_dir=".", pattern=f"{unique_test_module}.py")
                
                if not suite.countTestCases():
                    logger.warning(f"No test cases discovered for {test_file_path}")
                    return "No test cases found", False

                output = StringIO()
                runner = unittest.TextTestRunner(stream=output, verbosity=2)
                result = runner.run(suite)
                test_results = output.getvalue()
                output.close()
                
                logger.info(f"Tests completed. Success: {result.wasSuccessful()}, "
                           f"Tests run: {result.testsRun}, "
                           f"Errors: {len(result.errors)}, "
                           f"Failures: {len(result.failures)}")
                
                return test_results, result.wasSuccessful()
                
            except Exception as e:
                logger.error(f"Error running tests: {e}")
                return f"Error running tests: {e}", False
                
        except Exception as e:
            logger.error(f"Unexpected error in run_unit_tests: {e}")
            return f"Unexpected error: {e}", False
        finally:
            # Restore original state
            os.chdir(original_dir)
            sys.path = original_sys_path
            # Clean up the unique modules from cache
            clean_module_cache([unique_module_name, unique_test_module])
            logger.info("Restored original directory and sys.path")
            
    except Exception as e:
        logger.error(f"Error in run_unit_tests setup: {e}")
        return f"Error in test setup: {e}", False
    finally:
        # Clean up temporary files
        for file_path in [unique_code_file, test_file_path]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Could not remove {file_path}: {e}")


@app.post("/upload")
async def upload_code_file(file: UploadFile = File(...)):
    """Process a Python file and return unit test details, fix explanation, and fixed code."""
    logger.info("Received file upload: %s", file.filename)
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="File must be a .py file")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is not set.")

    # Create a unique temporary directory for this request
    temp_dir = tempfile.mkdtemp(prefix="code_analysis_")
    logger.info(f"Created temporary directory: {temp_dir}")
    
    try:
        code_file = os.path.join(temp_dir, file.filename)
        with open(code_file, "wb") as f:
            f.write(await file.read())
        logger.info("Saved uploaded file to: %s", code_file)

        original_module = os.path.splitext(file.filename)[0]
        module_name = original_module

        with open(code_file, "r") as f:
            code = f.read()

        syntax_message = ""
        syntax_fixed = False
        syntax_fix_explanation = ""

        # Step 1: Syntax check
        try:
            ast.parse(code)
            syntax_message = "Code looks good!"
            logger.info("Syntax validation successful for %s", code_file)
        except SyntaxError as e:
            syntax_errors = str(e)
            syntax_message = f"Found a small error: missing punctuation or typo"
            logger.warning("Syntax error in %s: %s", code_file, syntax_errors)
            syntax_fix_explanation, fixed_code = fix_syntax(code, syntax_errors, api_key)
            with open(code_file, "w") as f:
                f.write(fixed_code)
            syntax_fixed = True
            code = fixed_code

        # Step 2: Pylint analysis
        pylint_output = WritableObject()
        try:
            Run([code_file], reporter=TextReporter(pylint_output))
        except SystemExit as e:
            if e.code != 0:
                pylint_output.write(f"Pylint completed with issues (exit code: {e.code})")
        pylint_result = pylint_output.read()

        issues = ""
        if syntax_fixed:
            issues += f"Small fixes needed:\n{syntax_fix_explanation}\n\n"
        if pylint_result:
            issues += f"Code style suggestions:\n{pylint_result}\n"
        if not issues.strip():
            issues = "Your code looks great!"

        # Step 3: Generate unit tests
        test_code = generate_unit_tests(code, original_module, api_key)

        # Step 4: Run unit tests on original code
        original_test_results, original_test_success = run_unit_tests(
            test_code, code_file, original_module, temp_dir
        )

        # Step 5: Generate simple fix explanations
        explanation_prompt = (
            f"Explain how to fix these simple coding issues in plain English. Keep it short and friendly. "
            f"Don't use technical terms or code examples.\n\n"
            f"Code issues:\n{issues}"
        )
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role": "user", "content": explanation_prompt}]}
        
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            logical_fix_explanation = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating logical fix explanation: {e}")
            logical_fix_explanation = "Unable to generate explanation at this time."

        fix_prompt = (
            f"Fix this code based on the suggestions. Make it clean and working. "
            f"Return only the corrected code, nothing else.\n\n"
            f"Original Code:\n{code}\n\nSuggestions:\n{logical_fix_explanation}"
        )
        payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role": "user", "content": fix_prompt}]}
        
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            fixed_code = clean_code(response.json()["choices"][0]["message"]["content"])
            
            # Validate the fixed code
            if not fixed_code:
                raise ValueError("Fixed code is empty")
            try:
                ast.parse(fixed_code)
            except SyntaxError as e:
                raise ValueError(f"Generated fixed code has syntax errors: {e}")
        except Exception as e:
            logger.error(f"Error generating fixed code: {e}")
            fixed_code = code  # Use original code if fixing fails
            logical_fix_explanation = "Unable to generate fixes at this time."

        # Step 6: Create a separate temporary directory for fixed code testing
        fixed_temp_dir = tempfile.mkdtemp(prefix="fixed_code_analysis_")
        logger.info(f"Created fixed code temporary directory: {fixed_temp_dir}")
        
        try:
            # Save fixed code
            fixed_module_name = f"fixed_{original_module}"
            fixed_code_file = os.path.join(fixed_temp_dir, f"{fixed_module_name}.py")
            with open(fixed_code_file, "w") as f:
                f.write(fixed_code)
            logger.info(f"Fixed code saved to: {fixed_code_file}")

            # Step 7: Generate new test code for the fixed module
            fixed_test_code = generate_unit_tests(fixed_code, fixed_module_name, api_key)

            # Step 8: Run unit tests on fixed code
            fixed_test_results, fixed_test_success = run_unit_tests(
                fixed_test_code, fixed_code_file, fixed_module_name, fixed_temp_dir
            )
            
        finally:
            # Clean up fixed code temp directory
            shutil.rmtree(fixed_temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up fixed code temporary directory: {fixed_temp_dir}")

        return JSONResponse(
            content={
                "syntax_check": syntax_message,
                "pylint_results": pylint_result if pylint_result else "Code style looks good!",
                "generated_test_code": test_code,
                "original_test_results": original_test_results,
                "original_test_success": original_test_success,
                "syntax_fix_explanation": syntax_fix_explanation,
                "logical_fix_explanation": logical_fix_explanation,
                "fixed_code": fixed_code,
                "fixed_test_code": fixed_test_code,
                "fixed_test_results": fixed_test_results,
                "fixed_test_success": fixed_test_success,
            }
        )

    except Exception as e:
        logger.error(f"Error processing request for {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        # Clean up main temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up main temporary directory: {temp_dir}")


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)