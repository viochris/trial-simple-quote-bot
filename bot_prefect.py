import os
from prefect import flow, task
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables (useful for local testing)
load_dotenv()

# Fetch credentials from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@task(name="Generate Quote", retries=3, retry_delay_seconds=5)
def generate_quote():
    """
    Task to generate a motivational quote using Google Gemini AI.
    """
    print("\n⏰ ACTION TIME! Initiating connection to Gemini AI...")

    try:
        # Initialize the Gemini model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.7
        )

        # Prompt instruction for the AI (Requesting English Quote)
        # If you want Indonesian quotes, change the text inside quotes below.
        prompt_text = "Create 1 short, punchy motivational quote for a programmer. Just the quote, no intro text."
        
        # Execute the prompt
        response = llm.invoke(prompt_text)
        ai_msg = response.content

        # Log the result to the terminal console
        print("------------------------------------------------")
        print(f"🤖 AI MENTOR SAYS:\n{ai_msg}")
        print("------------------------------------------------")

        return ai_msg

    except Exception as e:
        # SAFE ERROR HANDLING
        # We process the error string but do not print 'e' directly
        error_str = str(e).lower()
        
        if "401" in error_str or "api_key" in error_str:
            safe_msg = "❌ Gemini Auth Error: Invalid API Key."
        elif "429" in error_str or "quota" in error_str:
            safe_msg = "⏳ Gemini Quota Error: Rate limit exceeded."
        elif "connection" in error_str:
            safe_msg = "❌ Gemini Network Error: Failed to connect."
        else:
            safe_msg = "❌ Gemini Internal Error (Details hidden)."

        print(safe_msg)
        return safe_msg

@task(name="Send to Telegram")
def to_telegram(msg):
    """
    Task to send the generated message to a specific Telegram Chat.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Telegram credentials are missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }

    try:
        # Send POST request to Telegram API
        response = requests.post(url, json=data)
        
        # Check HTTP Status Code (200 = OK)
        if response.status_code == 200:
            print("✅ Success: Message sent to Telegram!")
        else:
            # Log the specific error from Telegram for debugging
            print(f"❌ Telegram Refused: Status Code {response.status_code}")
            print(f"📄 Error Details: {response.text}")
            
    except Exception as e:
        # SAFE ERROR HANDLING
        # Preventing the 'url' variable (containing the token) from leaking in the logs.
        error_str = str(e).lower()

        if "connection" in error_str or "dns" in error_str:
            print("❌ Network Error: Failed to connect to Telegram API.")
        elif "timeout" in error_str:
            print("⏳ Timeout Error: Telegram API did not respond.")
        elif "ssl" in error_str:
            print("🔒 SSL Error: Certificate verification failed.")
        else:
            print("❌ Telegram Send Failed: Unknown error occurred.")

@flow(name="Daily Mentor Flow", log_prints=True)
def main_flow():
    """
    Main orchestration flow:
    1. Get Quote -> 2. Send to Telegram
    """
    quote = generate_quote()
    to_telegram(quote)

if __name__ == "__main__":
    # ==========================================
    # 🚀 EXECUTION MODE
    # ==========================================

    # --- OPTION 1: FOR GITHUB ACTIONS (ACTIVE) ---
    # This calls the function immediately (Run Once).
    # GitHub's YAML scheduler handles the timing (CRON).
    # When finished, the script exits to save server resources.
    main_flow()

    # --- OPTION 2: FOR LOCAL SERVER / VPS (COMMENTED OUT) ---
    # Use this if you run the script on your own laptop or a 24/7 server.
    # The '.serve()' method keeps the script running indefinitely 
    # and handles the scheduling internally.
    
    # main_flow.serve(
    #     name="deployment-mentor-pagi",
    #     # cron="0 7 * * *", # Run daily at 07:00 AM (server time)
    #     interval=10,        # Or run every 10 seconds (for testing)
    #     tags=["ai", "daily"]
    # )