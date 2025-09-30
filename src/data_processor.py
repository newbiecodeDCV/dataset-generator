"""
Data Processor - Convert LLM output to ADACS format
Xử lý output từ LLM và chuyển sang format ADACS
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from .pronunciation_engine import PronunciationEngine


class DataProcessor:
    def __init__(self, pronunciation_engine: PronunciationEngine):
        """
        Initialize data processor
        
        Args:
            pronunciation_engine: PronunciationEngine instance for transcription
        """
        self.pronunciation_engine = pronunciation_engine
    
    def parse_llm_response(self, response: str) -> Optional[Dict]:
        """
        Parse LLM response to extract structured data
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Parsed dict with text, context, en_words, difficulty or None if failed
        """
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            
            # Parse JSON
            data = json.loads(response)
            
            # Validate required fields
            required_fields = ["text", "context", "en_words", "difficulty"]
            if all(field in data for field in required_fields):
                return data
            else:
                print(f"Missing required fields in LLM response: {data}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from LLM response: {e}")
            print(f"Response: {response[:200]}...")
            return None
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None
    
    def extract_english_phrases(self, text: str, en_words: List[str]) -> List[str]:
        """
        Extract English phrases from text
        
        Args:
            text: Original text with English words
            en_words: List of English words
            
        Returns:
            List of English phrases (can include single words and multi-word phrases)
        """
        phrases = []
        
        # Add all individual words
        phrases.extend(en_words)
        
        # Find multi-word phrases (consecutive English words)
        words_in_text = text.split()
        
        i = 0
        while i < len(words_in_text):
            # Check if current word is English
            if words_in_text[i] in en_words:
                # Try to build a phrase
                phrase_words = [words_in_text[i]]
                j = i + 1
                
                while j < len(words_in_text) and words_in_text[j] in en_words:
                    phrase_words.append(words_in_text[j])
                    j += 1
                
                # If we found a multi-word phrase, add it
                if len(phrase_words) > 1:
                    phrases.append(" ".join(phrase_words))
                
                i = j
            else:
                i += 1
        
        # Remove duplicates while preserving order
        seen = set()
        unique_phrases = []
        for phrase in phrases:
            if phrase not in seen:
                seen.add(phrase)
                unique_phrases.append(phrase)
        
        return unique_phrases
    
    def build_adacs_format(self, 
                          origin_text: str, 
                          en_words: List[str],
                          context: str,
                          difficulty: str) -> Dict:
        """
        Build complete ADACS format data entry
        
        Args:
            origin_text: Original Vietnamese text with English words
            en_words: List of English words
            context: Meeting context
            difficulty: Difficulty level
            
        Returns:
            Complete ADACS format dict
        """
        # Generate Vietnamese pronunciations for English words
        vi_spoken_words = self.pronunciation_engine.transcribe_multiple(en_words)
        
        # Build spoken text (lowercase, with pronunciations)
        spoken_text = self._build_spoken_text(origin_text, en_words, vi_spoken_words)
        
        # Extract English phrases
        en_phrases = self.extract_english_phrases(origin_text, en_words)
        
        # Build complete entry
        entry = {
            "origin": origin_text,
            "spoken": spoken_text,
            "en_word": en_words,
            "vi_spoken_word": vi_spoken_words,
            "type": difficulty,
            "en_phrase": en_phrases
        }
        
        return entry
    
    def _build_spoken_text(self, 
                          origin_text: str, 
                          en_words: List[str], 
                          vi_spoken_words: List[str]) -> str:
        """
        Build spoken text by replacing English words with Vietnamese pronunciations
        
        Args:
            origin_text: Original text
            en_words: List of English words
            vi_spoken_words: List of Vietnamese pronunciations
            
        Returns:
            Spoken text (lowercase, with pronunciations)
        """
        # Start with lowercase origin
        spoken = origin_text.lower()
        
        # Create replacement mapping
        replacements = {}
        for en_word, vi_word in zip(en_words, vi_spoken_words):
            replacements[en_word.lower()] = vi_word
        
        # Sort by length (longest first) to handle overlapping words
        sorted_en_words = sorted(replacements.keys(), key=len, reverse=True)
        
        # Replace English words with Vietnamese pronunciations
        for en_word in sorted_en_words:
            # Use word boundaries to avoid partial replacements
            pattern = r'\b' + re.escape(en_word) + r'\b'
            spoken = re.sub(pattern, replacements[en_word], spoken, flags=re.IGNORECASE)
        
        return spoken
    
    def process_llm_to_adacs(self, llm_response: str) -> Optional[Dict]:
        """
        Complete pipeline: LLM response → ADACS format
        
        Args:
            llm_response: Raw response from LLM
            
        Returns:
            Complete ADACS format entry or None if processing failed
        """
        # Parse LLM response
        parsed = self.parse_llm_response(llm_response)
        if not parsed:
            return None
        
        # Build ADACS format
        try:
            adacs_entry = self.build_adacs_format(
                origin_text=parsed["text"],
                en_words=parsed["en_words"],
                context=parsed["context"],
                difficulty=parsed["difficulty"]
            )
            return adacs_entry
        except Exception as e:
            print(f"Error building ADACS format: {e}")
            return None


# Example usage
if __name__ == "__main__":
    from pronunciation_engine import PronunciationEngine
    
    # Initialize
    pronunciation = PronunciationEngine()
    processor = DataProcessor(pronunciation)
    
    # Test with sample LLM response
    sample_response = """{
  "text": "Team Leader yêu cầu update status của Sprint Planning Meeting này",
  "context": "sprint_planning",
  "en_words": ["Team", "Leader", "update", "status", "Sprint", "Planning", "Meeting"],
  "difficulty": "hard"
}"""
    
    print("=== Data Processor Test ===\n")
    print("Input LLM Response:")
    print(sample_response)
    print("\n" + "="*50 + "\n")
    
    # Process
    result = processor.process_llm_to_adacs(sample_response)
    
    if result:
        print("Output ADACS Format:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Processing failed!")