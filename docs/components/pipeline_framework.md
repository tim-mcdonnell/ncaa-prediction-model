# Pipeline Framework

## Overview
The Pipeline Framework provides a standardized approach to data processing tasks with consistent patterns for lifecycle management, state tracking, error handling, and more. It consists of four core components:

- **Base Pipeline**: Core pipeline infrastructure with lifecycle management
- **Pipeline Composition**: Mechanism for chaining pipelines together
- **Dependency Injection**: System for flexible dependency management
- **Monitoring Hooks**: Event-based monitoring system for telemetry

## Responsibilities
- Provide consistent pipeline lifecycle (validation, execution, cleanup)
- Enable composition of pipelines for complex workflows
- Support dependency injection for flexible component wiring
- Facilitate monitoring and telemetry collection
- Handle error conditions and resource management

## Key Classes
- `BasePipeline`: Abstract base class for all pipeline components
- `PipelineContext`: Container for pipeline input parameters and data
- `PipelineResult`: Container for pipeline output data and status
- `ComposedPipeline`: Pipeline that executes a sequence of other pipelines
- `Dependency`: Registry and resolver for dependency injection
- `PipelineMonitor`: Interface for components that monitor pipeline execution

## Usage Examples

### Basic Pipeline
```python
from src.pipelines.base_pipeline import BasePipeline, PipelineContext, PipelineResult, PipelineStatus

class DataProcessingPipeline(BasePipeline):
    async def _validate(self, context: PipelineContext) -> bool:
        return "data" in context.input_data
        
    async def _execute(self, context: PipelineContext) -> PipelineResult:
        # Process data
        input_data = context.input_data["data"]
        result_data = some_processing_function(input_data)
        
        return PipelineResult(
            status=PipelineStatus.SUCCESS,
            output_data={"result": result_data}
        )
        
    async def _cleanup(self) -> None:
        # Release resources
        pass

# Execute the pipeline
pipeline = DataProcessingPipeline()
context = PipelineContext(input_data={"data": your_data})
result = await pipeline.execute(context)
```

### Pipeline Composition
```python
from src.pipelines.pipeline_composition import ComposedPipeline

# Create individual pipelines
data_loader = DataLoaderPipeline()
data_processor = DataProcessingPipeline()
data_exporter = DataExportPipeline()

# Compose them into a single pipeline
workflow = ComposedPipeline(
    name="data_workflow",
    pipelines=[data_loader, data_processor, data_exporter]
)

# Execute the composed pipeline
result = await workflow.execute(PipelineContext(params={"source": "database"}))
```

### Dependency Injection
```python
from src.pipelines.dependency_injection import injectable, Dependency
from typing import Protocol

# Define protocol
class DataStorage(Protocol):
    async def save(self, data, path): ...

# Register implementation
Dependency.register(DataStorage, S3StorageImpl())

# Use in pipeline
class ExportPipeline(BasePipeline):
    @injectable
    def __init__(self, storage: DataStorage):
        super().__init__()
        self.storage = storage
        
    async def _execute(self, context):
        # Use the injected dependency
        await self.storage.save(context.input_data["data"], "output.parquet")
```

## Configuration

The Pipeline Framework provides several configuration options that control behavior related to:
- Logging and error handling
- Performance and concurrency
- Dependency injection
- Monitoring and telemetry

Configuration can be set through environment variables, configuration files, or programmatically at runtime.

### Base Pipeline Configuration

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_LOG_LEVEL` | `INFO` | Controls verbosity of pipeline logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PIPELINE_EXECUTION_TIMEOUT_MS` | `3600000` | Maximum time (in milliseconds) a pipeline can run before timeout (default: 1 hour) |
| `PIPELINE_STACK_TRACE_ON_ERROR` | `FALSE` | If `TRUE`, logs full stack traces when pipelines encounter errors |
| `PIPELINE_CACHE_ENABLED` | `TRUE` | Enable/disable result caching between pipeline runs |

#### Code Example: Setting Configuration Programmatically

```python
from src.pipelines.config import PipelineConfig

# Set configuration globally
PipelineConfig.set("log_level", "DEBUG")
PipelineConfig.set("execution_timeout_ms", 10000)  # 10 seconds

# Configuration can also be set per pipeline instance
class MyCustomPipeline(BasePipeline):
    def __init__(self, timeout_ms: int = None):
        super().__init__()
        if timeout_ms:
            self.set_config("execution_timeout_ms", timeout_ms)
```

### Pipeline Composition Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_COMPOSITION_VALIDATE_ALL` | `TRUE` | If `TRUE`, validates all pipelines before execution begins |
| `PIPELINE_COMPOSITION_PARALLEL` | `FALSE` | If `TRUE`, executes independent pipelines in parallel when possible |
| `PIPELINE_COMPOSITION_MAX_WORKERS` | `4` | Maximum number of worker threads for parallel execution |

#### Code Example: Configuring Composed Pipelines

```python
from src.pipelines.pipeline_composition import ComposedPipeline, CompositionConfig

# Create configuration
config = CompositionConfig(
    validate_all=True,
    parallel_execution=True,
    max_workers=8
)

# Apply to a composed pipeline
composed_pipeline = ComposedPipeline(
    name="parallel_data_processing",
    pipelines=[pipeline1, pipeline2, pipeline3],
    config=config
)
```

### Dependency Injection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPENDENCY_STRICT_MODE` | `TRUE` | If `TRUE`, fails when dependencies cannot be resolved |
| `DEPENDENCY_AUTO_REGISTER` | `FALSE` | If `TRUE`, automatically registers singleton implementations for protocols with only one implementation |
| `DEPENDENCY_REGISTRY_PATH` | None | Optional path to YAML file defining dependency mappings |

#### Code Example: Configuring the Dependency Registry

```python
from src.pipelines.dependency_injection import Dependency, injectable
from typing import Protocol

# Define protocol
class DataStorage(Protocol):
    async def save(self, data, path): ...

# Define implementation
class S3Storage:
    async def save(self, data, path):
        # Implementation...
        pass

# Register implementation
Dependency.register(DataStorage, S3Storage())

# Configure registry
Dependency.configure(strict_mode=True, auto_register=False)

# Load configurations from file
Dependency.load_config("configs/dependencies.yml")
```

Example dependencies.yml file:
```yaml
dependencies:
  - protocol: "src.interfaces.DataStorage"
    implementation: "src.storage.S3Storage"
    args:
      bucket: "my-data-bucket"
      region: "us-west-2"
  
  - protocol: "src.interfaces.ModelRegistry"
    implementation: "src.ml.MLflowRegistry"
    args:
      tracking_uri: "http://mlflow.example.com"
```

### Monitoring and Telemetry Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MONITORING_ENABLED` | `TRUE` | Master switch to enable/disable monitoring |
| `MONITORING_CONSOLE_ENABLED` | `TRUE` | Enable/disable console monitoring |
| `MONITORING_STATSD_ENABLED` | `FALSE` | Enable/disable StatsD metrics |
| `MONITORING_STATSD_HOST` | `localhost` | StatsD server hostname |
| `MONITORING_STATSD_PORT` | `8125` | StatsD server port |
| `MONITORING_STATSD_PREFIX` | `pipeline` | Prefix for StatsD metrics |
| `MONITORING_EVENT_FILTER` | None | Comma-separated list of event types to include (if empty, all events are included) |

#### Code Example: Configuring Monitoring

```python
from src.pipelines.monitoring import (
    register_monitor, ConsoleMonitor, StatsDMonitor, MonitoringConfig
)

# Configure monitoring globally
MonitoringConfig.set_enabled(True)
MonitoringConfig.set_event_filter(["pipeline_start", "pipeline_end", "pipeline_error"])

# Register monitors with custom configuration
console_monitor = ConsoleMonitor(
    log_level="INFO",
    include_metadata=True
)
register_monitor(console_monitor)

stats_monitor = StatsDMonitor(
    host="metrics.example.com",
    port=8125,
    prefix="ncaa.pipelines",
    include_tags=True
)
register_monitor(stats_monitor)
```

### Advanced Configuration Options

#### Retries and Error Handling

```python
from src.pipelines.base_pipeline import BasePipeline, RetryConfig

class DataFetchPipeline(BasePipeline):
    def __init__(self):
        super().__init__()
        
        # Configure retry behavior
        self.set_retry_config(RetryConfig(
            max_retries=3,
            retry_delay_ms=1000,  # 1 second initial delay
            backoff_factor=2.0,   # Exponential backoff
            retry_on_exceptions=[ConnectionError, TimeoutError]
        ))
```

#### Result Caching

```python
from src.pipelines.base_pipeline import BasePipeline, CacheConfig

class FeatureCalculationPipeline(BasePipeline):
    def __init__(self):
        super().__init__()
        
        # Configure caching behavior
        self.set_cache_config(CacheConfig(
            enabled=True,
            ttl_seconds=3600,  # Cache results for 1 hour
            cache_key_params=["season", "team_id"],  # Parameters that affect cache key
            cache_backend="redis"  # Use Redis for caching
        ))
```

### Configuration File Example

Configuration can also be loaded from a YAML file:

```yaml
# pipeline_config.yml
base_pipeline:
  log_level: INFO
  execution_timeout_ms: 3600000
  stack_trace_on_error: false
  cache_enabled: true

composition:
  validate_all: true
  parallel_execution: true
  max_workers: 4

dependency_injection:
  strict_mode: true
  auto_register: false
  registry_path: configs/dependencies.yml

monitoring:
  enabled: true
  console_enabled: true
  statsd_enabled: true
  statsd_host: metrics.example.com
  statsd_port: 8125
  statsd_prefix: ncaa.pipelines
  event_filter: [pipeline_start, pipeline_end, pipeline_error]
```

Loading the configuration:

```python
from src.pipelines.config import load_config_from_file

# Load configuration from file
load_config_from_file("configs/pipeline_config.yml")

# Configuration is now applied to all framework components
```

### Environment-Specific Configuration

You can set up environment-specific configurations using the `PIPELINE_ENV` environment variable:

```python
import os
from src.pipelines.config import load_config_from_file

# Load the environment-specific configuration
env = os.getenv("PIPELINE_ENV", "development")
config_path = f"configs/pipeline_config.{env}.yml"
load_config_from_file(config_path)
```

Common environments include:
- `development`: For local development (more verbose logging, shorter timeouts)
- `testing`: For test environments (in-memory dependencies, mocks)
- `production`: For production use (optimized performance, external services) 