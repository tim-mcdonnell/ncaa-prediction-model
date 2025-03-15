"""
Example demonstrating how to use the historical data collection script.

This script shows:
1. How to collect data for a specific range of seasons
2. How to configure the collection process
3. How to process the results

Usage:
    python -m examples.historical_data_collection_demo
"""

import asyncio
import json
from pathlib import Path

from src.scripts.historical_data_collection import (
    HistoricalDataCollector,
    collect_historical_data,
    create_progress_report
)


async def example_full_collection():
    """
    Example of collecting data for multiple seasons with the high-level API.
    
    This uses the collect_historical_data function which handles all steps
    including report generation and storage.
    """
    print("\n=== Example: Full Collection Process ===")
    print("Collecting data for 2022-2023 seasons...")
    
    # This is commented out as it would actually run the collection
    # which can take a long time and make real API calls
    """
    await collect_historical_data(
        start_year=2022,  # Only collect recent seasons for the demo
        end_year=2023,
        data_dir="demo_data",
        log_level="info"
    )
    """
    
    print("[Demo mode: Collection skipped]")
    print("This would collect all games from the 2022 and 2023 seasons")
    print("and store them in the demo_data directory.")


async def example_custom_collector():
    """
    Example of using the HistoricalDataCollector class directly for
    more control over the collection process.
    """
    print("\n=== Example: Custom Collector ===")
    print("Creating a custom collector for 2021-2022...")
    
    # Create collector
    collector = HistoricalDataCollector(
        start_year=2021,
        end_year=2022,
        data_dir="demo_data"
    )
    
    # In a real script, you would do:
    # results = await collector.collect_and_process()
    
    # For the demo, we'll simulate some results
    print("[Demo mode: Collection skipped]")
    
    # Create simulated results for demonstration
    simulated_results = [
        {
            "season": 2021,
            "pipeline_result": type('obj', (object,), {
                'status': type('obj', (object,), {'value': 'SUCCESS'}),
                'metadata': {
                    'games_count': 5000,
                    'teams_count': 350
                }
            }),
            "quality_report": type('obj', (object,), {
                'data_issues': [
                    "Column 'score' has 5 missing values"
                ],
                'overall_stats': {
                    'total_rows': 5000,
                    'missing_count': 5
                }
            })
        },
        {
            "season": 2022,
            "pipeline_result": type('obj', (object,), {
                'status': type('obj', (object,), {'value': 'SUCCESS'}),
                'metadata': {
                    'games_count': 5200,
                    'teams_count': 350
                }
            }),
            "quality_report": type('obj', (object,), {
                'data_issues': [],
                'overall_stats': {
                    'total_rows': 5200,
                    'missing_count': 0
                }
            })
        }
    ]
    
    # Create progress report from simulated results
    report = create_progress_report(simulated_results)
    
    # Print report summary
    print("\nGenerated Progress Report:")
    print(f"Total seasons: {report['total_seasons']}")
    print(f"Total games: {report['total_games']}")
    print(f"Total teams: {report['total_teams']}")
    print(f"Total issues: {report['total_issues']}")
    
    # Write report to file for demonstration
    reports_dir = Path("demo_data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / "demo_collection_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    
    print(f"\nSaved demo report to: {report_path}")


async def example_resumable_collection():
    """
    Example showing how to implement a resumable collection process
    that can be interrupted and continued.
    """
    print("\n=== Example: Resumable Collection ===")
    
    # In a real resumable collection, you would:
    # 1. Check which seasons have already been processed
    # 2. Create a collector for the remaining seasons
    # 3. Process only the remaining seasons
    
    print("To implement a resumable collection:")
    print("1. Check existing data directories:")
    
    # Code to check which seasons are already collected
    data_dir = Path("demo_data/cleaned")
    completed_seasons = []
    
    if data_dir.exists():
        completed_seasons = [int(dir_name) for dir_name in 
                            [d.name for d in data_dir.iterdir() if d.is_dir()]
                            if dir_name.isdigit()]
    
    # For the demo, we'll pretend some seasons are already collected
    completed_seasons = [2000, 2001, 2002]
    
    print(f"   - Already collected seasons: {completed_seasons}")
    
    # Determine remaining seasons
    all_seasons = list(range(2000, 2025))
    remaining_seasons = [s for s in all_seasons if s not in completed_seasons]
    
    print(f"   - Remaining seasons to collect: {remaining_seasons[:5]}... "
          f"(and {len(remaining_seasons) - 5} more)")
    
    # In a real script, you would process remaining seasons in batches
    print("\n2. Process remaining seasons in batches:")
    print("   - Batch size: 5 seasons")
    print("   - This allows interrupting and resuming the collection")
    
    batch_size = 5
    for i in range(0, len(remaining_seasons), batch_size):
        batch = remaining_seasons[i:i+batch_size]
        print(f"   - Processing batch: {batch}")
        
        # In a real script:
        # start_year = batch[0]
        # end_year = batch[-1]
        # await collect_historical_data(start_year, end_year, "data", "info")


async def main():
    """Run all examples."""
    print("=== Historical Data Collection Examples ===")
    print("These examples demonstrate how to use the collection script.")
    
    await example_full_collection()
    await example_custom_collector()
    await example_resumable_collection()
    
    print("\n=== Examples Completed ===")
    print("Check demo_data/reports for the demo report.")


if __name__ == "__main__":
    asyncio.run(main()) 