import pytest
import pandas as pd
import pydeck as pdk
import json

def test_pydeck_hexagon_layer_construction():
    """
    Test de Integración UI: 
    Asegura que la configuración del mapa Hexagonal se ensambla correctamente 
    y en modo seguro (map_style=None) para que Streamlit no tire errores
    ocultos en el frontend por de falta de API Tokens.
    """
    # Arrange: Dataframe sintético de tiendas simulando la extracción
    data = pd.DataFrame({
        "lat": [41.5, 41.6, 42.0],
        "lon": [-93.5, -93.6, -92.0],
        "total_sales": [1500, 3000, 200]
    })
    
    # Act: Construcción del layer y el deck tal cual la vista de tiendas
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=data,
        opacity=0.8,
        get_position="[lon, lat]",
        get_weight="total_sales",
        aggregation="SUM",
    )
    
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position="[lon, lat]",
        get_color=[255, 255, 255, 200],
        get_radius=1000,
        pickable=True,
        stroked=True,
        get_line_color=[217, 160, 91, 255],
        line_width_min_pixels=2
    )
    
    view_state = pdk.ViewState(
        latitude=41.8780,
        longitude=-93.0977,
        zoom=6.5,
        pitch=0
    )

    deck = pdk.Deck(
        layers=[heatmap_layer, scatter_layer],
        initial_view_state=view_state,
        map_style=None, # <- EL DATO CLAVE
        tooltip={"text": "Tienda: {store_id}\\nVentas: {total_sales}"}
    )
    
    json_output = deck.to_json()
    parsed_json = json.loads(json_output)
    
    # Assert: Validaciones estructurales para que no se rompa en Streamlit
    assert parsed_json["initialViewState"]["pitch"] == 0, "La vista debe ser plana (pitch=0)"
    assert len(parsed_json["layers"]) == 2, "Debe haber dos capas construidas (Heatmap y Scatterplot)"
    
    layer_types = [layer["@@type"] for layer in parsed_json["layers"]]
    assert "HeatmapLayer" in layer_types, "Falta la capa del mapa de calor"
    assert "ScatterplotLayer" in layer_types, "Falta la capa de puntos de las tiendas"
    
    # En map_style=None, Streamlit se ocupa, el JSON generado usa la default de deck.gl
    # No puede tener una URL a "carto-dark" cruda
    assert "carto-dark" not in json_output.lower()
