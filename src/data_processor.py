"""
Data Processor - Chuyển đổi output LLM sang format ADACS

Xử lý và chuyển đổi kết quả từ LLM thành format ADACS chuẩn.
Tích hợp pronunciation engine để auto-fix các lỗi phiên âm.

Tính năng chính:
- Parse và validate JSON output từ LLM
- Auto-fix từ tiếng Anh chưa được phiên âm
- Xây dựng spoken text với phiên âm chính xác
- Trích xuất English phrases từ origin text

Author: Dataset Generator Team
"""

import json
import re
from typing import Dict, List, Tuple, Optional


class DataProcessor:
    """
    Lớp xử lý dữ liệu chính trong pipeline.
    
    Chuyển đổi output từ LLM thành format ADACS chuẩn và tự động
    sửa các lỗi phiên âm phổ biến.
    
    Attributes:
        pronunciation_engine: Engine xử lý phiên âm tiếng Anh
    """
    def __init__(self, pronunciation_engine, use_ai_pronunciation: bool = False, ai_client=None):
        """
        Khởi tạo DataProcessor với pronunciation engine.
        
        Args:
            pronunciation_engine: Instance của PronunciationEngine để xử lý phiên âm
            use_ai_pronunciation: (Deprecated - bị bỏ qua)
            ai_client: (Deprecated - bị bỏ qua)
        """
        self.pronunciation_engine = pronunciation_engine
    
    def parse_llm_response(self, response: str) -> Optional[Dict]:
        """
        Phân tích response từ LLM để trích xuất dữ liệu có cấu trúc.
        
        Args:
            response: Raw response từ LLM (string JSON)
            
        Returns:
            Dict đã parse - ADACS format hoặc simple format
            None nếu parse thất bại
        """
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            
            # Parse JSON
            data = json.loads(response)
            
            # Check if it's ADACS format (direct from LLM)
            adacs_fields = ["origin", "spoken", "en_word", "vi_spoken_word", "type", "en_phrase"]
            if all(field in data for field in adacs_fields):
                return data
            
            # Check if it's simple format (needs processing)
            simple_fields = ["text", "context", "en_words", "difficulty"]
            if all(field in data for field in simple_fields):
                return data
            
            # If neither format matches
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
        Trích xuất các cụm từ tiếng Anh từ văn bản.
        
        Args:
            text: Văn bản gốc chứa các từ tiếng Anh
            en_words: Danh sách các từ tiếng Anh rời rạc
            
        Returns:
            Danh sách các phrase tiếng Anh (bao gồm từ đơn và cụm từ)
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
        Xây dựng entry hoàn chỉnh theo format ADACS.
        
        Args:
            origin_text: Văn bản tiếng Việt gốc có chứa từ tiếng Anh
            en_words: Danh sách các từ tiếng Anh
            context: Bối cảnh cuộc họp
            difficulty: Mức độ khó
            
        Returns:
            Dict hoàn chỉnh theo format ADACS
        """
        # Generate Vietnamese pronunciations for English words
        vi_spoken_words = self.pronunciation_engine.transcribe_multiple(en_words)
        
        # Validate and auto-fix pronunciations
        vi_spoken_words = self._validate_and_fix_pronunciations(en_words, vi_spoken_words)
        
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
    
    def _validate_and_fix_pronunciations(self, en_words: List[str], vi_spoken_words: List[str]) -> List[str]:
        """
        Validate và tự động sửa phiên âm nếu cần
        
        Args:
            en_words: Danh sách các từ tiếng Anh
            vi_spoken_words: Danh sách phiên âm tiếng Việt từ LLM
            
        Returns:
            Danh sách phiên âm đã được sửa lỗi
        """
        fixed_pronunciations = []
        
        for en_word, vi_word in zip(en_words, vi_spoken_words):
            # Kiểm tra xem vi_word có phải là tiếng Anh không (tức là LLM không phiên âm)
            # Nếu giống y hệt từ gốc (lowercase) => chưa được phiên âm
            if vi_word.lower() == en_word.lower():
                # Auto-fix: Gọi pronunciation engine
                corrected = self.pronunciation_engine.transcribe(en_word)
                print(f"  ⚠️  Auto-fixed: '{en_word}' → '{corrected}' (was '{vi_word}')")
                fixed_pronunciations.append(corrected)
            else:
                fixed_pronunciations.append(vi_word)
        
        return fixed_pronunciations
    
    def _build_spoken_text(self, 
                          origin_text: str, 
                          en_words: List[str], 
                          vi_spoken_words: List[str]) -> str:
        """
        Xây dựng spoken text bằng cách thay thế các từ tiếng Anh bằng phiên âm.
        
        Args:
            origin_text: Văn bản gốc
            en_words: Danh sách các từ tiếng Anh
            vi_spoken_words: Danh sách phiên âm tiếng Việt
            
        Returns:
            Văn bản spoken (chữ thường, có phiên âm)
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
        Pipeline hoàn chỉnh: LLM response → ADACS format.
        
        Args:
            llm_response: Raw response từ LLM
            
        Returns:
            Entry ADACS format hoàn chỉnh hoặc None nếu xử lý thất bại
        """
        # Parse LLM response
        parsed = self.parse_llm_response(llm_response)
        if not parsed:
            return None
        
        # Check if it's already in ADACS format
        adacs_fields = ["origin", "spoken", "en_word", "vi_spoken_word", "type", "en_phrase"]
        if all(field in parsed for field in adacs_fields):
            # Already in ADACS format, but VALIDATE AND FIX pronunciations
            print("\n  🔍 Validating LLM-generated pronunciations...")
            
            # Validate and fix vi_spoken_word
            original_vi_words = parsed["vi_spoken_word"].copy() if isinstance(parsed["vi_spoken_word"], list) else []
            parsed["vi_spoken_word"] = self._validate_and_fix_pronunciations(
                parsed["en_word"], 
                parsed["vi_spoken_word"]
            )
            
            # Rebuild spoken text with corrected pronunciations
            parsed["spoken"] = self._build_spoken_text(
                parsed["origin"],
                parsed["en_word"],
                parsed["vi_spoken_word"]
            )
            
            # Ensure lowercase
            parsed["spoken"] = parsed["spoken"].lower()
            
            return parsed
        
        # Otherwise, build ADACS format from simple format
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


# Ví dụ sử dụng
if __name__ == "__main__":
    from pronunciation_engine import PronunciationEngine
    
    # Khởi tạo
    pronunciation = PronunciationEngine()
    processor = DataProcessor(pronunciation)
    
    # Test với sample LLM response
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
    
    # Xử lý
    result = processor.process_llm_to_adacs(sample_response)
    
    if result:
        print("Output ADACS Format:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Xử lý thất bại!")
