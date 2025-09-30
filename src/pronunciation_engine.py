"""
Pronunciation Engine - Convert English words to Vietnamese phonetic transcription
Chuyển đổi từ tiếng Anh sang phiên âm tiếng Việt
"""

import json
import re
from typing import Dict, List, Optional
import os


class PronunciationEngine:
    def __init__(self, rules_file: str = "./data/pronunciation_rules.json"):
        """Initialize pronunciation engine with rules"""
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.cache = {}
        
    def _load_rules(self) -> Dict:
        """Load pronunciation rules from JSON file"""
        if os.path.exists(self.rules_file):
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"common_words": {}, "special_cases": {"acronyms": {}, "compound_words": {}}}
    
    def transcribe(self, en_word: str) -> str:
        """
        Convert English word to Vietnamese phonetic transcription
        
        Args:
            en_word: English word (e.g., "Meeting", "performance")
            
        Returns:
            Vietnamese phonetic transcription (e.g., "mí tinh", "pơ phóc men")
        """
        # Check cache first
        if en_word in self.cache:
            return self.cache[en_word]
        
        # Convert to lowercase for lookup
        word_lower = en_word.lower()
        
        # Check common words dictionary
        if word_lower in self.rules.get("common_words", {}):
            result = self.rules["common_words"][word_lower]
            self.cache[en_word] = result
            return result
        
        # Check acronyms (uppercase words like API, CEO)
        if en_word.isupper() and en_word in self.rules.get("special_cases", {}).get("acronyms", {}):
            result = self.rules["special_cases"]["acronyms"][en_word]
            self.cache[en_word] = result
            return result
        
        # Check compound words
        if "-" in en_word:
            if en_word.lower() in self.rules.get("special_cases", {}).get("compound_words", {}):
                result = self.rules["special_cases"]["compound_words"][en_word.lower()]
                self.cache[en_word] = result
                return result
        
        # Fallback: Apply phonetic rules
        result = self._apply_phonetic_rules(word_lower)
        self.cache[en_word] = result
        return result
    
    def _apply_phonetic_rules(self, word: str) -> str:
        """
        Apply basic phonetic rules for unknown words
        This is a simplified fallback method
        """
        # Basic syllable-based transcription
        # This is a simplified version - can be enhanced
        result = word.lower()
        
        # Common patterns
        patterns = {
            'tion': 'sờn',
            'ing': 'inh',
            'er': 'ơ',
            'ment': 'men',
            'age': 'ịt',
            'ee': 'i',
            'oo': 'u',
        }
        
        for en_pattern, vi_pattern in patterns.items():
            if en_pattern in result:
                result = result.replace(en_pattern, vi_pattern)
        
        # Add spaces between syllables (simple heuristic)
        # For unknown words, keep as-is with minimal transformation
        return result
    
    def transcribe_phrase(self, en_phrase: str) -> str:
        """
        Transcribe an English phrase to Vietnamese phonetic
        
        Args:
            en_phrase: English phrase (e.g., "Sprint Planning Meeting")
            
        Returns:
            Vietnamese transcription (e.g., "xờ pin pờ lán ninh mí tinh")
        """
        words = en_phrase.split()
        transcribed_words = [self.transcribe(word) for word in words]
        return " ".join(transcribed_words)
    
    def transcribe_multiple(self, en_words: List[str]) -> List[str]:
        """
        Transcribe multiple English words
        
        Args:
            en_words: List of English words
            
        Returns:
            List of Vietnamese transcriptions (same order, same length)
        """
        return [self.transcribe(word) for word in en_words]
    
    def add_to_cache(self, en_word: str, vi_transcription: str):
        """Add a manual transcription to cache"""
        self.cache[en_word] = vi_transcription
    
    def get_pronunciation_stats(self) -> Dict:
        """Get statistics about pronunciations"""
        return {
            "common_words_count": len(self.rules.get("common_words", {})),
            "acronyms_count": len(self.rules.get("special_cases", {}).get("acronyms", {})),
            "compound_words_count": len(self.rules.get("special_cases", {}).get("compound_words", {})),
            "cache_size": len(self.cache)
        }


# Example usage
if __name__ == "__main__":
    engine = PronunciationEngine()
    
    # Test transcriptions
    test_words = [
        "Meeting", "deadline", "performance", "Sprint", "API", 
        "Team", "Leader", "optimize", "database"
    ]
    
    print("=== Pronunciation Engine Test ===")
    for word in test_words:
        transcription = engine.transcribe(word)
        print(f"{word:15} → {transcription}")
    
    print(f"\nStats: {engine.get_pronunciation_stats()}")