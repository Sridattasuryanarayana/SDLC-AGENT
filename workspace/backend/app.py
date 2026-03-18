"""
Backend API - User Management System

A REST API for managing users with CRUD operations.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

# In-memory database (replace with real DB in production)
users_db = {}


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users."""
    return jsonify({
        'users': list(users_db.values()),
        'count': len(users_db)
    })


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user by ID."""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(users_db[user_id])


@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user."""
    data = request.json
    
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({'error': 'Name and email are required'}), 400
    
    user_id = str(uuid.uuid4())
    user = {
        'id': user_id,
        'name': data['name'],
        'email': data['email'],
        'created_at': datetime.now().isoformat()
    }
    users_db[user_id] = user
    
    return jsonify(user), 201


@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update an existing user."""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json
    user = users_db[user_id]
    
    if 'name' in data:
        user['name'] = data['name']
    if 'email' in data:
        user['email'] = data['email']
    
    user['updated_at'] = datetime.now().isoformat()
    users_db[user_id] = user
    
    return jsonify(user)


@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user."""
    if user_id not in users_db:
        return jsonify({'error': 'User not found'}), 404
    
    del users_db[user_id]
    return jsonify({'message': 'User deleted successfully'})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
