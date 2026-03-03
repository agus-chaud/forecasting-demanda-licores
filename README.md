# Forecasting de Ventas - Licores Iowa

**Pipeline de pronóstico de ventas de licores por categoría y tienda, usando DuckDB para agregación y feature engineering, y SARIMA para modelado de series temporales con estacionalidad semanal.**

---

## Contexto del negocio

**Problema**: Predecir la demanda de licores a nivel de categoría de producto y de tienda para apoyar decisiones de inventario, reposición y planificación comercial.

**Objetivo**: Construir un pipeline de forecasting que permita:
- Pronosticar ventas diarias por categoría y por tienda
- Capturar estacionalidad semanal (patrones por día de la semana)
- Evaluar el rendimiento con métricas MAPE y MAE
- Reutilizar features preparados para futuros modelos (XGBoost/LightGBM)

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
    → Feature engineering (LAG, AVG OVER, dia_semana, mes)
    → Export Parquet: data/ventas_por_categoria.parquet, ventas_por_tienda.parquet, features_ventas_diarias.parquet
    → Split temporal (cutoff)
    → SARIMA por grupo → predicciones + evaluación
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
- **Pipeline SARIMA**: `auto_arima` para búsqueda de parámetros; entrenamiento paralelo por categoría y tienda con `joblib`.
- **Pipeline XGBoost/LightGBM**: Modelo global con 13 features y label encoding de categoría.
- **Ensemble**: Promedio ponderado XGBoost + LightGBM optimizado por WMAPE.
- **Walk-forward validation**: 3 folds temporales para medir robustez.
- **Evaluación**: WMAPE (métrica principal), MAPE, MAE, RMSE. Tabla comparativa de 4 modelos.
- **Ejercicios SQL**: 11 ejercicios (E1.1-E1.8 + E2.1-E2.3) cubriendo CTEs, window functions, RANK, ROW_NUMBER, QUALIFY, NTILE, ROLLUP, recursive CTE, EXPLAIN.

### Visualizaciones creadas

- **Descomposición estacional** (tendencia, estacionalidad, residuos) para top 3 categorías.
- **ACF/PACF** para diagnóstico de parámetros SARIMA.
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
- Dashboard interactivo para monitoreo de predicciones.
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
├── DECISIONS.md                   # Registro de decisiones técnicas con justificaciones
├── docs/
│   ├── GUIA_SQL_FORECASTING_LICORES.md   # Guía SQL: glosario, ejercicios, cheat sheet
│   └── ejemplos_sql/                      # Scripts SQL por ejercicio (E1.1-E2.3)
├── requirements.txt
├── Iowa_Liquor_Sales.csv          # Dataset fuente (licencias Iowa)
├── forecasting-licores.ipynb      # Pipeline completo: SQL + diagnóstico + SARIMA + XGBoost + LightGBM
├── analisis.ipynb                 # EDA, Agente de Calidad, outliers
├── data/
│   ├── ventas_por_categoria.parquet
│   ├── ventas_por_tienda.parquet
│   └── features_ventas_diarias.parquet
├── artifacts/
│   └── quality/
│       └── quality_manifest.json  # Output del Agente de Calidad (analisis.ipynb)
├── .cursor/
│   ├── mcp.json                   # Config MCP: engram para memoria persistente
│   ├── plans/                     # Planes de desarrollo
│   └── rules/                     # Reglas (calidad, EDA, engram-memory, etc.)
├── skills/
│   └── forecasting-time-series-data/  # Skill de apoyo para forecasting
└── engram/                        # Plugin/memoria (no parte del core del forecasting)
```

### Archivos principales

| Archivo | Descripción |
|---------|-------------|
| `forecasting-licores.ipynb` | Pipeline completo: ejercicios SQL (E1.1-E2.3), diagnóstico estadístico, SARIMA, XGBoost, LightGBM, ensemble, walk-forward validation. |
| `docs/GUIA_SQL_FORECASTING_LICORES.md` | Guía de funcionalidades SQL: glosario de conceptos, ejercicios de replicación, cheat sheet y orden de estudio. Permite replicar las queries sin asistencia de IA. |
| `DECISIONS.md` | Registro de 10 decisiones técnicas con justificaciones y alternativas consideradas. |
| `analisis.ipynb` | Carga CSV, Agente de Calidad (5 dimensiones), validación, análisis de outliers (sus_promos, sus_errores). |
| `Iowa_Liquor_Sales.csv` | Dataset de ventas de licores del Estado de Iowa. |
| `data/*.parquet` | Agregaciones y features exportados para reutilización. |

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

### 3. Pipeline de forecasting (`forecasting_licores.ipynb`)

1. Abre el notebook en Jupyter o VS Code.
2. Ejecuta las celdas en orden:
   - Celdas 1–2: Imports y carga del CSV con DuckDB.
   - Celdas 3–4: Agregación por categoría y tienda.
   - Celda 6: Feature engineering (ventanas SQL).
   - Celdas 8: Export a Parquet.
   - Celda 10: Split temporal (genera `cutoff`, `train_*`, `test_*`).
   - Celdas 12–16: SARIMA (funciones, entrenamiento, evaluación, visualización).
3. Opcional: ajusta `SAMPLE_ROWS` en la celda 1 (`None` para usar el CSV completo) o `MIN_DAYS` en la celda 12.

**Nota**: El entrenamiento SARIMA por tienda puede tardar varios minutos (≈1500 tiendas). Las celdas instalan `duckdb` y `statsmodels` vía pip si no están instalados.

### 4. Análisis y calidad (`analisis.ipynb`)

1. Ejecuta las celdas en orden.
2. El Agente de Calidad genera `artifacts/quality/quality_manifest.json`.
3. Revisa `validated_df`, `df_quality`, `sus_promos` y `sus_errores` para el análisis de outliers.

### Uso básico del pipeline

- **Cambiar horizonte de predicción**: Modifica `STEPS_AHEAD = 30` en la celda 12.
- **Cambiar umbral de días mínimos**: Modifica `MIN_DAYS = 90` en la celda 12.
- **Regenerar Parquet**: Vuelve a ejecutar las celdas 1–8 de `forecasting_licores.ipynb`.
