#!/usr/bin/env python3
"""
Test script for Gemini integration
Kiểm tra xem Gemini API có hoạt động không
"""

import os
import yaml
from dotenv import load_dotenv
from src.gemini_client import create_gemini_client

def test_gemini_basic():
    """Test basic Gemini functionality"""
    print("🧪 Testing Gemini Basic Functionality...")
    
    # Load environment
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("Please add it to .env file:")
        print("GEMINI_API_KEY=your_api_key_here")
        return False
    
    print(f"✓ API key found: {api_key[:10]}...")
    
    # Load config
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✓ Config loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Create client
    try:
        client = create_gemini_client(config)
        if not client:
            print("❌ Failed to create Gemini client")
            return False
        print("✓ Gemini client created successfully")
    except Exception as e:
        print(f"❌ Error creating Gemini client: {e}")
        return False
    
    # Test simple generation
    try:
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in Vietnamese."}
        ]
        
        response = client.generate_response(
            messages=test_messages,
            temperature=0.7,
            max_tokens=50
        )
        
        if response:
            print(f"✓ Test response: {response[:100]}...")
            return True
        else:
            print("❌ No response from Gemini")
            return False
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return False

def test_gemini_with_generator():
    """Test Gemini with main generator"""
    print("\n🧪 Testing Gemini with Dataset Generator...")
    
    # Update config to use Gemini temporarily  
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Backup original provider
        original_provider = config.get('ai_provider', 'openai')
        
        # Set to Gemini
        config['ai_provider'] = 'gemini'
        
        # Save temp config
        with open('config_gemini_test.yaml', 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print("✓ Created test config with Gemini provider")
        
        # Try to initialize generator
        from generate_dataset import MeetingDatasetGenerator
        
        generator = MeetingDatasetGenerator('config_gemini_test.yaml')
        print(f"✓ Generator initialized with provider: {generator.provider}")
        
        # Test single sample generation (but don't actually generate)
        print("✓ Generator ready for Gemini usage")
        
        # Cleanup
        os.remove('config_gemini_test.yaml')
        print("✓ Test config cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in generator test: {e}")
        # Cleanup on error
        if os.path.exists('config_gemini_test.yaml'):
            os.remove('config_gemini_test.yaml')
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 GEMINI INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Basic functionality
    test1_passed = test_gemini_basic()
    
    # Test 2: Integration with generator
    test2_passed = test_gemini_with_generator()
    
    # Results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Basic Gemini Test:      {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Generator Integration:  {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Gemini integration ready to use.")
        print("\nTo use Gemini:")
        print("1. Edit config.yaml and change ai_provider to 'gemini'") 
        print("2. Make sure GEMINI_API_KEY is set in .env")
        print("3. Run: python generate_dataset.py --test")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()