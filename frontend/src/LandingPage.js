import React, { useState } from 'react';

// Vehicle data from backend database
const VEHICLE_DATA = {
  car: [
    { id: 'tesla_model_3', name: 'Tesla Model 3' },
    { id: 'bmw_3_series', name: 'BMW 3 Series' },
    { id: 'honda_civic', name: 'Honda Civic' }
  ],
  truck: [
    { id: 'ford_f150', name: 'Ford F-150' },
    { id: 'ram_1500', name: 'RAM 1500' },
    { id: 'toyota_tacoma', name: 'Toyota Tacoma' }
  ]
};

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function LandingPage({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Form data
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    vehicleType: 'car',
    vehicleModel: '',
    billId: ''
  });

  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
      // Reset vehicle model when vehicle type changes
      ...(name === 'vehicleType' ? { vehicleModel: '' } : {})
    }));
    setError(''); // Clear error when user types
  };

  // Form validation
  const validateForm = () => {
    if (!formData.username.trim()) {
      setError('Username is required');
      return false;
    }
    
    if (formData.username.trim().length < 3) {
      setError('Username must be at least 3 characters long');
      return false;
    }
    
    if (!isLogin && !formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    
    if (!isLogin && !formData.email.includes('@')) {
      setError('Please enter a valid email');
      return false;
    }
    
    if (!formData.password) {
      setError('Password is required');
      return false;
    }
    
    if (!isLogin && formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return false;
    }
    
    if (!isLogin && !formData.vehicleModel) {
      setError('Please select a vehicle model');
      return false;
    }
    
    return true;
  };

  // Call real backend authentication API
  const authenticateUser = async (endpoint, requestData) => {
    try {
      console.log(`🔐 Calling ${endpoint} with data:`, { ...requestData, password: '***' });
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      if (!result.success) {
        throw new Error(result.message || 'Authentication failed');
      }

      return result;
    } catch (error) {
      console.error(`❌ ${endpoint} failed:`, error);
      
      // Handle different types of errors
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        throw new Error('Unable to connect to server. Please ensure the backend is running.');
      } else if (error.message.includes('HTTP 400')) {
        throw new Error('Invalid input data. Please check your information.');
      } else if (error.message.includes('HTTP 401')) {
        throw new Error('Invalid username or password.');
      } else if (error.message.includes('HTTP 500')) {
        throw new Error('Server error. Please try again later.');
      } else {
        throw error;
      }
    }
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    setError('');
    
    try {
      let result;
      
      if (isLogin) {
        // Login user
        result = await authenticateUser('/api/auth/login', {
          username: formData.username.trim(),
          password: formData.password
        });
      } else {
        // Register user
        const vehicleData = VEHICLE_DATA[formData.vehicleType].find(v => v.id === formData.vehicleModel);
        
        result = await authenticateUser('/api/auth/register', {
          username: formData.username.trim(),
          email: formData.email.trim(),
          password: formData.password,
          vehicleType: formData.vehicleType,
          vehicleModel: formData.vehicleModel,
          billId: formData.billId.trim() || null
        });
      }

      // Success - call parent login handler with user data
      if (result.success && result.user) {
        console.log('✅ Authentication successful:', result.user.username);
        onLogin(result.user);
      } else {
        throw new Error('Authentication response missing user data');
      }
      
    } catch (err) {
      console.error('Authentication error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Toggle between login and register
  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setFormData({
      username: '',
      email: '',
      password: '',
      vehicleType: 'car',
      vehicleModel: '',
      billId: ''
    });
  };

  // Check backend connectivity
  const checkBackendHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return response.ok;
    } catch {
      return false;
    }
  };

  // Show backend status helper
  const showBackendStatus = async () => {
    const isConnected = await checkBackendHealth();
    if (!isConnected) {
      setError('Backend server is not responding. Please ensure the backend is running on http://localhost:8000');
    }
  };

  return (
    <div className="landing-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>🚗 AI Assistant</h1>
          <p>{isLogin ? 'Welcome back!' : 'Create your account'}</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {/* Username */}
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              className="form-input"
              value={formData.username}
              onChange={handleInputChange}
              placeholder="Enter your username (min 3 characters)"
              required
              minLength={3}
            />
          </div>

          {/* Email (Register only) */}
          {!isLogin && (
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                className="form-input"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="Enter your email"
                required
              />
            </div>
          )}

          {/* Password */}
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              className="form-input"
              value={formData.password}
              onChange={handleInputChange}
              placeholder={isLogin ? "Enter your password" : "Enter password (min 6 characters)"}
              required
              minLength={isLogin ? 1 : 6}
            />
          </div>

          {/* Vehicle Type (Register only) */}
          {!isLogin && (
            <div className="form-group">
              <label htmlFor="vehicleType">Vehicle Type</label>
              <select
                id="vehicleType"
                name="vehicleType"
                className="form-select"
                value={formData.vehicleType}
                onChange={handleInputChange}
                required
              >
                <option value="car">🚗 Car</option>
                <option value="truck">🚛 Truck</option>
              </select>
            </div>
          )}

          {/* Vehicle Model (Register only) */}
          {!isLogin && (
            <div className="form-group">
              <label htmlFor="vehicleModel">Vehicle Model</label>
              <select
                id="vehicleModel"
                name="vehicleModel"
                className="form-select"
                value={formData.vehicleModel}
                onChange={handleInputChange}
                required
              >
                <option value="">Select your vehicle model</option>
                {VEHICLE_DATA[formData.vehicleType].map(vehicle => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Bill ID (Register only, optional) */}
          {!isLogin && (
            <div className="form-group">
              <label htmlFor="billId">Bill ID / Verification ID (Optional)</label>
              <input
                type="text"
                id="billId"
                name="billId"
                className="form-input"
                value={formData.billId}
                onChange={handleInputChange}
                placeholder="Enter bill or verification ID"
              />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="error-message">
              {error}
              {error.includes('backend') && (
                <div style={{ marginTop: '10px', fontSize: '0.8rem' }}>
                  <button type="button" onClick={showBackendStatus} style={{ 
                    background: 'none', border: 'none', color: '#667eea', textDecoration: 'underline', cursor: 'pointer' 
                  }}>
                    Check backend status
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Submit Button */}
          <button 
            type="submit" 
            className="auth-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" style={{width: '20px', height: '20px', marginRight: '10px'}}></span>
                {isLogin ? 'Signing In...' : 'Creating Account...'}
              </>
            ) : (
              isLogin ? 'Sign In' : 'Create Account'
            )}
          </button>
        </form>

        {/* Switch between login/register */}
        <div className="auth-switch">
          {isLogin ? (
            <>
              Don't have an account?{' '}
              <button type="button" onClick={toggleMode}>
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button type="button" onClick={toggleMode}>
                Sign in
              </button>
            </>
          )}
        </div>

        {/* Backend connection status */}
        <div style={{ 
          textAlign: 'center', 
          marginTop: '15px', 
          fontSize: '0.8rem', 
          color: '#718096' 
        }}>
          Server: {API_BASE_URL}
        </div>
      </div>
    </div>
  );
}

export default LandingPage;