import asyncio
from phi3_intent import classify_intent_with_phi3

async def main():
    # prompt = "What are all the current in-process tickets currently in Jira?"
    prompt = "What were the meeting notes from the last standup?"
    result = await classify_intent_with_phi3(prompt)
    

if __name__ == "__main__":
    asyncio.run(main())