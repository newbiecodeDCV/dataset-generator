"""
ADACS Format Validator - Validate dataset compliance
Kiểm tra định dạng ADACS
"""

from typing import Dict, List, Tuple, Optional
from collections import Counter


class ADACSValidator:
    def __init__(self):
        """Initialize validator"""
        self.required_fields = ["origin", "spoken", "en_word", "vi_spoken_word", "type", "en_phrase"]
        self.valid_types = ["easy", "hard", "mixed"]
    
    def validate_sample(self, sample: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single ADACS sample
        
        Args:
            sample: ADACS format dict
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in sample:
                errors.append(f"Missing required field: {field}")
        
        # If missing fields, return early
        if errors:
            return False, errors
        
        # Validate field types
        if not isinstance(sample["origin"], str):
            errors.append("'origin' must be a string")
        
        if not isinstance(sample["spoken"], str):
            errors.append("'spoken' must be a string")
        
        if not isinstance(sample["en_word"], list):
            errors.append("'en_word' must be a list")
        elif len(sample["en_word"]) == 0:
            errors.append("'en_word' cannot be empty")
        
        if not isinstance(sample["vi_spoken_word"], list):
            errors.append("'vi_spoken_word' must be a list")
        
        if not isinstance(sample["en_phrase"], list):
            errors.append("'en_phrase' must be a list")
        
        # Validate type field
        if sample["type"] not in self.valid_types:
            errors.append(f"'type' must be one of {self.valid_types}, got '{sample['type']}'")
        
        # Validate alignment between en_word and vi_spoken_word
        if len(sample["en_word"]) != len(sample["vi_spoken_word"]):
            errors.append(
                f"Mismatch: en_word has {len(sample['en_word'])} items, "
                f"vi_spoken_word has {len(sample['vi_spoken_word'])} items"
            )
        
        # Validate that spoken is lowercase
        if sample["spoken"] != sample["spoken"].lower():
            errors.append("'spoken' must be all lowercase")
        
        # Validate that en_words appear in origin
        origin_lower = sample["origin"].lower()
        for en_word in sample["en_word"]:
            if en_word.lower() not in origin_lower:
                errors.append(f"English word '{en_word}' not found in origin text")
        
        # Validate that vi_spoken_words appear in spoken
        for vi_word in sample["vi_spoken_word"]:
            if vi_word not in sample["spoken"]:
                errors.append(f"Vietnamese pronunciation '{vi_word}' not found in spoken text")
        
        return len(errors) == 0, errors
    
    def validate_dataset(self, dataset: List[Dict]) -> Dict:
        """
        Validate entire dataset and return statistics
        
        Args:
            dataset: List of ADACS format samples
            
        Returns:
            Statistics dict with validation results
        """
        stats = {
            "total_samples": len(dataset),
            "valid_samples": 0,
            "invalid_samples": 0,
            "errors": [],
            "type_distribution": Counter(),
            "avg_en_words_per_sample": 0,
            "avg_text_length": 0,
        }
        
        total_en_words = 0
        total_text_length = 0
        
        for i, sample in enumerate(dataset):
            is_valid, errors = self.validate_sample(sample)
            
            if is_valid:
                stats["valid_samples"] += 1
                
                # Collect statistics
                stats["type_distribution"][sample["type"]] += 1
                total_en_words += len(sample["en_word"])
                total_text_length += len(sample["origin"])
            else:
                stats["invalid_samples"] += 1
                stats["errors"].append({
                    "sample_index": i,
                    "errors": errors
                })
        
        # Calculate averages
        if stats["valid_samples"] > 0:
            stats["avg_en_words_per_sample"] = total_en_words / stats["valid_samples"]
            stats["avg_text_length"] = total_text_length / stats["valid_samples"]
        
        return stats
    
    def print_validation_report(self, stats: Dict):
        """Print formatted validation report"""
        print("="*60)
        print("VALIDATION REPORT")
        print("="*60)
        
        print(f"\nTotal Samples: {stats['total_samples']}")
        print(f"Valid Samples: {stats['valid_samples']} ({stats['valid_samples']/stats['total_samples']*100:.1f}%)")
        print(f"Invalid Samples: {stats['invalid_samples']}")
        
        if stats['type_distribution']:
            print("\n--- Type Distribution ---")
            for type_name, count in stats['type_distribution'].most_common():
                print(f"  {type_name}: {count}")
        
        print(f"\nAverage English words per sample: {stats['avg_en_words_per_sample']:.1f}")
        print(f"Average text length: {stats['avg_text_length']:.0f} characters")
        
        if stats['errors']:
            print(f"\n--- Errors Found ({len(stats['errors'])}) ---")
            for error_info in stats['errors'][:5]:  # Show first 5 errors
                print(f"\nSample #{error_info['sample_index']}:")
                for error in error_info['errors']:
                    print(f"  - {error}")
            
            if len(stats['errors']) > 5:
                print(f"\n... and {len(stats['errors']) - 5} more errors")
        
        print("\n" + "="*60)


# Example usage
if __name__ == "__main__":
    validator = ADACSValidator()
    
    # Test sample
    test_sample = {
        "origin": "Team Leader yêu cầu update status của Sprint Planning Meeting này",
        "spoken": "tím lí đơ yêu cầu áp đét xờ tét tút của xờ pin pờ lán ninh mí tinh này",
        "en_word": ["Team", "Leader", "update", "status", "Sprint", "Planning", "Meeting"],
        "vi_spoken_word": ["tím", "lí đơ", "áp đét", "xờ tét tút", "xờ pin", "pờ lán ninh", "mí tinh"],
        "type": "hard",
        "en_phrase": ["Team", "Leader", "update", "status", "Sprint", "Planning", "Meeting", "Sprint Planning Meeting"]
    }
    
    print("=== Validator Test ===\n")
    is_valid, errors = validator.validate_sample(test_sample)
    
    if is_valid:
        print("✓ Sample is VALID!")
    else:
        print("✗ Sample is INVALID:")
        for error in errors:
            print(f"  - {error}")