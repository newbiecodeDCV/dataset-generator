#!/usr/bin/env python3
"""
Main Dataset Generator for ADACS Meeting Data

Tạo dataset code-switching Việt-Anh cho huấn luyện ASR trong bối cảnh meeting/tổng đài.
Sử dụng LLM (OpenAI/Gemini) để tạo câu tự nhiên và pronunciation engine để phiên âm chính xác.

Tính năng chính:
- Tạo câu code-switching tự nhiên theo context đa dạng
- Phiên âm chính xác từ regtag_v3.json (128k+ từ)
- Auto-fix các lỗi phiên âm từ LLM
- Validation ADACS format nghiêm ngặt
- Thống kê chi tiết chất lượng pronunciation

Author: Dataset Generator Team
"""

import os
import json
import yaml
import random
import time
import argparse
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# Import modules
from src.regtag_pronunciation_engine import RegtagPronunciationEngine
from src.prompt_builder import PromptBuilder
from src.data_processor import DataProcessor
from src.validator import ADACSValidator
from src.gemini_client import GeminiClient, create_gemini_client


class MeetingDatasetGenerator:
    """
    Lớp chính để tạo dataset code-switching cho ASR
    
    Chức năng:
    - Tích hợp LLM (OpenAI/Gemini) để tạo câu
    - Sử dụng RegtagPronunciationEngine để phiên âm chính xác
    - Auto-fix và validation ADACS format
    - Quản lý thống kê và báo cáo
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Khởi tạo dataset generator
        
        Args:
            config_path: Đường dẫn đến file cấu hình YAML
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize AI client based on provider
        self.provider = self.config.get('ai_provider', 'openai').lower()
        self.client = self._initialize_ai_client()
        
        # Initialize components
        # Use RegtagPronunciationEngine with regtag_v3.json ABSOLUTE priority
        self.pronunciation_engine = RegtagPronunciationEngine(
            regtag_path='/home/hiennt/Downloads/regtag_v3.json',
            rules_file=self.config['pronunciation']['rules_file']
        )
        self.prompt_builder = PromptBuilder(
            num_examples=self.config['few_shot']['num_examples']
        )
        # Check if AI pronunciation is enabled
        use_ai_pronunciation = self.config.get('pronunciation', {}).get('use_llm_for_complex', False)
        
        self.data_processor = DataProcessor(
            self.pronunciation_engine, 
            use_ai_pronunciation=use_ai_pronunciation,
            ai_client=self.client if use_ai_pronunciation else None
        )
        self.validator = ADACSValidator()
        
        # Statistics
        self.stats = {
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "api_errors": 0
        }
    
    def _initialize_ai_client(self) -> Union[OpenAI, GeminiClient]:
        """
        Initialize AI client based on configured provider
        
        Returns:
            OpenAI or GeminiClient instance
        """
        if self.provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            print(f"🔗 Using OpenAI API endpoint: {base_url}")
            return OpenAI(api_key=api_key, base_url=base_url)
            
        elif self.provider == 'gemini':
            client = create_gemini_client(self.config)
            if not client:
                raise ValueError("Failed to initialize Gemini client")
            return client
            
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}. Use 'openai' or 'gemini'")
    
    def _select_context_and_difficulty(self) -> tuple:
        """
        Randomly select context and difficulty based on configured weights
        
        Returns:
            (context, domain, difficulty)
        """
        # Select context based on weights
        contexts = list(self.config['meeting_contexts'].keys())
        weights = list(self.config['meeting_contexts'].values())
        context = random.choices(contexts, weights=weights)[0]
        
        # Select domain randomly
        domain = random.choice(self.config['domains'])
        
        # Select difficulty based on weights
        difficulties = list(self.config['difficulty_levels'].keys())
        diff_weights = list(self.config['difficulty_levels'].values())
        difficulty = random.choices(difficulties, weights=diff_weights)[0]
        
        return context, domain, difficulty
    
    def _call_ai_api(self, messages: List[Dict], retry_count: int = 0) -> Optional[str]:
        """
        Call AI API (OpenAI or Gemini) with retry logic
        
        Args:
            messages: List of message dicts
            retry_count: Current retry attempt
            
        Returns:
            API response content or None if failed
        """
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.config['openai']['model'],
                    messages=messages,
                    temperature=self.config['openai']['temperature'],
                    max_tokens=self.config['openai']['max_tokens']
                )
                return response.choices[0].message.content
                
            elif self.provider == 'gemini':
                return self.client.generate_response(
                    messages=messages,
                    temperature=self.config['gemini']['temperature'],
                    max_tokens=self.config['gemini']['max_tokens'],
                    max_retries=self.config['gemini']['max_retries']
                )
            
        except Exception as e:
            print(f"\n{self.provider.upper()} API Error: {e}")
            self.stats["api_errors"] += 1
            
            # Retry logic for OpenAI (Gemini handles retries internally)
            if self.provider == 'openai' and retry_count < self.config['openai']['max_retries']:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self._call_ai_api(messages, retry_count + 1)
            
            return None
    
    def generate_single_sample(self) -> Optional[Dict]:
        """
        Generate a single ADACS format sample
        
        Returns:
            ADACS format dict or None if generation failed
        """
        self.stats["total_attempts"] += 1
        
        # Select context and difficulty
        context, domain, difficulty = self._select_context_and_difficulty()
        
        # Build prompt messages
        messages = self.prompt_builder.build_messages(context, domain, difficulty)
        
        # Call AI API
        llm_response = self._call_ai_api(messages)
        if not llm_response:
            self.stats["failed"] += 1
            return None
        
        # Process response to ADACS format
        adacs_sample = self.data_processor.process_llm_to_adacs(llm_response)
        if not adacs_sample:
            self.stats["failed"] += 1
            return None
        
        # Validate sample
        is_valid, errors = self.validator.validate_sample(adacs_sample)
        if not is_valid:
            print(f"\nValidation failed: {errors}")
            self.stats["failed"] += 1
            return None
        
        self.stats["successful"] += 1
        return adacs_sample
    
    def generate_dataset(self, size: Optional[int] = None) -> List[Dict]:
        """
        Generate complete dataset
        
        Args:
            size: Number of samples to generate (overrides config)
            
        Returns:
            List of ADACS format samples
        """
        if size is None:
            size = self.config['dataset']['size']
        
        dataset = []
        batch_delay = self.config[self.provider]['batch_delay']
        
        print(f"\n{'='*60}")
        print(f"Starting dataset generation: {size} samples")
        if self.provider == 'openai':
            print(f"Provider: OpenAI - Model: {self.config['openai']['model']}")
        else:
            print(f"Provider: Gemini - Model: {self.config['gemini']['model']}")
        print(f"{'='*60}\n")
        
        pbar = tqdm(total=size, desc="Generating samples")
        
        while len(dataset) < size:
            # Generate sample
            sample = self.generate_single_sample()
            
            if sample:
                dataset.append(sample)
                pbar.update(1)
            
            # Rate limiting
            time.sleep(batch_delay)
            
            # Safety check: if too many failures, stop
            if self.stats["failed"] > size * 2:
                print("\n⚠ Too many failures. Stopping generation.")
                break
        
        pbar.close()
        
        return dataset
    
    def save_dataset(self, dataset: List[Dict], output_path: Optional[str] = None):
        """
        Save dataset to file
        
        Args:
            dataset: List of ADACS samples
            output_path: Output file path (overrides config)
        """
        if output_path is None:
            output_path = self.config['dataset']['output_file']
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Dataset saved to: {output_path}")
        print(f"  Total samples: {len(dataset)}")
    
    def print_statistics(self):
        """Print generation statistics"""
        print(f"\n{'='*60}")
        print("GENERATION STATISTICS")
        print(f"{'='*60}")
        print(f"Total attempts:    {self.stats['total_attempts']}")
        print(f"Successful:        {self.stats['successful']} ({self.stats['successful']/max(1,self.stats['total_attempts'])*100:.1f}%)")
        print(f"Failed:            {self.stats['failed']}")
        print(f"API errors:        {self.stats['api_errors']}")
        print(f"{'='*60}\n")
        
        # Print pronunciation statistics
        if hasattr(self.pronunciation_engine, 'get_stats'):
            print(f"\n{'='*60}")
            print("PRONUNCIATION QUALITY REPORT")
            print(f"{'='*60}")
            pron_stats = self.pronunciation_engine.get_stats()
            print(f"Total words transcribed: {pron_stats.get('total_calls', 0)}")
            print(f"\nSource breakdown:")
            print(f"  - From regtag_v3.json:  {pron_stats.get('regtag_hits', 0)} ({pron_stats.get('regtag_percentage', 0):.1f}%)")
            print(f"  - From rules.json:      {pron_stats.get('rules_hits', 0)} ({pron_stats.get('rules_percentage', 0):.1f}%)")
            print(f"  - From cache:           {pron_stats.get('cache_hits', 0)} ({pron_stats.get('cache_percentage', 0):.1f}%)")
            print(f"  - Fallback (low qual):  {pron_stats.get('fallback_used', 0)} ({pron_stats.get('fallback_percentage', 0):.1f}%)")
            
            # Report missing words
            if hasattr(self.pronunciation_engine, 'report_missing_words'):
                missing = self.pronunciation_engine.report_missing_words()
                if missing:
                    print(f"\n⚠️  Words not in dictionaries ({len(missing)}):")
                    for word in missing[:20]:  # Show first 20
                        print(f"     - {word}")
                    if len(missing) > 20:
                        print(f"     ... and {len(missing) - 20} more")
            print(f"{'='*60}\n")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Generate ADACS format dataset for meeting code-switching'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--output',
        help='Output file path (overrides config)'
    )
    parser.add_argument(
        '--size',
        type=int,
        help='Number of samples to generate (overrides config)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Generate only 5 samples for testing'
    )
    
    args = parser.parse_args()
    
    # Check API key based on provider in config
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            temp_config = yaml.safe_load(f)
        provider = temp_config.get('ai_provider', 'openai').lower()
        
        if provider == 'openai':
            if not os.getenv('OPENAI_API_KEY'):
                print("❌ Error: OPENAI_API_KEY environment variable not set!")
                print("Please set it in .env file or export it:")
                print("  export OPENAI_API_KEY='your-api-key-here'")
                return
        elif provider == 'gemini':
            if not os.getenv('GEMINI_API_KEY'):
                print("❌ Error: GEMINI_API_KEY environment variable not set!")
                print("Please set it in .env file or export it:")
                print("  export GEMINI_API_KEY='your-api-key-here'")
                return
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return
    
    try:
        # Initialize generator
        generator = MeetingDatasetGenerator(args.config)
        
        # Determine size
        if args.test:
            size = 5
            print("\n🧪 TEST MODE: Generating 5 samples")
        elif args.size:
            size = args.size
        else:
            size = None
        
        # Generate dataset
        dataset = generator.generate_dataset(size)
        
        # Save dataset
        generator.save_dataset(dataset, args.output)
        
        # Print statistics
        generator.print_statistics()
        
        # Validate dataset
        print("Validating dataset...")
        validation_stats = generator.validator.validate_dataset(dataset)
        generator.validator.print_validation_report(validation_stats)
        
        # Show sample
        if dataset:
            print("\n📝 Sample output:")
            print(json.dumps(dataset[0], ensure_ascii=False, indent=2))
        
        print("\n✅ Dataset generation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()