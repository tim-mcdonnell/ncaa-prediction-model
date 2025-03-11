# ADR-002: Analytics-Focused Data Storage with DuckDB

## Status

Accepted

## Date

2023-05-22

## Context

The NCAA Basketball Prediction Model requires a data storage solution that can:

1. Store raw data collected from ESPN APIs (games, teams, seasons, etc.)
2. Support efficient analytical queries for feature engineering
3. Integrate well with data processing and visualization components
4. Handle the expected data volume (22+ years of NCAA basketball data)
5. Provide good performance for complex statistical calculations
6. Be reasonably simple to set up and maintain

We need to consider the full lifecycle of our data pipeline from collection through feature engineering to visualization, while allowing for future extensibility.

## Decision

We will implement an analytics-focused data storage architecture with the following components:

1. **Primary Database**: DuckDB for data storage and analytical queries
2. **File-Based Storage Layer**: Organized storage of raw data and optimized formats
3. **Repository Abstraction Layer**: Database-agnostic interfaces for data access

The architecture will use:
- **DuckDB** as the primary database for storing processed data and computing features
- **Parquet files** for efficient, columnar storage of larger datasets
- **Repository pattern** to abstract database implementation details
- **SQLAlchemy** (optionally) for more complex ORM needs

### Key Components:

#### 1. File Storage Structure
```
data/
├── raw/                  # Raw data from ESPN API
│   ├── games/            # Game data organized by season
│   │   ├── 2000/
│   │   │   ├── game_123456.json
│   │   │   └── ...
│   │   ├── 2001/
│   │   └── ...
│   ├── teams/            # Team data
│   └── ...               # Other raw data
├── processed/            # Processed data in efficient formats
│   ├── games.parquet     # Cleaned and processed game data
│   ├── teams.parquet     # Team information
│   └── ...               # Other processed datasets
└── features/             # Engineered features for modeling
    ├── team_ratings.parquet
    ├── game_features.parquet
    └── ...
```

#### 2. Repository Pattern Implementation
```python
# src/data/storage/repository.py
from abc import ABC, abstractmethod

class Repository(ABC):
    """Abstract base repository defining the interface."""
    
    @abstractmethod
    def save(self, entity):
        """Save an entity to the repository."""
        pass
    
    @abstractmethod
    def find_by_id(self, entity_id):
        """Find an entity by its ID."""
        pass
    
    @abstractmethod
    def find_all(self, filters=None):
        """Find all entities matching the given filters."""
        pass

# Concrete implementation for DuckDB
class DuckDBRepository(Repository):
    """DuckDB implementation of repository."""
    
    def __init__(self, db_path, table_name):
        self.conn = duckdb.connect(db_path)
        self.table_name = table_name
    
    def save(self, entity):
        # Implementation for DuckDB
        pass
    
    def find_by_id(self, entity_id):
        # Implementation for DuckDB
        pass
    
    def find_all(self, filters=None):
        # Implementation for DuckDB
        pass
```

#### 3. Domain-Specific Repositories

```python
# src/data/storage/game_repository.py
class GameRepository(Repository):
    """Repository for game data with domain-specific methods."""
    
    @abstractmethod
    def find_by_season(self, season):
        """Find all games in a specific season."""
        pass
    
    @abstractmethod
    def find_by_team(self, team_id, season=None):
        """Find all games for a specific team."""
        pass
    
    @abstractmethod
    def find_matchups(self, team1_id, team2_id):
        """Find all games between two teams."""
        pass

# Concrete implementation for DuckDB
class DuckDBGameRepository(GameRepository):
    # Implementations of the abstract methods
    pass
```

## Consequences

### Benefits

1. **Analytical Performance**: DuckDB is optimized for the analytical queries we'll use in feature engineering
2. **Simplicity**: No need to run a separate database server or manage connection pools
3. **Pandas Integration**: Excellent integration with Pandas for data science workflows
4. **SQL Support**: Full SQL support with advanced analytical functions
5. **File-Based**: Easy to back up, version control, and share
6. **Migration Path**: The repository abstraction allows for switching to PostgreSQL if needed later

### Challenges

1. **Limited Concurrency**: DuckDB has more limited concurrency than PostgreSQL
2. **Maturity**: DuckDB is less mature than PostgreSQL, though it's rapidly developing
3. **Administration Tools**: Fewer administration tools compared to PostgreSQL
4. **Ecosystem**: Smaller ecosystem and community compared to PostgreSQL

## Alternatives Considered

### PostgreSQL

**Benefits**:
- Mature, widely-used database with extensive tooling
- Excellent concurrency support
- Advanced features like full-text search and stored procedures
- Strong ecosystem and community support

**Drawbacks**:
- Requires running a separate database server
- More complex to set up and maintain
- OLTP-oriented design (although with good analytical capabilities)
- Heavier operational burden for a data science project

**Rejection Rationale**: While PostgreSQL is an excellent database, its operational complexity is unnecessary for our current needs. The added setup and maintenance burden doesn't justify the benefits for a primarily analytical, single-user workload.

### SQLite

**Benefits**:
- Simple, file-based database
- Zero configuration
- Good integration with Python

**Drawbacks**:
- Limited analytical query performance
- Less suitable for larger datasets
- Limited concurrency
- Missing advanced analytical functions

**Rejection Rationale**: DuckDB offers all the simplicity benefits of SQLite but with vastly superior analytical performance and features.

### Pure Parquet Files + Pandas

**Benefits**:
- Extremely simple file-based storage
- Direct integration with Pandas
- No SQL knowledge required

**Drawbacks**:
- Limited query capabilities compared to SQL
- Potential memory issues with large datasets
- Less structured approach to data management

**Rejection Rationale**: While this approach works for smaller projects, our complex feature engineering will benefit significantly from SQL's expressive power and DuckDB's optimized query engine.

## References

- [DuckDB Documentation](https://duckdb.org/docs/)
- [Parquet Format](https://parquet.apache.org/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Analytics Engineering with DuckDB](https://motherduck.com/blog/analytics-engineering-duckdb/)
- [DuckDB vs PostgreSQL](https://motherduck.com/blog/duckdb-vs-postgres/)
- [Related ADR: ADR-001 Modular Data Collection Architecture](adr-001-modular-data-collection.md) 