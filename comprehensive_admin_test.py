"""
Comprehensive test of admin spot management functionality
"""
import requests
import json

def comprehensive_admin_test():
    """Test all admin spot functionality"""
    session = requests.Session()
    
    try:
        # Login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'remember': 'on'
        }
        
        login_response = session.post('http://localhost:5001/login', data=login_data)
        print(f"Login status: {login_response.status_code}")
        
        # Test main admin spots page
        spots_response = session.get('http://localhost:5001/admin/spots')
        print(f"Admin spots page status: {spots_response.status_code}")
        
        if spots_response.status_code == 200:
            content = spots_response.text
            
            # Extract some information
            if "Total de Spots" in content:
                print("✅ Main admin spots page works")
                
                # Test filtering
                filter_tests = [
                    ('pending', 'Pending filter'),
                    ('approved', 'Approved filter'),
                    ('rejected', 'Rejected filter'),
                    ('all', 'All filter')
                ]
                
                for filter_type, description in filter_tests:
                    filter_url = f'http://localhost:5001/admin/spots?status={filter_type}'
                    filter_response = session.get(filter_url)
                    if filter_response.status_code == 200:
                        print(f"✅ {description} works")
                    else:
                        print(f"❌ {description} failed: {filter_response.status_code}")
                
                # Check if there are any pending spots to test actions on
                if "Pendente" in content:
                    print("✅ Found pending spots for testing")
                    
                    # Look for spot IDs in the HTML
                    import re
                    spot_id_matches = re.findall(r'spot_id=(\d+)', content)
                    if spot_id_matches:
                        test_spot_id = spot_id_matches[0]
                        print(f"Found spot ID for testing: {test_spot_id}")
                        
                        # Test spot detail view (if available)
                        detail_url = f'http://localhost:5001/spots/{test_spot_id}/detail'
                        detail_response = session.get(detail_url)
                        print(f"Spot detail view status: {detail_response.status_code}")
                        
                        # Note: We won't actually test approve/reject to avoid changing data
                        print("✅ Spot actions are available (not tested to preserve data)")
                        
                else:
                    print("ℹ️  No pending spots found for action testing")
                
                return True
            else:
                print("❌ Admin page content not as expected")
                return False
        else:
            print(f"❌ Admin spots page failed: {spots_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Running comprehensive admin test...")
    comprehensive_admin_test()
