import React, { useState, useEffect, useRef } from 'react';
import { 
  Car, 
  MessageCircle, 
  History, 
  User, 
  LogOut, 
  Mic, 
  MicOff, 
  Send,
  Thermometer,
  Volume2,
  Lock,
  Unlock,
  Lightbulb,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  ChevronDown,
  ChevronRight,
  Clock,
  Trash2
} from 'lucide-react';

function Dashboard({ user, onLogout, onUpdateUser }) {
  const [activeTab, setActiveTab] = useState('vehicle');
  const [showProfile, setShowProfile] = useState(false);
  const [vehicleState, setVehicleState] = useState({
    climate: { temperature: 22, ac_on: false, fan_speed: 2 },
    music: { playing: false, volume: 50, current_track: 'No track' },
    vehicle: { doors_locked: false, lights_on: false }
  });
  const [userLocation, setUserLocation] = useState(null);
  
  // Assistant state
  const [assistantMessage, setAssistantMessage] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [chatHistory, setChatHistory] = useState([]); // Current session
  const [isLoading, setIsLoading] = useState(false);

  // 📚 NEW: Persistent History State
  const [persistentHistory, setPersistentHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedSessions, setExpandedSessions] = useState({});
  const [historyError, setHistoryError] = useState('');

  // 🎤 Voice Integration State
  const [speechRecognition, setSpeechRecognition] = useState(null);
  const [speechSynthesis, setSpeechSynthesis] = useState(null);
  const [isVoiceSupported, setIsVoiceSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [lastInputMethod, setLastInputMethod] = useState('text');
  const recognitionRef = useRef(null);
  const currentLocationRef = useRef(null);

  // 🔊 Smart text extraction for speech - only reads key information
  const extractKeyInfoForSpeech = (text) => {
    if (!text || text.trim().length === 0) return '';
    
    const cleanText = text.toLowerCase();
    
    // 1. LOCATION QUERIES - Just say the location
    if (cleanText.includes('your current location') || cleanText.includes('you are in') || cleanText.includes('you are at')) {
      const locationMatch = text.match(/(?:you are (?:in|at)|current location[:\s]+)([^.]+)/i);
      if (locationMatch) {
        return `You are in ${locationMatch[1].trim()}`;
      }
    }
    
    // 2. PLACE SEARCH - Just count and mention first few places
    if (cleanText.includes('found') && cleanText.includes('near')) {
      const foundMatch = text.match(/Found (\d+) ([^(]+?)(?:\s*\(|near you)/i);
      if (foundMatch) {
        const count = foundMatch[1];
        const placeType = foundMatch[2].trim();
        
        // Extract place names from the response
        const placeMatches = text.match(/📍\s*([^⭐(]+?)(?:\s*\(|\s*⭐|$)/g);
        if (placeMatches && placeMatches.length > 0) {
          const places = placeMatches.map(match => 
            match.replace(/📍\s*/, '').replace(/\s*\($/, '').trim()
          ).slice(0, 3); // Only first 3
          
          let response = `I found ${count} ${placeType} near you. `;
          if (places.length > 0) {
            if (places.length === 1) {
              response += `Including ${places[0]}.`;
            } else if (places.length === 2) {
              response += `Including ${places[0]} and ${places[1]}.`;
            } else {
              response += `Including ${places[0]}, ${places[1]}, and ${places[2]}`;
              if (parseInt(count) > 3) {
                response += `, plus ${parseInt(count) - 3} more options.`;
              } else {
                response += `.`;
              }
            }
          }
          return response;
        }
      }
    }
    
    // 3. NAVIGATION/DIRECTIONS - Just destination and key info
    if (cleanText.includes('distance:') && cleanText.includes('duration:')) {
      const lines = text.split('\n').filter(line => line.trim());
      const distanceLine = lines.find(line => line.includes('Distance:'));
      const durationLine = lines.find(line => line.includes('Duration:'));
      const destinationLine = lines.find(line => line.includes('📍') && !line.includes('Distance') && !line.includes('Duration'));
      
      let response = '';
      if (destinationLine) {
        const destination = destinationLine.replace(/📍/g, '').trim();
        response = `Navigation to ${destination}. `;
      }
      
      if (distanceLine) {
        response += distanceLine.replace(/📏/g, '').trim() + '. ';
      }
      
      if (durationLine) {
        response += durationLine.replace(/⏱️/g, '').trim() + '.';
      }
      
      return response || 'Navigation route calculated.';
    }
    
    // 4. VEHICLE CONTROLS - Just confirm the action
    if (cleanText.includes('temperature') && (cleanText.includes('set') || cleanText.includes('adjust'))) {
      return 'Temperature adjusted.';
    }
    
    if (cleanText.includes('air conditioning') || cleanText.includes('ac')) {
      if (cleanText.includes('turned on') || cleanText.includes('enabled')) {
        return 'Air conditioning turned on.';
      } else if (cleanText.includes('turned off') || cleanText.includes('disabled')) {
        return 'Air conditioning turned off.';
      }
    }
    
    if (cleanText.includes('music') || cleanText.includes('song')) {
      if (cleanText.includes('playing') || cleanText.includes('started')) {
        return 'Music started.';
      } else if (cleanText.includes('paused') || cleanText.includes('stopped')) {
        return 'Music paused.';
      } else if (cleanText.includes('volume')) {
        return 'Volume adjusted.';
      }
    }
    
    if (cleanText.includes('doors') || cleanText.includes('lock')) {
      if (cleanText.includes('locked')) {
        return 'Doors locked.';
      } else if (cleanText.includes('unlocked')) {
        return 'Doors unlocked.';
      }
    }
    
    if (cleanText.includes('lights')) {
      if (cleanText.includes('turned on') || cleanText.includes('enabled')) {
        return 'Lights turned on.';
      } else if (cleanText.includes('turned off') || cleanText.includes('disabled')) {
        return 'Lights turned off.';
      }
    }
    
    // 5. WEATHER - Just the key info
    if (cleanText.includes('weather') || cleanText.includes('temperature')) {
      const lines = text.split('\n').filter(line => line.trim());
      const tempLine = lines.find(line => line.includes('°') || line.includes('degrees'));
      const conditionLine = lines.find(line => line.includes('Condition:') || line.includes('Weather:'));
      
      let response = '';
      if (tempLine) {
        response = tempLine.replace(/🌤️|Temperature:|🌡️/g, '').trim();
      }
      if (conditionLine) {
        const condition = conditionLine.replace(/Condition:|Weather:|🌤️/g, '').trim();
        response += response ? ` with ${condition}` : condition;
      }
      
      return response || 'Weather information retrieved.';
    }
    
    // 6. ERROR MESSAGES - Just the main error
    if (cleanText.includes('sorry') || cleanText.includes('error') || cleanText.includes('issue')) {
      return 'Sorry, I encountered an issue. Please try again.';
    }
    
    // 7. GENERAL RESPONSES - Take only the first sentence or two
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    if (sentences.length > 0) {
      let response = sentences[0].trim();
      
      // Remove emojis for speech
      response = response.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '');
      
      // If it's a very short response, add the second sentence if available
      if (response.length < 50 && sentences.length > 1) {
        const secondSentence = sentences[1].replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim();
        response += '. ' + secondSentence;
      }
      
      return response;
    }
    
    return 'Task completed.';
  };

  // 🎤 Initialize voice capabilities
  useEffect(() => {
    // Initialize Speech Recognition
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const speechSynthesisObj = window.speechSynthesis;
      
      if (SpeechRecognition && speechSynthesisObj) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        setSpeechRecognition(recognition);
        setSpeechSynthesis(speechSynthesisObj);
        setIsVoiceSupported(true);
        recognitionRef.current = recognition;
        
        console.log('✅ Voice capabilities initialized successfully');
      } else {
        console.warn('⚠️ Voice recognition not supported in this browser');
        setIsVoiceSupported(false);
      }
    }
  }, []);

  // 🌍 Get user location on mount
  useEffect(() => {
    const getUserLocation = () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const location = {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              accuracy: position.coords.accuracy,
              fallback: false
            };
            console.log('📍 Real location obtained:', location);
            setUserLocation(location);
            currentLocationRef.current = location;
          },
          (error) => {
            console.warn('⚠️ Location access denied, using fallback location');
            const fallbackLocation = {
              latitude: 17.4065,
              longitude: 78.4772,
              accuracy: null,
              fallback: true
            };
            setUserLocation(fallbackLocation);
            currentLocationRef.current = fallbackLocation;
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes
          }
        );
      } else {
        console.warn('Geolocation not supported');
        const fallbackLocation = {
          latitude: 17.4065,
          longitude: 78.4772,
          fallback: true
        };
        setUserLocation(fallbackLocation);
        currentLocationRef.current = fallbackLocation;
      }
    };

    getUserLocation();
  }, []);

  // 📚 NEW: Load persistent chat history on mount
  useEffect(() => {
    const loadPersistentHistory = async () => {
      if (activeTab === 'history') {
        setHistoryLoading(true);
        setHistoryError('');
        
        try {
          const response = await fetch(`http://localhost:8000/api/memory/${user.username}`);
          
          if (response.status === 401) {
            console.error('❌ Authentication failed - logging out user');
            alert('Your session has expired. Please login again.');
            onLogout();
            return;
          }
          
          if (response.ok) {
            const data = await response.json();
            console.log('📚 Raw backend data:', data); // Debug log
            
            if (data.recent_interactions && Array.isArray(data.recent_interactions)) {
              console.log('📚 Processing interactions:', data.recent_interactions); // Debug log
              
              // Group interactions by sessions (by date)
              const groupedSessions = groupInteractionsBySessions(data.recent_interactions);
              setPersistentHistory(groupedSessions);
              console.log('📚 Loaded persistent history:', groupedSessions.length, 'sessions');
              console.log('📚 First session sample:', groupedSessions[0]); // Debug log
            } else {
              console.log('📚 No recent_interactions found in response');
              setPersistentHistory([]);
            }
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        } catch (error) {
          console.error('Failed to load chat history:', error);
          setHistoryError(`Failed to load chat history: ${error.message}`);
          setPersistentHistory([]);
        } finally {
          setHistoryLoading(false);
        }
      }
    };

    loadPersistentHistory();
  }, [activeTab, user.username, onLogout]);

  // 📚 Group interactions by sessions (by date and conversation gaps)
  const groupInteractionsBySessions = (interactions) => {
    if (!interactions || interactions.length === 0) return [];
    
    console.log('🔄 Grouping interactions:', interactions.length, 'total interactions');
    
    const sessions = [];
    let currentSession = null;
    
    // Sort interactions by timestamp
    const sortedInteractions = [...interactions].sort((a, b) => 
      new Date(a.timestamp) - new Date(b.timestamp)
    );
    
    for (let i = 0; i < sortedInteractions.length; i++) {
      const interaction = sortedInteractions[i];
      const interactionDate = new Date(interaction.timestamp);
      const dateString = interactionDate.toDateString();
      
      console.log(`🔄 Processing interaction ${i}:`, {
        timestamp: interaction.timestamp,
        user_input: interaction.user_input?.substring(0, 50),
        agent_response: interaction.agent_response?.substring(0, 50),
        agent_id: interaction.agent_id
      });
      
      // Start new session if:
      // 1. No current session
      // 2. Different date
      // 3. More than 30 minutes gap from last interaction
      if (!currentSession || 
          currentSession.date !== dateString ||
          (interactionDate - currentSession.lastInteraction) > 30 * 60 * 1000) {
        
        currentSession = {
          id: `session_${Date.now()}_${Math.random()}_${i}`,
          date: dateString,
          displayDate: formatSessionDate(interactionDate),
          startTime: interactionDate,
          lastInteraction: interactionDate,
          interactions: [],
          messageCount: 0
        };
        sessions.push(currentSession);
        console.log('📅 Created new session:', currentSession.displayDate);
      }
      
      // 🔧 FIXED: Each backend interaction contains BOTH user input AND agent response
      // Add user message first
      if (interaction.user_input && interaction.user_input.trim()) {
        currentSession.interactions.push({
          type: 'user',
          content: interaction.user_input,
          timestamp: interactionDate,
          agent_id: interaction.agent_id,
          actions_taken: interaction.actions_taken || []
        });
        currentSession.messageCount++;
        console.log('👤 Added user message:', interaction.user_input.substring(0, 30));
      }
      
      // Then add assistant response
      if (interaction.agent_response && interaction.agent_response.trim()) {
        currentSession.interactions.push({
          type: 'assistant',
          content: interaction.agent_response,
          timestamp: interactionDate,
          agent_id: interaction.agent_id,
          actions_taken: interaction.actions_taken || []
        });
        currentSession.messageCount++;
        console.log('🤖 Added assistant response:', interaction.agent_response.substring(0, 30));
      }
      
      currentSession.lastInteraction = interactionDate;
    }
    
    console.log('✅ Grouped into', sessions.length, 'sessions');
    sessions.forEach((session, i) => {
      console.log(`Session ${i}: ${session.displayDate} - ${session.messageCount} messages`);
    });
    
    // Sort sessions by most recent first
    return sessions.reverse();
  };

  // 📅 Format session date for display
  const formatSessionDate = (date) => {
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      });
    }
  };

  // 📚 Toggle session expansion
  const toggleSessionExpansion = (sessionId) => {
    setExpandedSessions(prev => ({
      ...prev,
      [sessionId]: !prev[sessionId]
    }));
  };

  // 📚 Clear all history
  const clearAllHistory = () => {
    if (window.confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
      setPersistentHistory([]);
      setChatHistory([]);
      // TODO: Call backend API to clear history if needed
      console.log('🗑️ History cleared by user');
    }
  };

  // ====================== AUTHENTICATION HELPER ======================
  const checkAuthAndLogout = (response) => {
    if (response.status === 401) {
      console.error('❌ Authentication failed - logging out user');
      alert('Your session has expired. Please login again.');
      onLogout();
      return true; // User was logged out
    }
    return false; // Continue normally
  };

  // Load vehicle state on mount
  useEffect(() => {
    const loadVehicleState = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/vehicle/status?user_id=${user.username}`);
        if (response.ok) {
          const data = await response.json();
          setVehicleState({
            climate: data.climate || { temperature: 22, ac_on: false, fan_speed: 2 },
            music: data.music || { playing: false, volume: 50, current_track: 'No track' },
            vehicle: data.vehicle || { doors_locked: false, lights_on: false }
          });
        } else if (response.status === 401) {
          console.error('❌ Authentication failed - logging out user');
          alert('Your session has expired. Please login again.');
          onLogout();
        }
      } catch (error) {
        console.error('Failed to load vehicle state:', error);
      }
    };
    
    loadVehicleState();
  }, [user, onLogout]);

  // Handle navigation
  const handleNavClick = (tab) => {
    setActiveTab(tab);
    setShowProfile(false);
  };

  // Handle profile toggle
  const handleProfileToggle = () => {
    setShowProfile(!showProfile);
  };

  // 🎤 Voice Functions
  const startVoiceRecognition = () => {
    if (!isVoiceSupported || !speechRecognition) {
      alert('Voice recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (isListening) {
      stopVoiceRecognition();
      return;
    }

    console.log('🎤 Starting voice recognition...');
    setIsListening(true);
    setLastInputMethod('voice');

    recognitionRef.current.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log('🎤 Voice input received:', transcript);
      
      // Process voice command immediately
      handleSendMessage(transcript, 'voice', currentLocationRef.current);
    };

    recognitionRef.current.onend = () => {
      console.log('🎤 Voice recognition ended');
      setIsListening(false);
    };

    recognitionRef.current.onerror = (event) => {
      console.error('🎤 Voice recognition error:', event.error);
      setIsListening(false);
      
      if (event.error === 'not-allowed') {
        alert('Microphone access denied. Please allow microphone access and try again.');
      } else if (event.error === 'no-speech') {
        console.log('🎤 No speech detected');
      } else {
        alert(`Voice recognition error: ${event.error}`);
      }
    };

    recognitionRef.current.start();
  };

  const stopVoiceRecognition = () => {
    if (recognitionRef.current && isListening) {
      console.log('🛑 Stopping voice recognition...');
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  const speakText = (text) => {
    if (!speechSynthesis || isSpeaking) return;
    
    // Extract only key information for speech
    const speechText = extractKeyInfoForSpeech(text);
    
    if (!speechText.trim()) {
      console.log('🔇 No key information to speak');
      return;
    }
    
    console.log('🔊 Original response:', text.substring(0, 100) + '...');
    console.log('🔊 Speaking key info:', speechText);
    
    setIsSpeaking(true);
    
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;
    
    utterance.onend = () => {
      console.log('🔊 Speech finished');
      setIsSpeaking(false);
    };
    
    utterance.onerror = (event) => {
      console.error('🔊 Speech error:', event.error);
      setIsSpeaking(false);
    };
    
    speechSynthesis.speak(utterance);
  };

  // ====================== ASSISTANT FUNCTIONS - FIXED FOR VOICE ======================
  
  // 🔧 UNIFIED: Single function to handle all message sending (voice and text)
  const handleSendMessage = async (message = assistantMessage, inputMethod = 'text', capturedLocation = null) => {
    if (!message.trim()) return;

    setIsLoading(true);
    const userMessage = { 
      type: 'user', 
      content: message, 
      timestamp: new Date(),
      inputMethod: inputMethod
    };
    setChatHistory(prev => [...prev, userMessage]);
    
    // Clear text input only if it's a text message
    if (inputMethod === 'text') {
      setAssistantMessage('');
    }

    try {
      // Prepare request body with location data
      const requestBody = {
        text: message,
        user_id: user.username
      };

      // Use captured location for voice or current location for text
      const locationToUse = capturedLocation || (userLocation ? {
        latitude: userLocation.latitude,
        longitude: userLocation.longitude,
        is_fallback: userLocation.fallback || false
      } : null);

      if (locationToUse) {
        requestBody.user_location = locationToUse;
        console.log(`🌍 ${inputMethod.toUpperCase()}: Sending location data:`, locationToUse);
      } else {
        console.log(`⚠️ ${inputMethod.toUpperCase()}: No location available to send`);
      }

      const response = await fetch('http://localhost:8000/api/voice/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        const result = await response.json();
        
        console.log(`🔍 ${inputMethod.toUpperCase()} Command Response:`, result);
        
        const botResponse = {
          type: 'assistant',
          content: result.response,
          timestamp: new Date(),
          actions: result.actions_taken || [],
          vehicleState: result.vehicle_state || {},
          shouldSpeak: inputMethod === 'voice'
        };
        
        setChatHistory(prev => [...prev, botResponse]);
        
        // Speak response only for voice commands
        if (inputMethod === 'voice' && speechSynthesis) {
          console.log('🔊 Speaking voice response:', result.response);
          speakText(result.response);
        }
        
        // Update dashboard state
        if (result.vehicle_state && Object.keys(result.vehicle_state).length > 0) {
          console.log(`🔄 Updating dashboard from ${inputMethod} command...`);
          
          let actualVehicleState = result.vehicle_state;
          if (result.vehicle_state.vehicle_state) {
            actualVehicleState = result.vehicle_state.vehicle_state;
          }
          
          setVehicleState(prev => {
            const newState = { ...prev };
            let hasUpdates = false;
            
            if (actualVehicleState.climate) {
              newState.climate = { ...prev.climate, ...actualVehicleState.climate };
              hasUpdates = true;
            }
            
            if (actualVehicleState.music) {
              newState.music = { ...prev.music, ...actualVehicleState.music };
              hasUpdates = true;
            }
            
            if (actualVehicleState.vehicle) {
              newState.vehicle = { ...prev.vehicle, ...actualVehicleState.vehicle };
              hasUpdates = true;
            }
            
            if (hasUpdates) {
              console.log(`✅ Dashboard updated from ${inputMethod} command`);
            }
            
            return newState;
          });
        }
      } else {
        throw new Error('Failed to get response from assistant');
      }
    } catch (error) {
      console.error(`${inputMethod} command failed:`, error);
      const errorResponse = {
        type: 'assistant',
        content: `Sorry, I encountered an issue processing your ${inputMethod} command. Please try again.`,
        timestamp: new Date()
      };
      setChatHistory(prev => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
      setLastInputMethod('text');
    }
  };

  // ====================== VEHICLE CONTROL FUNCTIONS ======================
  
  const handleTemperatureChange = async (increment) => {
    try {
      const newTemp = vehicleState.climate.temperature + increment;
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'set_temperature',
          parameters: { temperature: newTemp },
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        setVehicleState(prev => ({
          ...prev,
          climate: { ...prev.climate, temperature: newTemp }
        }));
      }
    } catch (error) {
      console.error('Failed to update temperature:', error);
    }
  };

  const handleACToggle = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'toggle_ac',
          parameters: {},
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        const newACState = !vehicleState.climate.ac_on;
        setVehicleState(prev => ({
          ...prev,
          climate: { ...prev.climate, ac_on: newACState }
        }));
      }
    } catch (error) {
      console.error('Failed to toggle AC:', error);
    }
  };

  const handleMusicToggle = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: vehicleState.music.playing ? 'pause_music' : 'play_music',
          parameters: {},
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        const newPlayingState = !vehicleState.music.playing;
        setVehicleState(prev => ({
          ...prev,
          music: { ...prev.music, playing: newPlayingState }
        }));
      }
    } catch (error) {
      console.error('Failed to toggle music:', error);
    }
  };

  const handleVolumeChange = async (increment) => {
    try {
      const newVolume = Math.max(0, Math.min(100, vehicleState.music.volume + increment));
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'set_volume',
          parameters: { volume: newVolume },
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        setVehicleState(prev => ({
          ...prev,
          music: { ...prev.music, volume: newVolume }
        }));
      }
    } catch (error) {
      console.error('Failed to update volume:', error);
    }
  };

  const handleDoorsToggle = async () => {
    try {
      const command = vehicleState.vehicle.doors_locked ? 'unlock_doors' : 'lock_doors';
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command,
          parameters: {},
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        const newLockState = !vehicleState.vehicle.doors_locked;
        setVehicleState(prev => ({
          ...prev,
          vehicle: { ...prev.vehicle, doors_locked: newLockState }
        }));
      }
    } catch (error) {
      console.error('Failed to toggle doors:', error);
    }
  };

  const handleLightsToggle = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/vehicle/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: 'toggle_lights',
          parameters: {},
          user_id: user.username
        })
      });
      
      if (checkAuthAndLogout(response)) return;
      
      if (response.ok) {
        const newLightsState = !vehicleState.vehicle.lights_on;
        setVehicleState(prev => ({
          ...prev,
          vehicle: { ...prev.vehicle, lights_on: newLightsState }
        }));
      }
    } catch (error) {
      console.error('Failed to toggle lights:', error);
    }
  };

  // ====================== RESPONSE FORMATTING FUNCTIONS ======================
  
  // 🔧 FIXED: Enhanced place search response parsing
  const formatPlaceSearchResponse = (content) => {
    // Parse place search response
    const lines = content.split('\n').filter(line => line.trim());
    const headerLine = lines[0];
    
    // Extract search info
    const foundMatch = headerLine.match(/Found (\d+) ([^(]+?)(?:\s*\(|near you)/i);
    if (!foundMatch) {
      return formatGeneralResponse(content);
    }
    
    const count = foundMatch[1];
    const placeType = foundMatch[2].trim();
    
    // 🔧 FIXED: Parse numbered list entries (1. 📍 Hotel Name...)
    const places = [];
    
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Look for numbered entries (1., 2., 3., etc.)
      const numberedMatch = line.match(/^(\d+)\.\s*(.+)/);
      if (numberedMatch) {
        const entryContent = numberedMatch[2]; // Content after "1. "
        console.log('🔧 Parsing numbered entry:', entryContent); // Debug log
        
        let name = '';
        let distance = '';
        let rating = '';
        let status = '';
        let address = '';
        
        // Remove the pin emoji first if present
        let cleanLine = entryContent.replace('📍', '').trim();
        
        // Extract distance (text in parentheses)
        const distanceMatch = cleanLine.match(/\(([^)]+)\)/);
        if (distanceMatch) {
          distance = distanceMatch[1];
          // Remove the distance part to get the name
          name = cleanLine.substring(0, cleanLine.indexOf('(')).trim();
          // Get everything after the distance
          const afterDistance = cleanLine.substring(cleanLine.indexOf(')') + 1).trim();
          
          // Extract rating (⭐ X.X/X or ⭐ X.X)
          const ratingMatch = afterDistance.match(/⭐\s*(\d+\.?\d*(?:\/\d+)?)/);
          if (ratingMatch) {
            rating = ratingMatch[1];
          }
          
          // Extract status (🟢 Open or 🔴 Closed)
          if (afterDistance.includes('🟢')) {
            status = 'Open';
          } else if (afterDistance.includes('🔴')) {
            status = 'Closed';
          }
          
          // Extract address (after 📮)
          const addressMatch = afterDistance.match(/📮\s*(.+)/);
          if (addressMatch) {
            address = addressMatch[1].trim();
          }
        } else {
          // Simpler format without parentheses - extract what we can
          const parts = cleanLine.split('⭐');
          name = parts[0].trim();
          
          if (parts.length > 1) {
            const ratingPart = parts[1].trim();
            const ratingMatch = ratingPart.match(/(\d+\.?\d*(?:\/\d+)?)/);
            if (ratingMatch) {
              rating = ratingMatch[1];
            }
          }
        }
        
        // Clean up name if it still has unwanted characters
        name = name.replace(/[⭐🟢🔴📮]/g, '').trim();
        
        console.log('🔧 Extracted place data:', { name, distance, rating, status, address }); // Debug log
        
        if (name) {
          places.push({
            name: name,
            distance: distance,
            rating: rating ? `⭐ ${rating}` : null,
            status: status,
            address: address,
            mapsUrl: `https://www.google.com/maps/search/${encodeURIComponent(name + (address ? ' ' + address : ''))}`
          });
        }
      }
    }
    
    console.log('🔧 Final parsed places:', places); // Debug log
    
    return (
      <div className="response-formatted place-search-response">
        <div className="search-header">
          <div className="search-icon">🔍</div>
          <div className="search-info">
            <h4>Found {count} {placeType}</h4>
            <p>Near your location</p>
          </div>
        </div>
        
        <div className="places-grid">
          {places.map((place, index) => (
            <div key={index} className="place-card">
              <div className="place-header">
                <div className="place-number">{index + 1}</div>
                <div className="place-main-info">
                  <h5 className="place-name">{place.name}</h5>
                  <div className="place-meta">
                    {place.distance && (
                      <span className="place-distance">📏 {place.distance}</span>
                    )}
                    {place.rating && (
                      <span className="place-rating">{place.rating}</span>
                    )}
                    {place.status && (
                      <span className={`place-status ${place.status.toLowerCase()}`}>
                        {place.status === 'Open' ? '🟢' : '🔴'} {place.status}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              {place.address && (
                <div className="place-address">
                  📮 {place.address}
                </div>
              )}
              
              <div className="place-actions">
                <a 
                  href={place.mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="maps-link-small"
                >
                  🗺️ Open in Maps
                </a>
              </div>
            </div>
          ))}
        </div>
        
        <div className="search-footer">
          💡 Click "Open in Maps" to get directions to any location
        </div>
      </div>
    );
  };

  // 🔧 FIXED: Better parsing for standardized backend responses
  const formatDirectionsResponse = (content) => {
    try {
      const lines = content.split('\n').filter(line => line.trim());
      
      // Extract components with improved parsing
      let destination = '';
      let distance = '';
      let duration = '';
      let directions = [];
      let mapsUrl = '';
      let hasError = false;
      
      for (const line of lines) {
        const trimmedLine = line.trim();
        
        // 🔧 FIXED: Parse the standardized 📍 Destination line
        if (trimmedLine.includes('📍 Destination:')) {
          destination = trimmedLine.replace('📍 Destination:', '').trim();
        } else if (trimmedLine.includes('📏 Distance:')) {
          distance = trimmedLine.replace('📏 Distance:', '').trim();
        } else if (trimmedLine.includes('⏱️ Duration:')) {
          duration = trimmedLine.replace('⏱️ Duration:', '').trim();
        } else if (trimmedLine.includes('🌐 Open in Google Maps:')) {
          // Extract URL from the line
          const urlMatch = trimmedLine.match(/https:\/\/[^\s]+/);
          if (urlMatch) {
            mapsUrl = urlMatch[0];
          }
        } else if (trimmedLine.match(/^\d+\./)) {
          // Turn-by-turn direction step
          directions.push(trimmedLine);
        } else if (trimmedLine.includes('❌')) {
          hasError = true;
        }
      }
      
      // 🔧 FIXED: Handle error responses gracefully
      if (hasError || !destination) {
        return (
          <div className="response-formatted error-response">
            <div className="error-content">
              <div className="error-icon">❌</div>
              <div className="error-text">
                {content}
              </div>
            </div>
          </div>
        );
      }
      
      // 🔧 FIXED: Enhanced directions response with proper button styling
      return (
        <div className="response-formatted directions-response">
          <div className="directions-header">
            <div className="route-info">
              <h4 className="destination-title">
                🧭 Navigation to {destination}
              </h4>
              <div className="trip-summary">
                {distance && (
                  <span className="trip-distance">
                    📏 {distance}
                  </span>
                )}
                {duration && (
                  <span className="trip-duration">
                    ⏱️ {duration}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {/* 🔧 FIXED: Better turn-by-turn directions display */}
          {directions.length > 0 && (
            <div className="directions-steps">
              <h5 className="steps-header">🗺️ Turn-by-Turn Directions:</h5>
              <div className="steps-list">
                {directions.map((direction, index) => {
                  // Parse step number and instruction
                  const stepMatch = direction.match(/^(\d+)\.\s*(.+)/);
                  if (stepMatch) {
                    const stepNumber = stepMatch[1];
                    const instruction = stepMatch[2];
                    
                    return (
                      <div key={index} className="direction-step">
                        <div className="step-number">{stepNumber}</div>
                        <div className="step-instruction">{instruction}</div>
                      </div>
                    );
                  } else {
                    return (
                      <div key={index} className="direction-step">
                        <div className="step-number">{index + 1}</div>
                        <div className="step-instruction">{direction}</div>
                      </div>
                    );
                  }
                })}
              </div>
            </div>
          )}
          
          {/* 🔧 FIXED: Styled button for Google Maps instead of text link */}
          {mapsUrl && (
            <div className="maps-button-container">
              <a 
                href={mapsUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="maps-navigation-button"
              >
                <span className="button-icon">🗺️</span>
                <span className="button-text">Open in Google Maps</span>
                <span className="button-arrow">→</span>
              </a>
            </div>
          )}
          
          <div className="navigation-footer">
            📍 Navigation route ready
          </div>
        </div>
      );
    } catch (error) {
      console.error('Error parsing directions response:', error);
      
      // 🔧 FIXED: Fallback for parsing errors
      return (
        <div className="response-formatted error-response">
          <div className="error-content">
            <div className="error-icon">⚠️</div>
            <div className="error-text">
              Unable to parse navigation response. Please try again.
            </div>
            <div className="error-details">
              {content}
            </div>
          </div>
        </div>
      );
    }
  };

  const formatLocationResponse = (content) => {
    const lines = content.split('\n').filter(line => line.trim());
    const mainLocation = lines[0];
    
    return (
      <div className="response-formatted location-response">
        <div className="location-main">
          <div className="location-icon">📍</div>
          <div className="location-text">{mainLocation.replace('📍', '').trim()}</div>
        </div>
      </div>
    );
  };

  const formatGeneralResponse = (content) => {
    // Handle Google Maps URLs in general responses
    if (content.includes('https://www.google.com/maps')) {
      const parts = content.split(/https:\/\/www\.google\.com\/maps[^\s]*/);
      const urlMatch = content.match(/https:\/\/www\.google\.com\/maps[^\s]*/);
      
      if (urlMatch && parts.length > 1) {
        return (
          <div className="response-formatted general-response">
            <div className="response-text">
              {parts[0].trim()}
            </div>
            <div className="maps-link-container">
              <a 
                href={urlMatch[0]} 
                target="_blank" 
                rel="noopener noreferrer"
                className="maps-link-button"
              >
                🗺️ Open in Google Maps
              </a>
            </div>
            {parts[1] && (
              <div className="response-text">
                {parts[1].trim()}
              </div>
            )}
          </div>
        );
      }
    }
    
    // Standard text response
    return (
      <div className="response-formatted general-response">
        <div className="response-text">
          {content}
        </div>
      </div>
    );
  };

  const formatResponse = (content) => {
    if (!content) return <div className="response-formatted">No response content</div>;
    
    // Determine response type and format accordingly
    if (content.includes('Turn-by-turn directions') || content.includes('📋') || content.includes('🧭')) {
      return formatDirectionsResponse(content);
    } else if (content.includes('📍') && content.split('\n').length <= 3) {
      return formatLocationResponse(content);
    } else if (content.match(/Found \d+ .+ near you/i) || content.includes('🔍')) {
      // This is a place search response
      return formatPlaceSearchResponse(content);
    } else {
      return formatGeneralResponse(content);
    }
  };

  // ====================== RENDER FUNCTIONS ======================
  
  const renderVehicleDashboard = () => (
    <div className="dashboard-content">
      <div className="dashboard-header">
        <h1>🚗 Vehicle Dashboard</h1>
        <p>Welcome, {user.username}! Control your vehicle systems from here.</p>
      </div>

      <div className="dashboard-grid">
        {/* Climate Control */}
        <div className="dashboard-card climate-card">
          <div className="card-header">
            <Thermometer className="card-icon" />
            <h3>Climate Control</h3>
          </div>
          <div className="card-content">
            <div className="temperature-display">
              <span className="temp-value">{vehicleState.climate.temperature}°C</span>
              <div className="temp-controls">
                <button onClick={() => handleTemperatureChange(1)} className="temp-btn">+</button>
                <button onClick={() => handleTemperatureChange(-1)} className="temp-btn">-</button>
              </div>
            </div>
            <div className="climate-status">
              <span className={`status-indicator ${vehicleState.climate.ac_on ? 'active' : ''}`}>
                {vehicleState.climate.ac_on ? '❄️ AC ON' : '❄️ AC OFF'}
              </span>
              <button 
                onClick={handleACToggle}
                className={`control-btn ${vehicleState.climate.ac_on ? 'active' : ''}`}
              >
                Toggle AC
              </button>
            </div>
          </div>
        </div>

        {/* Music Control */}
        <div className="dashboard-card music-card">
          <div className="card-header">
            <Volume2 className="card-icon" />
            <h3>Music Control</h3>
          </div>
          <div className="card-content">
            <div className="music-info">
              <div className="track-info">
                <span className="track-name">{vehicleState.music.current_track}</span>
                <span className={`play-status ${vehicleState.music.playing ? 'playing' : 'paused'}`}>
                  {vehicleState.music.playing ? '▶️ Playing' : '⏸️ Paused'}
                </span>
              </div>
            </div>
            <div className="music-controls">
              <button className="music-btn"><SkipBack size={20} /></button>
              <button 
                onClick={handleMusicToggle}
                className={`music-btn play-btn ${vehicleState.music.playing ? 'playing' : ''}`}
              >
                {vehicleState.music.playing ? <Pause size={20} /> : <Play size={20} />}
              </button>
              <button className="music-btn"><SkipForward size={20} /></button>
            </div>
            <div className="volume-control">
              <span>Volume: {vehicleState.music.volume}%</span>
              <div className="volume-buttons">
                <button onClick={() => handleVolumeChange(-10)} className="volume-btn">-</button>
                <button onClick={() => handleVolumeChange(10)} className="volume-btn">+</button>
              </div>
            </div>
          </div>
        </div>

        {/* Vehicle Systems */}
        <div className="dashboard-card vehicle-card">
          <div className="card-header">
            <Car className="card-icon" />
            <h3>Vehicle Systems</h3>
          </div>
          <div className="card-content">
            <div className="vehicle-controls">
              <div className="control-item">
                <button 
                  onClick={handleDoorsToggle}
                  className={`control-btn ${vehicleState.vehicle.doors_locked ? 'locked' : 'unlocked'}`}
                >
                  {vehicleState.vehicle.doors_locked ? <Lock size={20} /> : <Unlock size={20} />}
                  {vehicleState.vehicle.doors_locked ? 'Locked' : 'Unlocked'}
                </button>
              </div>
              <div className="control-item">
                <button 
                  onClick={handleLightsToggle}
                  className={`control-btn ${vehicleState.vehicle.lights_on ? 'lights-on' : 'lights-off'}`}
                >
                  <Lightbulb size={20} />
                  {vehicleState.vehicle.lights_on ? 'Lights On' : 'Lights Off'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAssistant = () => (
    <div className="assistant-content">
      <div className="assistant-header">
        <h1>🤖 AI Assistant</h1>
        <p>Ask me anything about your vehicle or navigation!</p>
      </div>

      <div className="chat-container">
        <div className="chat-history">
          {chatHistory.length === 0 ? (
            <div className="welcome-message">
              <div className="welcome-icon">👋</div>
              <h3>Hello, {user.username}!</h3>
              <p>I'm your AI assistant. I can help you with:</p>
              <ul>
                <li>🌡️ Climate control</li>
                <li>🎵 Music playback</li>
                <li>🗺️ Navigation and directions</li>
                <li>🚗 Vehicle systems</li>
                <li>📍 Location services</li>
              </ul>
              <p>Try saying something like "Find restaurants near me" or "Set temperature to 24"</p>
            </div>
          ) : (
            chatHistory.map((message, index) => (
              <div key={index} className={`message ${message.type}`}>
                <div className="message-content">
                  {message.type === 'assistant' ? formatResponse(message.content) : message.content}
                </div>
                <div className="message-time">
                  {message.timestamp.toLocaleTimeString()}
                  {message.inputMethod && (
                    <span className={`input-method ${message.inputMethod}`}>
                      {message.inputMethod === 'voice' ? '🎤' : '⌨️'}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="message assistant">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <input
              type="text"
              value={assistantMessage}
              onChange={(e) => setAssistantMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Type your message or use voice..."
              className="chat-input"
              disabled={isLoading}
            />
            <div className="chat-buttons">
              <button
                onClick={startVoiceRecognition}
                className={`voice-btn ${isListening ? 'listening' : ''} ${!isVoiceSupported ? 'disabled' : ''}`}
                disabled={!isVoiceSupported || isLoading}
                title={isVoiceSupported ? (isListening ? 'Stop listening' : 'Start voice input') : 'Voice not supported'}
              >
                {isListening ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <button
                onClick={() => handleSendMessage()}
                className="send-btn"
                disabled={!assistantMessage.trim() || isLoading}
              >
                <Send size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // 📚 NEW: Enhanced History Render with Persistent Storage
  const renderHistory = () => (
    <div className="history-content">
      <div className="history-header">
        <div className="history-title-section">
          <h1>📚 Chat History</h1>
          <p>All your conversations with the AI assistant</p>
        </div>
        <div className="history-actions">
          {persistentHistory.length > 0 && (
            <button 
              onClick={clearAllHistory}
              className="clear-history-btn"
              title="Clear all chat history"
            >
              <Trash2 size={16} />
              Clear All
            </button>
          )}
        </div>
      </div>
      
      <div className="history-container">
        {historyLoading ? (
          <div className="history-loading">
            <div className="spinner"></div>
            <p>Loading chat history...</p>
          </div>
        ) : historyError ? (
          <div className="history-error">
            <p>❌ {historyError}</p>
            <button 
              onClick={() => window.location.reload()}
              className="retry-btn"
            >
              Retry
            </button>
          </div>
        ) : persistentHistory.length === 0 ? (
          <div className="no-history">
            <History size={48} />
            <h3>No chat history yet</h3>
            <p>Start a conversation with your AI assistant to see your chat history here!</p>
            <p className="history-note">
              💡 Your conversations are automatically saved and will persist across sessions.
            </p>
          </div>
        ) : (
          <div className="history-sessions">
            {/* 🔧 DEBUG PANEL - Remove this after fixing */}
            {persistentHistory.length === 0 && (
              <details className="debug-panel">
                <summary>🔍 Debug: Click to see raw backend data</summary>
                <pre style={{
                  background: '#f1f3f4',
                  padding: '15px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  overflow: 'auto',
                  maxHeight: '300px'
                }}>
                  <strong>Backend Response Structure:</strong><br/>
                  Check browser console for detailed logs when you reload this page.
                  <br/><br/>
                  Expected backend format:<br/>
                  {`{
  "recent_interactions": [
    {
      "user_input": "Find restaurants near me",
      "agent_response": "I found 5 restaurants near you...",
      "agent_id": "navigation_agent", 
      "timestamp": "2024-07-02T11:12:40",
      "actions_taken": [...]
    }
  ]
}`}
                </pre>
              </details>
            )}
            
            {persistentHistory.map((session) => (
              <div key={session.id} className="history-session">
                <div 
                  className="session-header"
                  onClick={() => toggleSessionExpansion(session.id)}
                >
                  <div className="session-info">
                    <div className="session-icon">
                      {expandedSessions[session.id] ? 
                        <ChevronDown size={16} /> : 
                        <ChevronRight size={16} />
                      }
                    </div>
                    <div className="session-details">
                      <h4 className="session-date">{session.displayDate}</h4>
                      <p className="session-meta">
                        <Clock size={14} />
                        {session.messageCount} messages • {session.startTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </p>
                    </div>
                  </div>
                  <div className="session-preview">
                    {session.interactions.length > 0 && (
                      <span className="preview-text">
                        {session.interactions[0].type === 'user' ? '👤 ' : '🤖 '}
                        {session.interactions[0].content.substring(0, 50)}
                        {session.interactions[0].content.length > 50 ? '...' : ''}
                      </span>
                    )}
                  </div>
                </div>
                
                {expandedSessions[session.id] && (
                  <div className="session-conversations">
                    {session.interactions.map((interaction, index) => (
                      <div key={index} className={`history-message ${interaction.type}`}>
                        <div className="message-bubble">
                          <div className="message-content">
                            {interaction.type === 'assistant' ? 
                              formatResponse(interaction.content) : 
                              interaction.content
                            }
                          </div>
                          <div className="message-metadata">
                            <span className="message-time">
                              {interaction.timestamp.toLocaleTimeString()}
                            </span>
                            {interaction.agent_id && (
                              <span className="agent-info">
                                🤖 {interaction.agent_id.replace('_agent', '')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderProfile = () => {
    if (!showProfile) return null;

    return (
      <div className="profile-dropdown">
        <div className="profile-info">
          <div className="profile-avatar">
            <User size={40} />
          </div>
          <div className="profile-details">
            <h3>{user.username}</h3>
            <p>{user.email}</p>
            <p className="vehicle-info">{user.vehicle_type} {user.vehicle_model}</p>
          </div>
        </div>
        <div className="profile-actions">
          <button className="profile-action-btn" onClick={onLogout}>
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'vehicle':
        return renderVehicleDashboard();
      case 'assistant':
        return renderAssistant();
      case 'history':
        return renderHistory();
      default:
        return renderVehicleDashboard();
    }
  };

  return (
    <div className="dashboard">
      <style jsx>{`
        .dashboard {
          display: flex;
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .sidebar {
          width: 280px;
          background: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-right: 1px solid rgba(255, 255, 255, 0.2);
          padding: 20px;
          box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
        }

        .sidebar-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .sidebar-header h2 {
          margin: 0;
          color: #2d3748;
          font-size: 1.5rem;
          font-weight: 700;
        }

        .sidebar-header p {
          margin: 8px 0 0 0;
          color: #718096;
          font-size: 0.9rem;
        }

        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          color: #4a5568;
          font-weight: 500;
        }

        .nav-item:hover {
          background: rgba(102, 126, 234, 0.1);
          color: #667eea;
        }

        .nav-item.active {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .nav-item-icon {
          width: 20px;
          height: 20px;
        }

        .main-content {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          background: rgba(255, 255, 255, 0.1);
        }

        .profile-area {
          width: 60px;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 20px 10px;
          position: relative;
        }

        .profile-button {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.9);
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .profile-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .profile-dropdown {
          position: absolute;
          top: 70px;
          right: 0;
          width: 280px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
          padding: 20px;
          z-index: 1000;
        }

        .profile-info {
          display: flex;
          align-items: center;
          gap: 15px;
          margin-bottom: 20px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e2e8f0;
        }

        .profile-avatar {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea, #764ba2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .profile-details h3 {
          margin: 0;
          color: #2d3748;
          font-size: 1.1rem;
        }

        .profile-details p {
          margin: 4px 0 0 0;
          color: #718096;
          font-size: 0.9rem;
        }

        .vehicle-info {
          font-weight: 500;
          color: #4a5568 !important;
        }

        .profile-action-btn {
          width: 100%;
          padding: 10px;
          border: none;
          border-radius: 8px;
          background: #f7fafc;
          color: #4a5568;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 8px;
          justify-content: center;
          font-weight: 500;
        }

        .profile-action-btn:hover {
          background: #edf2f7;
          color: #2d3748;
        }

        /* Dashboard Content Styles */
        .dashboard-content {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 30px;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(10px);
        }

        .dashboard-header {
          text-align: center;
          margin-bottom: 40px;
        }

        .dashboard-header h1 {
          margin: 0;
          color: #2d3748;
          font-size: 2.2rem;
          font-weight: 700;
        }

        .dashboard-header p {
          margin: 10px 0 0 0;
          color: #718096;
          font-size: 1.1rem;
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }

        .dashboard-card {
          background: white;
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          transition: transform 0.2s ease;
        }

        .dashboard-card:hover {
          transform: translateY(-2px);
        }

        .card-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
        }

        .card-icon {
          width: 24px;
          height: 24px;
          color: #667eea;
        }

        .card-header h3 {
          margin: 0;
          color: #2d3748;
          font-size: 1.3rem;
          font-weight: 600;
        }

        .temperature-display {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
        }

        .temp-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: #2d3748;
        }

        .temp-controls {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .temp-btn {
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 8px;
          background: #667eea;
          color: white;
          font-size: 1.2rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .temp-btn:hover {
          background: #5a67d8;
          transform: scale(1.05);
        }

        .climate-status {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .status-indicator {
          padding: 6px 12px;
          border-radius: 20px;
          background: #f7fafc;
          color: #4a5568;
          font-size: 0.9rem;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .status-indicator.active {
          background: #667eea;
          color: white;
        }

        .control-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 8px;
          background: #f7fafc;
          color: #4a5568;
          cursor: pointer;
          transition: all 0.2s ease;
          font-weight: 500;
        }

        .control-btn:hover {
          background: #edf2f7;
          color: #2d3748;
        }

        .control-btn.active {
          background: #667eea;
          color: white;
        }

        .music-info {
          margin-bottom: 20px;
        }

        .track-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .track-name {
          font-size: 1.1rem;
          font-weight: 600;
          color: #2d3748;
        }

        .play-status {
          font-size: 0.9rem;
          color: #718096;
        }

        .play-status.playing {
          color: #667eea;
          font-weight: 500;
        }

        .music-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-bottom: 20px;
        }

        .music-btn {
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 50%;
          background: #f7fafc;
          color: #4a5568;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .music-btn:hover {
          background: #edf2f7;
          color: #2d3748;
        }

        .play-btn.playing {
          background: #667eea;
          color: white;
        }

        .volume-control {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .volume-buttons {
          display: flex;
          gap: 8px;
        }

        .volume-btn {
          width: 32px;
          height: 32px;
          border: none;
          border-radius: 6px;
          background: #667eea;
          color: white;
          cursor: pointer;
          transition: all 0.2s ease;
          font-weight: 600;
        }

        .volume-btn:hover {
          background: #5a67d8;
        }

        .vehicle-controls {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .control-item {
          display: flex;
          justify-content: center;
        }

        .control-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 20px;
          border: none;
          border-radius: 10px;
          background: #f7fafc;
          color: #4a5568;
          cursor: pointer;
          transition: all 0.2s ease;
          font-weight: 500;
          font-size: 1rem;
        }

        .control-btn.locked {
          background: #fed7d7;
          color: #c53030;
        }

        .control-btn.unlocked {
          background: #c6f6d5;
          color: #25855a;
        }

        .control-btn.lights-on {
          background: #fef5e7;
          color: #d69e2e;
        }

        .control-btn.lights-off {
          background: #edf2f7;
          color: #4a5568;
        }

        /* Assistant Styles */
        .assistant-content {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 30px;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(10px);
          height: calc(100vh - 40px);
          display: flex;
          flex-direction: column;
        }

        .assistant-header {
          text-align: center;
          margin-bottom: 30px;
        }

        .assistant-header h1 {
          margin: 0;
          color: #2d3748;
          font-size: 2.2rem;
          font-weight: 700;
        }

        .assistant-header p {
          margin: 10px 0 0 0;
          color: #718096;
          font-size: 1.1rem;
        }

        .chat-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          overflow: hidden;
          background: white;
        }

        .chat-history {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          max-height: calc(100vh - 300px);
        }

        .welcome-message {
          text-align: center;
          padding: 40px 20px;
          color: #4a5568;
        }

        .welcome-icon {
          font-size: 3rem;
          margin-bottom: 20px;
        }

        .welcome-message h3 {
          margin: 0 0 20px 0;
          color: #2d3748;
          font-size: 1.5rem;
        }

        .welcome-message p {
          margin: 10px 0;
          line-height: 1.5;
        }

        .welcome-message ul {
          text-align: left;
          display: inline-block;
          margin: 20px 0;
        }

        .welcome-message li {
          margin: 8px 0;
        }

        .message {
          margin-bottom: 16px;
          display: flex;
          flex-direction: column;
        }

        .message.user {
          align-items: flex-end;
        }

        .message.assistant {
          align-items: flex-start;
        }

        .message-content {
          max-width: 80%;
          padding: 12px 16px;
          border-radius: 16px;
          word-wrap: break-word;
        }

        .message.user .message-content {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
        }

        .message.assistant .message-content {
          background: #f7fafc;
          color: #2d3748;
          border: 1px solid #e2e8f0;
        }

        .message-time {
          font-size: 0.8rem;
          color: #a0aec0;
          margin-top: 4px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .input-method {
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 0.7rem;
          font-weight: 500;
        }

        .input-method.voice {
          background: #fed7d7;
          color: #c53030;
        }

        .input-method.text {
          background: #c6f6d5;
          color: #25855a;
        }

        .typing-indicator {
          display: flex;
          gap: 4px;
          align-items: center;
          padding: 8px 0;
        }

        .typing-indicator span {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #cbd5e0;
          animation: typing 1.5s infinite;
        }

        .typing-indicator span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-indicator span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
          }
          30% {
            transform: translateY(-10px);
          }
        }

        .chat-input-container {
          padding: 20px;
          border-top: 1px solid #e2e8f0;
          background: #f7fafc;
        }

        .chat-input-wrapper {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .chat-input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          font-size: 1rem;
          outline: none;
          transition: border-color 0.2s ease;
        }

        .chat-input:focus {
          border-color: #667eea;
        }

        .chat-buttons {
          display: flex;
          gap: 8px;
        }

        .voice-btn, .send-btn {
          width: 44px;
          height: 44px;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .voice-btn {
          background: #f7fafc;
          color: #4a5568;
          border: 2px solid #e2e8f0;
        }

        .voice-btn:hover:not(.disabled) {
          background: #edf2f7;
          color: #2d3748;
        }

        .voice-btn.listening {
          background: #fed7d7;
          color: #c53030;
          border-color: #feb2b2;
          animation: pulse 2s infinite;
        }

        .voice-btn.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(197, 48, 48, 0.7);
          }
          70% {
            box-shadow: 0 0 0 10px rgba(197, 48, 48, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(197, 48, 48, 0);
          }
        }

        .send-btn {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
        }

        .send-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* 📚 NEW: Enhanced History Styles */
        .history-content {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 30px;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
          backdrop-filter: blur(10px);
          height: calc(100vh - 40px);
          display: flex;
          flex-direction: column;
        }

        .history-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e2e8f0;
        }

        .history-title-section h1 {
          margin: 0;
          color: #2d3748;
          font-size: 2.2rem;
          font-weight: 700;
        }

        .history-title-section p {
          margin: 10px 0 0 0;
          color: #718096;
          font-size: 1.1rem;
        }

        .history-actions {
          display: flex;
          gap: 12px;
        }

        .clear-history-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          background: white;
          color: #e53e3e;
          cursor: pointer;
          transition: all 0.2s ease;
          font-weight: 500;
        }

        .clear-history-btn:hover {
          background: #fed7d7;
          border-color: #feb2b2;
        }

        .history-container {
          flex: 1;
          overflow-y: auto;
        }

        .history-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px 20px;
          color: #718096;
        }

        .history-loading .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #e2e8f0;
          border-top: 3px solid #667eea;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 20px;
        }

        .history-error {
          text-align: center;
          padding: 60px 20px;
          color: #e53e3e;
        }

        .retry-btn {
          margin-top: 15px;
          padding: 10px 20px;
          border: 1px solid #e53e3e;
          border-radius: 8px;
          background: white;
          color: #e53e3e;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .retry-btn:hover {
          background: #fed7d7;
        }

        .no-history {
          text-align: center;
          padding: 60px 20px;
          color: #a0aec0;
        }

        .no-history svg {
          margin-bottom: 20px;
          color: #cbd5e0;
        }

        .no-history h3 {
          margin: 0 0 15px 0;
          color: #4a5568;
          font-size: 1.3rem;
        }

        .no-history p {
          margin: 10px 0;
          line-height: 1.5;
        }

        .history-note {
          background: #f7fafc;
          padding: 15px;
          border-radius: 8px;
          margin-top: 20px;
          color: #4a5568 !important;
          font-size: 0.9rem;
        }

        .history-sessions {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .history-session {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          overflow: hidden;
          transition: all 0.2s ease;
        }

        .history-session:hover {
          border-color: #667eea;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }

        .session-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 20px;
          cursor: pointer;
          background: #f8f9fa;
          border-bottom: 1px solid #e2e8f0;
          transition: background 0.2s ease;
        }

        .session-header:hover {
          background: #f1f3f4;
        }

        .session-info {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .session-icon {
          color: #667eea;
        }

        .session-details h4 {
          margin: 0;
          color: #2d3748;
          font-size: 1.1rem;
          font-weight: 600;
        }

        .session-meta {
          margin: 4px 0 0 0;
          color: #718096;
          font-size: 0.85rem;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .session-preview {
          flex: 1;
          text-align: right;
          max-width: 200px;
        }

        .preview-text {
          color: #a0aec0;
          font-size: 0.85rem;
          font-style: italic;
        }

        .session-conversations {
          padding: 20px;
          background: #fafbfc;
        }

        .history-message {
          margin-bottom: 16px;
          display: flex;
          flex-direction: column;
        }

        .history-message.user {
          align-items: flex-end;
        }

        .history-message.assistant {
          align-items: flex-start;
        }

        .message-bubble {
          max-width: 80%;
        }

        .history-message.user .message-content {
          background: linear-gradient(135deg, #667eea, #764ba2);
          color: white;
          padding: 12px 16px;
          border-radius: 16px;
          border-bottom-right-radius: 4px;
        }

        .history-message.assistant .message-content {
          background: white;
          border: 1px solid #e2e8f0;
          padding: 12px 16px;
          border-radius: 16px;
          border-bottom-left-radius: 4px;
        }

        .message-metadata {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-top: 6px;
          font-size: 0.75rem;
          color: #a0aec0;
        }

        .agent-info {
          background: #e2e8f0;
          padding: 2px 8px;
          border-radius: 10px;
          color: #4a5568;
          font-weight: 500;
        }

        /* Debug Panel */
        .debug-panel {
          margin-bottom: 20px;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 15px;
          background: #f8f9fa;
        }

        .debug-panel summary {
          cursor: pointer;
          font-weight: 600;
          color: #4a5568;
          margin-bottom: 10px;
        }

        .debug-panel summary:hover {
          color: #667eea;
        }

        /* Enhanced Response Formatting */
        .response-formatted {
          background: #f8f9fa;
          border-radius: 12px;
          padding: 16px;
          border-left: 4px solid #667eea;
        }
        
        .place-search-response {
          border-left-color: #48bb78;
        }
        
        .search-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
          padding-bottom: 12px;
          border-bottom: 1px solid #e2e8f0;
        }
        
        .search-icon {
          font-size: 1.5rem;
        }
        
        .search-info h4 {
          margin: 0;
          color: #2d3748;
          font-size: 1.1rem;
          font-weight: 600;
        }
        
        .search-info p {
          margin: 2px 0 0 0;
          color: #718096;
          font-size: 0.9rem;
        }
        
        .places-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 16px;
        }
        
        .place-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 16px;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .place-card:hover {
          border-color: #667eea;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
          transform: translateY(-1px);
        }
        
        .place-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 8px;
        }
        
        .place-number {
          background: #667eea;
          color: white;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.85rem;
          font-weight: 600;
          flex-shrink: 0;
        }
        
        .place-main-info {
          flex: 1;
        }
        
        .place-name {
          margin: 0 0 6px 0;
          color: #2d3748;
          font-size: 1rem;
          font-weight: 600;
          line-height: 1.3;
        }
        
        .place-meta {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }
        
        .place-distance {
          font-size: 0.8rem;
          color: #4a5568;
          background: #edf2f7;
          padding: 3px 8px;
          border-radius: 12px;
        }
        
        .place-rating {
          font-size: 0.8rem;
          color: #d69e2e;
          background: #fef5e7;
          padding: 3px 8px;
          border-radius: 12px;
        }
        
        .place-status {
          font-size: 0.8rem;
          padding: 3px 8px;
          border-radius: 12px;
        }
        
        .place-status.open {
          color: #25855a;
          background: #c6f6d5;
        }
        
        .place-status.closed {
          color: #c53030;
          background: #fed7d7;
        }
        
        .place-address {
          font-size: 0.85rem;
          color: #718096;
          line-height: 1.4;
          margin-bottom: 12px;
          padding-left: 40px;
        }
        
        .place-actions {
          padding-left: 40px;
        }
        
        .maps-link-small {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: linear-gradient(135deg, #4285f4, #34a853);
          color: white;
          padding: 8px 14px;
          border-radius: 6px;
          text-decoration: none;
          font-size: 0.85rem;
          font-weight: 500;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(66, 133, 244, 0.3);
        }
        
        .maps-link-small:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 8px rgba(66, 133, 244, 0.4);
          color: white;
          text-decoration: none;
        }
        
        .search-footer {
          text-align: center;
          font-size: 0.8rem;
          color: #718096;
          background: #f7fafc;
          padding: 8px;
          border-radius: 6px;
          margin-top: 8px;
        }
        
        .directions-response {
          border-left-color: #48bb78;
        }
        
        .directions-header {
          margin-bottom: 16px;
        }
        
        .directions-header h4 {
          margin: 0 0 8px 0;
          color: #2d3748;
          font-size: 1.1rem;
        }
        
        .trip-stats {
          display: flex;
          gap: 16px;
          font-size: 0.9rem;
          color: #718096;
        }
        
        .distance, .duration {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        
        .directions-list {
          margin: 16px 0;
        }
        
        .directions-list h5 {
          margin: 0 0 12px 0;
          color: #4a5568;
          font-size: 0.95rem;
        }
        
        .direction-step {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-bottom: 8px;
          padding: 8px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
        }
        
        .step-number {
          background: #667eea;
          color: white;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.8rem;
          font-weight: 600;
          flex-shrink: 0;
        }
        
        .step-instruction {
          color: #2d3748;
          line-height: 1.4;
          font-size: 0.9rem;
        }
        
        .more-steps {
          text-align: center;
          color: #718096;
          font-style: italic;
          margin-top: 8px;
        }
        
        .location-response {
          text-align: center;
          padding: 8px;
        }
        
        .location-main {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        
        .location-icon {
          font-size: 1.2rem;
        }
        
        .location-text {
          font-weight: 500;
          color: #2d3748;
        }
        
        .response-footer {
          margin-top: 16px;
          font-size: 0.85rem;
          color: #718096;
          font-style: italic;
          text-align: center;
          padding: 8px;
          background: #f7fafc;
          border-radius: 6px;
        }
        
        .general-response .response-text {
          line-height: 1.4;
        }
        
        .maps-link-container {
          margin: 16px 0;
          text-align: center;
        }
        
        .maps-link-button {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: linear-gradient(135deg, #4285f4, #34a853);
          color: white;
          padding: 12px 20px;
          border-radius: 8px;
          text-decoration: none;
          font-size: 0.95rem;
          font-weight: 600;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
        }
        
        .maps-link-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(66, 133, 244, 0.4);
          color: white;
          text-decoration: none;
        }

        .maps-action-container {
          margin: 16px 0;
          text-align: center;
        }
        
        .maps-action-button {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: linear-gradient(135deg, #4285f4, #34a853);
          color: white;
          padding: 12px 20px;
          border-radius: 8px;
          text-decoration: none;
          font-size: 0.95rem;
          font-weight: 600;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
        }
        
        .maps-action-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(66, 133, 244, 0.4);
          color: white;
          text-decoration: none;
        }
        
        .maps-action-button:active {
          transform: translateY(0);
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        /* 🔧 FIXED: Enhanced navigation response styling */
        .error-response {
          border-left-color: #e53e3e;
          background: #fed7d7;
        }
        
        .error-content {
          display: flex;
          align-items: flex-start;
          gap: 12px;
        }
        
        .error-icon {
          font-size: 1.5rem;
          flex-shrink: 0;
        }
        
        .error-text {
          color: #c53030;
          font-weight: 500;
          line-height: 1.4;
        }
        
        .error-details {
          margin-top: 10px;
          font-size: 0.9rem;
          color: #744210;
          background: #fef5e7;
          padding: 8px 12px;
          border-radius: 6px;
          border-left: 3px solid #d69e2e;
        }
        
        .directions-response {
          border-left-color: #48bb78;
          padding: 20px;
        }
        
        .directions-header {
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 2px solid #e2e8f0;
        }
        
        .route-info {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        
        .destination-title {
          margin: 0;
          color: #2d3748;
          font-size: 1.3rem;
          font-weight: 700;
          line-height: 1.3;
        }
        
        .trip-summary {
          display: flex;
          gap: 20px;
          flex-wrap: wrap;
        }
        
        .trip-distance, .trip-duration {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: #f7fafc;
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 0.9rem;
          font-weight: 500;
          color: #4a5568;
          border: 1px solid #e2e8f0;
        }
        
        .directions-steps {
          margin: 20px 0;
        }
        
        .steps-header {
          margin: 0 0 15px 0;
          color: #2d3748;
          font-size: 1.1rem;
          font-weight: 600;
        }
        
        .steps-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        
        .direction-step {
          display: flex;
          align-items: flex-start;
          gap: 15px;
          padding: 12px 16px;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          transition: all 0.2s ease;
        }
        
        .direction-step:hover {
          border-color: #cbd5e0;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .step-number {
          background: linear-gradient(135deg, #48bb78, #38a169);
          color: white;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.9rem;
          font-weight: 700;
          flex-shrink: 0;
          box-shadow: 0 2px 4px rgba(72, 187, 120, 0.3);
        }
        
        .step-instruction {
          color: #2d3748;
          line-height: 1.5;
          font-size: 0.95rem;
          flex: 1;
          padding-top: 4px;
        }
        
        /* 🔧 FIXED: Enhanced Google Maps button styling */
        .maps-button-container {
          margin: 25px 0 15px 0;
          text-align: center;
        }
        
        .maps-navigation-button {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          background: linear-gradient(135deg, #4285f4, #34a853);
          color: white;
          padding: 16px 24px;
          border-radius: 12px;
          text-decoration: none;
          font-size: 1rem;
          font-weight: 600;
          transition: all 0.3s ease;
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
          border: none;
          cursor: pointer;
          min-width: 200px;
        }
        
        .maps-navigation-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(66, 133, 244, 0.4);
          color: white;
          text-decoration: none;
        }
        
        .maps-navigation-button:active {
          transform: translateY(0);
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
        }
        
        .button-icon {
          font-size: 1.2rem;
        }
        
        .button-text {
          flex: 1;
          text-align: center;
        }
        
        .button-arrow {
          font-size: 1.1rem;
          font-weight: 700;
          transition: transform 0.2s ease;
        }
        
        .maps-navigation-button:hover .button-arrow {
          transform: translateX(3px);
        }
        
        .navigation-footer {
          margin-top: 15px;
          text-align: center;
          font-size: 0.9rem;
          color: #718096;
          background: #f7fafc;
          padding: 10px;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
        }
        
        /* Mobile responsiveness for navigation responses */
        @media (max-width: 768px) {
          .directions-response {
            padding: 15px;
          }
          
          .destination-title {
            font-size: 1.1rem;
          }
          
          .trip-summary {
            flex-direction: column;
            gap: 10px;
          }
          
          .direction-step {
            padding: 10px 12px;
            gap: 12px;
          }
          
          .step-number {
            width: 28px;
            height: 28px;
            font-size: 0.8rem;
          }
          
          .step-instruction {
            font-size: 0.9rem;
          }
          
          .maps-navigation-button {
            padding: 14px 20px;
            font-size: 0.95rem;
            min-width: 180px;
          }
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .dashboard {
            flex-direction: column;
          }
          
          .sidebar {
            width: 100%;
            padding: 15px;
          }
          
          .sidebar-nav {
            flex-direction: row;
            overflow-x: auto;
          }
          
          .main-content {
            padding: 15px;
          }
          
          .profile-area {
            display: none;
          }
          
          .dashboard-grid {
            grid-template-columns: 1fr;
          }
          
          .chat-input-wrapper {
            flex-direction: column;
            gap: 12px;
          }
          
          .chat-input {
            width: 100%;
          }
          
          .chat-buttons {
            width: 100%;
            justify-content: center;
          }

          .history-header {
            flex-direction: column;
            gap: 15px;
            align-items: flex-start;
          }

          .session-header {
            flex-direction: column;
            gap: 10px;
            align-items: flex-start;
          }

          .session-preview {
            text-align: left;
            max-width: none;
          }

          .place-meta {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
          }
        }
      `}</style>
      
      {/* Left Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>🚗 AI Assistant</h2>
          <p>Welcome, {user.username}</p>
        </div>

        <nav className="sidebar-nav">
          <div
            className={`nav-item ${activeTab === 'vehicle' ? 'active' : ''}`}
            onClick={() => handleNavClick('vehicle')}
          >
            <Car className="nav-item-icon" />
            <span className="nav-item-text">Vehicle Dashboard</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'assistant' ? 'active' : ''}`}
            onClick={() => handleNavClick('assistant')}
          >
            <MessageCircle className="nav-item-icon" />
            <span className="nav-item-text">AI Assistant</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => handleNavClick('history')}
          >
            <History className="nav-item-icon" />
            <span className="nav-item-text">Chat History</span>
          </div>
        </nav>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {renderContent()}
      </div>

      {/* Right Profile Area */}
      <div className="profile-area">
        <button 
          className="profile-button"
          onClick={handleProfileToggle}
        >
          <User size={20} />
        </button>
        {renderProfile()}
      </div>
    </div>
  );
}

export default Dashboard;