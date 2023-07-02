import csv
import datetime
import math
import gpxpy
import gpxpy.gpx
import xml.etree.ElementTree as ET
from typing import List, Tuple

# Earth’s radius in metres
R_m = 6371000

# Util to convert degrees to radians
deg_to_rad = lambda d: d * math.pi / 180

# Get UTC now without the bulk
utc = lambda: datetime.datetime.utcnow()

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate the distance between 2 coordinates using the 'great circle distance'"""
    lat1_rad = deg_to_rad(lat1)
    lat2_rad = deg_to_rad(lat2)
    d_lat_rad = deg_to_rad(lat2 - lat1)
    d_long_rad = deg_to_rad(lon2 - lon1)

    a = (
        math.sin(d_lat_rad/2) * math.sin(d_lat_rad/2) + 
        math.sin(d_long_rad/2) * math.sin(d_long_rad/2) *
        math.cos(lat1_rad) * math.cos(lat2_rad)
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R_m * c


class Waypoint:
    """
        Represents a waypoint
        
        Members:
            - latitude (float): Latitude in [-90, 90]
            - longitude (float): Longitude in [-180, 180]
            - [optional] elevation (int): Elevation in m above sea level
            - [optional] time (datetime): Time at which the waypoint was created
            - [optional] name (str): Name of the point
            - [optional] desc (str): Description of the point
    """
    def __init__(self, lat: float, lon: float, elev: int = 0, time: datetime = utc(), name: str = "", desc: str = "") -> None:
        self.latitude = lat
        self.longitude = lon
        self.elevation = elev
        self.time = time
        self.name = name
        self.description = desc

    def __repr__(self) -> str:
        return (
            type(self).__name__ + f"(latitude={self.latitude}, longitude={self.longitude}, elevation={self.elevation}, time={self.time}, name={self.name}, description={self.description})"
        )

    def set(self, lat: float, lon: float, elev: int) -> None:
        """Set the waypoint"""
        self.latitude = lat
        self.longitude = lon
        self.elevation = elev

    def compare_m(self, waypoint: "Waypoint") -> float:
        """Get distance (in metres) between 2 waypoints"""
        return haversine(self.latitude, self.longitude, waypoint.latitude, waypoint.longitude)


class Routepoint(Waypoint):
    """
        Represents a routepoint
        Inherits from Waypoint
    """
    def __init__(self, lat: float, lon: float, elev: int = 0, time: datetime = utc(), name: str = "", desc: str = "") -> None:
        super().__init__(lat, lon, elev, time, name, desc)


class Track:
    """Represents a track"""
    def __init__(self, name: str = "", desc: str = "") -> None:
        self.track = []
        self.name = name
        self.description = desc

    def __repr__(self) -> str:
        return (
            type(self).__name__ + f"(track={self.track}, name={self.name}, description={self.description})"
        )

    def set(self, track: List[Waypoint]) -> None:
        """Replace the track entirely"""
        self.track = track

    def reset(self) -> None:
        """Reset the track"""
        self.track = []

    def add_waypoint(self, waypoint: Waypoint) -> None:
        """Add a waypoint to the track"""
        self.track.append(waypoint)

    def remove_waypoint(
        self, waypoint: Waypoint
    ) -> Waypoint:
        """Remove a waypoint from the track and return it"""
        return self.track.remove(waypoint)
    
    def get_edges(self) -> List[Tuple]:
        """Get the edges between each waypoint"""
        edges = []        
        for i, v in enumerate(self.track[:-1]):
            edges.append((v, self.track[i+1]))
        return edges

    def edge_distances_m(self) -> List[float]:
        """Get the distance between each point in a track"""
        overall = []
        for ___, (a, b) in enumerate(self.get_edges()):
            overall.append(a.compare_m(b))
        return overall
    
    def track_distance_m(self) -> float:
        """Get the distance of the track in metres"""
        overall = 0
        for ___, (a, b) in enumerate(self.get_edges()):
            overall += a.compare_m(b)
        return overall
    
    def distance_to_end_m(self, waypoint: Waypoint) -> float: 
        """Get the distance to the end of the track in metres"""
        return waypoint.compare_m(self.track[-1])


class Region(Track):
    """Represents a (polygonal) region"""
    def __init__(self, name: str = "", desc: str = "") -> None:
        super().__init__(name, desc)

    def get_edges(self) -> List[Tuple]:
        """Get the edges between each waypoint"""
        edges = []        
        for i, v in enumerate(self.track[:-1]):
            edges.append((v, self.track[i+1]))
        edges.append((self.track[-1], self.track[0]))
        return edges


class Route:
    """Represents a route"""
    def __init__(self, name: str = "", desc: str = "") -> None:
        self.route = []
        self.name = name
        self.description = desc

    def __repr__(self) -> str:
        return (
            type(self).__name__ + f"(route={self.route}, name={self.name}, description={self.description})"
        )

    def set(self, route: List[Routepoint]) -> None:
        """Replace the route entirely"""
        self.route = route
    
    def reset(self) -> None:
        """Reset the route"""
        self.route = []

    def add_routepoint(self, routepoint: Routepoint) -> None:
        """Add a routepoint to the end of the route"""
        self.route.append(routepoint)

    def remove_routepoint(self, routepoint: Routepoint) -> Routepoint:
        """Remove a routepoint from the route and return it"""
        return self.route.remove(routepoint)
    
    def get_edges(self) -> List[Tuple]:
        """Get the edges between each routepoint"""
        edges = []        
        for i, v in enumerate(self.route[:-1]):
            edges.append((v, self.route[i+1]))
        return edges
    
    def edge_distances_m(self) -> List[float]:
        """Get the distance between each point in a route"""
        overall = []
        for ___, (a, b) in enumerate(self.get_edges()):
            overall.append(a.compare_m(b))
        return overall
    
    def route_distance_m(self) -> float:
        """Get the distance of the route in metres"""
        overall = 0
        for ___, (a, b) in enumerate(self.get_edges()):
            overall += a.compare_m(b)
        return overall
    
    def distance_to_end_m(self, routepoint: Routepoint) -> float:
        """Get the distance to the end of the route in metres"""
        return routepoint.compare_m(self.route[-1])


class GPX:
    """Represents a GPX file"""
    def __init__(self) -> None:
        self.doc = ""
        self.waypoints: List[Waypoint] = []
        self.tracks: List[Track] = []
        self.routes: List[Route] = []

    def __repr__(self) -> str:
        return (
            type(self).__name__ + f"(doc={self.doc}, waypoints={self.waypoints}, tracks={self.tracks}, routes={self.routes})"
        )

    def to_csv(self, include_waypoints: bool = True, include_tracks: bool = True, include_routes: bool = True):
        """Convert to a CSV file"""
        with open("gpxparser.csv", "w", newline="") as file:
            writer = csv.writer(file)
            fields = ["type", "latitude", "longitude", "elevation", "time", "name", "description"]

            if self.waypoints and include_waypoints:
                writer.writerow(fields)
                for w in self.waypoints:
                    writer.writerow(["W", w.latitude, w.longitude, w.elevation, w.time, w.name, w.description])
                writer.writerow([])

            if self.tracks and include_tracks:
                writer.writerow(fields)
                for t in self.tracks:
                    for w in t.track:
                        writer.writerow(["T", w.latitude, w.longitude, w.elevation, w.time, w.name, w.description])
                    writer.writerow([])

            if self.routes and include_routes:
                writer.writerow(fields)
                for r in self.routes:
                    for w in r.route:
                        writer.writerow(["R", w.latitude, w.longitude, w.elevation, w.time, w.name, w.description])
                    writer.writerow([])


class GPXParser:
    """Provides basic utilities for GPX files"""
    def __init__(self) -> None:
        self.gpx = GPX()

    def __repr__(self) -> str:
        return (
            type(self).__name__ + f"(gpx={self.gpx})"
        )

    def parse(self, file) -> GPX:
        """Parse GPX"""
        self.gpx.doc = gpxpy.parse(file)
        self.gpx.waypoints = self.to_waypoints()
        self.gpx.tracks = self.to_tracks()
        self.gpx.routes = self.to_routes()
        return self.gpx

    def to_waypoints(self) -> List[Waypoint]:
        """Convert the parsed GPX document into a list of waypoints"""
        waypoints: List[Waypoint] = []
        for waypoint in self.gpx.doc.waypoints:
            waypoints.append(Waypoint(lat=waypoint.latitude, lon=waypoint.longitude, name=waypoint.name))
        return waypoints

    def to_tracks(self) -> List[Track]:
        """Convert the parsed GPX document into a list of tracks"""
        tracks: List[Track] = []
        for track in self.gpx.doc.tracks:
            newTrack = Track(name=track.name, desc=f"number: {track.number}")
            for segment in track.segments:
                for point in segment.points:
                    waypoint = Waypoint(point.latitude, point.longitude, point.elevation, point.time)
                    newTrack.add_waypoint(waypoint)
            tracks.append(newTrack)
        return tracks

    def to_routes(self) -> List[Route]:
        """Convert the parsed GPX document into a list of routes"""
        routes: List[Route] = []
        for route in self.gpx.doc.routes:
            newRoute = Route(name=route.name, desc=f"number: {route.number}")
            for point in route.points:
                routepoint = Routepoint(point.latitude, point.longitude, point.elevation, point.time)
                newRoute.add_routepoint(routepoint)
            routes.append(newRoute)		
        return routes
