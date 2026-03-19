# Forecasting de Ventas - Licores Iowa

**Pipeline de pronóstico de ventas de licores por categoría y tienda, usando DuckDB para agregación y feature engineering, y SARIMA para modelado de series temporales con estacionalidad semanal.**

---

## Contexto del negocio

**Problema**: Predecir la demanda de licores a nivel de categoría de producto y de tienda para apoyar decisiones de inventario, reposición y planificación comercial.

**Objetivo**: Construir un pipeline de forecasting que permita:
- Pronosticar ventas diarias por categoría y por tienda
- Capturar estacionalidad semanal (patrones por día de la semana)
- Evaluar el rendimiento con métricas MAPE y MAE
- Generar **forecast futuro** (más allá de los datos históricos) para planificación real de inventario
- Dashboard interactivo con backtesting y predicciones hacia adelante

---

## Enfoque y decisiones técnicas

### Metodología

1. **Carga y limpieza**: Lectura directa del CSV `Iowa_Liquor_Sales.csv` con DuckDB; limpieza de `Sale (Dollars)` (eliminación de `$` y comas).
2. **Agregación temporal**: Ventas diarias agrupadas por categoría y por tienda.
3. **Feature engineering**: LAG (7, 14, 28 días), medias móviles (7 y 28 días), `dia_semana` y `mes` para capturar estacionalidad. Las ventanas excluyen el día actual para evitar *data leakage*.
4. **Split temporal**: Cutoff = `fecha_max - 30 días`; train hasta cutoff, test los últimos 30 días.
5. **Modelado SARIMA**: Un modelo SARIMA(1,0,1)(1,0,1)[7] por cada categoría/tienda; filtro de series con mínimo 90 días de datos.

### Pipeline de datos

```
Iowa_Liquor_Sales.csv
    → DuckDB (raw_ventas)
    → Agregación: ventas_categoria, ventas_tienda, ventas_diarias
    → Feature engineering (LAG, AVG OVER, dia_semana, mes, ewm, volatilidad, festivos Iowa)
    → Export Parquet: data/ventas_por_categoria_2/, ventas_por_tienda_2/
    → Split temporal (cutoff = fecha_max - 30 días)
    → SARIMA por grupo → predicciones + evaluación (backtesting)
    → XGBoost / LightGBM global → ensemble optimizado por WMAPE
    → Fase 9: Recursive multi-step forecasting → predicciones futuras (30 días más allá de fecha_max)
    → Dashboard Streamlit (4 páginas): Resumen | Categorías | Tiendas | Forecast Futuro
```

### Decisiones técnicas

| Decisión | Justificación |
|----------|---------------|
| **DuckDB** | SQL in-memory para agregaciones y ventanas; evita conflictos de PyArrow al exportar Parquet. |
| **SARIMA(1,0,1)(1,0,1)[7]** | Estacionalidad semanal (s=7); parámetros conservadores para estabilidad. |
| **Reindex diario con fillna(0)** | Las series tienen fechas irregulares; SARIMA requiere frecuencias fijas. Días sin ventas → 0. |
| **Filtro 90 días** | Series muy cortas no permiten estimar bien el componente estacional. |
| **Un modelo por serie** | Cada categoría/tienda tiene su propia dinámica; no se usa un modelo global. |

### Relación con `analisis.ipynb`

En `analisis.ipynb` existe un **Agente de Calidad** (5 dimensiones: Completitud, Unicidad, Validez, Outliers, Schema) que produce `validated_df` y `quality_manifest.json`. El plan en `.cursor/plans/` propone integrar DuckDB *después* de ese agente. En cambio, `forecasting_licores.ipynb` carga el CSV directamente con DuckDB y aplica su propia limpieza, sin depender de `validated_df`. Los dos flujos son compatibles pero actualmente independientes.

---

## Resultados e impacto

### Funcionalidades entregadas

- **Carga y agregación con DuckDB**: Tablas `ventas_categoria`, `ventas_tienda`, `ventas_diarias`.
- **Feature engineering con ventanas SQL**: `lag_7d`, `lag_14d`, `lag_28d`, `roll_mean_7`, `roll_mean_28`, `dia_semana`, `mes`, `es_finde`, `ratio_lag7_roll28`, `trend_7`.
- **Export Parquet**: `data/ventas_por_categoria.parquet`, `data/ventas_por_tienda.parquet`, `data/features_ventas_diarias.parquet`.
- **Diagnóstico estadístico**: Test ADF, ACF/PACF, descomposición estacional para las top 3 categorías.
- **Heatmap de Tiendas**: Extracción robusta de coordenadas (con `duckdb` y parsing de ubicación para Iowa) para visualización de densidad.
- **Pipeline SARIMA**: `auto_arima` para búsqueda de parámetros; entrenamiento paralelo por categoría y tienda con `joblib`.
- **Pipeline XGBoost/LightGBM**: Modelo global con ~28 features (lags, rolling, EWM, volatilidad, festivos Iowa, target encoding) y label encoding de categoría.
- **Ensemble**: Promedio ponderado XGBoost + LightGBM optimizado por WMAPE (peso guardado en `artifacts/modeling/forecasting_ensemble.json`).
- **Walk-forward validation**: 3 folds temporales para medir robustez.
- **Evaluación**: WMAPE (métrica principal), MAPE, MAE, RMSE. Tabla comparativa de 4 modelos.
- **Fase 9 — Forecast Futuro**: Recursive multi-step forecasting para generar predicciones de los próximos 30 días más allá de `fecha_max`. Target encoding persistido en `artifacts/modeling/target_encoding_maps.json`. Outputs: `forecasting_future_categories.parquet` y `forecasting_future_stores.parquet`.
- **Dashboard Streamlit** (4 páginas): Resumen del modelo, Predicciones por categoría, Predicciones por tienda, **Forecast Futuro** (horizonte 7/14/30 días, banda CI q10-q90, ranking, descarga CSV).
- **Tests de integración**: 17 casos en `tests/test_forecast_page.py` (fixtures sintéticos, sin dependencia del notebook).
- **Ejercicios SQL**: 11 ejercicios (E1.1-E1.8 + E2.1-E2.3) cubriendo CTEs, window functions, RANK, ROW_NUMBER, QUALIFY, NTILE, ROLLUP, recursive CTE, EXPLAIN.

### Visualizaciones creadas

- **Descomposición estacional** (tendencia, estacionalidad, residuos) para top 3 categorías.
- **ACF/PACF** para diagnóstico de parámetros SARIMA.
- **Mapa de Calor de Tiendas**: Modelo espacial montado sobre `pydeck` (Streamlit) para interactuar con hubs comerciales usando métricas predictivas y reales.
- **SARIMA: Predicción vs Real** (top 3 categorías).
- **Feature Importance** (XGBoost y LightGBM).
- **Resumen de calidad** (en `analisis.ipynb`): `df_quality` con completeness, validity y outliers.

### Tabla comparativa de modelos

| Modelo | Métrica principal | Notas |
|--------|-------------------|-------|
| SARIMA (por categoría) | WMAPE | auto_arima, paralelo con joblib |
| XGBoost (global) | WMAPE | 13 features, 200 trees |
| LightGBM (global) | WMAPE | 13 features, leaf-wise |
| Ensemble (XGB+LGB) | WMAPE | Promedio ponderado optimizado |

*Los valores numéricos se obtienen al ejecutar el notebook.*

---

## Principales desafíos y cómo se solucionaron

| Desafío | Solución |
|---------|----------|
| **Error `pandas.period already defined` al usar `to_parquet`** | Export con DuckDB (`COPY ... TO 'file.parquet' (FORMAT PARQUET)`), evitando el pipeline pandas/PyArrow. |
| **Series temporales con fechas irregulares** | Tratamiento contextual: `fillna(0)` para categorías (agregado estatal); exclusión de días de cierre para tiendas individuales. |
| **Estacionalidad semanal vs mensual** | SARIMA con s=7 (semanal) confirmado por ACF con picos en lag 7, 14, 21. |
| **MAPE inflado por series con ventas bajas** | WMAPE (Weighted MAPE) como métrica principal; pondera por volumen de ventas. |
| **Parámetros SARIMA sin justificación** | `auto_arima` para búsqueda automática con AIC, previa validación con test ADF y ACF/PACF. |

---

## Futuras mejoras

- Integrar DuckDB en `analisis.ipynb` *después* del agente de calidad, usando `validated_df` como input.
- Considerar SARIMAX con mes como exógena para estacionalidad mensual.
- Hyperparameter tuning con `TimeSeriesSplit` de sklearn para XGBoost/LightGBM.
- Guardar modelos quantile (q10/q90) a disco para reemplazar el CI sintético ±20% del forecast futuro.
- Guardar el ensemble weight de tiendas a `forecasting_ensemble_store.json` (actualmente fijo en 0.5).
- Integrar SARIMA en el forecast futuro una vez que `pmdarima` esté disponible en el entorno.
- Ejecutar pipeline completo con `SAMPLE_ROWS=None` (27M+ filas) y documentar métricas finales.

---

## Lecciones aprendidas

1. **`fillna(0)` no siempre es correcto**: "Sin registro" puede significar "tienda cerrada" a nivel individual. El tratamiento contextual por nivel de agregación es clave.
2. **MAPE estándar es engañoso**: Series con ventas bajas ($5-$50) inflan MAPE al dividir por valores pequeños. WMAPE da métricas representativas del negocio.
3. **Diagnosticar antes de modelar**: El flujo Box-Jenkins (ADF → ACF/PACF → auto_arima) evita elegir parámetros SARIMA arbitrariamente.
4. **Walk-forward validation > train/test split único**: Un solo split de 30 días no mide si el modelo es robusto en diferentes períodos.
5. **DuckDB para SQL analytics**: Window functions, QUALIFY, ROLLUP, recursive CTEs — todo funciona in-memory sin necesidad de un RDBMS.
6. **Ensemble casi siempre ayuda**: Promediar XGBoost + LightGBM con peso optimizado típicamente mejora sobre cualquier modelo individual.

---

## Estructura del proyecto

```
Forecasing Licores/
├── README.md
├── DECISIONS.md                   # Registro de decisiones técnicas (D01-D18)
├── docs/
│   ├── GUIA_SQL_FORECASTING_LICORES.md   # Guía SQL: glosario, ejercicios, cheat sheet
│   └── ejemplos_sql/                      # Scripts SQL por ejercicio (E1.1-E2.3)
├── requirements.txt
├── Iowa_Liquor_Sales.csv          # Dataset fuente (licencias Iowa, ~3.3 GB)
├── forecasting-licores.ipynb      # Pipeline completo (Fases 1-9): SQL + SARIMA + XGBoost + LightGBM + Forecast Futuro
├── analisis-calidad.ipynb         # DuckDB → Parquets particionados (ventas_por_categoria_2, ventas_por_tienda_2)
├── data/
│   ├── ventas_por_categoria_2/    # Parquet particionado (input del notebook de forecasting)
│   ├── ventas_por_tienda_2/       # Parquet particionado
│   ├── modelos_sarima/            # Modelos SARIMA serializados (top 4 categorías)
│   └── predictions/
│       ├── forecasting_predictions.parquet           # Backtesting por categoría (30 días test)
│       ├── forecasting_predictions_by_store.parquet  # Backtesting por tienda
│       ├── forecasting_future_categories.parquet     # Forecast futuro por categoría (Fase 9)
│       └── forecasting_future_stores.parquet         # Forecast futuro por tienda (Fase 9)
├── artifacts/
│   └── modeling/
│       ├── forecasting_xgb_global.joblib             # Modelo XGBoost categorías
│       ├── forecasting_lgb_global.joblib             # Modelo LightGBM categorías
│       ├── forecasting_xgb_store_global.joblib       # Modelo XGBoost tiendas (Tweedie)
│       ├── forecasting_lgb_store_global.joblib       # Modelo LightGBM tiendas (Tweedie)
│       ├── forecasting_ensemble.json                 # Peso ensemble categorías (best_w=0.65)
│       ├── target_encoding_maps.json                 # TE maps (Fase 9, historia completa)
│       └── experiment_manifest_latest.json           # Métricas del último run
├── dashboard/
│   ├── app.py                     # Entrada Streamlit (login → redirect)
│   ├── auth.py                    # Autenticación simple
│   ├── paths.py                   # Rutas base (independiente del cwd)
│   ├── theme.py                   # Colores, CSS, helpers visuales
│   └── pages/
│       ├── 1_Resumen_modelo.py        # Métricas del modelo, historial de runs
│       ├── 2_Predicciones_categorias.py  # Backtesting por categoría
│       ├── 3_Predicciones_tiendas.py    # Backtesting por tienda + mapa
│       ├── 4_Forecast_Futuro.py         # Forecast futuro (horizonte 7/14/30 días)
│       └── _utils_forecast.py           # Helper load_future_parquet
├── tests/
│   └── test_forecast_page.py      # 17 integration tests (smart-testing, fixtures sintéticos)
├── .cursor/
│   ├── mcp.json                   # Config MCP: engram para memoria persistente
│   └── rules/                     # Reglas (calidad, EDA, engram-memory, etc.)
└── engram/                        # Plugin/memoria (no parte del core del forecasting)
```

### Archivos principales

| Archivo | Descripción |
|---------|-------------|
| `forecasting-licores.ipynb` | Pipeline completo (Fases 1-9): ejercicios SQL, SARIMA, XGBoost, LightGBM, ensemble, walk-forward validation, **Fase 9 recursive forecast futuro**. |
| `analisis-calidad.ipynb` | DuckDB → Parquets particionados. Calidad de datos, limpieza, exportación. |
| `dashboard/pages/4_Forecast_Futuro.py` | Página de forecast hacia adelante: gráfico 3 zonas (backtesting + vline + zona futuro), CI q10-q90, ranking, descarga CSV. |
| `tests/test_forecast_page.py` | 17 integration tests con fixtures sintéticos. Validan comportamiento del dashboard sin depender del notebook. |
| `DECISIONS.md` | Registro de 18 decisiones técnicas con justificaciones y alternativas consideradas. |
| `artifacts/modeling/target_encoding_maps.json` | Target encoding maps persistidos (Fase 9). Evita recargar el CSV de 3.3 GB para inferencia. |
| `data/predictions/forecasting_future_*.parquet` | Forecast futuro por categoría y tienda (generado por Fase 9). |

---

## Requisitos

- **Python**: 3.10+ (recomendado; usado en `avanzado-venv`).
- **Dependencias** (`requirements.txt`):

```
duckdb>=1.0.0
pandas
numpy
matplotlib
seaborn
statsmodels
tqdm
pmdarima
xgboost
lightgbm
scikit-learn
joblib
pytest
pydeck
```

---

## Memoria persistente (Engram)

El proyecto usa [Engram](https://github.com/gentleman-programming/engram) para memoria persistente del agente entre sesiones. El flujo está configurado en `.cursor/mcp.json` y la regla en `.cursor/rules/engram-memory.mdc`.

### Requisitos

- **Engram** instalado y en PATH: `go install github.com/gentleman-programming/engram@latest` (o el binario desde releases)
- **Cursor** con MCP habilitado

### Verificación

```bash
engram version   # Debe mostrar la versión
engram stats     # Estadísticas de la BD (en ~/.engram/)
```

### Si las herramientas no aparecen

1. Comprobar que `engram` está en PATH
2. **Reiniciar Cursor por completo** tras editar `.cursor/mcp.json`
3. En Cursor: Settings → MCP → verificar que el servidor `engram` esté conectado (sin errores)

### Herramientas disponibles (vía MCP)

- `mem_save` — guardar decisiones, bugs, descubrimientos
- `mem_search` — buscar en memorias pasadas
- `mem_context` — recuperar contexto de sesiones recientes
- `mem_session_summary` — resumir sesión antes de cerrar

---

## Dataset

### Origen

- **Archivo**: `Iowa_Liquor_Sales.csv`
- **Fuente**: Ventas de licores reguladas por el Estado de Iowa (datos públicos).
- **Formato**: CSV con encabezado.

### Columnas clave utilizadas

| Columna | Uso |
|---------|-----|
| `Date` | Fecha de venta (formato MM/DD/YYYY). |
| `Category Name` | Nombre de categoría de producto. |
| `Store Number` | Identificador de tienda. |
| `Sale (Dollars)` | Monto en ventas; requiere limpieza (`$`, comas). |

### Columnas adicionales (analisis.ipynb / quality report)

Entre otras: `Invoice/Item Number`, `Store Name`, `Address`, `City`, `County`, `Item Description`, `Bottles Sold`, `Volume Sold (Liters)`, `State Bottle Cost`, `State Bottle Retail`.

### Archivos intermedios

| Archivo | Descripción |
|---------|-------------|
| `data/ventas_por_categoria.parquet` | `fecha`, `categoria`, `ventas` (agregación diaria). |
| `data/ventas_por_tienda.parquet` | `fecha`, `store_id`, `ventas` (agregación diaria). |
| `data/features_ventas_diarias.parquet` | `fecha`, `ventas`, `lag_7d`, `lag_14d`, `lag_28d`, `roll_mean_7`, `roll_mean_28`, `dia_semana`, `mes`. |
| `artifacts/quality/quality_manifest.json` | Métricas de calidad del Agente de Calidad (completitud, validez, outliers, etc.). |

---

## Cómo ejecutarlo y usarlo

### 1. Entorno

```bash
# Crear y activar entorno virtual (ejemplo)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Dataset

Coloca `Iowa_Liquor_Sales.csv` en la raíz del proyecto. Si no dispones del archivo, descárgalo desde la fuente oficial de datos de Iowa (licencias de licores).

### 3. Pipeline de forecasting (`forecasting-licores.ipynb`)

1. Abre el notebook en Jupyter o VS Code.
2. Ejecuta las celdas en orden — el notebook tiene caching de modelos con `joblib`, por lo que las re-ejecuciones son rápidas si los artefactos ya existen.
3. **Para generar el forecast futuro (Fase 9)**, ejecuta las celdas al final del notebook:
   - **Celda 9.1** — Setup: define `FUTURE_HORIZON = 30` y `future_dates_cat`.
   - **Celda 9.2** — Target encoding: carga desde cache si existe `target_encoding_maps.json`; si no existe, recalcula y guarda.
   - **Celda 9.3** — Forecast categorías: loop recursivo, genera `forecasting_future_categories.parquet`.
   - **Celda 9.4** — Forecast tiendas: loop recursivo, genera `forecasting_future_stores.parquet`.
   - **Celda 9.5** — Tests de comportamiento: 8 assertions automáticas que validan el output.

**Nota**: El loop de tiendas puede tardar varios minutos (≈170 tiendas × 30 días × features). Si faltan modelos globales en `artifacts/modeling/`, el notebook te pide ejecutar `forecasting-licores_respaldo_entrenamiento.ipynb` antes de llegar a Fase 9.

### 4. Dashboard

```bash
streamlit run dashboard/app.py
```

- **Página 4 — Forecast Futuro** requiere que la Fase 9 del notebook haya corrido y los parquets existan en `data/predictions/`.
- Si los parquets no existen, la página muestra un warning en lugar de fallar.

### 5. Tests

```bash
pytest tests/test_forecast_page.py -v
```

17 tests de integración que validan el comportamiento del dashboard de forecast futuro. No requieren correr el notebook (usan fixtures sintéticos).

### 4. Análisis y calidad (`analisis.ipynb`)

1. Ejecuta las celdas en orden.
2. El Agente de Calidad genera `artifacts/quality/quality_manifest.json`.
3. Revisa `validated_df`, `df_quality`, `sus_promos` y `sus_errores` para el análisis de outliers.

### Uso básico del pipeline

- **Cambiar horizonte de predicción**: Modifica `STEPS_AHEAD = 30` en la celda 12.
- **Cambiar umbral de días mínimos**: Modifica `MIN_DAYS = 90` en la celda 12.
- **Regenerar Parquet**: Vuelve a ejecutar las celdas 1–8 de `forecasting_licores.ipynb`.
