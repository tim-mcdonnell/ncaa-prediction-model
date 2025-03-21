"""Parquet storage utilities for the NCAA Basketball Prediction Model.

This module provides functionality for storing and retrieving NCAA basketball data
using partitioned Parquet files for the bronze layer, following the medallion architecture.
It implements endpoint-specific partitioning strategies based on data characteristics.
"""

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl
import structlog

# Initialize logger
logger = structlog.get_logger(__name__)


class ParquetStorage:
    """Utility class for Parquet file operations with endpoint-specific partitioning strategies."""

    def __init__(self: "ParquetStorage", base_dir: str = "data/raw") -> None:
        """Initialize Parquet storage.

        Args:
            base_dir: Base directory for storing Parquet files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Initialized Parquet storage", base_dir=str(self.base_dir))

    def write_scoreboard_data(
        self: "ParquetStorage",
        date: str,
        source_url: str,
        parameters: dict[str, Any],
        data: dict[str, Any],
        content_hash: str | None = None,
        created_at: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Write scoreboard data to partitioned Parquet files.

        Args:
            date: Date string in YYYY-MM-DD format
            source_url: Source URL
            parameters: Request parameters
            data: Response data
            content_hash: Optional content hash (will be generated if not provided)
            created_at: Optional timestamp (will use current time if not provided)

        Returns:
            Dict containing success status and file information
        """
        # Parse year and month from date for partitioning
        if not date:
            logger.error("Date is required for scoreboard data partitioning")
            return {"success": False, "error": "Date is required for partitioning"}

        try:
            year, month, _ = date.split("-")
        except ValueError:
            logger.error("Invalid date format", date=date)
            return {"success": False, "error": "Invalid date format"}

        # Create partition directory
        partition_dir = self.base_dir / "scoreboard" / f"year={year}" / f"month={month}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for storage
        if created_at is None:
            created_at = datetime.datetime.now()

        # Handle parameters - ensure it's a JSON string
        params_json = parameters if isinstance(parameters, str) else json.dumps(parameters)

        # Prepare JSON data
        json_data = json.dumps(data) if not isinstance(data, str) else data

        # Generate content hash if not provided
        if content_hash is None:
            content_hash = hashlib.sha256(json_data.encode("utf-8")).hexdigest()
            logger.debug("Generated content hash for scoreboard data", date=date, hash=content_hash)

        # Define target file path
        file_path = partition_dir / "data.parquet"

        # Create DataFrame with a single row
        new_row = pl.DataFrame(
            {
                "date": [date],
                "source_url": [source_url],
                "parameters": [params_json],
                "content_hash": [content_hash],  # Now always has a value
                "raw_data": [json_data],
                "created_at": [created_at],
                "year": [str(year)],  # Ensure year is a string type
                "month": [str(month)],  # Ensure month is a string type
            }
        )

        # If file exists, read it, check for changes, and update if needed
        if file_path.exists():
            try:
                # Read existing file
                try:
                    existing_df = pl.read_parquet(file_path)
                except Exception as e:
                    logger.error(
                        "Error reading existing Parquet file, will create new file",
                        file=str(file_path),
                        error=str(e),
                    )
                    # If file is corrupted, create a new one
                    try:
                        success = self._write_dataframe_safely(new_row, file_path)
                        if not success:
                            logger.error(
                                "Failed to create new scoreboard data file after read error",
                                file=str(file_path),
                            )
                            return {"success": False, "error": "Failed to write Parquet file"}

                        logger.info(
                            "Created new scoreboard data Parquet file after read error",
                            date=date,
                            year=year,
                            month=month,
                            file=str(file_path),
                        )
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "partition_dir": str(partition_dir),
                            "date": date,
                            "year": year,
                            "month": month,
                        }
                    except Exception as e:
                        logger.error(
                            "Error creating new Parquet file after read error",
                            file=str(file_path),
                            error=str(e),
                        )
                        return {"success": False, "error": str(e)}

                # Check if this date already exists in the file
                existing_row = existing_df.filter(pl.col("date") == date)
                if existing_row.height > 0:
                    try:
                        # Get the existing hash
                        existing_hash = existing_row.select("content_hash").row(0)[0]

                        # Handle empty hash case
                        if not existing_hash:
                            logger.info(
                                "Empty content hash found - updating data",
                                date=date,
                                new_hash=content_hash[:10],
                            )
                            updated_df = existing_df.filter(pl.col("date") != date)
                            combined_df = pl.concat([updated_df, new_row], how="diagonal")
                        # Compare hashes to see if data has changed
                        elif existing_hash == content_hash:
                            logger.info(
                                "Content hash unchanged - skipping update",
                                date=date,
                                hash=content_hash[:10],
                            )
                            return {
                                "success": True,
                                "file_path": str(file_path),
                                "partition_dir": str(partition_dir),
                                "date": date,
                                "year": year,
                                "month": month,
                                "unchanged": True,
                            }
                        else:
                            # Update the existing row since content has changed
                            logger.info(
                                "Content hash changed - updating data",
                                date=date,
                                old_hash=existing_hash[:10] if existing_hash else "",
                                new_hash=content_hash[:10],
                            )
                            updated_df = existing_df.filter(pl.col("date") != date)
                            combined_df = pl.concat([updated_df, new_row], how="diagonal")
                    except Exception as e:
                        # If there's any error accessing the hash, update the row
                        logger.warning(
                            "Error accessing content hash - updating data",
                            date=date,
                            error=str(e),
                            new_hash=content_hash[:10],
                        )
                        updated_df = existing_df.filter(pl.col("date") != date)
                        combined_df = pl.concat([updated_df, new_row], how="diagonal")
                else:
                    # Append the new row
                    combined_df = pl.concat([existing_df, new_row], how="diagonal")

                # Add extra error handling around write operation
                try:
                    success = self._write_dataframe_safely(combined_df, file_path)
                    if not success:
                        logger.error(
                            "Failed to write scoreboard data",
                            file=str(file_path),
                        )
                        return {"success": False, "error": "Failed to write Parquet file"}

                    logger.info(
                        "Updated existing scoreboard data in Parquet file",
                        date=date,
                        year=year,
                        month=month,
                        file=str(file_path),
                    )
                except Exception as e:
                    logger.error(
                        "Error writing Parquet file",
                        file=str(file_path),
                        error=str(e),
                    )
                    return {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(
                    "Error updating existing Parquet file",
                    file=str(file_path),
                    error=str(e),
                )
                return {"success": False, "error": str(e)}
        else:
            # Write new DataFrame to Parquet file
            try:
                success = self._write_dataframe_safely(new_row, file_path)
                if not success:
                    logger.error(
                        "Failed to create new scoreboard data file",
                        file=str(file_path),
                    )
                    return {"success": False, "error": "Failed to write Parquet file"}

                logger.info(
                    "Created new scoreboard data Parquet file",
                    date=date,
                    year=year,
                    month=month,
                    file=str(file_path),
                )
            except Exception as e:
                logger.error(
                    "Error creating new Parquet file",
                    file=str(file_path),
                    error=str(e),
                )
                return {"success": False, "error": str(e)}

        return {
            "success": True,
            "file_path": str(file_path),
            "partition_dir": str(partition_dir),
            "date": date,
            "year": year,
            "month": month,
        }

    def write_team_data(
        self: "ParquetStorage",
        source_url: str,
        parameters: dict[str, Any],
        data: dict[str, Any],
        content_hash: str | None = None,
        created_at: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Write team data to Parquet file (no date partitioning).

        Args:
            source_url: Source URL
            parameters: Request parameters
            data: Response data
            content_hash: Optional content hash (will be generated if not provided)
            created_at: Optional timestamp (will use current time if not provided)

        Returns:
            Dict containing success status and file information
        """
        # Create directory for teams without date partitioning
        teams_dir = self.base_dir / "teams"
        teams_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for storage
        if created_at is None:
            created_at = datetime.datetime.now()

        # Handle parameters - ensure it's a JSON string
        params_json = parameters if isinstance(parameters, str) else json.dumps(parameters)

        # Prepare JSON data
        json_data = json.dumps(data) if not isinstance(data, str) else data

        # Generate content hash if not provided
        if content_hash is None:
            content_hash = hashlib.sha256(json_data.encode("utf-8")).hexdigest()
            logger.debug("Generated content hash for team data", hash=content_hash)

        # Define target file path
        file_path = teams_dir / "data.parquet"

        # Create DataFrame with a single row
        new_row = pl.DataFrame(
            {
                "source_url": [source_url],
                "parameters": [params_json],
                "content_hash": [content_hash],  # Now always has a value
                "raw_data": [json_data],
                "created_at": [created_at],
            }
        )

        # If file exists, read it, check if data exists with the same hash, and update if needed
        if file_path.exists():
            try:
                # Read existing file
                try:
                    existing_df = pl.read_parquet(file_path)
                except Exception as e:
                    logger.error(
                        "Error reading existing team Parquet file, will create new file",
                        file=str(file_path),
                        error=str(e),
                    )
                    # If file is corrupted, create a new one
                    try:
                        success = self._write_dataframe_safely(new_row, file_path)
                        if not success:
                            logger.error(
                                "Failed to create new team data file after read error",
                                file=str(file_path),
                            )
                            return {"success": False, "error": "Failed to write Parquet file"}

                        logger.info(
                            "Created new team data Parquet file after read error",
                            file=str(file_path),
                        )
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "directory": str(teams_dir),
                        }
                    except Exception as e:
                        logger.error(
                            "Error creating new team Parquet file after read error",
                            file=str(file_path),
                            error=str(e),
                        )
                        return {"success": False, "error": str(e)}

                # Check if we already have data with the same parameters
                param_matches = existing_df.filter(pl.col("parameters") == params_json)
                if param_matches.height > 0:
                    try:
                        # Get the existing hash for matching parameters
                        existing_hash = param_matches.select("content_hash").row(0)[0]

                        # Handle empty hash case
                        if not existing_hash:
                            logger.info(
                                "Empty content hash found - updating team data",
                                new_hash=content_hash[:10],
                            )
                            # Remove existing entry with these parameters
                            updated_df = existing_df.filter(pl.col("parameters") != params_json)
                            combined_df = pl.concat([updated_df, new_row], how="diagonal")
                        # Compare hashes to see if data has changed
                        elif existing_hash == content_hash:
                            logger.info(
                                "Content hash unchanged - skipping team data update",
                                hash=content_hash[:10],
                            )
                            return {
                                "success": True,
                                "file_path": str(file_path),
                                "directory": str(teams_dir),
                                "unchanged": True,
                            }
                        else:
                            # Update the existing row since content has changed
                            logger.info(
                                "Content hash changed - updating team data",
                                old_hash=existing_hash[:10] if existing_hash else "",
                                new_hash=content_hash[:10],
                            )
                            # Remove existing entry with these parameters
                            updated_df = existing_df.filter(pl.col("parameters") != params_json)
                            combined_df = pl.concat([updated_df, new_row], how="diagonal")
                    except Exception as e:
                        # If there's any error accessing the hash, update the row
                        logger.warning(
                            "Error accessing content hash - updating team data",
                            error=str(e),
                            new_hash=content_hash[:10],
                        )
                        # Remove existing entry with these parameters
                        updated_df = existing_df.filter(pl.col("parameters") != params_json)
                        combined_df = pl.concat([updated_df, new_row], how="diagonal")
                else:
                    # No existing data with these parameters, append the new row
                    combined_df = pl.concat([existing_df, new_row], how="diagonal")

                # Add extra error handling around write operation
                try:
                    success = self._write_dataframe_safely(combined_df, file_path)
                    if not success:
                        logger.error(
                            "Failed to write team data",
                            file=str(file_path),
                        )
                        return {"success": False, "error": "Failed to write Parquet file"}

                    logger.info(
                        "Updated existing team data in Parquet file",
                        file=str(file_path),
                    )
                except Exception as e:
                    logger.error(
                        "Error writing team Parquet file",
                        file=str(file_path),
                        error=str(e),
                    )
                    return {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(
                    "Error updating existing Parquet file",
                    file=str(file_path),
                    error=str(e),
                )
                return {"success": False, "error": str(e)}
        else:
            # Write new DataFrame to Parquet file
            try:
                success = self._write_dataframe_safely(new_row, file_path)
                if not success:
                    logger.error(
                        "Failed to create new team data file",
                        file=str(file_path),
                    )
                    return {"success": False, "error": "Failed to write Parquet file"}

                logger.info(
                    "Created new team data Parquet file",
                    file=str(file_path),
                )
            except Exception as e:
                logger.error(
                    "Error creating new team Parquet file",
                    file=str(file_path),
                    error=str(e),
                )
                return {"success": False, "error": str(e)}

        return {
            "success": True,
            "file_path": str(file_path),
            "directory": str(teams_dir),
        }

    def read_scoreboard_data(
        self: "ParquetStorage", date: str, latest_only: bool = True
    ) -> str | None:
        """Read scoreboard data for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            latest_only: If True, return only the latest record for this date

        Returns:
            Raw JSON data string or None if not found
        """
        if not date:
            logger.error("Date is required for reading scoreboard data")
            return None

        try:
            year, month, _ = date.split("-")
        except ValueError:
            logger.error("Invalid date format", date=date)
            return None

        # Path to the specific partition
        partition_dir = self.base_dir / "scoreboard" / f"year={year}" / f"month={month}"
        file_path = partition_dir / "data.parquet"

        if not file_path.exists():
            logger.warning(
                "Parquet file does not exist",
                date=date,
                file_path=str(file_path),
            )
            return None

        try:
            df = pl.read_parquet(file_path)
            # Filter for the specific date
            date_data = df.filter(pl.col("date") == date)
            if date_data.is_empty():
                logger.warning("No data found for date", date=date)
                return None

            if latest_only:
                # Get the latest record based on created_at
                latest_record = date_data.sort("created_at", descending=True).row(0, named=True)
                return latest_record["raw_data"]
            else:
                # Return all records as a list
                return date_data.get_column("raw_data").to_list()

        except Exception as e:
            logger.error(
                "Error reading Parquet file",
                file=str(file_path),
                error=str(e),
            )
            return None

    def read_team_data(self: "ParquetStorage", latest_only: bool = True) -> str | None:
        """Read team data.

        Args:
            latest_only: If True, return only the latest record

        Returns:
            Raw JSON data string or None if not found
        """
        # Path to the teams directory
        teams_dir = self.base_dir / "teams"
        file_path = teams_dir / "data.parquet"

        if not file_path.exists():
            logger.warning("Team data file does not exist", file_path=str(file_path))
            return None

        try:
            df = pl.read_parquet(file_path)

            if df.is_empty():
                logger.warning("No team data found")
                return None

            if latest_only:
                # Get the latest record based on created_at
                latest_record = df.sort("created_at", descending=True).row(0, named=True)
                return latest_record["raw_data"]
            else:
                # Return all records as a list
                return df.get_column("raw_data").to_list()

        except Exception as e:
            logger.error(
                "Error reading Parquet file",
                file=str(file_path),
                error=str(e),
            )
            return None

    def get_processed_dates(self: "ParquetStorage", endpoint: str = "scoreboard") -> list[str]:
        """Get list of dates that have already been processed.

        Args:
            endpoint: API endpoint name (default: "scoreboard")

        Returns:
            List of dates that have already been processed in YYYY-MM-DD format
        """
        if endpoint != "scoreboard":
            # Non-date-based endpoints don't have processed dates
            return []

        # Scoreboard data is stored in year/month partitions
        scoreboard_dir = self.base_dir / "scoreboard"
        if not scoreboard_dir.exists():
            return []

        # Find all year directories
        processed_dates = []
        for year_dir in scoreboard_dir.glob("year=*"):
            year = year_dir.name.split("=")[1]

            # Find all month directories for this year
            for month_dir in year_dir.glob("month=*"):
                month = month_dir.name.split("=")[1]

                # Check for data.parquet file in this partition
                file_path = month_dir / "data.parquet"
                if file_path.exists():
                    try:
                        df = pl.read_parquet(file_path)
                        # Extract unique dates
                        dates = df.get_column("date").unique().to_list()
                        processed_dates.extend(dates)
                    except Exception as e:
                        logger.error(
                            "Error reading Parquet file",
                            file=str(file_path),
                            error=str(e),
                            year=year,
                            month=month,
                        )

        # Remove duplicates and sort
        return sorted(set(processed_dates))

    def list_endpoints(self: "ParquetStorage") -> list[str]:
        """List all endpoints available in the Parquet storage.

        Returns:
            List of endpoint names
        """
        # Get all directories in the base directory
        endpoints = []
        for item in self.base_dir.glob("*"):
            if item.is_dir():
                endpoints.append(item.name)

        return sorted(endpoints)

    def _write_dataframe_safely(self, df, file_path, batch_size=500, compression="zstd"):
        """Write a DataFrame to a Parquet file safely with error handling and memory management.

        Args:
            df: The DataFrame to write
            file_path: Path to write the file to
            batch_size: Size of batches for batch writing if needed
            compression: Compression algorithm to use

        Returns:
            bool: True if successful, False if failed
        """
        import os
        import tempfile
        from pathlib import Path

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Create a temporary file in the same directory
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path))
        os.close(fd)  # Close the file descriptor as we'll use the path
        temp_path = Path(temp_path)

        try:
            # Try standard writing first to the temp file
            try:
                df.write_parquet(temp_path, compression=compression)

                # Move the temp file to the final location
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(temp_path, file_path)
                return True
            except Exception as e:
                logger.warning(
                    "Failed to write Parquet with compression, trying without compression",
                    error=str(e),
                    file=str(file_path),
                )

                # Try without compression to the temp file
                try:
                    df.write_parquet(temp_path, compression=None)

                    # Move the temp file to the final location
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(temp_path, file_path)
                    return True
                except Exception as e2:
                    logger.warning(
                        "Failed to write Parquet without compression, trying batch mode",
                        error=str(e2),
                        file=str(file_path),
                    )

                    # Try batch writing for larger files
                    try:
                        total_rows = len(df)
                        if total_rows <= batch_size:
                            # DataFrame too small - standard methods already failed
                            logger.error(
                                "All writing methods failed for small DataFrame",
                                error=str(e2),
                                file=str(file_path),
                            )
                            return False

                        # Process in batches and save incrementally
                        first_batch = True
                        batch_temp_path = Path(str(temp_path) + ".batch")

                        for i in range(0, total_rows, batch_size):
                            end_idx = min(i + batch_size, total_rows)
                            batch = df.slice(i, end_idx - i)

                            if first_batch:
                                # For first batch, create new file
                                try:
                                    batch.write_parquet(batch_temp_path, compression=None)
                                    first_batch = False
                                except Exception as e3:
                                    logger.error(
                                        "Failed to write first batch",
                                        error=str(e3),
                                        file=str(batch_temp_path),
                                    )
                                    return False
                            else:
                                # For subsequent batches, append to existing file
                                try:
                                    existing = pl.read_parquet(batch_temp_path)
                                    combined = pl.concat([existing, batch])
                                    combined.write_parquet(batch_temp_path, compression=None)
                                except Exception as e3:
                                    logger.error(
                                        "Failed during batch writing",
                                        error=str(e3),
                                        file=str(batch_temp_path),
                                        batch=f"{i}/{total_rows}",
                                    )
                                    return False

                        # Rename batch temp file to final location
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        os.rename(batch_temp_path, file_path)

                        logger.info(
                            "Successfully wrote file in batch mode",
                            file=str(file_path),
                            total_rows=total_rows,
                            batch_size=batch_size,
                        )
                        return True
                    except Exception as e3:
                        logger.error(
                            "Batch writing failed",
                            error=str(e3),
                            file=str(file_path),
                        )
                        return False
        finally:
            # Clean up temporary files
            if temp_path.exists():
                os.remove(temp_path)
            batch_temp_path = Path(str(temp_path) + ".batch")
            if batch_temp_path.exists():
                os.remove(batch_temp_path)
