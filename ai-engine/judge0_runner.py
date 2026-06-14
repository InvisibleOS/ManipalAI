import requests
import time

def run_test_cases(source_code, language_id, test_cases):
    """
    Submits code to Judge0 for multiple test cases and evaluates the results.
    
    Args:
        source_code (str): The source code to evaluate.
        language_id (int): The Judge0 language ID for the code.
        test_cases (list of dict): List of test cases, each containing 'input' and 'expected_output'.
        
    Returns:
        dict: Summary of the results, including total, passed, failed counts, and per-test-case breakdown.
    """
    base_url = "https://ce.judge0.com/submissions"
    
    results = []
    total = len(test_cases)
    passed_count = 0
    failed_count = 0
    
    for idx, tc in enumerate(test_cases):
        stdin = tc.get('input', '')
        expected_output = tc.get('expected_output', '')
        
        payload = {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": stdin,
            "expected_output": expected_output
        }
        
        try:
            # 1. Submit code
            post_response = requests.post(
                f"{base_url}?base64_encoded=false&wait=false", 
                json=payload
            )
            post_response.raise_for_status()
            token = post_response.json().get('token')
            
            if not token:
                raise ValueError("No token received from Judge0")
                
            # 2. Poll for results
            while True:
                get_response = requests.get(f"{base_url}/{token}?base64_encoded=false")
                get_response.raise_for_status()
                data = get_response.json()
                
                status_id = data.get('status', {}).get('id')
                
                # Status 1: In Queue, Status 2: Processing
                if status_id not in (1, 2):
                    break
                    
                time.sleep(1) # Poll every 1 second
                
            # Process result
            status_desc = data.get('status', {}).get('description', 'Unknown')
            
            # Get actual output
            actual_output = data.get('stdout')
            if actual_output is None:
                actual_output = data.get('compile_output')
            if actual_output is None:
                actual_output = data.get('stderr')
            if actual_output is None:
                actual_output = ""
            
            # Judge0 status_id 3 is 'Accepted'
            passed = (status_id == 3)
            
            if passed:
                passed_count += 1
            else:
                failed_count += 1
                
            results.append({
                "test_case": idx + 1,
                "status": status_desc,
                "actual_output": str(actual_output).strip() if actual_output else "",
                "expected_output": str(expected_output).strip() if expected_output else "",
                "passed": passed
            })
            
        except Exception as e:
            failed_count += 1
            results.append({
                "test_case": idx + 1,
                "status": "Error",
                "actual_output": str(e),
                "expected_output": expected_output,
                "passed": False
            })
            
    summary = {
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "results": results
    }
    
    return summary


