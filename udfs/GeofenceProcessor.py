from pyflink.common import Types
from pyflink.datastream import ProcessFunction
from pyflink.datastream.state import ValueStateDescriptor, ValueState
import math
from utils import NotificationService, MessagePayload


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate distance between two points on Earth (in kilometers)
    """
    R = 6371  
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    return R * c 

class GeofenceProcessFunction(ProcessFunction):
    def __init__(self):
        self.geofence_state: ValueState = None
        self.status_state: ValueState = None
        
    def open(self, runtime_context):
        # State for geofence parameters (initial coords + radius)
        self.geofence_state = runtime_context.get_state(
            ValueStateDescriptor("geofence", Types.PICKLED_BYTE_ARRAY())
        )
        
        # State for current geofence status
        self.status_state = runtime_context.get_state(
            ValueStateDescriptor("status", Types.STRING())
        )
        
        # Initialize services
        self.notification_service = NotificationService()
        self.db_client = GeofenceDBClient()  # Implement your DB client

    def process_element(self, geo_msg: MessagePayload, ctx):
        # Get current vehicle data
        current_vin = geo_msg.vin
        current_lat = geo_msg.HMI_Latitude
        current_lon = geo_msg.HMI_Longitude
        
         
        if None in (current_lat, current_lon):
            print(f"[WARN] Missing GPS data for VIN={current_vin}")
            return
        
      
        geofence_data = self._get_geofence_data(current_vin)
        if not geofence_data:
            return  # Will retry on next message

        distance = haversine(
            current_lon, current_lat,
            geofence_data['initial_lon'], geofence_data['initial_lat']
        )
        
        new_status = "OUTSIDE" if distance > geofence_data['radius'] else "INSIDE"
        previous_status = self.status_state.value()

        self._handle_state_transition(current_vin, new_status, previous_status)

    def _get_geofence_data(self, vin: str) -> dict:
        data = self.geofence_state.value()
        if data:
            return data
        try:
            data = self.db_client.get_geofence(vin)
            if data:
                self.geofence_state.update(data)
                return data
            print(f"[WARN] No geofence config for VIN={vin}")
        except Exception as e:
            print(f"[ERROR] DB fetch failed for VIN={vin}: {str(e)}")
        return None


    def _handle_state_transition(self, vin: str, new_status: str, previous_status: str):
        if not previous_status:
            if new_status == "OUTSIDE":
                self._trigger_notification(vin, "geofence_out")
            self.status_state.update(new_status)
        elif new_status != previous_status:
            event_type = f"geofence_{new_status.lower()}"
            self._trigger_notification(vin, event_type)
            self.status_state.update(new_status)

    def _trigger_notification(self, vin: str, event_type: str):
        print(f"[INFO] Triggering {event_type} for VIN={vin}")
        self.notification_service.send_notification(vin=vin, event=event_type)
    
        
class GeofenceDBClient:
    def __init__(self):
        # Replace this mock with real DB client
        self.mock_db = {
            "VIN1234": {
                'initial_lat': 37.7749,      # Example latitude
                'initial_lon': -122.4194,    # Example longitude
                'radius': 1000               # in meters
            },
            "VIN5678": {
                'initial_lat': 28.6139,
                'initial_lon': 77.2090,
                'radius': 1500
            }
        }

    def get_geofence(self, vin: str) -> dict:
        return self.mock_db.get(vin)