import requests
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
import uuid

load_dotenv()

class NotificationService():
    """
    Handles all notification delivery logic.
    No business rules - just delivers messages to the API.
    """
    
    def __init__(self):
        
        self.api_key =os.getenv("API_KEY")
        self.api_endpoint =os.getenv("API_ENDPOINT") 
        self.timeout = 5
    
    def send_notification(self, recipient: str, vin: str, timestamp: datetime, message: str) -> bool:
        """
        Send notification to configured API endpoint.
        
        Args:
            recipient: vehicle owner
            vin: Vehicle identification number
            timestamp: When the event occurred,
            message: Human-readable message
            
        Returns:
            bool: True if notification was successfully sent
        """
        payload = self._build_payload(recipient=recipient, vin=vin, timestamp=timestamp, message=message)
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        print(f"ATTEMPTING TO SEND: {message} to {recipient}")
        print(f"API ENDPOINT: {self.api_endpoint}")
        print(f"API KEY Present: {'Yes' if self.api_key else 'No'}")
        
        try:
            response = requests.post(self.api_endpoint, json=payload, headers=headers, timeout=5)            
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Notification API error: {str(e)}")
            return False
    


    
    def _build_payload(self, recipient: str, vin: str, timestamp: datetime, message: str) -> Dict:
        """Construct the API request payload"""
        return {
            "channel": ["mail"],
            "type": "alert",
            "data": {
                "notification_id": str(uuid.uuid4()),
                "event_type": "soc-notification",
                "vehicle": vin,
                "timestamp": self._format_timestamp(timestamp),
                "message": message,
                "email": recipient
            }
        }
    
    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime to ISO-8601 with UTC timezone"""
        if not isinstance(dt, datetime):
            raise TypeError(
                f"Invalid timestamp type. Expected datetime, got {type(dt)}. "
                f"Raw value: {dt} (verify epoch conversion)"
            )
        return dt.astimezone(timezone.utc).isoformat()