import subprocess

try:
    result = subprocess.run(['venv\\Scripts\\flask', 'db', 'upgrade'], capture_output=True, text=True)
    with open('migration_error.txt', 'w', encoding='utf-8') as f:
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
    print("Done writing to migration_error.txt")
except Exception as e:
    print(f"Error: {e}")
