#!/usr/bin/env python3
"""
Main Dataset Generator for ADACS Meeting Data
Tạo dataset code-switching cho meeting context với format ADACS
"""

import os
import json
import yaml
import random
import time
import argparse
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# Import modules
from src.pronunciation_engine import PronunciationEngine
from src.prompt_builder import PromptBuilder
from src.data_processor import DataProcessor
from src.validator import ADACSValidator


class MeetingDatasetGenerator:
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize dataset generator
        
        Args:
            config_path: Path to configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        
        # Initialize components
        self.pronunciation_engine = PronunciationEngine(
            rules_file=self.config['pronunciation']['rules_file']
        )
        self.prompt_builder = PromptBuilder(
            num_examples=self.config['few_shot']['num_examples']
        )
        self.data_processor = DataProcessor(self.pronunciation_engine)
        self.validator = ADACSValidator()
        
        # Statistics
        self.stats = {
            "total_attempts": 0,
            "successful": 0,
            "failed": 0,
            "api_errors": 0
        }
    
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
    
    def _call_openai_api(self, messages: List[Dict], retry_count: int = 0) -> Optional[str]:
        """
        Call OpenAI API with retry logic
        
        Args:
            messages: List of message dicts
            retry_count: Current retry attempt
            
        Returns:
            API response content or None if failed
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=messages,
                temperature=self.config['openai']['temperature'],
                max_tokens=self.config['openai']['max_tokens']
            )
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"\nAPI Error: {e}")
            self.stats["api_errors"] += 1
            
            # Retry logic
            if retry_count < self.config['openai']['max_retries']:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self._call_openai_api(messages, retry_count + 1)
            
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
        
        # Call OpenAI API
        llm_response = self._call_openai_api(messages)
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
        batch_delay = self.config['openai']['batch_delay']
        
        print(f"\n{'='*60}")
        print(f"Starting dataset generation: {size} samples")
        print(f"Model: {self.config['openai']['model']}")
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
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("Please set it in .env file or export it:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
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