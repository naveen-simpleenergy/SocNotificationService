import requests
import os
from datetime import datetime, timezone, timedelta
from typing import  Dict
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
    
    def send_notification_payload2(self, vin: str, soc: float, range: float, time: datetime) -> bool:
        """
        Send notification with additional range information.
        
        Args:
            vin: Vehicle identification number
            soc: State of charge percentage
            range: Estimated range in kilometers
            time: Timestamp of the event
        Returns:
            bool: True if notification was successfully sent
        """
        payload_2 = self._range_payload(vin=vin, soc=soc, range=range,time=time)
      
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_endpoint, json=payload_2, headers=headers, timeout=self.timeout)
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
        
    def _range_payload(self, vin: str, soc: float, range: float, time: datetime) -> Dict:
        """Construct the API request payload with range information"""
        return {
            "channel": ["dynamic-island"],
            "type": "bsnn",
            "data": {
                "vin": vin,
                "percentage": soc,
                "range": range,
                "startTime": time
            }
        }
    
    def _format_timestamp(epoch_ms: int) -> str:
        """Convert epoch ms to IST ISO-8601 string"""
        dt_utc = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = dt_utc.astimezone(ist)
        return dt_ist.isoformat()