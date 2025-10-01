"""
Regtag Pronunciation Engine - Phiên âm chính xác từ regtag_v3.json

Engine phiên âm sạch và hiệu quả với ưu tiên tuyệt đối cho regtag_v3.json.
Luôn lấy phiên âm đầu tiên (chuẩn nhất) cho mỗi từ.

Ưu tiên xử lý:
1. Cache (tốc độ)
2. regtag_v3.json (độ chính xác cao nhất - 128k+ từ)
3. pronunciation_rules.json (backup cho từ chuyên ngành)
4. Fallback (giữ nguyên từ gốc)

Author: Dataset Generator Team
"""

import json
import os
from typing import Dict, List, Optional
import logging


class RegtagPronunciationEngine:
    """
    Engine phiên âm chính xác với logic rõ ràng
    
    Ưu tiên xử lý:
    1. regtag_v3.json (Ưu tiên tuyệt đối - lấy phiên âm đầu tiên)
    2. pronunciation_rules.json (backup cho từ chuyên ngành)
    3. Cache (tốc độ)
    4. Fallback (giải pháp cuối cùng)
    
    Tính năng:
    - Lấy phiên âm chính xác từ 128k+ từ trong regtag_v3.json
    - Thống kê chi tiết nguồn phiên âm
    - Báo cáo từ thiếu trong dictionary
    """
    
    def __init__(self, 
                 regtag_path: str = '/home/hiennt/Downloads/regtag_v3.json',
                 rules_file: str = './data/pronunciation_rules.json',
                 cache_file: str = './data/pronunciation_cache.json'):
        """Initialize with regtag as absolute priority"""
        self.regtag_path = regtag_path
        self.rules_file = rules_file
        self.cache_file = cache_file
        
        # Load data
        self.regtag = self._load_regtag()
        self.rules = self._load_rules()
        self.cache = {}  # In-memory cache only
        
        # Statistics
        self.stats = {
            'total_calls': 0,
            'regtag_hits': 0,
            'rules_hits': 0,
            'cache_hits': 0,
            'fallback_used': 0
        }
        
        # Logging
        logging.basicConfig(level=logging.WARNING)
        self.logger = logging.getLogger(__name__)
        
        print(f"✅ RegtagPronunciationEngine initialized:")
        print(f"   📚 Regtag: {len(self.regtag)} words")
        print(f"   📖 Rules:  {len(self.rules.get('common_words', {}))} words")
    
    def _load_regtag(self) -> Dict[str, str]:
        """
        Load regtag_v3.json
        LUÔN LẤY PHIÊN ÂM ĐẦU TIÊN (index 0)
        """
        if not os.path.exists(self.regtag_path):
            self.logger.warning(f"regtag_v3.json not found at {self.regtag_path}")
            return {}
        
        try:
            with open(self.regtag_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Process: word -> first pronunciation
            processed = {}
            for word, pronunciations in data.items():
                if pronunciations and isinstance(pronunciations, list) and len(pronunciations) > 0:
                    # LUÔN LẤY PHIÊN ÂM ĐẦU TIÊN
                    processed[word.lower()] = pronunciations[0]
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error loading regtag_v3.json: {e}")
            return {}
    
    def _load_rules(self) -> Dict:
        """Load pronunciation_rules.json as backup only"""
        if not os.path.exists(self.rules_file):
            return {"common_words": {}}
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"common_words": {}}
    
    def transcribe(self, word: str) -> str:
        """
        Transcribe English word to Vietnamese pronunciation
        
        Priority (STRICT):
        1. Cache (nhanh nhất)
        2. Regtag_v3.json (ABSOLUTE PRIORITY)
        3. Pronunciation_rules.json (backup)
        4. Fallback (cuối cùng)
        
        Returns:
            Vietnamese pronunciation (string only)
        """
        self.stats['total_calls'] += 1
        
        # 1. Check in-memory cache
        if word in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[word]
        
        word_lower = word.lower()
        result = None
        source = None
        
        # 2. Check REGTAG FIRST (ABSOLUTE PRIORITY)
        if word_lower in self.regtag:
            result = self.regtag[word_lower]
            source = 'regtag'
            self.stats['regtag_hits'] += 1
        
        # 3. Check pronunciation rules (ONLY if not in regtag)
        elif word_lower in self.rules.get('common_words', {}):
            result = self.rules['common_words'][word_lower]
            source = 'rules'
            self.stats['rules_hits'] += 1
        
        # 4. Fallback (last resort)
        else:
            result = self._simple_fallback(word_lower)
            source = 'fallback'
            self.stats['fallback_used'] += 1
            self.logger.warning(f"Using fallback for: '{word}' → '{result}'")
        
        # Cache result
        self.cache[word] = result
        
        # Debug log
        self.logger.debug(f"[{source}] {word} → {result}")
        
        return result
    
    def _simple_fallback(self, word: str) -> str:
        """
        Simple fallback for unknown words
        Just return lowercase - let human review later
        """
        # Cơ bản: giữ nguyên lowercase
        # Trong production, từ này sẽ được human review
        return word.lower()
    
    def transcribe_multiple(self, words: List[str]) -> List[str]:
        """Transcribe multiple words"""
        return [self.transcribe(word) for word in words]
    
    def get_stats(self) -> Dict:
        """Get detailed statistics"""
        total = max(self.stats['total_calls'], 1)  # Avoid division by zero
        
        return {
            **self.stats,
            'regtag_percentage': (self.stats['regtag_hits'] / total) * 100,
            'rules_percentage': (self.stats['rules_hits'] / total) * 100,
            'cache_percentage': (self.stats['cache_hits'] / total) * 100,
            'fallback_percentage': (self.stats['fallback_used'] / total) * 100
        }
    
    def report_missing_words(self) -> List[str]:
        """
        Report words that used fallback
        These need to be added to dictionaries
        """
        missing = []
        for word, pron in self.cache.items():
            word_lower = word.lower()
            # If pronunciation equals word (fallback case)
            if pron == word_lower:
                missing.append(word)
        return missing
    
    def get_pronunciation_source(self, word: str) -> str:
        """Debug: check where pronunciation comes from"""
        word_lower = word.lower()
        if word_lower in self.regtag:
            return f"regtag: {self.regtag[word_lower]}"
        elif word_lower in self.rules.get('common_words', {}):
            return f"rules: {self.rules['common_words'][word_lower]}"
        else:
            return "fallback (not found)"


# Test
if __name__ == "__main__":
    print("="*60)
    print("TESTING RegtagPronunciationEngine")
    print("="*60)
    
    engine = RegtagPronunciationEngine()
    
    # Test các từ có vấn đề trước đây
    test_words = [
        'task', 'product', 'user', 'experience',
        'pipeline', 'sync', 'align', 'optimize', 'system',
        'campaign', 'workload', 'KPI', 'Q3'
    ]
    
    print("\n" + "="*60)
    print("TRANSCRIPTION RESULTS")
    print("="*60)
    
    for word in test_words:
        result = engine.transcribe(word)
        source = engine.get_pronunciation_source(word)
        print(f"{word:15} → {result:25} [{source}]")
    
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    
    stats = engine.get_stats()
    print(f"Total words:     {stats['total_calls']}")
    print(f"From regtag:     {stats['regtag_hits']} ({stats['regtag_percentage']:.1f}%)")
    print(f"From rules:      {stats['rules_hits']} ({stats['rules_percentage']:.1f}%)")
    print(f"From cache:      {stats['cache_hits']} ({stats['cache_percentage']:.1f}%)")
    print(f"Fallback:        {stats['fallback_used']} ({stats['fallback_percentage']:.1f}%)")
    
    missing = engine.report_missing_words()
    if missing:
        print(f"\n⚠️  Missing words ({len(missing)}): {missing}")
    
    print("\n" + "="*60)
