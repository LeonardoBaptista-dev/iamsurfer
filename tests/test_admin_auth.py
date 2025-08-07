"""
Test admin functionality with authentication
"""
import requests
import json

def test_admin_with_auth():
    """Test admin functionality by logging in first"""
    session = requests.Session()
    
    try:
        # First, get the login page to check the form
        login_page = session.get('http://localhost:5001/login')
        print(f"Login page status: {login_page.status_code}")
        
        # Attempt to login as admin
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'remember': 'on'
        }
        
        login_response = session.post('http://localhost:5001/login', data=login_data)
        print(f"Login response status: {login_response.status_code}")
        
        # Check if redirected (successful login)
        if login_response.status_code == 200:
            if "login" in login_response.url.lower():
                print("❌ Login failed - still on login page")
                return False
            else:
                print("✅ Login successful - redirected")
        
        # Now try to access admin spots page
        admin_response = session.get('http://localhost:5001/admin/spots')
        print(f"Admin spots status: {admin_response.status_code}")
        print(f"Admin spots content length: {len(admin_response.content)}")
        
        if admin_response.status_code == 200:
            content = admin_response.text
            if "Gerenciar Spots de Surf" in content:
                print("✅ Admin spots page loaded successfully")
                
                # Check for key elements
                checks = [
                    ("Total de Spots", "Statistics section"),
                    ("Pendentes", "Pending count"),
                    ("Aprovados", "Approved count"),
                    ("badge", "Status badges"),
                    ("table", "Spots table"),
                    ("btn-success", "Action buttons")
                ]
                
                for check_text, description in checks:
                    if check_text in content:
                        print(f"✅ {description} found")
                    else:
                        print(f"❌ {description} not found")
                
                return True
            else:
                print("❌ Admin content not found - checking first 500 chars:")
                print(content[:500])
                return False
        else:
            print(f"❌ Admin page error: {admin_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing admin functionality with authentication...")
    test_admin_with_auth()
