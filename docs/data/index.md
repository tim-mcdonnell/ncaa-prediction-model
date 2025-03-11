---
title: Data Documentation
description: Documentation for data collection, processing, and storage
---

# Data Documentation

This section contains documentation related to data collection, processing, and storage for the NCAA Basketball Prediction Model.

## Structure

- **Collection**: Documentation related to data collection from various sources
  - [ESPN API Integration](collection/espn-api-integration.md): Details about ESPN API endpoints for NCAA basketball data

## Overview

The NCAA Basketball Prediction Model uses a Parquet-first approach for data storage, with well-defined pipelines for collecting, processing, and analyzing the data. The collection pipeline is responsible for gathering raw data from various sources, which is then transformed by the processing pipeline into a standardized format suitable for feature engineering and model training.

All data flows through these sequential pipelines, ensuring consistency and reliability in the data processing workflow. 