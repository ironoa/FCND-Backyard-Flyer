import argparse
import time
from enum import Enum

import numpy as np

from udacidrone import Drone
from udacidrone.connection import MavlinkConnection, WebSocketConnection  # noqa: F401
from udacidrone.messaging import MsgID

class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5

TARGET_ALTITUDE = 3.0

class BackyardFlyer(Drone):

    def __init__(self, connection):
        super().__init__(connection)
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = []
        self.in_mission = True
        self.check_state = {}

        # initial state
        self.flight_state = States.MANUAL

        # TODO: Register all your callbacks here
        self.register_callback(MsgID.LOCAL_POSITION, self.local_position_callback) #changes in local_position
        self.register_callback(MsgID.LOCAL_VELOCITY, self.velocity_callback) #changes in local_velocity
        self.register_callback(MsgID.STATE, self.state_callback) #changes in either armed or guided

    def is_target_close(self):
      return np.linalg.norm(self.local_position[0:2]-self.target_position[0:2])<0.2

    def is_target_altitude_close(self):
      return -1 * self.local_position[2] >= self.target_position[2] * 0.95

    def is_altitude_ground_level(self):
      return abs(self.local_position[2]) < 0.1   
    
    def local_position_callback(self):
        """
        This triggers when `MsgID.LOCAL_POSITION` is received and self.local_position contains new data
        """
        if self.flight_state == States.TAKEOFF:
          if self.is_target_altitude_close():
            self.all_waypoints = self.calculate_box()
            self.target_position = self.all_waypoints[0]
            self.all_waypoints.pop(0)
            self.waypoint_transition()

        if self.flight_state == States.WAYPOINT:
          if self.is_target_close() == True :
            if len(self.all_waypoints)>0:
              self.target_position = self.all_waypoints[0]
              self.all_waypoints.pop(0)
              self.waypoint_transition()
            else:
              self.landing_transition()    

    def velocity_callback(self):
        """
        This triggers when `MsgID.LOCAL_VELOCITY` is received and self.local_velocity contains new data
        """
        if self.flight_state == States.LANDING: 
          if self.local_velocity[2] == 0 and self.is_altitude_ground_level():
            self.disarming_transition() 

    def state_callback(self):
        """
        This triggers when `MsgID.STATE` is received and self.armed and self.guided contain new data
        """
        if self.flight_state == States.MANUAL:
          self.arming_transition()
        if self.flight_state == States.ARMING:
          self.takeoff_transition()  
        
    def calculate_box(self):
        waypoints = [
          [10.0, 0.0, TARGET_ALTITUDE],
          [10.0, 10.0, TARGET_ALTITUDE],
          [0.0, 10.0, TARGET_ALTITUDE],
          [0.0, 0.0, TARGET_ALTITUDE],
        ]
        return waypoints

    def arming_transition(self):
        if self.global_position[0] == 0 or self.global_position[1] == 0 or self.global_position[2] == 0:
          return #bugfix, bug present also in solution branch

        print("arming transition")
        self.take_control()
        self.arm()
        self.set_home_position(self.global_position[0],self.global_position[1],self.global_position[2])
        self.flight_state = States.ARMING

    def takeoff_transition(self):
        print("takeoff transition")
        self.target_position[2] = TARGET_ALTITUDE
        self.takeoff(self.target_position[2])
        self.flight_state = States.TAKEOFF

    def waypoint_transition(self):
        print("waypoint transition")
        waypoint = self.target_position
        print(waypoint)
        self.cmd_position(waypoint[0],waypoint[1],waypoint[2],0)
        self.flight_state = States.WAYPOINT

    def landing_transition(self):
        print("landing transition")
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        print("disarm transition")
        self.disarm()
        self.in_mission = False
        self.flight_state = States.DISARMING

    def manual_transition(self):
        print("manual transition")
        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):
        print("Creating log file")
        self.start_log("Logs", "NavLog.txt")
        print("starting connection")
        self.connection.start()
        print("Closing log file")
        self.stop_log()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5760, help='Port number')
    parser.add_argument('--host', type=str, default='127.0.0.1', help="host address, i.e. '127.0.0.1'")
    args = parser.parse_args()

    conn = MavlinkConnection('tcp:{0}:{1}'.format(args.host, args.port), threaded=False, PX4=False)
    #conn = WebSocketConnection('ws://{0}:{1}'.format(args.host, args.port))
    drone = BackyardFlyer(conn)
    time.sleep(2)
    drone.start()
