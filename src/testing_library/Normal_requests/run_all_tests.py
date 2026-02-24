import os
import subprocess
import sys

def run_tests():
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # List all files in the directory
    files = os.listdir(current_dir)
    
    # Filter files: .py extension, not this script, not test_portfolio
    test_files = [
        f for f in files 
        if f.endswith('.py') 
        and f != os.path.basename(__file__) 
        and f != 'test_portfolio.py'
    ]
    
    test_files.sort()
    
    print(f"🔍 Found {len(test_files)} tests to run in {current_dir}\n")
    
    passed = []
    failed = []
    
    for test_file in test_files:
        print(f"▶️ Running {test_file}...")
        file_path = os.path.join(current_dir, test_file)
        
        # Run the test file as a separate process
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=False, # Let output flow to stdout so user sees progress
                text=True,
                check=False # Don't raise exception on failure, check return code manually
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file} passed!\n")
                passed.append(test_file)
            else:
                print(f"❌ {test_file} failed with exit code {result.returncode}\n")
                failed.append(test_file)
                
        except Exception as e:
            print(f"❌ Error running {test_file}: {e}\n")
            failed.append(test_file)
            
    print("-" * 50)
    print("📊 Test Summary:")
    print(f"✅ Passed: {len(passed)}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print("\nFailed tests:")
        for f in failed:
            print(f" - {f}")
            
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
