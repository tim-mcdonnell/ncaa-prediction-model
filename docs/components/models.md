# Models

## Overview
The models component trains, evaluates, and applies predictive models for NCAA basketball games. It supports multiple model types and provides a consistent interface for training and prediction.

## Responsibilities
- Train prediction models using calculated features
- Evaluate model performance with appropriate metrics
- Generate predictions for upcoming games
- Store model artifacts and predictions
- Track model versions and performance

## Key Classes
- `ModelTrainer`: Handles model training and hyperparameter tuning
- `ModelEvaluator`: Evaluates model performance
- `PredictionPipeline`: Orchestrates prediction generation
- `ModelRegistry`: Tracks available models and their versions

## Usage Examples

```python
# Train a model
from src.models import ModelTrainer

trainer = ModelTrainer()
model = trainer.train(
    features=["team_offensive_efficiency", "team_defensive_efficiency"],
    target="win_probability",
    model_type="xgboost"
)

# Evaluate a model
from src.models import ModelEvaluator

evaluator = ModelEvaluator()
metrics = evaluator.evaluate(
    model=model,
    test_data=test_data,
    metrics=["accuracy", "log_loss", "brier_score"]
)

# Generate predictions
from src.pipelines import PredictionPipeline

pipeline = PredictionPipeline()
predictions = pipeline.generate_predictions(
    target_date="20240315"
)
```

## Model Types

### Core Models
- Regression models (ElasticNet, XGBoost)
- Classification models (Logistic Regression, XGBoost)
- Ensemble models (Stacking of multiple models)

### Specialized Models
- Point spread prediction
- Total points prediction
- Win probability estimation

## Evaluation Metrics
- Prediction accuracy (binary outcomes)
- Log loss (probability calibration)
- Brier score (probability accuracy)
- Mean squared error (point spreads)
- ROI when compared to Vegas lines

## Model Training Workflow
1. Feature selection based on domain knowledge
2. Train/validation/test split (typically by season)
3. Hyperparameter tuning with cross-validation
4. Model evaluation on hold-out test data
5. Model deployment for predictions

## Configuration
Model behavior can be configured in `configs/models.toml`:

```toml
[training]
cv_folds = 5
train_seasons = [2018, 2019, 2020, 2021, 2022]
test_seasons = [2023]

[xgboost]
max_depth = 6
learning_rate = 0.1
n_estimators = 100

[evaluation]
metrics = ["accuracy", "log_loss", "brier_score"]
``` 