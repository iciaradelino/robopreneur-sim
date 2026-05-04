from math import hypot

from shapely import affinity
from shapely.geometry import Point, Polygon


class FloorPlan:
    def __init__(self, config):
        exterior = config.get("exterior", [])
        holes = config.get("holes", [])
        polygon = Polygon(exterior, holes=holes)
        if polygon.is_empty:
            raise ValueError("floor plan polygon is empty")
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            raise ValueError("floor plan polygon is invalid")

        min_x, min_y, max_x, max_y = polygon.bounds
        self._x_offset = -min_x
        self._y_offset = -min_y
        self.geometry = affinity.translate(
            polygon, xoff=self._x_offset, yoff=self._y_offset
        )
        self.width = max_x - min_x
        self.height = max_y - min_y
        self._routing_engine = self._build_routing_engine()

    def normalize_point(self, point):
        return (point[0] + self._x_offset, point[1] + self._y_offset)

    def random_point(self, rng, max_attempts=5000):
        min_x, min_y, max_x, max_y = self.geometry.bounds
        for _ in range(max_attempts):
            x = rng.random() * (max_x - min_x) + min_x
            y = rng.random() * (max_y - min_y) + min_y
            candidate = Point(x, y)
            if self.geometry.covers(candidate):
                return (x, y)
        representative = self.geometry.representative_point()
        return (representative.x, representative.y)

    def compute_path(self, start, end):
        snapped_start = self._snap_inside(start)
        snapped_end = self._snap_inside(end)
        path = self._route_with_engine(snapped_start, snapped_end)
        if path:
            return path
        return [snapped_end]

    def _build_routing_engine(self):
        try:
            import jupedsim as jps
        except ImportError as exc:
            raise ImportError(
                "jupedsim is required for world.mode=floor_plan. install dependencies in requirements.txt."
            ) from exc

        builders = [
            lambda: jps.RoutingEngine(self.geometry),
            lambda: jps.RoutingEngine(geometry=self.geometry),
            lambda: jps.RoutingEngine(polygon=self.geometry),
        ]
        for builder in builders:
            try:
                return builder()
            except Exception:
                continue
        return None

    def _route_with_engine(self, start, end):
        if self._routing_engine is None:
            return None

        method_names = ("compute_waypoints", "shortest_path", "route", "find_path")
        for method_name in method_names:
            method = getattr(self._routing_engine, method_name, None)
            if method is None:
                continue
            try:
                raw_path = method(start, end)
            except Exception:
                continue
            path = self._coerce_path(raw_path, end)
            if path:
                return path
        return None

    def _coerce_path(self, raw_path, end):
        if raw_path is None:
            return None

        if hasattr(raw_path, "waypoints"):
            raw_path = raw_path.waypoints

        if not isinstance(raw_path, (list, tuple)):
            return None

        path = []
        for point in raw_path:
            if isinstance(point, Point):
                path.append((point.x, point.y))
                continue
            if (
                isinstance(point, (list, tuple))
                and len(point) >= 2
                and all(isinstance(v, (int, float)) for v in point[:2])
            ):
                path.append((float(point[0]), float(point[1])))
                continue
            if hasattr(point, "x") and hasattr(point, "y"):
                path.append((float(point.x), float(point.y)))

        if not path:
            return None
        if hypot(path[-1][0] - end[0], path[-1][1] - end[1]) > 1e-9:
            path.append(end)
        return path

    def _snap_inside(self, point):
        candidate = Point(point[0], point[1])
        if self.geometry.covers(candidate):
            return (point[0], point[1])
        nearest = self.geometry.boundary.interpolate(self.geometry.boundary.project(candidate))
        return (nearest.x, nearest.y)
