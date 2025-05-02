from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def make_phone_call():
    """
    Make a phone call using Twilio to the specified number
    """
    try:
        # Get Twilio credentials from environment variables
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # The number we want to call
        to_number = "+919987334843"

        if not all([account_sid, auth_token, twilio_number]):
            print("Missing Twilio credentials")
            return False

        client = Client(account_sid, auth_token)

        # Make the call
        call = client.calls.create(
            to=to_number,
            from_=twilio_number,
            url='http://demo.twilio.com/docs/voice.xml'  # This is a Twilio demo URL
        )

        print(f"Call initiated to {to_number}. Call SID: {call.sid}")
        return True
    except Exception as e:
        print(f"Error making phone call: {str(e)}")
        return False 