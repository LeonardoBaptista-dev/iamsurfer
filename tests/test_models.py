import unittest
from app import app, db
from models import User, Post, Comment, Like, Follow, Message

class TestUserModel(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_password_hashing(self):
        with app.app_context():
            user = User(username='test', email='test@example.com')
            user.set_password('password')
            self.assertFalse(user.check_password('wrongpassword'))
            self.assertTrue(user.check_password('password'))
    
    def test_follow(self):
        with app.app_context():
            user1 = User(username='user1', email='user1@example.com')
            user2 = User(username='user2', email='user2@example.com')
            db.session.add_all([user1, user2])
            db.session.commit()
            
            self.assertFalse(user1.is_following(user2))
            user1.follow(user2)
            self.assertTrue(user1.is_following(user2))
            user1.unfollow(user2)
            self.assertFalse(user1.is_following(user2))
    
    def test_follow_self(self):
        with app.app_context():
            user = User(username='user', email='user@example.com')
            db.session.add(user)
            db.session.commit()
            
            self.assertFalse(user.follow(user))
            self.assertFalse(user.is_following(user))

class TestPostModel(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Criar usuário de teste
            self.user = User(username='testuser', email='test@example.com')
            db.session.add(self.user)
            db.session.commit()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_post_creation(self):
        with app.app_context():
            post = Post(content='Test post content', user_id=self.user.id)
            db.session.add(post)
            db.session.commit()
            
            self.assertIsNotNone(post.id)
            self.assertEqual(post.content, 'Test post content')
            self.assertEqual(post.author, self.user)
    
    def test_comment_creation(self):
        with app.app_context():
            post = Post(content='Test post content', user_id=self.user.id)
            db.session.add(post)
            db.session.commit()
            
            comment = Comment(content='Test comment', post_id=post.id, user_id=self.user.id)
            db.session.add(comment)
            db.session.commit()
            
            self.assertIsNotNone(comment.id)
            self.assertEqual(comment.content, 'Test comment')
            self.assertEqual(comment.author, self.user)
            self.assertEqual(comment.post, post)
    
    def test_like_creation(self):
        with app.app_context():
            post = Post(content='Test post content', user_id=self.user.id)
            db.session.add(post)
            db.session.commit()
            
            like = Like(post_id=post.id, user_id=self.user.id)
            db.session.add(like)
            db.session.commit()
            
            self.assertIsNotNone(like.id)
            self.assertEqual(like.user, self.user)
            self.assertEqual(like.post, post)

if __name__ == '__main__':
    unittest.main() 