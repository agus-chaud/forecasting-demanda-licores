import pytest
import sys
from pathlib import Path
import pandas as pd

# Add scripts directory to path to import our module
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.append(str(scripts_dir))

from extract_store_locations import parse_coordinate

class TestCoordinateExtraction:
    """
    Pruebas unitarias para la extracción de coordenadas de las tiendas.
    Aplicando patrón AAA y behavior-driven tests.
    """

    def test_extract_coordinates_from_point_format(self):
        # Arrange
        location_string = "POINT (-91.387531 40.39978)"
        
        # Act
        lat, lon = parse_coordinate(location_string)
        
        # Assert
        assert pytest.approx(lat, 0.0001) == 40.39978
        assert pytest.approx(lon, 0.0001) == -91.387531

    def test_extract_coordinates_from_tuple_format(self):
        # Arrange
        location_string = "(40.39978, -91.387531)"
        
        # Act
        lat, lon = parse_coordinate(location_string)
        
        # Assert
        assert pytest.approx(lat, 0.0001) == 40.39978
        assert pytest.approx(lon, 0.0001) == -91.387531

    def test_returns_none_for_malformed_string(self):
        # Arrange
        location_string = "Alguna direccion sin coordenadas"
        
        # Act
        lat, lon = parse_coordinate(location_string)
        
        # Assert
        assert lat is None
        assert lon is None

    def test_returns_none_for_nan(self):
        # Arrange
        location_string = float('nan')
        
        # Act
        lat, lon = parse_coordinate(location_string)
        
        # Assert
        assert lat is None
        assert lon is None
        
    def test_edge_case_coordinates_outside_iowa_ignored(self):
        # Arrange
        # Latitudes reales de Iowa están entre 40 y 44. Longitudes entre -97 y -89.
        location_string = "POINT (0.00000 0.0000)"
        
        # Act
        lat, lon = parse_coordinate(location_string)
        
        # Assert
        assert lat is None
        assert lon is None
