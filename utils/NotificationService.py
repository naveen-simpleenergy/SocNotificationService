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
    
    def send_notification(self, vin: str, soc: float, event: str) -> bool:
        """
        Send notification to configured API endpoint.
        
        Args:
            vin: Vehicle identification number
            event_type: Type of the event being notified
        Returns:
            bool: True if notification was successfully sent
        """
        payload = self._build_payload(vin=vin, soc=soc, event=event)
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_endpoint, json=payload, headers=headers, timeout=5)            
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Notification API error: {str(e)}")
            return False
    


    
    def _build_payload(self, vin: str,soc:float,event:str) -> Dict:
        """Construct the API request payload"""
        return {
            "channel": ["push"],
            "type": "alert",
            "data": {
                "event": event,
                "vin": vin,
                "soc": soc,
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