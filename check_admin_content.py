"""
Check what the admin page actually returns
"""
import requests

def check_admin_content():
    """Check what the admin spots page actually returns"""
    try:
        response = requests.get('http://localhost:5001/admin/spots')
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        print("\n--- First 1000 characters of response ---")
        print(response.text[:1000])
        print("\n--- Last 500 characters of response ---")
        print(response.text[-500:])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_admin_content()
