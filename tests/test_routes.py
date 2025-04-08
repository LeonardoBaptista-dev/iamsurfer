import unittest
from app import app, db
from models import User, Post, Comment, Like, Follow, Message

class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Criar usuário de teste
            test_user = User(username='testuser', email='test@example.com')
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_login_page(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
    
    def test_signup_page(self):
        response = self.app.get('/signup')
        self.assertEqual(response.status_code, 200)
    
    def test_login_successful(self):
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
    
    def test_login_failed(self):
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Por favor, verifique suas credenciais', response.data)
    
    def test_logout(self):
        # Login primeiro
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        # Tentativa de logout
        response = self.app.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

class TestMainRoutes(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Criar usuário de teste
            test_user = User(username='testuser', email='test@example.com')
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_profile_page(self):
        # Login primeiro
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        response = self.app.get('/profile/testuser')
        self.assertEqual(response.status_code, 200)
    
    def test_edit_profile(self):
        # Login primeiro
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'password'
        })
        
        response = self.app.post('/profile/edit', data={
            'username': 'testuser',
            'email': 'updated@example.com',
            'bio': 'Test bio',
            'location': 'Test location'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            self.assertEqual(user.email, 'updated@example.com')
            self.assertEqual(user.bio, 'Test bio')
            self.assertEqual(user.location, 'Test location')

if __name__ == '__main__':
    unittest.main() 