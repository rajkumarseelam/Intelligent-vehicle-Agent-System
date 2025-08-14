"""
Smart Intent Classification for Agentic AI Vehicle Assistant
Routes user requests to appropriate agents or triggers Groq AI fallback
Comprehensive pattern matching with confidence scoring
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class IntentCategory(Enum):
    CLIMATE = "climate"
    MUSIC = "music" 
    VEHICLE_CONTROL = "vehicle_control"
    NAVIGATION = "navigation"
    VEHICLE_INFO = "vehicle_info"
    GENERAL_CONVERSATION = "general_conversation"

@dataclass
class IntentMatch:
    category: IntentCategory
    subcategory: str
    confidence: float
    matched_keywords: List[str]
    target_agent: str

class IntentClassifier:
    """Comprehensive intent classification with agent routing"""
    
    def __init__(self):
        self.intent_patterns = self._build_intent_patterns()
        self.exclusion_patterns = self._build_exclusion_patterns()
    
    def _build_intent_patterns(self) -> Dict:
        """Build comprehensive intent patterns with agent mapping"""
        return {
            # ====================== CLIMATE CONTROL ======================
            IntentCategory.CLIMATE: {
                "temperature_control": {
                    "keywords": [
                        "temperature", "temp", "degrees", "celsius", "fahrenheit",
                        "set temperature", "adjust temperature", "change temperature"
                    ],
                    "patterns": [
                        r"(?:set|change|adjust)\s+(?:the\s+)?temperature\s+to\s+(\d+)",
                        r"make\s+it\s+(\d+)\s+degrees",
                        r"temperature\s+(\d+)",
                        r"(\d+)\s*(?:degrees?|°)"
                    ],
                    "confidence": 0.95,
                    "agent": "climate_agent"
                },
                "comfort_adjustment": {
                    "keywords": [
                        "hot in here", "cold in here", "warm in here", "cool in here",
                        "too hot", "too cold", "warmer", "cooler", "heat up", "cool down",
                        "stuffy", "chilly", "freezing"
                    ],
                    "exclude_contexts": ["weather", "outside", "forecast", "find", "search", "near"],
                    "confidence": 0.85,
                    "agent": "climate_agent"
                },
                "ac_control": {
                    "keywords": [
                        "ac", "air conditioning", "air conditioner", "a/c",
                        "turn on ac", "turn off ac", "toggle ac", "start ac", "stop ac"
                    ],
                    "patterns": [
                        r"turn\s+(?:on|off)\s+(?:the\s+)?(?:ac|air\s+conditioning)",
                        r"(?:start|stop|toggle)\s+(?:the\s+)?ac"
                    ],
                    "confidence": 0.9,
                    "agent": "climate_agent"
                },
                "fan_control": {
                    "keywords": [
                        "fan", "fan speed", "ventilation", "airflow", "circulation",
                        "increase fan", "decrease fan", "fan level"
                    ],
                    "confidence": 0.85,
                    "agent": "climate_agent"
                }
            },
            
            # ====================== MUSIC CONTROL ======================
            IntentCategory.MUSIC: {
                "playback_control": {
                    "keywords": [
                        "play music", "start music", "play song", "start playing",
                        "resume music", "unpause", "begin music"
                    ],
                    "patterns": [
                        r"play\s+(?:some\s+)?music",
                        r"start\s+(?:playing\s+)?music",
                        r"resume\s+music"
                    ],
                    "confidence": 0.9,
                    "agent": "entertainment_agent"
                },
                "pause_stop": {
                    "keywords": [
                        "pause music", "stop music", "pause", "stop", "halt music",
                        "stop playing", "pause the music", "cease music"
                    ],
                    "patterns": [
                        r"(?:pause|stop)\s+(?:the\s+)?music",
                        r"(?:pause|stop)\s+playing"
                    ],
                    "confidence": 0.95,
                    "agent": "entertainment_agent"
                },
                "track_navigation": {
                    "keywords": [
                        "next song", "next track", "skip song", "skip track", "skip",
                        "previous song", "previous track", "back", "last track",
                        "go back", "skip forward", "skip backward"
                    ],
                    "patterns": [
                        r"(?:next|skip)\s+(?:song|track)",
                        r"(?:previous|back|last)\s+(?:song|track)",
                        r"go\s+back"
                    ],
                    "confidence": 0.9,
                    "agent": "entertainment_agent"
                },
                "volume_control": {
                    "keywords": [
                        "volume", "loud", "louder", "quiet", "quieter", "soft",
                        "turn up", "turn down", "increase volume", "decrease volume",
                        "mute", "unmute", "sound level"
                    ],
                    "patterns": [
                        r"(?:set|change)\s+(?:the\s+)?volume\s+to\s+(\d+)",
                        r"volume\s+(\d+)",
                        r"make\s+it\s+(?:louder|quieter|loud|quiet)"
                    ],
                    "confidence": 0.9,
                    "agent": "entertainment_agent"
                }
            },
            
            # ====================== VEHICLE CONTROL ======================
            IntentCategory.VEHICLE_CONTROL: {
                "door_control": {
                    "keywords": [
                        "lock doors", "unlock doors", "lock the doors", "unlock the doors",
                        "door locks", "secure doors", "open doors", "close doors"
                    ],
                    "patterns": [
                        r"(?:lock|unlock)\s+(?:the\s+)?doors?",
                        r"(?:secure|open)\s+(?:the\s+)?(?:car|vehicle)"
                    ],
                    "confidence": 0.95,
                    "agent": "vehicle_control_agent"
                },
                "lights_control": {
                    "keywords": [
                        "lights", "headlights", "headlamps", "turn on lights", "turn off lights",
                        "toggle lights", "vehicle lights", "car lights"
                    ],
                    "patterns": [
                        r"turn\s+(?:on|off)\s+(?:the\s+)?(?:lights?|headlights?)",
                        r"toggle\s+(?:the\s+)?lights?"
                    ],
                    "confidence": 0.9,
                    "agent": "vehicle_control_agent"
                }
            },
            
            # ====================== NAVIGATION ======================
            IntentCategory.NAVIGATION: {
                "location_query": {
                    "keywords": [
                        "where am i", "current location", "my location", "where are we",
                        "what is my location", "tell me where i am", "location"
                    ],
                    "patterns": [
                        r"where\s+am\s+i",
                        r"(?:current|my)\s+location",
                        r"where\s+are\s+we"
                    ],
                    "confidence": 0.95,
                    "agent": "navigation_agent"
                },
                "directions": {
                    "keywords": [
                        "navigate", "directions", "route", "go to", "take me to",
                        "drive to", "head to", "how to get to", "way to", "path to"
                    ],
                    "patterns": [
                        r"(?:navigate|directions?)\s+to\s+(.+)",
                        r"(?:go|drive|take\s+me)\s+to\s+(.+)",
                        r"how\s+(?:do\s+i|can\s+i)\s+get\s+to\s+(.+)"
                    ],
                    "confidence": 0.9,
                    "agent": "navigation_agent"
                },
                "place_search": {
                    "keywords": [
                        "find", "search", "locate", "look for", "where is", "nearest",
                        "nearby", "close", "around", "near me", "temple", "restaurant",
                        "hospital", "gas station", "coffee", "mall", "shopping",
                        # 🔧 ADD THESE HOTEL KEYWORDS:
                        "hotel", "hotels", "accommodation", "lodging", "stay", "guest house", "resort"
                    ],
                    "patterns": [
                        r"find\s+(.+)\s+near\s+me",
                        r"(?:where\s+is|find|locate)\s+(?:the\s+)?nearest\s+(.+)",
                        r"search\s+for\s+(.+)",
                        r"look\s+for\s+(.+)\s+(?:nearby|around|close)",
                        # 🔧 ADD THESE HOTEL PATTERNS:
                        r"find\s+(?:hotels?|accommodation|lodging)",
                        r"(?:hotels?|accommodation)\s+(?:in|near|around)",
                        r"where\s+(?:can\s+i|to)\s+stay"
                    ],
                    "confidence": 0.9,
                    "agent": "navigation_agent"
                },
                

                "weather": {
                    "keywords": [
                        "weather", "how is the weather", "what's the weather", "weather like",
                        "current weather", "weather conditions"
                    ],
                    "patterns": [
                        r"(?:what.?s|how.?s)\s+the\s+weather",
                        r"how\s+is\s+the\s+weather"
                    ],
                    "confidence": 0.95,  # Higher confidence for weather
                    "agent": "navigation_agent"
                }
            },
            
            # ====================== VEHICLE INFORMATION ======================
            IntentCategory.VEHICLE_INFO: {
                "vehicle_inquiry": {
                    "keywords": [
                        "tell me about", "information about", "details about", "specs",
                        "specifications", "features", "what is", "describe", "explain",
                        "tesla", "bmw", "honda", "ford", "model 3", "civic", "f-150"
                    ],
                    "patterns": [
                        r"tell\s+me\s+about\s+(?:the\s+)?(.+)",
                        r"(?:what|how)\s+(?:is|are)\s+(?:the\s+)?(.+)",
                        r"(?:info|information|details)\s+(?:about|on)\s+(.+)",
                        r"(?:specs|features)\s+of\s+(?:the\s+)?(.+)"
                    ],
                    "confidence": 0.8,
                    "agent": "vehicle_info_agent"
                }
            },
            
            # ====================== GENERAL CONVERSATION ======================
            IntentCategory.GENERAL_CONVERSATION: {
                "greetings": {
                    "keywords": [
                        "hello", "hi", "hey", "good morning", "good afternoon",
                        "good evening", "good night", "greetings", "howdy"
                    ],
                    "confidence": 0.9,
                    "agent": "user_experience_agent"
                },
                "general_chat": {
                    "keywords": [
                        "how are you", "what can you do", "help me", "assist me",
                        "what's up", "thank you", "thanks", "appreciate"
                    ],
                    "confidence": 0.7,
                    "agent": "user_experience_agent"
                }
            }
        }
    
    def _build_exclusion_patterns(self) -> Dict:
        """Build exclusion patterns to prevent false matches"""
        return {
            IntentCategory.CLIMATE: {
                # Don't trigger climate for weather/navigation queries
                "weather_context": ["weather", "outside", "forecast", "atmospheric"],
                "location_context": ["find", "search", "locate", "near", "place", "hotel", "restaurant"]
            }
        }
    
    def classify_intent(self, message: str) -> Dict:
        """Main intent classification function"""
        message_lower = message.lower().strip()
        
        # Find all potential matches
        all_matches = []
        
        for category, subcategories in self.intent_patterns.items():
            for subcategory, config in subcategories.items():
                confidence = self._calculate_confidence(message_lower, config, category)
                
                if confidence > 0:
                    matched_keywords = self._get_matched_keywords(message_lower, config)
                    
                    match = IntentMatch(
                        category=category,
                        subcategory=subcategory,
                        confidence=confidence,
                        matched_keywords=matched_keywords,
                        target_agent=config["agent"]
                    )
                    all_matches.append(match)
        
        # Sort by confidence and select best match
        all_matches.sort(key=lambda x: x.confidence, reverse=True)
        
        if not all_matches or all_matches[0].confidence < 0.3:
            # No clear intent - trigger Groq AI fallback
            return {
                "primary_intent": "general_conversation",
                "subcategory": "unknown",
                "confidence": 0.0,
                "target_agent": "master_agent",  # Will trigger Groq AI
                "matched_keywords": [],
                "explanation": "No specific intent detected, using general conversation"
            }
        
        best_match = all_matches[0]
        
        logger.info(f"🎯 Intent: {best_match.category.value}/{best_match.subcategory} "
                   f"(confidence: {best_match.confidence:.2f}) -> {best_match.target_agent}")
        
        return {
            "primary_intent": best_match.category.value,
            "subcategory": best_match.subcategory,
            "confidence": best_match.confidence,
            "target_agent": best_match.target_agent,
            "matched_keywords": best_match.matched_keywords,
            "explanation": f"Detected {best_match.category.value} intent with {best_match.confidence:.1%} confidence"
        }
    
    def _calculate_confidence(self, message: str, config: Dict, category: IntentCategory) -> float:
        """Calculate confidence score for intent match"""
        base_confidence = config.get("confidence", 0.5)
        score = 0.0
        
        # Check keyword matches
        keyword_score = 0
        for keyword in config["keywords"]:
            if keyword in message:
                # Multi-word keywords get higher score
                keyword_score += 0.4 if len(keyword.split()) > 1 else 0.2
        
        # Check pattern matches
        pattern_score = 0
        if "patterns" in config:
            for pattern in config["patterns"]:
                if re.search(pattern, message, re.IGNORECASE):
                    pattern_score += 0.5
                    break  # Only count one pattern match
        
        # Combine scores
        score = keyword_score + pattern_score
        
        # Apply exclusions
        if category in self.exclusion_patterns:
            exclusions = self.exclusion_patterns[category]
            
            # Check specific exclusions for this subcategory
            if "exclude_contexts" in config:
                for exclude_context in config["exclude_contexts"]:
                    if exclude_context in message:
                        score *= 0.1  # Heavily penalize excluded contexts
                        logger.info(f"🚫 Reducing score for {category.value} due to exclusion: {exclude_context}")
                        break
            
            # Check general category exclusions
            for exclusion_type, exclusion_words in exclusions.items():
                if any(word in message for word in exclusion_words):
                    score *= 0.3  # Moderate penalty for general exclusions
                    break
        
        # Scale by base confidence
        final_score = min(score * base_confidence, 1.0)
        
        # Minimum threshold
        return final_score if final_score > 0.15 else 0.0
    
    def _get_matched_keywords(self, message: str, config: Dict) -> List[str]:
        """Get list of keywords that matched in the message"""
        matched = []
        for keyword in config["keywords"]:
            if keyword in message:
                matched.append(keyword)
        return matched

# Global classifier instance
_classifier = IntentClassifier()

def classify_intent(message: str) -> Dict:
    """Main function to classify user intent"""
    return _classifier.classify_intent(message)

def explain_intent_classification(message: str) -> str:
    """Get detailed explanation of intent classification"""
    result = classify_intent(message)
    
    explanation = f"Message: '{message}'\n"
    explanation += f"Intent: {result['primary_intent']}/{result['subcategory']}\n"
    explanation += f"Confidence: {result['confidence']:.1%}\n"
    explanation += f"Target Agent: {result['target_agent']}\n"
    
    if result['matched_keywords']:
        explanation += f"Matched Keywords: {', '.join(result['matched_keywords'])}\n"
    
    explanation += f"Explanation: {result['explanation']}"
    
    return explanation

# Example usage and testing
if __name__ == "__main__":
    test_messages = [
        # Climate
        "set temperature to 25",
        "it's too hot in here",
        "turn on the AC",
        
        # Music
        "play music",
        "pause the music",
        "next song please",
        "set volume to 70",
        
        # Vehicle Control
        "lock the doors",
        "turn on headlights",
        
        # Navigation
        "where am i",
        "find restaurants near me",
        "navigate to downtown",
        "what's the weather",
        "find hotels near me",  # Test hotel search
        
        # Vehicle Info
        "tell me about tesla model 3",
        "features of BMW 3 series",
        
        # General
        "hello there",
        "how are you doing",
        "what's 2+2",  # Should trigger Groq AI
        "tell me a joke"  # Should trigger Groq AI
    ]
    
    print("🧪 Testing Intent Classification:")
    print("=" * 50)
    
    for message in test_messages:
        result = classify_intent(message)
        print(f"\n'{message}'")
        print(f"  → {result['primary_intent']}/{result['subcategory']}")
        print(f"  → Agent: {result['target_agent']}")
        print(f"  → Confidence: {result['confidence']:.1%}")
        
        if result['confidence'] < 0.3:
            print(f"  → 🤖 Will use Groq AI fallback")