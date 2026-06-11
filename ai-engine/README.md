# Judge0 Code Runner

A lightweight Python module to evaluate source code against multiple test cases using the Judge0 CE public API.

## Installation

1. Make sure you have Python installed.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

You can import and use the `run_test_cases` function in your Python projects to automatically submit code and evaluate its output.

### Function Signature

```python
def run_test_cases(source_code: str, language_id: int, test_cases: list) -> dict:
```

### Parameters

1. **`source_code`** (string): The raw source code you want to execute.
2. **`language_id`** (integer): The Judge0 Language ID corresponding to the programming language of your source code (e.g., `71` for Python 3, `62` for Java, `50` for C).
3. **`test_cases`** (list of dictionaries): A list containing the test cases to evaluate. Each dictionary must have the following structure:
    - `input`: The standard input (`stdin`) to provide to the code during execution.
    - `expected_output`: The expected standard output (`stdout`) to validate against.

### Example

```python
from judge0_runner import run_test_cases
import json

# The code you want to test
source = "print(input())"

# Judge0 language ID for Python 3
lang_id = 71

# The list of test cases
tests = [
    {
        "input": "hello",
        "expected_output": "hello"
    },
    {
        "input": "123",
        "expected_output": "123"
    }
]

# Run the evaluation
results = run_test_cases(source, lang_id, tests)

# Print the results
print(json.dumps(results, indent=2))
```

### Returned Output Format

The function returns a JSON-serializable dictionary containing an overall summary along with the breakdown for each individual test case:

```json
{
  "total": 2,
  "passed": 2,
  "failed": 0,
  "results": [
    {
      "test_case": 1,
      "status": "Accepted",
      "actual_output": "hello",
      "expected_output": "hello",
      "passed": true
    },
    {
      "test_case": 2,
      "status": "Accepted",
      "actual_output": "123",
      "expected_output": "123",
      "passed": true
    }
  ]
}
```

- **`status`**: The descriptive status returned by Judge0 (e.g., `Accepted`, `Wrong Answer`, `Runtime Error`, `Compilation Error`, `Time Limit Exceeded`).
- **`passed`**: `true` if the output perfectly matches the expected output (Judge0 Status `3`), `false` otherwise.
