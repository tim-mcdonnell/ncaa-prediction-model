"""
Data cleaning utilities for NCAA basketball data.

This module provides components for:
- Validating data against Pydantic schemas
- Cleaning data according to defined rules
- Generating data quality reports
- Fixing common data issues automatically
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

import polars as pl
from pydantic import BaseModel, ValidationError

# Set up logging
logger = logging.getLogger(__name__)


class CleaningRuleType(str, Enum):
    """Types of cleaning rules that can be applied to data."""
    CLIP = "clip"
    FILL_NULL = "fill_null"
    FILL_EMPTY = "fill_empty"
    MAP_VALUES = "map_values"
    REGEX_REPLACE = "regex_replace"
    DROP_DUPLICATES = "drop_duplicates"
    DROP_NULLS = "drop_nulls"


class CleaningRule(BaseModel):
    """
    Definition of a data cleaning rule.
    
    Attributes:
        column: Column name to apply rule to (or None for table-wide rules)
        rule_type: Type of cleaning rule to apply
        params: Parameters specific to the rule type
    """
    column: Optional[str] = None
    rule_type: CleaningRuleType
    params: Dict[str, Any] = {}


class ValidationResult(BaseModel):
    """
    Result of a data validation operation.
    
    Attributes:
        is_valid: Whether the data is valid according to the schema
        valid_count: Number of valid rows
        invalid_count: Number of invalid rows
        validation_errors: List of validation errors
        error_details: Detailed information about validation failures
    """
    is_valid: bool
    valid_count: int
    invalid_count: int
    validation_errors: List[Any]
    error_details: Dict[str, Any] = {}


class ColumnStats(BaseModel):
    """
    Statistics for a specific column in a data quality report.
    
    Attributes:
        column: Column name
        dtype: Data type of the column
        null_count: Number of null values
        empty_count: Number of empty strings (for string columns)
        unique_count: Number of unique values
        min_value: Minimum value (for numeric columns)
        max_value: Maximum value (for numeric columns)
        out_of_range_count: Number of values outside expected range
        additional_metrics: Any additional column-specific metrics
    """
    column: str
    dtype: str
    null_count: int
    empty_count: Optional[int] = None
    unique_count: int
    min_value: Optional[Union[int, float, str]] = None
    max_value: Optional[Union[int, float, str]] = None
    out_of_range_count: Optional[int] = None
    additional_metrics: Dict[str, Any] = {}


class QualityReport(BaseModel):
    """
    Data quality report with overall and column-specific statistics.
    
    Attributes:
        overall_stats: Overall statistics for the dataset
        column_stats: List of statistics for each column
        data_issues: Identified data quality issues
        recommendations: Recommendations for data cleaning
    """
    overall_stats: Dict[str, Any]
    column_stats: List[Dict[str, Any]]
    data_issues: List[str] = []
    recommendations: List[str] = []


class DataCleaner:
    """
    Utilities for data cleaning and validation.
    
    Provides functionality to:
    - Validate data against Pydantic schemas
    - Clean data according to defined rules
    - Generate data quality reports
    - Fix common data issues automatically
    """
    
    def validate_schema(
        self, 
        data: pl.DataFrame, 
        schema: Type[BaseModel]
    ) -> ValidationResult:
        """
        Validate a DataFrame against a Pydantic schema.
        
        Args:
            data: DataFrame to validate
            schema: Pydantic model class defining the expected schema
            
        Returns:
            ValidationResult with validation statistics and errors
        """
        logger.debug(f"Validating data against schema: {schema.__name__}")
        
        validation_errors = []
        valid_count = 0
        invalid_count = 0
        
        # Convert to dictionary records for validation
        records = data.to_dicts()
        
        # Validate each record
        for i, record in enumerate(records):
            try:
                schema(**record)
                valid_count += 1
            except ValidationError as e:
                invalid_count += 1
                error = {
                    "row_index": i,
                    "errors": e.errors()
                }
                validation_errors.append(error)
        
        # Determine overall validity
        is_valid = invalid_count == 0
        
        return ValidationResult(
            is_valid=is_valid,
            valid_count=valid_count,
            invalid_count=invalid_count,
            validation_errors=validation_errors,
            error_details={
                "schema": schema.__name__,
                "total_records": len(records)
            }
        )
    
    def clean_data(
        self, 
        data: pl.DataFrame, 
        rules: List[CleaningRule]
    ) -> pl.DataFrame:
        """
        Apply cleaning rules to a DataFrame.
        
        Args:
            data: DataFrame to clean
            rules: List of cleaning rules to apply
            
        Returns:
            Cleaned DataFrame
        """
        logger.debug(f"Cleaning data with {len(rules)} rules")
        
        # Start with a copy of the original data
        result = data.clone()
        
        # Apply each rule
        for rule in rules:
            result = self._apply_rule(result, rule)
        
        return result
    
    def _apply_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """
        Apply a single cleaning rule to a DataFrame.
        
        Args:
            data: DataFrame to clean
            rule: Cleaning rule to apply
            
        Returns:
            DataFrame with rule applied
        """
        logger.debug(f"Applying rule: {rule.rule_type} to column: {rule.column}")
        
        if rule.rule_type == CleaningRuleType.CLIP:
            return self._apply_clip_rule(data, rule)
        
        elif rule.rule_type == CleaningRuleType.FILL_NULL:
            return self._apply_fill_null_rule(data, rule)
        
        elif rule.rule_type == CleaningRuleType.FILL_EMPTY:
            return self._apply_fill_empty_rule(data, rule)
        
        elif rule.rule_type == CleaningRuleType.MAP_VALUES:
            return self._apply_map_values_rule(data, rule)
        
        elif rule.rule_type == CleaningRuleType.DROP_NULLS:
            return self._apply_drop_nulls_rule(data, rule)
        
        elif rule.rule_type == CleaningRuleType.DROP_DUPLICATES:
            return self._apply_drop_duplicates_rule(data, rule)
        
        # Rule type not implemented
        logger.warning(f"Cleaning rule type not implemented: {rule.rule_type}")
        return data
    
    def _apply_clip_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply clipping rule to numeric column."""
        if not rule.column:
            logger.warning("Clip rule requires column specification")
            return data
        
        min_value = rule.params.get("min_value")
        max_value = rule.params.get("max_value")
        
        if min_value is None and max_value is None:
            logger.warning("Clip rule requires min_value or max_value")
            return data
        
        # Create expressions for clipping
        expressions = []
        for col in data.columns:
            if col == rule.column:
                expr = pl.col(col)
                expr = expr.clip(min_value, max_value)
                expressions.append(expr)
            else:
                expressions.append(pl.col(col))
        
        return data.select(expressions)
    
    def _apply_fill_null_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply fill null rule to column."""
        if not rule.column:
            logger.warning("Fill null rule requires column specification")
            return data
        
        fill_value = rule.params.get("fill_value")
        if fill_value is None:
            logger.warning("Fill null rule requires fill_value")
            return data
        
        return data.with_columns(
            pl.col(rule.column).fill_null(fill_value)
        )
    
    def _apply_fill_empty_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply fill empty string rule to column."""
        if not rule.column:
            logger.warning("Fill empty rule requires column specification")
            return data
        
        fill_value = rule.params.get("fill_value")
        if fill_value is None:
            logger.warning("Fill empty rule requires fill_value")
            return data
        
        # Use a more direct approach to replace empty strings
        return data.with_columns(
            pl.when(pl.col(rule.column) == "")
            .then(pl.lit(fill_value))
            .otherwise(pl.col(rule.column))
            .alias(rule.column)
        )
    
    def _apply_map_values_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply value mapping rule to column."""
        if not rule.column:
            logger.warning("Map values rule requires column specification")
            return data
        
        mapping = rule.params.get("mapping")
        if not mapping:
            logger.warning("Map values rule requires mapping dictionary")
            return data
        
        # Create expression for mapping values
        expr = pl.col(rule.column)
        for old_val, new_val in mapping.items():
            expr = pl.when(expr == old_val).then(pl.lit(new_val)).otherwise(expr)
        
        return data.with_columns(expr.alias(rule.column))
    
    def _apply_drop_nulls_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply drop nulls rule."""
        if rule.column:
            return data.drop_nulls(rule.column)
        else:
            return data.drop_nulls()
    
    def _apply_drop_duplicates_rule(
        self, 
        data: pl.DataFrame, 
        rule: CleaningRule
    ) -> pl.DataFrame:
        """Apply drop duplicates rule."""
        subset = rule.params.get("subset")
        keep = rule.params.get("keep", "first")
        
        return data.unique(subset=subset, keep=keep)
    
    def generate_quality_report(self, data: pl.DataFrame) -> QualityReport:
        """
        Generate a data quality report for a DataFrame.
        
        Args:
            data: DataFrame to analyze
            
        Returns:
            QualityReport with data quality metrics
        """
        logger.debug("Generating data quality report")
        
        # Overall stats
        overall_stats = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "missing_count": data.null_count().sum().sum(),
            "duplicate_count": len(data) - len(data.unique()),
        }
        
        # Column stats
        column_stats = []
        data_issues = []
        recommendations = []
        
        for column in data.columns:
            # Get basic column stats
            col_data = data.select(pl.col(column))
            dtype = str(col_data.dtypes[0])
            null_count = col_data.null_count().sum().sum().item()  # Convert to scalar
            unique_count = len(col_data.unique())
            
            # Create column stats entry
            stats = {
                "column": column,
                "dtype": dtype,
                "null_count": null_count,
                "unique_count": unique_count,
            }
            
            # Add type-specific metrics
            # Check for numeric columns by looking for Int or Float values
            if "Int" in dtype or "Float" in dtype:
                # Numeric column
                if not col_data.is_empty():
                    try:
                        non_null = col_data.drop_nulls()
                        if not non_null.is_empty():
                            min_value = non_null.min()[0, 0]
                            max_value = non_null.max()[0, 0]
                            stats["min_value"] = min_value
                            stats["max_value"] = max_value
                            
                            # Count out-of-range values
                            out_of_range_count = 0
                            
                            # This is just a basic example - real implementation 
                            # would have more sophisticated range checking
                            if column == "jersey":  # Example column-specific logic
                                out_of_range_count = len(
                                    col_data.filter(
                                        (pl.col(column) < 0) | (pl.col(column) > 99)
                                    )
                                )
                            
                            stats["out_of_range_count"] = out_of_range_count
                            
                            if out_of_range_count > 0:
                                data_issues.append(
                                    f"Column '{column}' has {out_of_range_count} "
                                    f"values outside expected range"
                                )
                                recommendations.append(
                                    f"Apply clipping rule to '{column}'"
                                )
                    except Exception as e:
                        msg = f"Error calculating numeric stats for {column}: {e}"
                        logger.warning(msg)
            
            elif "String" in dtype:
                # String column
                empty_count = len(col_data.filter(pl.col(column) == ""))
                stats["empty_count"] = empty_count
                
                if empty_count > 0:
                    data_issues.append(
                        f"Column '{column}' has {empty_count} empty strings"
                    )
                    recommendations.append(
                        f"Apply fill_empty rule to '{column}'"
                    )
            
            # Add to column stats list
            column_stats.append(stats)
            
            # Check for missing values
            if null_count > 0:
                data_issues.append(
                    f"Column '{column}' has {null_count} missing values"
                )
                recommendations.append(
                    f"Apply fill_null rule to '{column}'"
                )
        
        return QualityReport(
            overall_stats=overall_stats,
            column_stats=column_stats,
            data_issues=data_issues,
            recommendations=recommendations
        )
    
    def fix_common_issues(self, data: pl.DataFrame) -> pl.DataFrame:
        """
        Automatically fix common data issues.
        
        This method applies a set of common data cleaning rules:
        - Replace nulls with appropriate default values
        - Replace empty strings with appropriate values
        - Clip numeric values to reasonable ranges
        
        Args:
            data: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        logger.debug("Applying common data fixes")
        
        # Start with a copy of the original data
        result = data.clone()
        
        # Generate quality report to identify issues
        report = self.generate_quality_report(data)
        
        # Create rules based on identified issues
        rules = []
        
        # Fix numeric ranges
        for col_stats in report.column_stats:
            col_name = col_stats["column"]
            
            # Handle out-of-range values in numeric columns
            if ("out_of_range_count" in col_stats and 
                    col_stats["out_of_range_count"] > 0):
                if col_name == "jersey":  # Example column-specific logic
                    rules.append(
                        CleaningRule(
                            column=col_name,
                            rule_type=CleaningRuleType.CLIP,
                            params={"min_value": 0, "max_value": 99}
                        )
                    )
            
            # Handle nulls
            if col_stats["null_count"] > 0:
                fill_value = None
                
                # Choose appropriate default values based on column name
                # This is a simplified example - real implementation would be
                # more sophisticated
                if "name" in col_name.lower():
                    fill_value = "UNKNOWN"
                elif "id" in col_name.lower():
                    continue  # Don't fill ID columns
                elif "Int" in col_stats["dtype"] or "Float" in col_stats["dtype"]:
                    # For numeric columns, use median or 0
                    non_null = data.select(pl.col(col_name)).drop_nulls()
                    if not non_null.is_empty():
                        try:
                            fill_value = non_null.median()[0, 0]
                        except ValueError:
                            fill_value = 0
                
                if fill_value is not None:
                    rules.append(
                        CleaningRule(
                            column=col_name,
                            rule_type=CleaningRuleType.FILL_NULL,
                            params={"fill_value": fill_value}
                        )
                    )
            
            # Handle empty strings
            if "empty_count" in col_stats and col_stats["empty_count"] > 0:
                rules.append(
                    CleaningRule(
                        column=col_name,
                        rule_type=CleaningRuleType.FILL_EMPTY,
                        params={"fill_value": "UNKNOWN"}
                    )
                )
        
        # Apply the rules
        if rules:
            result = self.clean_data(result, rules)
        
        return result 