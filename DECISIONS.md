# Registro de Decisiones Técnicas

Cada decisión relevante del proyecto se documenta aquí con su justificación y alternativas consideradas.

---

## D01: Motor de procesamiento SQL — DuckDB

**Fecha**: 2026-02-26
**Decisión**: Usar DuckDB como motor SQL in-memory para todo el pipeline de datos.
**Alternativas consideradas**:
- pandas puro: más familiar, pero lento para 3.3GB y sin SQL nativo
- SQLite: requiere carga previa a disco, más lento para analytics
- PySpark: overkill para un solo archivo CSV en una máquina local
**Justificación**: DuckDB lee CSV directamente con `read_csv_auto()`, soporta window functions completas (LAG, AVG OVER, NTILE, QUALIFY), y exporta Parquet sin conflictos de PyArrow. Performance: 500K filas en ~5-15s.
**Impacto**: Eliminó el error `pandas.period already defined` al exportar Parquet.

---

## D02: Estacionalidad semanal (s=7)

**Fecha**: 2026-02-26
**Decisión**: Usar período estacional s=7 (semanal) en SARIMA.
**Alternativas consideradas**:
- s=30 (mensual): SARIMA estándar solo permite un período estacional; s=30 es más lento y menos preciso para patrones semanales
- SARIMAX con mes como exógena: viable pero añade complejidad sin clara mejora
**Justificación**: Las ventas de licores tienen patrón fuerte de día de la semana (más ventas viernes/sábado). El ACF muestra picos en lag 7, 14, 21 confirmando estacionalidad semanal.
**Impacto**: Captura el patrón dominante de la serie.

---

## D03: fillna(0) contextual por nivel de agregación

**Fecha**: 2026-03-02
**Decisión**: Tratamiento diferenciado de datos faltantes según nivel de agregación.
**Alternativas consideradas**:
- fillna(0) universal: razonamiento original — si no hay registro, no hubo venta
- Interpolación lineal: inventaría ventas que nunca existieron
- Forward fill: asume que las ventas se mantienen, no realista para días sin operación
**Justificación**:
- **Categoría (todo Iowa)**: fillna(0) es correcto. Si nadie en todo el estado compró "100 Proof Vodka" un martes, la venta fue realmente $0. En `analisis-calidad.ipynb` se reindexan las series diarias y se aplica `fillna(0)` solo en este nivel.
- **Tienda individual**: una tienda sin registros un domingo probablemente estaba cerrada. La demanda no era $0. SARIMA modela estas caídas como patrón, inflando la varianza.
- **Solución**: Detectar días de cierre (0 transacciones en TODAS las categorías de una tienda) y excluirlos del entrenamiento SARIMA o marcarlos con un flag `es_cierre_tienda = 1` sin imputar 0 ventas.
- **Validación**: La política se documenta y prueba explícitamente con ejemplos sintéticos en `analisis-calidad.ipynb` para evitar regresiones.
**Impacto**: Reduce la varianza artificial en series de tiendas y evita interpretar erróneamente cierres de tienda como días de demanda nula.

---

## D04: WMAPE como métrica principal

**Fecha**: 2026-03-02
**Decisión**: Reemplazar MAPE estándar por WMAPE (Weighted MAPE) como métrica principal.
**Alternativas consideradas**:
- MAPE estándar: divide por valor real de cada observación → series con ventas bajas ($5-$50) inflan el error absurdamente
- MAE: no es porcentual, difícil de comparar entre escalas
- RMSE: penaliza outliers, útil como complemento
**Justificación**: WMAPE = sum(|error|) / sum(|actual|). Pondera por volumen de ventas, dando más peso a categorías/tiendas de alto volumen. Esto es lo relevante para decisiones de inventario.
**Impacto**: Los números de error son más interpretables y representativos del negocio.

---

## D05: Parámetros SARIMA vía auto_arima

**Fecha**: 2026-03-02
**Decisión**: Usar `pmdarima.auto_arima` para encontrar parámetros óptimos en las top 3 categorías, luego aplicar esos parámetros al resto.
**Alternativas consideradas**:
- SARIMA(1,0,1)(1,0,1)[7] fijo: parámetros conservadores sin justificación estadística
- Grid search exhaustivo por serie: muy lento para 63+ categorías
- auto_arima por cada serie: óptimo pero impracticable en tiempo
**Justificación**: auto_arima usa AIC stepwise para buscar el mejor modelo. Las top 3 categorías son representativas. Es un balance entre optimización y tiempo de ejecución.
**Impacto**: Parámetros basados en datos reales (ADF + ACF/PACF) en vez de asumidos.

---

## D06: Modelo global vs por categoría para XGBoost/LightGBM

**Fecha**: 2026-03-02
**Decisión**: Entrenar un solo modelo global con categoría como feature (Label Encoding).
**Alternativas consideradas**:
- Un modelo por categoría (como SARIMA): más específico pero 68 modelos a mantener
- Modelo global sin categoría: pierde información de qué categoría es
**Justificación**: Los gradient boosted trees aprenden interacciones naturalmente. Con `categoria_enc` como feature, el modelo puede aprender patrones compartidos (estacionalidad semanal) y específicos (nivel de ventas por categoría). Categorías con pocos datos se benefician del transfer learning implícito.
**Impacto**: Un solo modelo para mantener y actualizar, con generalización entre categorías.

---

## D07: Ensemble XGBoost + LightGBM con peso optimizado

**Fecha**: 2026-03-02
**Decisión**: Combinar predicciones de XGBoost y LightGBM con promedio ponderado, optimizando el peso por WMAPE.
**Alternativas consideradas**:
- Solo XGBoost: más simple, un modelo menos
- Stacking con meta-learner: más complejo, riesgo de overfitting con datos limitados
- Promedio simple 50/50: no aprovecha diferencias de rendimiento
**Justificación**: Grid search sobre peso w ∈ [0, 1] (paso 0.05) es rápido y robusto. Si un modelo domina, el peso lo refleja.
**Impacto**: Ensemble típicamente mejora 1-3% sobre el mejor modelo individual.

---

## D08: Walk-forward validation (3 folds)

**Fecha**: 2026-03-02
**Decisión**: Validar con 3 folds temporales (cutoff retrocede 30 días por fold).
**Alternativas consideradas**:
- Un solo split train/test: simple pero no mide robustez
- K-fold estándar: viola la estructura temporal (entrenaría con datos futuros)
- 5+ folds: más robusto pero lento con SARIMA
**Justificación**: Walk-forward es el estándar para series temporales. 3 folds es suficiente para medir varianza del WMAPE sin exceder tiempo razonable.
**Impacto**: Si WMAPE varía poco entre folds, el modelo es estable.

---

## D09: Filtro de 90 días mínimo para SARIMA

**Fecha**: 2026-02-26
**Decisión**: Solo entrenar SARIMA en series con al menos 90 días de datos.
**Alternativas consideradas**:
- 60 días: permite más series pero SARIMA con s=7 necesita >2 ciclos completos para estimar estacionalidad
- 120 días: más robusto pero excluye series útiles
- Sin filtro: SARIMA falla silenciosamente con series cortas
**Justificación**: 90 días = ~13 semanas = ~13 ciclos estacionales (s=7). Suficiente para estimar componentes estacionales con confianza.
**Impacto**: Excluye categorías/tiendas con datos insuficientes, mejorando calidad promedio de los modelos.

---

## D10: Exclusión del día actual en rolling features

**Fecha**: 2026-02-26
**Decisión**: `AVG(ventas) OVER (ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)` — excluir el día actual.
**Alternativas consideradas**:
- `ROWS BETWEEN 7 PRECEDING AND CURRENT ROW`: incluye el día actual → data leakage
**Justificación**: Al predecir el día t, solo podemos usar información hasta t-1. Incluir t en el feature significa que el modelo "ve" la respuesta.
**Impacto**: Previene data leakage. Las métricas reflejan rendimiento real en producción.

---

## D11: Refactor de feature engineering y cache de modelos

**Fecha**: 2026-03-06
**Decisión**: Simplificar el pipeline de feature engineering y entrenamiento de modelos globales (XGBoost, SARIMA) trabajando sólo con pandas y cacheando los modelos entrenados por serie/categoría, separando el entrenamiento pesado en un notebook de respaldo (`forecasting-licores_respaldo_entrenamiento.ipynb`) para mantener el notebook principal en modo cache-first (si faltan artefactos, guía a ejecutar el respaldo).
**Alternativas consideradas**:
- Mantener el feature engineering repartido entre SQL/DuckDB y pandas: mayor complejidad y más puntos de fallo
- No cachear modelos: reentrenar todo en cada ejecución del notebook, con tiempos de corrida altos
**Justificación**:
- Centralizar el feature engineering (lags, medias móviles, features de calendario, flags de cierre, etc.) en un único pipeline en pandas hace el código más legible, testeable y fácil de depurar.
- Eliminar dependencia de DuckDB en la etapa de modelado reduce fricción para correr el notebook en otros entornos (por ejemplo, sin motor SQL instalado).
- Cachear los modelos entrenados (por ejemplo con `joblib`) por clave de serie/categoría permite reutilizar resultados entre corridas, acelerar el flujo iterativo y evitar sobrecostos de CPU si sólo cambian algunos parámetros o el horizonte de predicción.
**Impacto**: El notebook de forecasting es más reproducible y rápido de ejecutar; además, se puede inspeccionar y reutilizar fácilmente el conjunto de modelos entrenados para análisis posteriores o futuros despliegues. El entrenamiento completo queda “amarrado” al respaldo, y el principal hace carga desde disco para llegar a Fase 9 con pocas celdas.

---

## D12: Dataset ML global por tienda (XGBoost/LightGBM)

**Fecha**: 2026-03-09
**Decisión**: Construir un dataset `df_xgb_tienda` global por tienda (una sola tabla) análogo a `df_xgb` por categoría, con lags/ventanas y calendar features a nivel `store_id`, y un solo modelo global que usa `store_id_enc` como feature.
**Alternativas consideradas**:
- Un modelo separado por tienda: máximo ajuste por serie, pero explosión de modelos y riesgo de overfitting en tiendas con pocos datos.
- Modelo global sin identificar la tienda: pierde información clave de nivel y patrón específico por tienda.
- Usar exclusivamente el cache `features_tienda` generado en `analisis-calidad.ipynb`: menos código en el notebook, pero acopla demasiado el pipeline de modelado a la lógica de ese notebook y dificulta la trazabilidad de las features.
**Justificación**:
- Un **modelo global por tienda** replica la ventaja ya usada a nivel categoría (transfer de información entre series) y reduce la complejidad operativa a un solo modelo para todas las tiendas.
- Construir `df_xgb_tienda` en `forecasting-licores.ipynb` con pandas permite mantener en un solo lugar la definición de lags (`lag_1`, `lag_7`, `lag_14`, `lag_28`, `lag_52`, `lag_365`), estadísticas de ventana (`roll_mean_7/28`, `roll_std_7/28`, `cv_7`, `roll_mean_7`, `roll_min_7`, `roll_range_7`, `ewm_7/28`) y features de calendario (`dia_semana`, `mes`, `dia_mes`, `es_finde`, `es_festivo`, `es_semana_navidad`, `es_semana_thanksgiving`, `trimestre`, `dias_hasta_navidad`) de forma consistente con el pipeline por categoría.
- Se reutiliza el mismo **cutoff temporal** que categoría (`fecha_max - 30 días`) para entrenar y evaluar, asegurando comparabilidad entre modelos por categoría y por tienda.
- Se introduce un filtro de **mínimo 90 días en train por tienda**, coherente con D09, para evitar entrenar el modelo con series extremadamente cortas que añaden ruido y no aportan valor al negocio.
- `store_id` se codifica con un **Label Encoding simple** (`store_id_enc`) suficiente para modelos de árboles de boosting (no depende del valor numérico absoluto y evita data leakage porque no usa el target).
**Impacto**:
- Se obtiene un dataset `df_xgb_tienda` listo para entrenar XGBoost/LightGBM globales por tienda (`X_train_store`, `y_train_store`, `X_test_store`, `y_test_store`), con el mismo esquema de features que a nivel categoría más la identificación de tienda.
- El pipeline queda preparado para la siguiente fase del plan (entrenar modelos XGBoost/LightGBM y ensemble por tienda) sin modificar de nuevo la capa de datos.

---

## D13: Forecasting en escala logarítmica para modelos de boosting

**Fecha**: 2026-03-06
**Decisión**: Aplicar `log1p` al target (`ventas`) antes de entrenar XGBoost y LightGBM, y revertir con `expm1` al generar predicciones.
**Alternativas consideradas**:
- Escala original (sin transformación): MSE dominado por outliers de alto valor; el modelo aprende a minimizar error en categorías grandes y falla en categorías medianas.
- Transformación Box-Cox: más flexible que log1p pero requiere estimar λ y no garantiza que 0 se mapee a 0.
- Target encoding con suavizado: complementario, no alternativo.
**Justificación**: Las ventas diarias siguen una distribución log-normal (cola derecha pesada). SARIMA ya trabajaba en escala log y obtenía mejor WMAPE. Log1p permite aplicar la misma escala con valores 0 (días sin ventas = log1p(0) = 0) sin manejo especial. Al entrenar con el target en escala log, el MSE penaliza errores relativos en lugar de absolutos, mejorando el rendimiento en categorías de bajo volumen.
**Impacto**: Reduce el WMAPE de los modelos de boosting al alinear el espacio de optimización con la métrica de negocio (errores relativos ponderados). Los modelos ahora son comparables a SARIMA en términos de escala de entrenamiento.

---

## D14: Dashboard Streamlit con autenticación y tema oscuro

**Fecha**: 2026-03-08
**Decisión**: Construir un dashboard Streamlit multi-página en `dashboard/` con login por usuario/contraseña, tema oscuro estilo "tienda de licores" y tres páginas: Resumen del modelo, Ventas y predicciones, Comparativa e historial.
**Alternativas consideradas**:
- Jupyter/Voilà: ya existe el notebook, pero no es adecuado para usuarios de negocio (demasiado técnico, requiere ejecutar celdas).
- Tableau/Power BI: herramientas externas que requieren licencia y no están integradas con el pipeline Python.
- Dash (Plotly): alternativa viable, pero Streamlit tiene menor fricción para desarrollo rápido con el mismo stack Python.
**Justificación**:
- **Página única de entrada**: tras el login, `app.py` redirige directamente a `1_Resumen_modelo.py` con `st.switch_page()`, evitando una pantalla de bienvenida vacía.
- **Solo XGBoost en producción**: la página de resumen muestra únicamente métricas de XGBoost (mejor modelo del último run) para evitar confundir a usuarios de negocio con comparaciones técnicas de modelos.
- **Métricas con lenguaje de negocio**: cada métrica (WMAPE, MAPE, MAE, RMSE) incluye `help=` en `st.metric()` y un expander con explicación en términos de inventario, stock y planificación, no en términos estadísticos.
- **Fuente de datos desacoplada**: `paths.py` resuelve la ruta base (repo root o `dashboard/`) según si existe `artifacts/modeling/`, permitiendo correr con `streamlit run dashboard/app.py` desde cualquier directorio.
- **Artefactos esperados**: el notebook debe generar `artifacts/modeling/experiment_manifest_latest.json` (métricas XGBoost), `artifacts/modeling/experiments_history.csv` (historial de runs) y `data/predictions/forecasting_predictions.parquet` (predicciones por categoría).
**Impacto**: Los usuarios de negocio pueden monitorear el rendimiento del modelo y explorar predicciones sin abrir un notebook. El dashboard es stateless (solo lee artefactos) y no depende de que el notebook esté ejecutándose.

---

## D15: Mapa de Calor Geoespacial con PyDeck y extracción eficiente

**Fecha**: 2026-03-17
**Decisión**: Implementar un mapa de calor en Streamlit usando `pydeck` y extraer coordenadas desde el CSV original con un script dedicado en DuckDB, guiado por prácticas de Smart-Testing.
**Alternativas consideradas**:
- Plotly/Folium: Folium es lento para muchos scatter points; Plotly Express es funcional, pero PyDeck ofrece capas progresivas (pitch) y excelente rendimiento WebGL con miles de puntos geográficos.
- Parsear coordenadas en Pandas cargando el dataset entero: Consume demasiada RAM (dataset ~3.5GB) y puede causar OOM en entornos pequeños.
**Justificación**:
- Reusamos DuckDB para extraer únicamente `Store Number` y `Store Location` agregados, completando la tarea iterativa en segundos.
- Se implementó una función de parsing inteligente que soporta tanto el formato WKT `POINT (LON LAT)` como tuplas `(LAT, LON)`, validando los datos contra las fronteras geográficas de Iowa (Patrón AAA bajo la skill `smart-testing`).
- PyDeck se acopla de manera nativa con Streamlit (`view_state` y `ScatterplotLayer`), calculando el radio del punto dinámicamente y aplicando la variable global del color `ACCENT`.
**Impacto**: Análisis espacial intuitivo e interactivo integrado en el dashboard de ventas, permitiendo detectar visualmente focos calientes de demanda sin tiempos de recarga perceptibles.

---

## D16: Recursive Multi-Step Forecasting para predicción futura (Fase 9)

**Fecha**: 2026-03-17
**Decisión**: Implementar recursive multi-step forecasting para XGBoost/LightGBM, donde cada predicción del día `t` alimenta los lags del día `t+1`, generando un horizonte de 30 días más allá de `fecha_max`.
**Alternativas consideradas**:
- **Direct multi-step**: entrenar N modelos separados, uno por cada paso de horizonte. No aplicable sin re-entrenar; requiere N veces más tiempo y almacenamiento.
- **Solo SARIMA**: SARIMA hace multi-step nativo vía `forecast(steps=N)`, pero los modelos guardados requieren `pmdarima` que no siempre está disponible, y solo cubren las top 4 categorías.
- **Congelar las predicciones en el período de test**: seguir mostrando únicamente backtesting. Descartado por ser inútil para decisiones de negocio.
**Justificación**:
- Los modelos XGBoost/LightGBM ya entrenados son single-step regressors. El único camino para multi-step sin reentrenamiento es recursivo.
- Lag features críticos: `lag_1` (day 2+) y `lag_7` (day 8+) requieren el buffer de predicciones. `lag_52` (52 días) y `lag_365` siempre disponibles desde la historia real (datos 2014).
- El estado EWM (`ewm_7`, `ewm_28`) se continúa recursivamente: `ewm_t = α·pred_t + (1-α)·ewm_{t-1}`. Esto es correcto porque `adjust=False` en pandas es justamente esa fórmula recurrente.
- Features de intermitencia de tiendas (`days_since_purchase`, `last_nonzero_amount`, etc.) se fijan en el último valor real conocido: para un horizonte de 30 días, estos no cambian significativamente.
- CI sintético ±20% como fallback porque los modelos quantile (q10/q90) no están serializados en disco.
**Impacto**: El dashboard pasa de ser un espejo retrovisor (backtesting) a una herramienta de planificación real. El notebook genera `forecasting_future_categories.parquet` y `forecasting_future_stores.parquet`.

---

## D17: Target Encoding persistido en disco (artifacts/modeling/target_encoding_maps.json)

**Fecha**: 2026-03-17
**Decisión**: En Fase 9, aplicar target encoding de forma cache-first: si `artifacts/modeling/target_encoding_maps.json` existe, cargarlo desde disco; si no existe, recalcular usando la historia completa hasta `fecha_max` (no solo el train window) y persistirlo en `artifacts/modeling/target_encoding_maps.json`.
**Alternativas consideradas**:
- Recalcular TE siempre: aumenta tiempo en ejecuciones repetidas porque fuerza a leer y agregar el dataset completo.
- Guardar el TE del train (calculado con datos ≤ cutoff): más conservador pero sub-óptimo para forecast futuro (desperdicia el período de test como información).
**Justificación**: Para forecasting futuro no existe el riesgo de data leakage que justificaba el TE solo-train durante el backtesting. Usando toda la historia disponible el TE captura mejor el nivel real de demanda de cada categoría/tienda. Persistirlo en JSON evita recargar el dataset de 3.3 GB para inferencia incremental.
**Impacto**: `target_encoding_maps.json` es reutilizable por el dashboard, por pipelines de re-inferencia y por futuros notebooks sin necesidad de DuckDB ni del CSV original.

---

## D18: Página "Forecast Futuro" en el dashboard con 3 zonas visuales

**Fecha**: 2026-03-17
**Decisión**: Nueva página `4_Forecast_Futuro.py` con un gráfico de 3 zonas: backtesting (gris punteado) | vline "Último dato real" | zona de forecast (color ACCENT + banda CI q10-q90 con `fill='tonexty'`).
**Alternativas consideradas**:
- Agregar el forecast futuro a las páginas existentes (2 y 3): crea confusión entre predicciones históricas evaluadas vs. predicciones hacia adelante sin ground truth.
- Solo mostrar el forecast sin contexto histórico: el usuario no puede juzgar la credibilidad del modelo sin ver cómo funcionó en el pasado.
**Justificación**: Separar en una página dedicada mantiene la claridad conceptual: páginas 2 y 3 = evaluación del modelo (tiene actual), página 4 = herramienta de negocio (no tiene actual). El contexto de backtesting en el mismo gráfico permite al usuario calibrar confianza en el forecast sin cambiar de página. `add_vrect` + `add_vline` en Plotly da la separación visual sin código adicional.
**Impacto**: Dashboard pasa a tener valor operacional real. Tests de integración con 17 casos validan comportamiento desde la perspectiva del usuario (fixtures sintéticos, sin depender de los parquets de producción).
