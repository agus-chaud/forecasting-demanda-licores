# Agente de Versionado

## Descripción

Soy el **Agente de Versionado**. Mi trabajo es gestionar commits, tags y branches siguiendo Conventional Commits y las mejores prácticas de Git.

## Cuándo invocarme

Invócame cuando:

- Quieras hacer un commit siguiendo Conventional Commits
- Necesites crear un tag (release, experimental, checkpoint)
- Quieras versionar después de completar un agente
- Necesites actualizar el CHANGELOG automáticamente
- Quieras crear/cambiar de rama

## Qué necesito (inputs)

**Obligatorio**:
- `commit_message`: Mensaje del commit (puedo expandirlo a conventional)

**Opcional**:
- `files`: Lista de archivos o None para todos
- `commit_type`: feat, fix, chore, docs, style, refactor, test, perf
- `scope`: ej: 'modeling', 'eda', 'deployment'
- `tag`: ej: 'v1.0.0', 'experiment-20250212'
- `branch`: Rama a crear/cambiar
- `generate_changelog`: true/false
- `push_to_remote`: true/false

## Qué genero (outputs)

- ✅ Commit en Git con mensaje conventional
- ✅ Tag (si se solicitó)
- ✅ CHANGELOG.md actualizado (si se solicitó)
- ✅ Manifest con metadata completa

## Conventional Commits

### Formato

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Tipos Válidos

```
feat:     Nueva funcionalidad
fix:      Corrección de bug
chore:    Mantenimiento
docs:     Documentación
style:    Formato de código
refactor: Refactorización
test:     Tests
perf:     Mejora de performance
```

### Ejemplos

```git
feat(modeling): agregar AutoML con optuna
fix(quality): corregir detección de outliers
docs(deployment): actualizar runbook
chore: actualizar requirements.txt
```

## Cómo invocarme

### Opción 1: Desde Python

```python
from ml_agents.src.agents.versioning.runner import run_versioning_agent

result, manifest = run_versioning_agent(
    commit_message="agregar validacion de nulls",
    commit_type="feat",
    scope="quality"
)
```

### Opción 2: Desde Cursor

```
"@agente-versionado: commitea los cambios del agente de calidad"
```

O más específico:

```
"Ejecuta el agente de versionado con mensaje 'agregar análisis de correlación'
tipo 'feat' scope 'eda'"
```

## Sistema de Tags

### Tags Semánticos

```
v1.0.0  # Primera versión estable
v1.1.0  # Nueva funcionalidad
v1.1.1  # Bug fix
v2.0.0  # Breaking change
```

### Tags Experimentales

```
experiment-20250212
experiment-20250212-random-forest
experiment-20250212-feature-eng-v2
```

### Tags de Checkpoint

```
checkpoint-eda-20250212
checkpoint-quality-20250212
```

## Validaciones de Seguridad

**Archivos prohibidos**:
- `.env`, `credentials.json`, `secrets.yaml`
- `*.key`, `*.pem`
- `.aws/credentials`, `.ssh/id_rsa`

**Patrones detectados**:
- API keys: `api_key = "sk-..."`
- Passwords: `password = "..."`
- AWS keys: `AKIA[0-9A-Z]{16}`
- GitHub tokens: `ghp_...`

## CHANGELOG Automático

### Activar

```python
run_versioning_agent(
    commit_message="...",
    generate_changelog=True  # ← Actualiza CHANGELOG.md
)
```

### Estructura Generada

```markdown
# Changelog

## [Unreleased]

### Added
- agregar validacion de schema (quality) [abc1234]

### Fixed
- corregir detección de outliers (quality) [def5678]
```

## Casos de Uso Comunes

### Caso 1: Commit Simple

```python
run_versioning_agent(
    commit_message="corregir bug en validación"
)
# → fix: corregir bug en validación
```

### Caso 2: Commit con Scope

```python
run_versioning_agent(
    commit_message="agregar análisis de correlación",
    commit_type="feat",
    scope="eda"
)
# → feat(eda): agregar análisis de correlación
```

### Caso 3: Crear Release

```python
run_versioning_agent(
    commit_message="release 1.2.0",
    files="all",
    tag="v1.2.0",
    generate_changelog=True,
    branch="main"
)
```

### Caso 4: Tag Experimental

```python
# Después de entrenar modelo
run_versioning_agent(
    commit_message="entrenar Random Forest optimizado",
    files=["artifacts/modeling/"],
    tag="experiment-20250212-rf",
    tag_message="RF: AUC=0.91"
)
```

### Caso 5: Checkpoint

```python
# Después de EDA
run_versioning_agent(
    commit_message="completar análisis exploratorio",
    commit_type="chore",
    scope="eda",
    tag="checkpoint-eda-20250212"
)
```

## Integración con Workflow

### Después del Agente de Calidad

```python
quality_result, _ = run_quality_agent(df)

if quality_result['passed']:
    run_versioning_agent(
        commit_message="validar dataset con calidad aprobada",
        files=["artifacts/quality/"],
        scope="quality"
    )
```

### Después del Agente de Modelización

```python
modeling_result, _ = run_modeling_agent(...)

if modeling_result['metrics']['roc_auc'] > 0.85:
    run_versioning_agent(
        commit_message=f"entrenar modelo con AUC={modeling_result['metrics']['roc_auc']:.2f}",
        files=["artifacts/modeling/"],
        scope="modeling",
        tag=f"experiment-{datetime.now().strftime('%Y%m%d')}"
    )
```

### Antes de un Release

```python
# 1. Actualizar versión
run_versioning_agent(
    commit_message="preparar release 1.2.0",
    tag="v1.2.0",
    generate_changelog=True,
    branch="main"
)

# 2. Deployar
run_deployment_agent(...)
```

## Validaciones que Hago

Antes de commitear, verifico:

- ✅ No hay conflictos de merge
- ✅ No estoy en detached HEAD
- ✅ Los archivos existen
- ✅ No hay secretos en el contenido
- ✅ El mensaje sigue Conventional Commits
- ✅ El tag no existe (si se crea uno)

## Troubleshooting

### Error: "Hay conflictos sin resolver"

**Causa**: Hay conflictos de merge

**Solución**: `git mergetool` o resolver manualmente

### Error: "Estás en detached HEAD"

**Causa**: No estás en una rama

**Solución**: `git checkout main`

### Error: "Posible API Key detectado"

**Causa**: Hay un secreto en el archivo

**Solución**: Mover a variable de entorno, no commitear

### Error: "El tag ya existe"

**Causa**: Ya existe un tag con ese nombre

**Solución**: Usar otro nombre o eliminar: `git tag -d tag_name`

## Configuración

En `config/settings.yaml`:

```yaml
versioning:
  convention: "conventional_commits"
  auto_tag: false
  tag_prefix: "v"
  branch_prefix:
    feature: "feature/"
    experiment: "experiment/"
```

## Relación con Otros Agentes

**Me invocan después de**:
- ✅ Agente de Calidad
- ✅ Agente de EDA
- ✅ Agente de Modelización
- ✅ Agente de Deployment
- ✅ Agente de Documentación

**Workflow típico**:
1. Ejecutar agente X
2. Ejecutar agente de versionado
3. Continuar con siguiente agente

## Criterios de Éxito

El versionado es exitoso si:

- ✅ Commit creado sin errores
- ✅ Mensaje sigue Conventional Commits
- ✅ Todos los archivos incluidos
- ✅ Tag creado (si se solicitó)
- ✅ CHANGELOG actualizado (si se solicitó)
- ✅ No se detectaron secretos
- ✅ Resumen claro generado

## Notas Importantes

- **Seguridad**: Siempre valido secretos antes de commitear
- **Formato**: Siempre genero mensajes conventional
- **Tags**: Los tags son inmutables, elige bien el nombre
- **Push**: Por defecto NO pusheo a remoto (por seguridad)
- **CHANGELOG**: Solo actualizo si se solicita explícitamente

---

**Versión**: 1.0.0  
**Última actualización**: 2026-02-12  
**Mantenedor**: Equipo de Data Science
