"""
Simple HTTP test for admin panel
"""
import requests
import json

def test_admin_spots_page():
    """Test if admin spots page loads without errors"""
    try:
        # Test the admin spots page
        response = requests.get('http://localhost:5001/admin/spots')
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        
        if response.status_code == 200:
            if len(response.content) > 100:  # Should have substantial content
                print("✅ Admin spots page loads successfully")
                
                # Check if it contains expected elements
                content = response.text
                if "Gerenciar Spots de Surf" in content:
                    print("✅ Page title found")
                else:
                    print("❌ Page title not found")
                    
                if "Total de Spots" in content:
                    print("✅ Statistics section found")
                else:
                    print("❌ Statistics section not found")
                    
                if "badge" in content:
                    print("✅ Badge elements found (likely status badges)")
                else:
                    print("❌ No badge elements found")
                    
                return True
            else:
                print("❌ Page content too short - likely template error")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False

if __name__ == "__main__":
    print("Testing admin spots page with full template...")
    test_admin_spots_page()
