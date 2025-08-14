import React, { useState, useEffect } from 'react';
import LandingPage from './LandingPage';
import Dashboard from './Dashboard';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Verify user authentication with backend
  const verifyUserAuth = async (userData) => {
    try {
      // Test if user can access protected endpoint
      const response = await fetch('http://localhost:8000/api/vehicle/status?user_id=' + userData.username);
      
      if (response.status === 401) {
        console.log('❌ Stored user is not authenticated on backend');
        return false;
      }
      
      if (response.ok) {
        console.log('✅ User authentication verified');
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('❌ Auth verification failed:', error);
      return false;
    }
  };

  // Check if user is already logged in on app start
  useEffect(() => {
    const checkExistingAuth = async () => {
      const savedUser = localStorage.getItem('vehicleAssistantUser');
      if (savedUser) {
        try {
          const userData = JSON.parse(savedUser);
          
          // ✅ VERIFY WITH BACKEND
          const isValid = await verifyUserAuth(userData);
          
          if (isValid) {
            setCurrentUser(userData);
            setIsLoggedIn(true);
            console.log('✅ Restored valid user session');
          } else {
            console.log('❌ Stored user session is invalid - clearing');
            localStorage.removeItem('vehicleAssistantUser');
          }
        } catch (error) {
          console.error('Error loading saved user:', error);
          localStorage.removeItem('vehicleAssistantUser');
        }
      }
      setLoading(false);
    };

    checkExistingAuth();
  }, []);

  // Handle successful login
  const handleLogin = (userData) => {
    setCurrentUser(userData);
    setIsLoggedIn(true);
    localStorage.setItem('vehicleAssistantUser', JSON.stringify(userData));
    console.log('✅ User logged in:', userData.username);
  };

  // Handle logout
  const handleLogout = () => {
    setCurrentUser(null);
    setIsLoggedIn(false);
    localStorage.removeItem('vehicleAssistantUser');
    console.log('✅ User logged out');
  };

  // Update user data
  const updateUser = (updatedUserData) => {
    setCurrentUser(updatedUserData);
    localStorage.setItem('vehicleAssistantUser', JSON.stringify(updatedUserData));
  };

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>🚗 Loading AI Vehicle Assistant...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      {!isLoggedIn ? (
        <LandingPage onLogin={handleLogin} />
      ) : (
        <Dashboard 
          user={currentUser} 
          onLogout={handleLogout}
          onUpdateUser={updateUser}
        />
      )}
    </div>
  );
}

export default App;