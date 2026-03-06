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
- **Categoría (todo Iowa)**: fillna(0) es correcto. Si nadie en todo el estado compró \"100 Proof Vodka\" un martes, la venta fue realmente $0. En `analisis-calidad.ipynb` se reindexan las series diarias y se aplica `fillna(0)` solo en este nivel.
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
**Decisión**: Simplificar el pipeline de feature engineering y entrenamiento de modelos globales (XGBoost, SARIMA) trabajando sólo con pandas y cacheando los modelos entrenados por serie/categoría.
**Alternativas consideradas**:
- Mantener el feature engineering repartido entre SQL/DuckDB y pandas: mayor complejidad y más puntos de fallo
- No cachear modelos: reentrenar todo en cada ejecución del notebook, con tiempos de corrida altos
**Justificación**:
- Centralizar el feature engineering (lags, medias móviles, features de calendario, flags de cierre, etc.) en un único pipeline en pandas hace el código más legible, testeable y fácil de depurar.
- Eliminar dependencia de DuckDB en la etapa de modelado reduce fricción para correr el notebook en otros entornos (por ejemplo, sin motor SQL instalado).
- Cachear los modelos entrenados (por ejemplo con `joblib`) por clave de serie/categoría permite reutilizar resultados entre corridas, acelerar el flujo iterativo y evitar sobrecostos de CPU si sólo cambian algunos parámetros o el horizonte de predicción.
**Impacto**: El notebook de forecasting es más reproducible y rápido de ejecutar; además, se puede inspeccionar y reutilizar fácilmente el conjunto de modelos entrenados para análisis posteriores o futuros despliegues.
