from pyflink.common import Types
from pyflink.datastream import ProcessFunction, CoProcessFunction
from pyflink.datastream.state import ValueStateDescriptor, ValueState
from utils import MessagePayload, NotificationService
import math

class GeofenceCoProcessFunction(CoProcessFunction):
    def __init__(self):
        self.geofence_state: ValueState = None
        self.status_state: ValueState = None
        self.notification_service: NotificationService = None
        
    def open(self, runtime_context):
        self.geofence_state = runtime_context.get_state(
            ValueStateDescriptor("geofence_config", Types.PICKLED_BYTE_ARRAY())
        )
        
        self.status_state = runtime_context.get_state(
            ValueStateDescriptor("geofence_status", Types.STRING())
        )
        
        self.notification_service = NotificationService()

    def process_element1(self, geo_fence_msg, ctx):
        """Process geo-fence configuration updates"""
        vin = geo_fence_msg.vin
        if geo_fence_msg.geofenceEnabled.lower() == 'false':
            self.geofence_state.clear()
            self.status_state.clear()
            print(f"Disabled geofence monitoring for VIN={vin}")
            return
        
        new_config = {
            'center_lat': geo_fence_msg.center.lat,
            'center_lon': geo_fence_msg.center.lng,
            'radius': geo_fence_msg.radiusMeters,
            'geo_mode': geo_fence_msg.geofenceEnabled
        }
        self.geofence_state.update(new_config)
        print(f"Updated geofence config for VIN={vin}: {new_config}")

    def process_element2(self, location_update:MessagePayload, ctx):
        """Process location coordinates"""
        vin = location_update.vin
        current_lat = location_update.HMI_Latitude
        current_lon = location_update.HMI_Longitude
        
        if None in (current_lat, current_lon):
            print(f"Skipping invalid location for VIN={vin}")
            return
            
        geofence_config = self.geofence_state.value()
        if not geofence_config or geofence_config.get('geo_mode', 'false').lower() != 'true':
            return  # Geofence not active for this VIN
        
       
        distance = haversine(
            current_lon, current_lat,
            geofence_config['center_lon'], geofence_config['center_lat']
        )
        
        new_status = "OUTSIDE" if distance > geofence_config['radius'] else "INSIDE"
        previous_status = self.status_state.value()

       
        if not previous_status:  
            if new_status == "OUTSIDE":
                self._send_notification(vin, "geofence_out")
            self.status_state.update(new_status)
        elif new_status != previous_status:
            event_type = f"geofence_{new_status.lower()}"
            self._send_notification(vin, event_type)
            self.status_state.update(new_status)

    def _send_notification(self, vin: str, event_type: str):
        print(f"Notifying {event_type} for VIN={vin}")
        self.notification_service.send_notification(vin=vin, event=event_type)

def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate distance between two points on Earth (in kilometers)"""
    R = 6371  
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    return R * c
