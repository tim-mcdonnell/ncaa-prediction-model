# Technology Stack

This project leverages a modern Python-based technology stack, optimized for data processing, machine learning, and visualization.

## Core Technologies

| Category | Technologies | Purpose |
|----------|--------------|---------|
| **Language** | Python 3.11 | Primary development language |
| **Package Management** | [uv](https://github.com/astral-sh/uv) | Fast, reliable dependency management |
| **Code Quality** | [ruff](https://github.com/astral-sh/ruff) | Linting and formatting |
| **Type Checking** | mypy | Static type checking |
| **Testing** | pytest | Unit and integration testing |
| **Documentation** | MkDocs, Material theme | Project documentation |

## Data Stack

| Category | Technologies | Purpose |
|----------|--------------|---------|
| **Data Analysis** | Polars, NumPy | Data manipulation and numerical computing |
| **Data Storage** | Parquet | Column-oriented data storage format |
| **API Integration** | httpx | HTTP client for API communication |
| **Data Validation** | Pydantic | Data validation and parsing |
| **Pipeline Orchestration** | Custom pipeline modules | Data flow orchestration |

## Machine Learning Stack

| Category | Technologies | Purpose |
|----------|--------------|---------|
| **ML Framework** | scikit-learn | Core ML algorithms and utilities |
| **Advanced ML** | XGBoost/LightGBM | Gradient boosting algorithms |
| **Model Validation** | scikit-learn, custom metrics | Model evaluation |
| **Hyperparameter Optimization** | scikit-learn, Optuna | Parameter tuning |
| **Feature Engineering** | Custom transformers, sklearn pipeline | Feature creation |

## Visualization Stack

| Category | Technologies | Purpose |
|----------|--------------|---------|
| **Dashboard** | Dash | Interactive web application |
| **Visualizations** | Plotly | Interactive charts and graphs |
| **Exploratory Analysis** | Jupyter notebooks | Data exploration and modeling |
| **Reporting** | Custom components | Model performance reporting |

## Development Tools

| Category | Technologies | Purpose |
|----------|--------------|---------|
| **Version Control** | Git, GitHub | Source code management |
| **CI/CD** | GitHub Actions | Continuous integration and deployment |
| **Environment Management** | uv | Virtual environment management |
| **Dependency Tracking** | pyproject.toml | Project metadata and dependencies |

## Why These Technologies?

### uv for Package Management

We chose [uv](https://github.com/astral-sh/uv) as our package manager because:

- It's **10-100x faster** than pip
- Provides consistent, reproducible builds
- Works seamlessly with pyproject.toml
- Offers excellent caching with a global package cache

### Parquet and Polars for Data Storage and Processing

We chose a Parquet-first approach with Polars because:

- **Columnar Storage**: Parquet's columnar format is ideal for analytical workloads
- **Compression**: Efficient storage with high compression ratios
- **Performance**: Polars provides extremely fast data processing (10-100x faster than Pandas)
- **Memory Efficiency**: Better memory usage for large datasets
- **Simplicity**: Direct file-based storage without database overhead
- **Integration**: Excellent support for Parquet files in Python data ecosystem
- **Arrow Compatibility**: Built on Apache Arrow for interoperability
- **Functional Pipelines**: Clean, expressive data processing with Polars

### Dash/Plotly for Visualization

We chose Dash and Plotly for our dashboard because:

- Pure Python development (no JavaScript required)
- Interactive visualizations with minimal code
- Responsive design for various screen sizes
- Integration with Polars data structures

### scikit-learn for Machine Learning

We chose scikit-learn as our primary ML framework because:

- Consistent API across algorithms
- Excellent pipeline abstractions
- Strong community and documentation
- Seamless integration with NumPy and our data pipeline 