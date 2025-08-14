import axios from 'axios';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('🌐 API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('✅ API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('❌ API Response Error:', error.response?.status, error.response?.data);
    
    // Handle common errors
    if (error.response?.status === 401) {
      // Unauthorized - could redirect to login
      console.warn('Unauthorized access - user might need to login again');
    } else if (error.response?.status >= 500) {
      console.error('Server error - backend might be down');
    } else if (error.code === 'ECONNABORTED') {
      console.error('Request timeout - slow network or server');
    }
    
    return Promise.reject(error);
  }
);

// ====================== AUTHENTICATION API ======================

export const authAPI = {
  // Register new user (mock implementation - backend doesn't have this yet)
  register: async (userData) => {
    try {
      // TODO: Implement actual registration endpoint in backend
      // For now, simulate registration
      console.log('📝 Registering user:', userData.username);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Return mock user data
      return {
        success: true,
        user: {
          id: Date.now(),
          username: userData.username,
          email: userData.email,
          vehicleType: userData.vehicleType,
          vehicleModel: userData.vehicleModel,
          vehicleData: {
            id: userData.vehicleModel,
            name: userData.vehicleModel.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
          },
          billId: userData.billId,
          createdAt: new Date().toISOString()
        }
      };
    } catch (error) {
      throw new Error('Registration failed: ' + error.message);
    }
  },

  // Login user (mock implementation - backend doesn't have this yet)
  login: async (credentials) => {
    try {
      // TODO: Implement actual login endpoint in backend
      console.log('🔐 Logging in user:', credentials.username);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Return mock user data (in real app, this would come from backend)
      return {
        success: true,
        user: {
          id: Date.now(),
          username: credentials.username,
          email: `${credentials.username}@example.com`,
          vehicleType: 'car', // Would come from user's profile
          vehicleModel: 'tesla_model_3',
          vehicleData: {
            id: 'tesla_model_3',
            name: 'Tesla Model 3'
          },
          lastLogin: new Date().toISOString()
        }
      };
    } catch (error) {
      throw new Error('Login failed: ' + error.message);
    }
  }
};

// ====================== VEHICLE CONTROL API ======================

export const vehicleAPI = {
  // Get current vehicle status
  getStatus: async (userId = 'default_user') => {
    try {
      const response = await api.get('/api/vehicle/status', {
        params: { user_id: userId }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get vehicle status:', error);
      throw error;
    }
  },

  // Execute vehicle command
  executeCommand: async (command, parameters = {}, userId = 'default_user') => {
    try {
      const response = await api.post('/api/vehicle/command', {
        command,
        parameters,
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('Failed to execute vehicle command:', error);
      throw error;
    }
  },

  // Climate control functions
  climate: {
    setTemperature: async (temperature, userId = 'default_user') => {
      return vehicleAPI.executeCommand('set_temperature', { temperature }, userId);
    },

    toggleAC: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('toggle_ac', {}, userId);
    },

    setFanSpeed: async (speed, userId = 'default_user') => {
      return vehicleAPI.executeCommand('set_fan_speed', { speed }, userId);
    }
  },

  // Music control functions
  music: {
    play: async (trackName = null, userId = 'default_user') => {
      return vehicleAPI.executeCommand('play_music', { track_name: trackName }, userId);
    },

    pause: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('pause_music', {}, userId);
    },

    nextTrack: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('next_track', {}, userId);
    },

    previousTrack: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('previous_track', {}, userId);
    },

    setVolume: async (volume, userId = 'default_user') => {
      return vehicleAPI.executeCommand('set_volume', { volume }, userId);
    }
  },

  // Vehicle systems control
  systems: {
    lockDoors: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('lock_doors', {}, userId);
    },

    unlockDoors: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('unlock_doors', {}, userId);
    },

    toggleLights: async (userId = 'default_user') => {
      return vehicleAPI.executeCommand('toggle_lights', {}, userId);
    }
  }
};

// ====================== AI ASSISTANT API ======================

export const assistantAPI = {
  // Send text message to assistant
  sendMessage: async (message, userId = 'default_user') => {
    try {
      const response = await api.post('/api/voice/process', {
        text: message,
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('Failed to send message to assistant:', error);
      throw error;
    }
  },

  // Upload audio for voice processing
  uploadAudio: async (audioBlob, userId = 'default_user') => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.wav');
      formData.append('user_id', userId);

      const response = await api.post('/api/voice/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Failed to upload audio:', error);
      throw error;
    }
  },

  // Get conversation history
  getHistory: async (userId = 'default_user') => {
    try {
      const response = await api.get(`/api/memory/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get conversation history:', error);
      throw error;
    }
  },

  // Get agents status
  getAgentsStatus: async () => {
    try {
      const response = await api.get('/api/agents/status');
      return response.data;
    } catch (error) {
      console.error('Failed to get agents status:', error);
      throw error;
    }
  }
};

// ====================== WEBSOCKET API ======================

class WebSocketAPI {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.messageHandlers = [];
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect(userId = 'default_user') {
    try {
      const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws';
      this.socket = new WebSocket(wsUrl);
      
      this.socket.onopen = () => {
        console.log('🔌 WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Send initial user identification
        this.send({
          type: 'user_connected',
          user_id: userId,
          timestamp: new Date().toISOString()
        });
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 WebSocket message received:', data);
          
          // Notify all message handlers
          this.messageHandlers.forEach(handler => {
            try {
              handler(data);
            } catch (error) {
              console.error('Error in message handler:', error);
            }
          });
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.socket.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        this.isConnected = false;
        
        // Auto-reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          setTimeout(() => this.connect(userId), 2000 * this.reconnectAttempts);
        }
      };

      this.socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  send(data) {
    if (this.isConnected && this.socket) {
      this.socket.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, message not sent:', data);
    }
  }

  addMessageHandler(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isConnected = false;
    }
  }
}

// Create singleton WebSocket instance
export const webSocketAPI = new WebSocketAPI();

// ====================== HEALTH CHECK API ======================

export const healthAPI = {
  check: async () => {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  },

  // Check if backend is available
  isBackendAvailable: async () => {
    try {
      await healthAPI.check();
      return true;
    } catch (error) {
      return false;
    }
  }
};

// ====================== VOICE RECORDING UTILITIES ======================

export const voiceAPI = {
  // Start recording audio
  startRecording: () => {
    return new Promise((resolve, reject) => {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          const mediaRecorder = new MediaRecorder(stream);
          const audioChunks = [];

          mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
          };

          mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            stream.getTracks().forEach(track => track.stop());
            resolve(audioBlob);
          };

          // Return recorder to allow stopping
          resolve({
            recorder: mediaRecorder,
            stop: () => mediaRecorder.stop()
          });

          mediaRecorder.start();
        })
        .catch(reject);
    });
  },

  // Play audio from URL or blob
  playAudio: (audioSource) => {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      
      if (audioSource instanceof Blob) {
        audio.src = URL.createObjectURL(audioSource);
      } else {
        audio.src = audioSource;
      }

      audio.onended = resolve;
      audio.onerror = reject;
      
      audio.play().catch(reject);
    });
  }
};

// ====================== ERROR HANDLING UTILITIES ======================

export const handleAPIError = (error, context = 'API call') => {
  let errorMessage = 'An unexpected error occurred';
  
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const data = error.response.data;
    
    switch (status) {
      case 400:
        errorMessage = data.detail || 'Invalid request';
        break;
      case 401:
        errorMessage = 'Authentication required';
        break;
      case 403:
        errorMessage = 'Access denied';
        break;
      case 404:
        errorMessage = 'Service not found';
        break;
      case 500:
        errorMessage = 'Server error - please try again later';
        break;
      default:
        errorMessage = data.detail || `Server error (${status})`;
    }
  } else if (error.request) {
    // Network error
    errorMessage = 'Unable to connect to server. Please check your internet connection.';
  } else {
    // Other error
    errorMessage = error.message || 'An unexpected error occurred';
  }
  
  console.error(`❌ ${context} failed:`, errorMessage);
  return errorMessage;
};

// Export default API object for convenience
export default {
  auth: authAPI,
  vehicle: vehicleAPI,
  assistant: assistantAPI,
  webSocket: webSocketAPI,
  health: healthAPI,
  voice: voiceAPI,
  handleError: handleAPIError
};