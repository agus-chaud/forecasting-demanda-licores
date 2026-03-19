---
name: caches-fase9
overview: "Separar entrenamiento y cache-loading: mover entrenamiento de SARIMA/XGB/LGB a un notebook respaldo, y ajustar el notebook principal para que valide y cargue caches y llegue a `## Fase 9 — Forecast Futuro` con el mínimo de celdas ejecutadas y sin re-entrenar."
todos:
  - id: create-backup-notebook
    content: Crear `forecasting-licores_respaldo_entrenamiento.ipynb` con todas las celdas de entrenamiento (SARIMA+walk-forward+XGB/LGB global+XGB/LGB tiendas+ensemble json).
    status: pending
  - id: refactor-main-cache-only
    content: Editar `forecasting-licores.ipynb` para eliminar `else:` de entrenamiento y dejar solo carga desde caches (SARIMA en `model_cache`, ML en `artifacts/modeling`). Si falta cache, instruir ejecutar el notebook respaldo.
    status: pending
  - id: use-feature-caches
    content: Reemplazar recomputación pesada de features en Fase 6/tiendas para `df_xgb`/`df_xgb_store` usando `features_categoria` y `features_tienda`; agregar checks de columnas requeridas antes de Fase 9.
    status: pending
  - id: add-bootstrap-cell
    content: Agregar una celda `bootstrap_fase9` antes de `## Fase 9` que deje listos `df_xgb`, `df_xgb_store`, `FEATURES`, `FEATURES_STORE`, y cargue los 4 modelos desde `joblib`.
    status: pending
  - id: te-maps-cache
    content: Modificar `Fase 9.2` para reutilizar `artifacts/modeling/target_encoding_maps.json` si existe; si no, recalcular y persistir.
    status: pending
  - id: min-run-steps
    content: Documentar en el notebook principal la secuencia mínima de ejecución para llegar a Fase 9 con pocas celdas.
    status: pending
  - id: verify-outputs
    content: Tras la refactorización, correr Fase 9 y verificar que se generen los `.parquet` y que pasen los tests de Fase 9.5.
    status: pending
isProject: false
---

# Plan de acción para llegar a Fase 9 rápido (usando caches)

## Objetivo

- Que `forecasting-licores.ipynb` llegue hasta `## Fase 9 — Forecast Futuro` ejecutando pocas celdas y sin entrenar modelos (solo cargar desde caché).
- Mover TODO el código de entrenamiento (SARIMA + walk-forward + XGB/LGB global y tiendas) a un notebook de respaldo, para que el principal quede “cache-first” y legible.

## 1) Crear notebook respaldo de entrenamiento

- Crear un nuevo notebook: `[forecasting-licores_respaldo_entrenamiento.ipynb](forecasting-licores_respaldo_entrenamiento.ipynb)`.
- Dentro del respaldo, incluir (en este orden) las celdas/sections de entrenamiento que hoy viven en `forecasting-licores.ipynb`:
  - SARIMA (Fase 5): `auto_arima` + entrenamiento de modelos y persistencia.
  - Walk-forward SARIMA: cálculo de `resultados_walkforward_cat` y guardado del `pkl` (ej. `walkforward_sarima_categoria.pkl`).
  - XGBoost/LightGBM global (Fase 6): entrenamiento y `joblib.dump` a `artifacts/modeling/forecasting_xgb_global.joblib` y `artifacts/modeling/forecasting_lgb_global.joblib`.
  - XGB/LGB tiendas (bloque equivalente a Fase 8): entrenamiento y `joblib.dump` a `artifacts/modeling/forecasting_xgb_store_global.joblib` y `...forecasting_lgb_store_global.joblib`.
  - Ensemble weight (categorías): escribir `artifacts/modeling/forecasting_ensemble.json`.
- Agregar en el respaldo una celda “RUN TRAINING” (tipo guía) que:
  - imprime qué caches va a generar,
  - y al final valida que existen los archivos esperados.

## 2) Convertir el notebook principal en “cache-only”

Archivo objetivo: `[forecasting-licores.ipynb](forecasting-licores.ipynb)`.

### 2.1 Reemplazar training por carga desde caches

- Para SARIMA:
  - Dejar solo el bloque que carga desde `[model_cache](model_cache/)` (la celda que imprime `[CACHE] Modelos SARIMA cargados...`).
  - Si faltan caches, mostrar un mensaje que indique explícitamente: “Ejecutá el notebook respaldo: `forecasting-licores_respaldo_entrenamiento.ipynb`”.
- Para XGB/LGB global:
  - Mantener la lógica de `joblib.load` desde `artifacts/modeling/forecasting_xgb_global.joblib` y `...forecasting_lgb_global.joblib`.
  - Eliminar (en el principal) el `else:` que entrena si no existen los modelos.
- Para XGB/LGB tiendas:
  - Igual: mantener `joblib.load` desde `artifacts/modeling/forecasting_xgb_store_global.joblib` y `...forecasting_lgb_store_global.joblib`.
  - Eliminar el entrenamiento dentro del notebook principal.

### 2.2 Minimizar feature engineering usando caches existentes

- Ya se cargan en Fase 1/celdas iniciales:
  - `features_categoria` desde `data/cache_features_categoria`
  - `features_tienda` desde `data/cache_features_tienda`
- En lugar de recomputar features desde `ventas_por_categoria_2` (bloque pesado de Fase 6), ajustar para que:
  - `df_xgb` tome como base `features_categoria`.
  - `df_xgb_store` tome como base `features_tienda`.
- Agregar un “guard” (con prints claros) antes de Fase 9 para asegurar que existan las columnas mínimas requeridas por `FEATURES`/`FEATURES_STORE` (si faltara alguna, calcularla solo si es imprescindible; si no, levantar un error con instrucción).

### 2.3 Bootstrap único antes de Fase 9

- Insertar una celda “bootstrap_fase9” justo antes de `## Fase 9 — Forecast Futuro` que deje listos SOLO:
  - `df_xgb` y `df_xgb_store`
  - `FEATURES` y `FEATURES_STORE`
  - `model_xgb`, `model_lgb`, `model_xgb_store`, `model_lgb_store`
  - y un chequeo de existencia de `artifacts/modeling/forecasting_ensemble.json`.
- Comentarlo en el notebook para que sea fácil de entender qué depende de qué.

## 3) Acelerar dentro de la Fase 9 (pequeño ajuste)

- En `[Fase 9.2](forecasting-licores.ipynb)`, hoy siempre recalcula TE y escribe `artifacts/modeling/target_encoding_maps.json`.
- Cambiarlo a:
  - si el archivo existe, cargarlo desde disco;
  - si no existe, recalcular y guardarlo.
- Esto reduce tiempo en ejecuciones repetidas y evita recomputaciones innecesarias.

## 4) Secuencia mínima de ejecución (para vos)

Luego de la refactorización:

1. En `forecasting-licores.ipynb`, ejecutá SOLO:
  - la celda inicial que carga `features_categoria`/`features_tienda` (si no está ya ejecutada).
  - la celda `bootstrap_fase9`.
2. Ejecutá `## Fase 9`:
  - Fase 9.1 (setup)
  - Fase 9.2 (TE maps, ahora con cache si existe)
  - Fase 9.3 (categorías)
  - Fase 9.4 (tiendas)
  - Fase 9.5 (tests) solo si querés validar.

## 5) Verificación final

- Confirmar que aparecen los outputs:
  - `data/predictions/forecasting_future_categories.parquet`
  - `data/predictions/forecasting_future_stores.parquet`
- Confirmar que los tests de Fase 9.5 pasan (o registrar los fallos).

## 6) Riesgos / decisiones

- Si alguna columna requerida no está en los `cache_features_*`, el guard debe decirte exactamente qué falta.
- Si `forecasting_ensemble.json` no existe, hay 2 caminos:
  - levantar error con instrucción para correr el respaldo,
  - o calcularlo rápido en el principal usando solo predicciones del global XGB/LGB (más rápido que entrenar, pero igualmente requiere pasar por split/evaluación).

