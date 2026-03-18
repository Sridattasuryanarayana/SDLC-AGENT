/**
 * Frontend - User Management Dashboard
 * 
 * React application consuming the Backend API
 */

import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:5001/api';

function App() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  // Fetch users on mount
  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE}/users`);
      const data = await response.json();
      setUsers(data.users || []);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch users');
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (editingId) {
        // Update user
        await fetch(`${API_BASE}/users/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        // Create user
        await fetch(`${API_BASE}/users`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      
      setFormData({ name: '', email: '' });
      setEditingId(null);
      fetchUsers();
    } catch (err) {
      setError('Operation failed');
    }
  };

  const handleEdit = (user) => {
    setFormData({ name: user.name, email: user.email });
    setEditingId(user.id);
  };

  const handleDelete = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await fetch(`${API_BASE}/users/${userId}`, { method: 'DELETE' });
        fetchUsers();
      } catch (err) {
        setError('Delete failed');
      }
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="app">
      <header>
        <h1>User Management Dashboard</h1>
      </header>

      <main>
        {error && <div className="error">{error}</div>}

        <section className="form-section">
          <h2>{editingId ? 'Edit User' : 'Add New User'}</h2>
          <form onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
            <button type="submit">{editingId ? 'Update' : 'Add'} User</button>
            {editingId && (
              <button type="button" onClick={() => {
                setEditingId(null);
                setFormData({ name: '', email: '' });
              }}>
                Cancel
              </button>
            )}
          </form>
        </section>

        <section className="users-section">
          <h2>Users ({users.length})</h2>
          {users.length === 0 ? (
            <p className="empty">No users yet. Add one above!</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.name}</td>
                    <td>{user.email}</td>
                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                    <td>
                      <button onClick={() => handleEdit(user)}>Edit</button>
                      <button onClick={() => handleDelete(user.id)} className="delete">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
