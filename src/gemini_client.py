#!/usr/bin/env python3
"""
Gemini API Client for Dataset Generation
Wrapper around Google's Generative AI SDK
"""

import os
import time
from typing import List, Dict, Optional
import google.generativeai as genai


class GeminiClient:
    """Client for Google Gemini API with retry logic and error handling"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google API key
            model: Gemini model name
        """
        self.api_key = api_key
        self.model_name = model
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(model)
    
    def generate_response(
        self, 
        messages: List[Dict], 
        temperature: float = 0.7,
        max_tokens: int = 300,
        retry_count: int = 0,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Generate response from Gemini API
        
        Args:
            messages: List of message dicts (OpenAI format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            retry_count: Current retry attempt
            max_retries: Maximum retry attempts
            
        Returns:
            Generated text or None if failed
        """
        try:
            # Convert OpenAI format messages to Gemini format
            prompt = self._convert_messages_to_prompt(messages)
            
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=0.8,
                top_k=10
            )
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings={
                    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
            )
            
            return response.text
            
        except Exception as e:
            print(f"\nGemini API Error: {e}")
            
            # Retry logic with exponential backoff
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                return self.generate_response(
                    messages, temperature, max_tokens, retry_count + 1, max_retries
                )
            
            return None
    
    def _convert_messages_to_prompt(self, messages: List[Dict]) -> str:
        """
        Convert OpenAI format messages to single prompt for Gemini
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Single prompt string
        """
        prompt_parts = []
        
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System Instructions:\n{content}\n")
            elif role == 'user':
                prompt_parts.append(f"User: {content}\n")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}\n")
        
        return "\n".join(prompt_parts)
    
    def test_connection(self) -> bool:
        """
        Test connection to Gemini API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_prompt = "Hello, this is a test message."
            response = self.model.generate_content(test_prompt)
            return response.text is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


def create_gemini_client(config: Dict) -> Optional[GeminiClient]:
    """
    Factory function to create Gemini client
    
    Args:
        config: Configuration dict with Gemini settings
        
    Returns:
        GeminiClient instance or None if failed
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    try:
        client = GeminiClient(
            api_key=api_key,
            model=config['gemini']['model']
        )
        
        # Test connection
        if not client.test_connection():
            print("⚠ Warning: Gemini connection test failed")
            return None
            
        return client
        
    except Exception as e:
        print(f"Failed to create Gemini client: {e}")
        return None