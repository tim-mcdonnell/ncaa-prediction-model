# Task: Implement Collection Pipeline for NCAA Basketball Data

## Task Summary
Develop the Collection Pipeline component that uses the ESPN API client to fetch and store NCAA basketball data as Parquet files.

## Context and Background
The Collection Pipeline is responsible for orchestrating the data collection process, using the ESPN API client to fetch data and then storing it in Parquet files. This pipeline needs to support both complete historical data collection and incremental updates during the basketball season.

This component connects the ESPN API client to our storage system and implements the business logic for determining what data to collect, how to validate it, and how to store it efficiently. It's a critical piece of the overall pipeline architecture as it provides the raw data that all downstream components will work with.

## Specific Requirements

### Data Collection Logic
- [ ] Implement season-based collection strategy
- [ ] Create game-specific data fetching
- [ ] Develop team roster collection
- [ ] Build conference and standings collection
- [ ] Implement boxscore and detailed statistics collection

### Incremental Updates
- [ ] Develop logic to identify new/changed games
- [ ] Create efficient update strategies
- [ ] Implement date-based collection for active seasons
- [ ] Build reconciliation for modified data

### Parquet Storage
- [ ] Create Parquet file organization structure
- [ ] Implement efficient write patterns
- [ ] Add compression and optimization
- [ ] Build partitioning strategy for large datasets

### Validation and Monitoring
- [ ] Implement data validation during collection
- [ ] Create collection metrics and logs
- [ ] Add completeness checking
- [ ] Build error reporting for failed collections

## Implementation Guidance

The Collection Pipeline should extend the BasePipeline class:

```python
from src.pipelines.base_pipeline import BasePipeline
from src.data.collection.espn.client import ESPNClient
import polars as pl
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import date, datetime, timedelta
import yaml

class CollectionPipeline(BasePipeline):
    """
    Pipeline for collecting NCAA basketball data from ESPN API and storing as Parquet files.
    
    Supports both full historical collection and incremental updates.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Collection Pipeline.
        
        Args:
            config_path: Path to YAML configuration file, or None to use defaults
        """
        super().__init__(config_path)
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.raw_dir = self.data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
    
    async def collect_season_games(self, season: int, mode: str = "complete"):
        """
        Collect all games for a specific NCAA basketball season.
        
        Args:
            season: Year representing the season (e.g., 2023 for 2022-2023 season)
            mode: "complete" to fetch all games, "incremental" for only new/changed games
            
        Returns:
            Number of games collected
        """
        self.logger.info(f"Collecting {mode} data for {season} season")
        
        # Configuration for ESPN API
        base_url = self.config.get("espn_api", {}).get("base_url", 
                 "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball")
        
        # Create API client
        async with ESPNClient(base_url=base_url) as client:
            # TODO: Implement collection logic
            pass
    
    async def collect_all_seasons(self, start_year: int, end_year: Optional[int] = None):
        """
        Collect data for multiple seasons.
        
        Args:
            start_year: First season to collect (e.g., 2002)
            end_year: Last season to collect, or None for current season
            
        Returns:
            Dictionary with collection statistics by season
        """
        # Default end_year to current season if not specified
        if end_year is None:
            current_year = datetime.now().year
            # If we're in Jan-July, we're in the previous year's season
            end_year = current_year if datetime.now().month > 7 else current_year - 1
        
        results = {}
        for year in range(start_year, end_year + 1):
            count = await self.collect_season_games(year)
            results[year] = count
        
        return results
    
    def save_parquet(self, df: pl.DataFrame, category: str, name: str):
        """
        Save a dataframe as a Parquet file in the appropriate directory.
        
        Args:
            df: Polars DataFrame to save
            category: Data category (e.g., "games", "teams", "conferences")
            name: Specific name for this dataset
            
        Returns:
            Path to the saved file
        """
        # TODO: Implement Parquet saving logic
        pass
```

## Acceptance Criteria
- [ ] All unit tests pass (`uv python -m pytest tests/pipelines/test_collection_pipeline.py -v`)
- [ ] Pipeline can collect complete NCAA basketball seasons
- [ ] Incremental updates correctly identify and fetch only new/changed data
- [ ] Data is properly stored in Parquet files with appropriate structure
- [ ] Collection process handles ESPN API errors gracefully
- [ ] Performance is reasonable for large data collection operations
- [ ] Documentation clearly explains how to use the pipeline

## Resources and References
- [Pipeline Architecture Document](../../pipeline-architecture.md)
- [ESPN API Client Task](./api_integration.md)
- [Polars Documentation](https://pola.rs/docs/)
- [Apache Parquet Format](https://parquet.apache.org/docs/)

## Constraints and Caveats
- Collection operations may take significant time for historical data
- ESPN API limitations may require careful rate limiting
- Large datasets may require partitioning for efficient storage and retrieval
- Must handle API format changes or inconsistencies gracefully

## Next Steps After Completion
Upon completion of this task, we will:
1. Run the collection pipeline to fetch historical NCAA basketball data
2. Begin work on the Processing Pipeline to transform this raw data
3. Document the structure and content of the collected data

## Related to Milestone
**Related to Milestone**: Milestone 1: Data Collection and Storage  
**Task ID**: #3  
**Priority**: High  
**Estimated Effort**: 4 days  
**Assigned To**: TBD  

## Description
This task involves implementing the CollectionPipeline class that orchestrates the data collection process using the ESPN API client. The pipeline will be responsible for fetching NCAA basketball data, validating it, and storing it in Parquet files. It needs to support both complete historical data collection and incremental updates during the basketball season.

## Technical Details
The implementation should extend the BasePipeline class, use the ESPN API client for data fetching, and Polars/Pyarrow for Parquet file operations. The pipeline should implement efficient incremental update strategies and appropriate partitioning for large datasets. Configuration should follow the project's patterns and be customizable through YAML files.

## Subtasks
- [ ] Develop collection pipeline for NCAA basketball games
- [ ] Implement season-based collection logic
- [ ] Create incremental update functionality
- [ ] Build Parquet file storage utilities
- [ ] Add data validation during collection
- [ ] Write comprehensive unit tests
- [ ] Create documentation and usage examples

## Dependencies
- ESPN API Client implementation
- Base Pipeline implementation
- Project structure for data storage

## Progress Updates
<!-- To be filled as work progresses -->

---

## Notes
The Collection Pipeline should be designed with scalability in mind, as we'll eventually need to collect data for many seasons. Consider implementing parallelization where appropriate, but be mindful of API rate limits. 