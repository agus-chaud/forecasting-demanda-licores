import duckdb
import pandas as pd
import re
from pathlib import Path

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "Iowa_Liquor_Sales.csv"
OUTPUT_PATH = BASE_DIR / "data" / "store_coordinates.parquet"

def parse_coordinate(location_str: str) -> tuple:
    """
    Parsea strings malformados o mixtos para obtener lat y lon.
    Ejemplos esperados:
    - POINT (-91.387531 40.39978)  -> LON, LAT
    - (40.39978, -91.387531)       -> LAT, LON
    
    Devuelve: (latitud, longitud) como floats. Si falla, (None, None).
    """
    if pd.isna(location_str) or not isinstance(location_str, str):
        return None, None
        
    # Extraer todos los números que parezcan coordenadas
    matches = re.findall(r'([+-]?\d+\.\d+)', location_str)
    
    if len(matches) >= 2:
        val1, val2 = float(matches[0]), float(matches[1])
        
        # En Iowa, la latitud está entre 40 y 44 (positiva), y la longitud entre -96 y -90 (negativa)
        # Esto hace el parsing "smart" sin importar el orden en que vengan
        if 40 <= val1 <= 44 and -97 <= val2 <= -89:
            return val1, val2 # (lat, lon)
        elif 40 <= val2 <= 44 and -97 <= val1 <= -89:
            return val2, val1 # (lat, lon)
            
    return None, None

def main():
    print(f"[{pd.Timestamp.now()}] Iniciando extracción de coordenadas con DuckDB...")
    
    # Query eficiente en DuckDB, evitamos cargar todo el DF a memoria.
    query = f"""
        SELECT 
            "Store Number" as store_id, 
            MAX("Store Location") as location
        FROM read_csv_auto('{DATA_PATH}', all_varchar=true)
        WHERE "Store Location" IS NOT NULL
        GROUP BY "Store Number"
    """
    
    try:
        df = duckdb.query(query).df()
    except Exception as e:
        print(f"Error procesando CSV con DuckDB: {e}")
        return

    print(f"[{pd.Timestamp.now()}] {len(df)} tiendas únicas extraídas. Parseando coordenadas...")
    
    # Aplicar parsing
    coords = df['location'].apply(parse_coordinate)
    df['lat'] = [c[0] for c in coords]
    df['lon'] = [c[1] for c in coords]
    
    # Limpieza final
    df_valid = df.dropna(subset=['lat', 'lon']).copy()
    
    df_final = df_valid[['store_id', 'lat', 'lon']].copy()
    df_final['store_id'] = df_final['store_id'].astype(int)
    
    # Guardar a Parquet
    df_final.to_parquet(OUTPUT_PATH, index=False)
    
    print(f"[{pd.Timestamp.now()}] Extracción exitosa! {len(df_final)} coordenadas válidas guardadas en {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
