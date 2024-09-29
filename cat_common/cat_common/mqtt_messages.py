from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class CatTelemetry:
    centroid_x: float
    centroid_y: float

    def to_dict(self):
        return {
            'centroid_x': self.centroid_x,
            'centroid_y': self.centroid_y
        }
        
