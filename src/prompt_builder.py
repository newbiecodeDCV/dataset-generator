"""
Prompt Builder - Create few-shot prompts for OpenAI API
Xây dựng prompts với few-shot examples
"""

import json
import random
from typing import List, Dict, Optional


class PromptBuilder:
    def __init__(self, 
                 system_prompt_file: str = "./prompts/system_prompt.txt",
                 few_shot_file: str = "./prompts/few_shot_examples.json",
                 num_examples: int = 3):
        """
        Initialize prompt builder
        
        Args:
            system_prompt_file: Path to system prompt template
            few_shot_file: Path to few-shot examples JSON
            num_examples: Number of examples to include in prompt
        """
        self.system_prompt = self._load_system_prompt(system_prompt_file)
        self.few_shot_examples = self._load_few_shot_examples(few_shot_file)
        self.num_examples = num_examples
    
    def _load_system_prompt(self, file_path: str) -> str:
        """Load system prompt from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "Bạn là chuyên gia tạo dữ liệu code-switching Việt-Anh."
    
    def _load_few_shot_examples(self, file_path: str) -> List[Dict]:
        """Load few-shot examples from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def build_few_shot_prompt(self, 
                              context: str, 
                              domain: str, 
                              difficulty: str) -> str:
        """
        Build few-shot user prompt with examples
        
        Args:
            context: Meeting context (e.g., "daily_standup", "sprint_planning")
            domain: Business domain (e.g., "software_development")
            difficulty: Difficulty level ("easy", "hard", "mixed")
            
        Returns:
            Complete user prompt with few-shot examples
        """
        # Select relevant examples (prefer same difficulty)
        selected_examples = self._select_examples(difficulty)
        
        # Build examples section
        examples_text = "Dưới đây là các ví dụ mẫu về code-switching trong meeting:\n\n"
        
        for i, example in enumerate(selected_examples, 1):
            # Use ADACS format directly from few-shot examples
            example_json = {
                "origin": example.get("origin", ""),
                "spoken": example.get("spoken", ""),
                "en_word": example.get("en_word", []),
                "vi_spoken_word": example.get("vi_spoken_word", []),
                "type": example.get("type", "easy"),
                "en_phrase": example.get("en_phrase", [])
            }
            examples_text += f"[Ví dụ {i}]\n"
            examples_text += json.dumps(example_json, ensure_ascii=False, indent=2)
            examples_text += "\n\n"
        
        # Build context-specific instruction
        context_guidance = self._get_context_guidance(context, domain, difficulty)
        
        instruction = f"""---

Bây giờ hãy tạo 1 câu mới cho:
- Bối cảnh: {self.format_context_name(context)}
- Lĩnh vực: {domain}
- Độ khó: {difficulty}

{context_guidance}

CHỈ trả về JSON (KHÔNG thêm ```json), theo format như ví dụ trên."""
        
        return examples_text + instruction
    
    def _select_examples(self, difficulty: str) -> List[Dict]:
        """
        Select few-shot examples, preferring similar difficulty
        
        Args:
            difficulty: Target difficulty level
            
        Returns:
            List of selected examples
        """
        if not self.few_shot_examples:
            return []
        
        # Separate examples by difficulty
        same_difficulty = [ex for ex in self.few_shot_examples if ex.get("type", ex.get("difficulty")) == difficulty]
        other_examples = [ex for ex in self.few_shot_examples if ex.get("type", ex.get("difficulty")) != difficulty]
        
        # Select examples
        selected = []
        
        # Prioritize same difficulty
        if same_difficulty:
            selected.extend(random.sample(same_difficulty, min(2, len(same_difficulty))))
        
        # Add some variety
        remaining = self.num_examples - len(selected)
        if remaining > 0 and other_examples:
            selected.extend(random.sample(other_examples, min(remaining, len(other_examples))))
        
        return selected[:self.num_examples]
    
    def get_system_prompt(self) -> str:
        """Get the system prompt"""
        return self.system_prompt
    
    def build_messages(self, context: str, domain: str, difficulty: str) -> List[Dict]:
        """
        Build complete messages array for OpenAI API
        
        Args:
            context: Meeting context
            domain: Business domain
            difficulty: Difficulty level
            
        Returns:
            List of message dicts for OpenAI API
        """
        return [
            {
                "role": "system",
                "content": self.get_system_prompt()
            },
            {
                "role": "user",
                "content": self.build_few_shot_prompt(context, domain, difficulty)
            }
        ]
    
    def format_context_name(self, context: str) -> str:
        """Format context name to human-readable Vietnamese"""
        context_map = {
            "daily_standup": "Daily Standup Meeting",
            "sprint_planning": "Sprint Planning Meeting",
            "client_presentation": "Thuyết trình cho Client",
            "technical_discussion": "Thảo luận Kỹ thuật",
            "performance_review": "Đánh giá Hiệu suất",
            "training_session": "Buổi Training",
            "team_meeting": "Họ p Team"
        }
        return context_map.get(context, context)
    
    def _get_context_guidance(self, context: str, domain: str, difficulty: str) -> str:
        """Get context-specific guidance for generating natural sentences"""
        
        context_guides = {
            "daily_standup": {
                "scenario": "Báo cáo tiến độ công việc hàng ngày",
                "common_phrases": ["hôm qua em đã", "hôm nay em sẽ", "có issue nào không", "task nào block"],
                "keywords": ["task", "issue", "block", "fix", "bug", "code", "commit", "push"]
            },
            "sprint_planning": {
                "scenario": "Lên kế hoạch và ưẼ lượng công việc cho Sprint",
                "common_phrases": ["Sprint này cần", "estimate bao nhiêu", "user story nào priority", "capacity của team"],
                "keywords": ["Sprint", "backlog", "user story", "estimate", "priority", "capacity", "velocity"]
            },
            "client_presentation": {
                "scenario": "Trình bày và demo sản phẩm cho khách hàng",
                "common_phrases": ["chúng tôi sẽ demo", "feature này giúp", "khách hàng có thể", "performance cải thiện"],
                "keywords": ["demo", "feature", "dashboard", "analytics", "user experience", "performance"]
            },
            "technical_discussion": {
                "scenario": "Thảo luận giải pháp kỹ thuật và kiến trúc hệ thống",
                "common_phrases": ["architecture này", "implement sao", "API nào support", "database optimize"],
                "keywords": ["API", "database", "architecture", "framework", "integration", "deployment"]
            },
            "performance_review": {
                "scenario": "Đánh giá kết quả công việc và KPI",
                "common_phrases": ["KPI tháng này", "target đạt chưa", "performance cải thiện", "skill nào cần học"],
                "keywords": ["KPI", "target", "performance", "achievement", "goal", "skill"]
            },
            "training_session": {
                "scenario": "Hướng dẫn và đào tạo kỹ năng",
                "common_phrases": ["training hôm nay về", "skill này quan trọng", "practice thêm", "có question không"],
                "keywords": ["training", "skill", "practice", "workshop", "tutorial", "guide"]
            },
            "team_meeting": {
                "scenario": "Họ p team tổng quát và đồng bộ thông tin",
                "common_phrases": ["team mình cần", "project tiến độ sao", "deadline bên nào", "resource đủ chưa"],
                "keywords": ["project", "deadline", "resource", "timeline", "update", "sync"]
            }
        }
        
        guide = context_guides.get(context, {"scenario": "Cuộc họ p công việc", "keywords": ["meeting", "team"]})
        
        guidance = f"Tình huống: {guide['scenario']}\n"
        
        if difficulty == "easy":
            guidance += "Gợi ý: Dùng 1-2 từ tiếng Anh đơn giản, xen kẽ tự nhiên"
        elif difficulty == "hard": 
            guidance += "Gợi ý: Dùng nhiều thuật ngữ chuyên môn, cụm từ liên tiếp"
        else:  # mixed
            guidance += "Gợi ý: Kết hợp từ đơn giản và thuật ngữ chuyên môn"
        
        return guidance


# Example usage
if __name__ == "__main__":
    builder = PromptBuilder()
    
    print("=== Prompt Builder Test ===\n")
    
    # Test building messages
    messages = builder.build_messages(
        context="sprint_planning",
        domain="software_development",
        difficulty="hard"
    )
    
    print("System Prompt:")
    print(messages[0]["content"])
    print("\n" + "="*50 + "\n")
    
    print("User Prompt:")
    print(messages[1]["content"])