"""
Agentic AI Multi-Agent System for In-Vehicle Assistant
Multiple specialized AI agents with Groq AI fallback for general queries
Maintains frontend-backend coherence for seamless integration
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import aiohttp

# Groq AI integration
try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ Groq not installed. Install with: pip install groq")

logger = logging.getLogger(__name__)

class AgentType(Enum):
    MASTER = "master"
    VEHICLE_CONTROL = "vehicle_control"
    NAVIGATION = "navigation" 
    ENTERTAINMENT = "entertainment"
    CLIMATE = "climate"
    USER_EXPERIENCE = "user_experience"
    VEHICLE_INFO = "vehicle_info"

@dataclass
class AgentMessage:
    content: str
    user_id: str
    timestamp: datetime
    message_type: str = "user_input"
    agent_id: Optional[str] = None
    actions_taken: List[str] = None
    vehicle_state: Dict = None
    user_location: Optional[Dict] = None
    
    def __post_init__(self):
        if self.actions_taken is None:
            self.actions_taken = []
        if self.vehicle_state is None:
            self.vehicle_state = {}

@dataclass
class UserProfile:
    user_id: str
    username: str
    email: str
    vehicle_type: str
    vehicle_model: str
    vehicle_data: Dict
    created_at: datetime
    last_active: datetime
    total_interactions: int = 0
    preferred_temperature: int = 22
    preferred_volume: int = 50
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_active'] = self.last_active.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserProfile':
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_active'] = datetime.fromisoformat(data['last_active'])
        return cls(**data)

class MemoryManager:
    """Enhanced memory manager with authentication and chat history"""
    
    def __init__(self):
        self.database_file = "data/users.db"
        self.interaction_history: Dict[str, List[Dict]] = defaultdict(list)
        self.user_profiles: Dict[str, UserProfile] = {}
        os.makedirs("data", exist_ok=True)
        
    async def initialize(self):
        """Initialize database and load data"""
        await self._init_database()
        logger.info("✅ Memory Manager initialized")
    
    async def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.database_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                vehicle_model TEXT NOT NULL,
                vehicle_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def register_user(self, username: str, email: str, password: str, 
                           vehicle_type: str, vehicle_model: str, vehicle_data: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """Register new user"""
        try:
            conn = sqlite3.connect(self.database_file)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                conn.close()
                return False, "Username or email already exists", None
            
            # Hash password and insert user
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, vehicle_type, vehicle_model, vehicle_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, vehicle_type, vehicle_model, json.dumps(vehicle_data)))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Create user profile
            user_profile = UserProfile(
                user_id=username,
                username=username,
                email=email,
                vehicle_type=vehicle_type,
                vehicle_model=vehicle_model,
                vehicle_data=vehicle_data,
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            self.user_profiles[username] = user_profile
            
            user_data = {
                "id": user_id,
                "username": username,
                "email": email,
                "vehicleType": vehicle_type,
                "vehicleModel": vehicle_model,
                "vehicleData": vehicle_data,
                "createdAt": datetime.now().isoformat()
            }
            
            logger.info(f"✅ User registered: {username}")
            return True, "User registered successfully", user_data
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, f"Registration failed: {str(e)}", None
    
    async def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """Authenticate user login"""
        try:
            conn = sqlite3.connect(self.database_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, password_hash, vehicle_type, vehicle_model, vehicle_data
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user_row = cursor.fetchone()
            if not user_row:
                conn.close()
                return False, "User not found", None
            
            user_id, db_username, email, password_hash, vehicle_type, vehicle_model, vehicle_data_str = user_row
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                conn.close()
                return False, "Invalid password", None
            
            # Update last login
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            vehicle_data = json.loads(vehicle_data_str)
            
            # Create/update user profile
            profile = UserProfile(
                user_id=username,
                username=username,
                email=email,
                vehicle_type=vehicle_type,
                vehicle_model=vehicle_model,
                vehicle_data=vehicle_data,
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            self.user_profiles[username] = profile
            
            user_data = {
                "id": user_id,
                "username": username,
                "email": email,
                "vehicleType": vehicle_type,
                "vehicleModel": vehicle_model,
                "vehicleData": vehicle_data,
                "lastLogin": datetime.now().isoformat()
            }
            
            logger.info(f"✅ User authenticated: {username}")
            return True, "Login successful", user_data
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, f"Authentication failed: {str(e)}", None
    
    async def is_user_authenticated(self, user_id: str) -> bool:
        """Check if user is authenticated"""
        try:
            conn = sqlite3.connect(self.database_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ? AND is_active = 1", (user_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception:
            return False
    
    async def store_interaction(self, user_id: str, user_message: AgentMessage, agent_response: AgentMessage):
        """Store user interaction"""
        try:
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_message.content,
                "agent_response": agent_response.content,
                "agent_id": agent_response.agent_id,
                "actions_taken": agent_response.actions_taken
            }
            
            self.interaction_history[user_id].append(interaction)
            
            # Keep only last 50 interactions per user
            if len(self.interaction_history[user_id]) > 50:
                self.interaction_history[user_id] = self.interaction_history[user_id][-50:]
            
            # Update user profile
            if user_id in self.user_profiles:
                self.user_profiles[user_id].total_interactions += 1
                self.user_profiles[user_id].last_active = datetime.now()
                
        except Exception as e:
            logger.error(f"Error storing interaction: {e}")
    
    async def get_user_memory(self, user_id: str) -> Dict:
        """Get user memory for API"""
        try:
            recent_interactions = self.interaction_history[user_id][-20:]  # Last 20
            
            return {
                "recent_interactions": recent_interactions,
                "memory_stats": {
                    "total_interactions": len(self.interaction_history[user_id]),
                    "last_active": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting user memory: {e}")
            return {"error": str(e)}

class GroqAIIntegration:
    """Groq AI integration for general queries that don't match specific agents"""
    
    def __init__(self):
        self.client = None
        self.available = False
        self._initialize_groq()
    
    def _initialize_groq(self):
        """Initialize Groq client"""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("⚠️ GROQ_API_KEY not found in environment variables")
                return
            
            if not GROQ_AVAILABLE:
                logger.warning("⚠️ Groq package not installed")
                return
                
            self.client = AsyncGroq(api_key=api_key)
            self.available = True
            logger.info("✅ Groq AI integration initialized")
            
        except Exception as e:
            logger.error(f"❌ Groq initialization failed: {e}")
            self.available = False
    
    async def get_general_response(self, user_message: str, context: str = "") -> str:
        """Get general response from Groq AI"""
        try:
            if not self.available:
                return "I'm here to help with vehicle controls, navigation, music, and climate. Please ask me something specific about your car!"
            
            # Create context-aware prompt
            system_prompt = """You are a helpful AI assistant in a smart vehicle. You can have general 
            conversations, answer questions, and provide helpful information. Be friendly and informative. 
            Provide complete and useful responses to user queries. Make sure to double check the info you are providing."""
            
            user_prompt = f"Context: {context}\n\nUser message: {user_message}"
            
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-8b-8192",  # Fast model for general conversation
                max_tokens=800,
                temperature=0.7
            )
            
            response = chat_completion.choices[0].message.content.strip()
            logger.info(f"🤖 Groq AI response: {response[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ Groq AI error: {e}")
            return "I'm here to help! Try asking me about vehicle controls, music, navigation, or climate settings."

class BaseAgent:
    """Base class for all specialized agents"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, memory_manager: MemoryManager, tools: List = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.memory_manager = memory_manager
        self.tools = tools or []
        self.active = True
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        """Check if this agent can handle the message"""
        return False  # Override in specific agents
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process message and return response"""
        try:
            # Get response and actions
            response_text, actions_taken, vehicle_state = await self._handle_message(message)
            
            # Create response
            response = AgentMessage(
                content=response_text,
                user_id=message.user_id,
                timestamp=datetime.now(),
                message_type="agent_response",
                agent_id=self.agent_id,
                actions_taken=actions_taken,
                vehicle_state=vehicle_state
            )
            
            # Store interaction
            await self.memory_manager.store_interaction(message.user_id, message, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error: {e}")
            return AgentMessage(
                content="I encountered an issue processing your request. Please try again.",
                user_id=message.user_id,
                timestamp=datetime.now(),
                agent_id=self.agent_id
            )
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle message - override in specific agents"""
        return "I can help you!", [], {}

class MasterAgent(BaseAgent):
    """Master agent that coordinates other agents and handles Groq AI fallback"""
    
    def __init__(self, memory_manager: MemoryManager, orchestrator):
        super().__init__("master_agent", AgentType.MASTER, memory_manager)
        self.orchestrator = orchestrator
        self.groq_ai = GroqAIIntegration()
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Coordinate with specialist agents or use Groq AI fallback"""
        try:
            # Import here to avoid circular imports
            from intent_disambiguation import classify_intent
            
            # Classify intent
            intent_data = classify_intent(message.content)
            
            if not intent_data or intent_data.get('confidence', 0) < 0.3:
                # No specific intent detected - use Groq AI for general conversation
                logger.info(f"🤖 No specific intent detected, using Groq AI for: '{message.content}'")
                
                # Get context from recent interactions
                user_memory = await self.memory_manager.get_user_memory(message.user_id)
                recent_context = ""
                if user_memory.get('recent_interactions'):
                    recent = user_memory['recent_interactions'][-3:]  # Last 3 interactions
                    recent_context = " ".join([f"User: {r['user_input']} Assistant: {r['agent_response']}" for r in recent])
                
                groq_response = await self.groq_ai.get_general_response(message.content, recent_context)
                
                response = AgentMessage(
                    content=groq_response,
                    user_id=message.user_id,
                    timestamp=datetime.now(),
                    agent_id="groq_ai_agent",
                    actions_taken=["general_conversation"],
                    vehicle_state={}
                )
                
                await self.memory_manager.store_interaction(message.user_id, message, response)
                return response
            
            # Find the best agent for this intent
            target_agent = intent_data.get('target_agent', 'user_experience_agent')
            
            if target_agent in self.orchestrator.agents:
                agent_response = await self.orchestrator.agents[target_agent].process_message(message)
                logger.info(f"🎯 Routed to {target_agent}: {agent_response.content[:50]}...")
                return agent_response
            else:
                # Fallback to master agent handling
                return await super().process_message(message)
                
        except Exception as e:
            logger.error(f"Master agent error: {e}")
            # Fallback to Groq AI on any error
            groq_response = await self.groq_ai.get_general_response(message.content, "")
            return AgentMessage(
                content=groq_response,
                user_id=message.user_id,
                timestamp=datetime.now(),
                agent_id="master_agent",
                actions_taken=["error_fallback"],
                vehicle_state={}
            )

class ClimateAgent(BaseAgent):
    """Climate control specialist agent"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("climate_agent", AgentType.CLIMATE, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        intent = intent_data.get('primary_intent', '')
        return any(word in intent for word in ['climate', 'temperature', 'ac', 'air'])
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle climate control requests"""
        # Import tools here to avoid circular imports
        from tools import ClimateTools
        
        message_lower = message.content.lower()
        
        # Temperature control
        temp_match = re.search(r'(\d+)\s*(?:degrees?|°)', message_lower)
        if temp_match:
            temperature = int(temp_match.group(1))
            result = await ClimateTools.set_temperature(temperature)
            if result.get('success'):
                return result['message'], [f"set_temperature: {temperature}°C"], result.get('vehicle_state', {})
        
        # AC control
        if any(word in message_lower for word in ['ac', 'air conditioning']):
            result = await ClimateTools.toggle_ac()
            if result.get('success'):
                return result['message'], ["toggle_ac"], result.get('vehicle_state', {})
        
        # Temperature adjustment
        if any(word in message_lower for word in ['hot', 'warm', 'increase', 'up']):
            result = await ClimateTools.set_temperature(25)
            if result.get('success'):
                return result['message'], ["increase_temperature"], result.get('vehicle_state', {})
        
        if any(word in message_lower for word in ['cold', 'cool', 'decrease', 'down']):
            result = await ClimateTools.set_temperature(20)
            if result.get('success'):
                return result['message'], ["decrease_temperature"], result.get('vehicle_state', {})
        
        return "I'll help you with climate control. Try saying 'set temperature to 22' or 'turn on AC'.", [], {}

class EntertainmentAgent(BaseAgent):
    """Music and entertainment specialist agent"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("entertainment_agent", AgentType.ENTERTAINMENT, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        intent = intent_data.get('primary_intent', '')
        return any(word in intent for word in ['music', 'play', 'pause', 'volume', 'entertainment'])
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle music and entertainment requests"""
        from tools import MusicTools
        
        message_lower = message.content.lower()
        
        # Music playback control - fixed pause detection
        if any(word in message_lower for word in ['pause', 'stop']) and 'music' in message_lower:
            result = await MusicTools.pause_music()
            if result.get('success'):
                return result['message'], ["pause_music"], result.get('vehicle_state', {})
        
        elif any(word in message_lower for word in ['play', 'start']) or 'music' in message_lower:
            result = await MusicTools.play_music()
            if result.get('success'):
                return result['message'], ["play_music"], result.get('vehicle_state', {})
        
        # Track navigation
        if any(word in message_lower for word in ['next', 'skip']):
            result = await MusicTools.next_track()
            if result.get('success'):
                return result['message'], ["next_track"], result.get('vehicle_state', {})
        
        if any(word in message_lower for word in ['previous', 'back']):
            result = await MusicTools.previous_track()
            if result.get('success'):
                return result['message'], ["previous_track"], result.get('vehicle_state', {})
        
        # Volume control
        vol_match = re.search(r'volume\s*(?:to\s*)?(\d+)', message_lower)
        if vol_match:
            volume = int(vol_match.group(1))
            result = await MusicTools.set_volume(volume)
            if result.get('success'):
                return result['message'], [f"set_volume: {volume}%"], result.get('vehicle_state', {})
        
        return "I'll help you with music. Try saying 'play music', 'pause', 'next track', or 'set volume to 70'.", [], {}

class VehicleControlAgent(BaseAgent):
    """Vehicle systems control specialist agent"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("vehicle_control_agent", AgentType.VEHICLE_CONTROL, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        intent = intent_data.get('primary_intent', '')
        return any(word in intent for word in ['vehicle', 'door', 'lock', 'light', 'unlock'])
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle vehicle control requests"""
        from tools import VehicleTools
        
        message_lower = message.content.lower()
        
        # Door control
        if 'lock' in message_lower and 'door' in message_lower:
            result = await VehicleTools.lock_doors()
            if result.get('success'):
                return result['message'], ["lock_doors"], result.get('vehicle_state', {})
        
        if 'unlock' in message_lower and 'door' in message_lower:
            result = await VehicleTools.unlock_doors()
            if result.get('success'):
                return result['message'], ["unlock_doors"], result.get('vehicle_state', {})
        
        # Lights control
        if any(word in message_lower for word in ['lights', 'headlights']):
            result = await VehicleTools.toggle_lights()
            if result.get('success'):
                return result['message'], ["toggle_lights"], result.get('vehicle_state', {})
        
        return "I'll help you control vehicle systems. Try saying 'lock doors', 'unlock doors', or 'turn on lights'.", [], {}

class NavigationAgent(BaseAgent):
    """🔧 ENHANCED: Navigation agent with comprehensive place search and tourist attractions"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("navigation_agent", AgentType.NAVIGATION, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        intent = intent_data.get('primary_intent', '')
        return any(word in intent for word in ['navigation', 'directions', 'location', 'weather', 'find', 'search'])
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """🔧 ENHANCED: Handle navigation with comprehensive tourist attraction support"""
        from tools import NavigationTools
        
        message_lower = message.content.lower()
        user_location = message.user_location
        
        # Extract coordinates if available
        latitude = user_location.get('latitude') if user_location else None
        longitude = user_location.get('longitude') if user_location else None
        
        logger.info(f"🔧 NavigationAgent processing: '{message_lower}'")
        
        # 🔧 ENHANCED: Weather requests with comprehensive patterns
        if any(pattern in message_lower for pattern in [
            'weather', 'forecast', 'temperature outside', 'climate outside',
            'is it raining', 'will it rain', 'sunny', 'cloudy', 'weather report',
            'current weather', 'weather conditions', 'atmospheric conditions'
        ]):
            logger.info("🌤️ Processing weather request")
            result = await NavigationTools.get_weather(latitude=latitude, longitude=longitude)
            if result.get('success'):
                return result['message'], ["get_weather"], {}
        
        # 🔧 ENHANCED: Location requests with better patterns
        if any(phrase in message_lower for phrase in [
            'where am i', 'current location', 'my location', 'where are we',
            'what is my location', 'tell me where i am', 'show location',
            'gps position', 'coordinates', 'position update'
        ]):
            logger.info("📍 Processing location request")
            result = await NavigationTools.get_current_location(latitude=latitude, longitude=longitude)
            if result.get('success'):
                return result['message'], ["get_current_location"], {}
        
        # 🔧 ENHANCED: Place search with comprehensive tourist attraction support
        if any(word in message_lower for word in [
            'find', 'search', 'locate', 'look for', 'nearest', 'nearby', 'close',
            'suggest', 'recommend', 'show me', 'places', 'visit', 'tourist',
            'attraction', 'sightseeing', 'spots', 'points of interest'
        ]):
            logger.info("🔍 Processing place search request")
            place_type = self._extract_enhanced_place_type(message_lower)
            logger.info(f"🔧 Extracted place type: '{place_type}' from message: '{message_lower}'")
            
            result = await NavigationTools.search_nearby_places(place_type, latitude=latitude, longitude=longitude)
            if result.get('success'):
                action_taken = f"search_places: {place_type}"
                if place_type == 'tourist_attraction':
                    action_taken = "search_tourist_attractions"
                return result['message'], [action_taken], {}
        
        # 🔧 ENHANCED: Directions with better extraction
        if any(word in message_lower for word in [
            'navigate', 'directions', 'route', 'go to', 'take me to',
            'drive to', 'head to', 'guide me to', 'show route to'
        ]):
            logger.info("🧭 Processing directions request")
            destination = self._extract_destination(message_lower)
            if destination:
                result = await NavigationTools.get_directions(destination, latitude=latitude, longitude=longitude)
                if result.get('success'):
                    return result['message'], [f"get_directions: {destination}"], {}
        
        # 🔧 ENHANCED: Fallback with helpful suggestions
        return self._get_helpful_fallback_response(message_lower), ["navigation_assistance"], {}
    
    def _extract_enhanced_place_type(self, message: str) -> str:
        """🔧 ENHANCED: Extract place type with comprehensive tourist attraction support"""
        message_lower = message.lower()
        
        # 🔧 FIXED: Hotel/lodging detection (HIGH PRIORITY)
        hotel_keywords = [
            'hotel', 'hotels', 'lodging', 'accommodation', 'stay', 'guest house', 
            'resort', 'resorts', 'inn', 'motel', 'bed and breakfast', 'bnb',
            'place to stay', 'where to stay', 'accommodation options'
        ]
        
        if any(keyword in message_lower for keyword in hotel_keywords):
            logger.info("🔧 Detected hotel/lodging request")
            return 'lodging'
        
        # 🔧 ENHANCED: Tourist attractions and sightseeing
        tourist_keywords = [
            'visit', 'tourist', 'attraction', 'sightseeing', 'landmark', 'monument',
            'places to visit', 'tourist attractions', 'sightseeing spots', 'points of interest',
            'tourist places', 'visiting spots', 'places to see', 'must visit', 'tourist spots',
            'scenic places', 'beautiful places', 'famous places', 'popular places',
            'suggest places', 'recommend places', 'interesting places', 'worth visiting'
        ]
        
        if any(keyword in message_lower for keyword in tourist_keywords):
            logger.info("🔧 Detected tourist attraction request")
            return 'tourist_attraction'
        
        # 🔧 ENHANCED: Religious places
        if any(word in message_lower for word in ['temple', 'temples', 'church', 'churches', 'mosque', 'mosques', 'worship', 'religious', 'pray', 'prayer', 'shrine']):
            logger.info("🔧 Detected worship place request")
            return 'place_of_worship'
        
        # 🔧 ENHANCED: Restaurants and food
        if any(word in message_lower for word in ['restaurant', 'restaurants', 'food', 'eat', 'dine', 'dining', 'meal', 'lunch', 'dinner', 'breakfast']):
            logger.info("🔧 Detected restaurant request")
            return 'restaurant'
        
        # 🔧 ENHANCED: Shopping
        if any(word in message_lower for word in ['mall', 'shopping', 'store', 'shop', 'shops', 'market', 'shopping center', 'bazaar', 'retail']):
            logger.info("🔧 Detected shopping request")
            return 'shopping_mall'
        
        # 🔧 ENHANCED: Medical facilities  
        if any(word in message_lower for word in ['hospital', 'hospitals', 'medical', 'clinic', 'doctor', 'health', 'pharmacy', 'medical center']):
            logger.info("🔧 Detected hospital request")
            return 'hospital'
        
        # 🔧 ENHANCED: Coffee and cafes
        if any(word in message_lower for word in ['coffee', 'cafe', 'cafes', 'coffee shop', 'tea', 'beverages']):
            logger.info("🔧 Detected cafe request")
            return 'cafe'
        
        # 🔧 ENHANCED: Gas stations
        if any(word in message_lower for word in ['gas', 'fuel', 'petrol', 'station', 'gas station', 'fuel station']):
            logger.info("🔧 Detected gas station request")
            return 'gas_station'
        
        # 🔧 ENHANCED: Banks and ATMs
        if any(word in message_lower for word in ['bank', 'banks', 'atm', 'banking', 'financial']):
            logger.info("🔧 Detected bank request")
            return 'bank'
        
        # 🔧 ENHANCED: Special handling for general place queries
        general_place_keywords = ['places', 'spots', 'locations', 'areas', 'somewhere', 'anywhere']
        if any(keyword in message_lower for keyword in general_place_keywords):
            # If it's a general place query, default to tourist attractions
            logger.info("🔧 General places query - defaulting to tourist attractions")
            return 'tourist_attraction'
        
        # Default fallback
        logger.info("🔧 Using default establishment type")
        return 'establishment'
    
    def _extract_destination(self, message: str) -> str:
        """🔧 FIXED: Extract destination from navigation request"""
        patterns = [
            # FIXED: Proper spacing for optional me/us group
            r'(?:navigate|directions?|route|guide)\s+(?:(?:me|us)\s+)?to\s+(.+)',
            r'(?:go|drive|take\s+me|head)\s+to\s+(.+)',
            r'how\s+(?:do\s+i|can\s+i)\s+get\s+to\s+(.+)',
            r'(?:show|get|give)\s+(?:me|us)\s+(?:directions?|route)\s+(?:to|for)\s+(.+)',
            r'(?:plot|plan)\s+(?:a\s+)?(?:course|route)\s+to\s+(.+)',
            # ADDED: Additional patterns for common variations
            r'directions?\s+(?:to|for)\s+(.+)',
            r'route\s+to\s+(.+)',
            r'where\s+is\s+(.+)',
            r'find\s+route\s+to\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                destination = match.group(1).strip()
                # Clean up common endings
                destination = re.sub(r'\s+(please|now|immediately)$', '', destination, flags=re.IGNORECASE)
                
                # Debug logging
                logger.info(f"🎯 Extracted destination: '{destination}' from: '{message}'")
                return destination
        
        # Debug logging for failed extraction
        logger.warning(f"❌ Failed to extract destination from: '{message}'")
        return ""
    
    def _get_helpful_fallback_response(self, message: str) -> str:
        """🔧 ENHANCED: Provide helpful fallback response with suggestions"""
        
        # Analyze what the user might have wanted
        if any(word in message for word in ['place', 'where', 'location']):
            return """🗺️ I can help you with navigation and location services! Try asking:

🔍 **Find Places:** "Find restaurants near me" or "Suggest places to visit"
📍 **Get Location:** "Where am I?" or "What's my current location?"  
🧭 **Get Directions:** "Navigate to downtown" or "How do I get to the mall?"
🌤️ **Check Weather:** "What's the weather?" or "How's the weather today?"

What would you like to explore?"""
        
        elif any(word in message for word in ['help', 'can you', 'what']):
            return """🚗 I'm your navigation assistant! Here's what I can do:

🎯 **Tourist Attractions:** "Places to visit in Eluru" or "Tourist attractions nearby"
🍽️ **Restaurants:** "Find restaurants near me" or "Good places to eat"
🏨 **Hotels:** "Find hotels nearby" or "Accommodation options"
🛕 **Temples:** "Nearest temples" or "Religious places nearby"
🛍️ **Shopping:** "Shopping malls near me" or "Markets nearby"
⛽ **Services:** "Gas stations nearby" or "Banks near me"

Just tell me what you're looking for!"""
        
        else:
            return """🗺️ I can help you with navigation and finding places! Try asking about:

• Places to visit and tourist attractions
• Restaurants, hotels, and services nearby  
• Directions and navigation to any location
• Your current location and weather information

What would you like to find or explore?"""
    
    def _is_tourist_query(self, message: str) -> bool:
        """Check if this is specifically a tourist/sightseeing query"""
        tourist_indicators = [
            'visit', 'tourist', 'attraction', 'sightseeing', 'places to visit',
            'tourist attractions', 'must visit', 'worth visiting', 'suggest places',
            'recommend places', 'interesting places', 'beautiful places', 'famous places'
        ]
        
        return any(indicator in message.lower() for indicator in tourist_indicators)

class VehicleInfoAgent(BaseAgent):
    """Vehicle information specialist agent"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("vehicle_info_agent", AgentType.VEHICLE_INFO, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        intent = intent_data.get('primary_intent', '')
        return any(word in intent for word in ['vehicle_info', 'tell me about', 'specs', 'features'])
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle vehicle information requests"""
        from tools import VehicleInfoTools
        
        # Extract vehicle name and info type
        vehicle_query = self._extract_vehicle_name(message.content)
        info_type = self._extract_info_type(message.content)
        
        result = await VehicleInfoTools.get_vehicle_info(vehicle_query, info_type)
        if result.get('success'):
            return result['message'], [f"get_vehicle_info: {vehicle_query}"], {}
        
        return "I can provide information about vehicles like Tesla Model 3, BMW 3 Series, Honda Civic, Ford F-150, and more. What would you like to know?", [], {}
    
    def _extract_vehicle_name(self, message: str) -> str:
        """Extract vehicle name from message"""
        message_lower = message.lower()
        
        vehicles = ['tesla model 3', 'bmw 3 series', 'honda civic', 'ford f-150', 'ram 1500', 'toyota tacoma']
        for vehicle in vehicles:
            if vehicle in message_lower:
                return vehicle
        
        # Look for individual makes/models
        if 'tesla' in message_lower:
            return 'tesla model 3'
        elif 'bmw' in message_lower:
            return 'bmw 3 series'
        elif 'honda' in message_lower:
            return 'honda civic'
        elif 'ford' in message_lower:
            return 'ford f-150'
        
        return 'general'
    
    def _extract_info_type(self, message: str) -> str:
        """Extract information type from message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['engine', 'power', 'performance']):
            return 'engine'
        elif any(word in message_lower for word in ['features', 'technology']):
            return 'features'
        elif any(word in message_lower for word in ['price', 'cost']):
            return 'price'
        elif any(word in message_lower for word in ['pros', 'cons']):
            return 'pros'
        else:
            return 'general'

class UserExperienceAgent(BaseAgent):
    """User experience and personalization specialist agent"""
    
    def __init__(self, memory_manager: MemoryManager):
        super().__init__("user_experience_agent", AgentType.USER_EXPERIENCE, memory_manager)
    
    async def can_handle(self, message: str, intent_data: Dict) -> bool:
        # This agent handles general queries that don't match other agents
        return intent_data.get('confidence', 0) < 0.3
    
    async def _handle_message(self, message: AgentMessage) -> Tuple[str, List[str], Dict]:
        """Handle general user experience requests"""
        return "I'm here to help you with your vehicle. I can control climate, music, navigation, and vehicle systems. What would you like me to do?", ["general_assistance"], {}

class AgentOrchestrator:
    """Orchestrates communication between multiple AI agents"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.agents: Dict[str, BaseAgent] = {}
        
    async def initialize(self):
        """Initialize all agents and memory"""
        await self.memory_manager.initialize()
        
        # Create all agents
        self.agents = {
            "master_agent": MasterAgent(self.memory_manager, self),
            "climate_agent": ClimateAgent(self.memory_manager),
            "entertainment_agent": EntertainmentAgent(self.memory_manager),
            "vehicle_control_agent": VehicleControlAgent(self.memory_manager),
            "navigation_agent": NavigationAgent(self.memory_manager),
            "vehicle_info_agent": VehicleInfoAgent(self.memory_manager),
            "user_experience_agent": UserExperienceAgent(self.memory_manager)
        }
        
        logger.info(f"✅ Initialized {len(self.agents)} AI agents with Groq AI fallback")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process message through master agent"""
        try:
            return await self.agents["master_agent"].process_message(message)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return AgentMessage(
                content="I'm experiencing technical difficulties. Please try again.",
                user_id=message.user_id,
                timestamp=datetime.now(),
                agent_id="orchestrator_error"
            )
    
    async def get_vehicle_status(self, user_id: str) -> Dict:
        """Get comprehensive vehicle status"""
        from tools import get_complete_vehicle_state
        return get_complete_vehicle_state()
    
    def get_memory_manager(self) -> MemoryManager:
        """Get memory manager instance"""
        return self.memory_manager