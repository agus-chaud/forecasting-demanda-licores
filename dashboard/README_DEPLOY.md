# Despliegue del dashboard en Streamlit Cloud

## Requisitos previos

- Repositorio con el proyecto (notebook de forecasting ya ejecutado al menos una vez para generar `data/predictions/`, `artifacts/modeling/experiment_manifest_latest.json` y `artifacts/modeling/experiments_history.csv`).
- Cuenta en [Streamlit Cloud](https://share.streamlit.io/).

## Pasos para desplegar

### 1. Conectar el repositorio

1. Entra en [Streamlit Cloud](https://share.streamlit.io/) e inicia sesión (GitHub).
2. Pulsa **"New app"**.
3. Elige el **repositorio**, la **rama** (p. ej. `main`) y la **ruta del directorio** del proyecto (raíz del repo).

### 2. Configurar comando y directorio

- **Main file path**: `dashboard/app.py`
- **Working directory**: deja la raíz del repositorio (así las rutas `artifacts/` y `data/` se resuelven correctamente).

En la UI de Cloud suele ser algo como:

- **Repository**: `tu-usuario/forecasing-licores`
- **Branch**: `main`
- **Main file path**: `dashboard/app.py`
- (Si hay campo "Working directory", déjalo vacío o raíz.)

El comando que ejecutará Cloud será equivalente a:

```bash
streamlit run dashboard/app.py
```

Desde la raíz del repo, por tanto el directorio de trabajo será la raíz y el dashboard encontrará `artifacts/modeling/` y `data/predictions/`.

### 3. Añadir Secrets (usuario y contraseña)

En la ficha de tu app en Streamlit Cloud: **Settings → Secrets**.

Añade las claves que el dashboard espera (formato TOML):

```toml
usuario = "tu_usuario"
password = "tu_contraseña"
```

**Importante**: No subas nunca usuario ni contraseña al repositorio. Solo configúralos en la pestaña Secrets de Streamlit Cloud.

Alternativamente, en el entorno de ejecución de Cloud puedes configurar variables de entorno (si tu fork del código las usa): `DASHBOARD_USUARIO` y `DASHBOARD_PASSWORD`.

### 4. Dependencias

Streamlit Cloud instalará las dependencias desde `requirements.txt` en la raíz del repo, si existe. Si el `requirements.txt` del dashboard está en `dashboard/requirements.txt`, asegúrate de que en la raíz del proyecto haya un `requirements.txt` que incluya al menos:

- streamlit
- pandas
- pyarrow (para Parquet)
- plotly (opcional, si se usan gráficos Plotly)

O configura en Cloud el path al archivo de requisitos si permite especificar `dashboard/requirements.txt`.

### 5. URL pública

Tras el primer deploy, Streamlit Cloud te dará una URL pública (ej. `https://tu-app.streamlit.app`). Comparte esa URL con quien deba acceder; entrarán con el **usuario** y **contraseña** configurados en Secrets.

## Ejecución en local

Desde la **raíz del repositorio**:

```bash
# Crear secrets local (no versionar)
mkdir -p dashboard/.streamlit
echo 'usuario = "admin"'      > dashboard/.streamlit/secrets.toml
echo 'password = "tu_pass"'   >> dashboard/.streamlit/secrets.toml

# Ejecutar
streamlit run dashboard/app.py
```

Asegúrate de tener generados antes `data/predictions/forecasting_predictions.parquet` (o .csv), `artifacts/modeling/experiment_manifest_latest.json` y `artifacts/modeling/experiments_history.csv` (ejecutando el notebook de forecasting).
