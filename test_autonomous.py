import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from memory import AgentMemory
from command_parser import CommandParser

def test_autonomous_loop():
    print("=== Testing Memory Module ===")
    memory = AgentMemory("test_memory.db")
    memory.add_interaction("open youtube", [{"action": "open_website", "url": "https://youtube.com"}], ["ok:Opened https://youtube.com"])
    context = memory.get_recent_context()
    print("Context retrieved:")
    print(context)
    
    print("\n=== Testing Command Parser (Dynamic Response & Memory) ===")
    parser = CommandParser()
    
    # Test 1: Contextual reference "close it"
    print("\n--- Test 1: Contextual reference ---")
    stt_mock = {"text": "pa a re", "is_code_switched": False}
    print(f"User says: {stt_mock['text']}")
    commands = parser.parse(stt_mock, memory_context=context)
    print(f"Parsed Commands: {commands}")
    
    # Test 2: Dynamic Response generation (Done action)
    print("\n--- Test 2: Dynamic Response ---")
    # Simulate that we just executed an action and now we want to finish.
    stt_mock_2 = {"text": "What did you just do?"}
    context_2 = "Agent parsed actions: [{'action': 'open_website', 'url': 'https://youtube.com'}]\nSystem execution results: ['ok:Opened https://youtube.com']\n"
    commands_2 = parser.parse(stt_mock_2, memory_context=context_2)
    print(f"Parsed Commands: {commands_2}")

if __name__ == "__main__":
    test_autonomous_loop()
