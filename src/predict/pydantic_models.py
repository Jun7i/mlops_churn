# TODO: Define Pydantic models for API validation
# - Create input schema for customer data (all required features)
# - Create output schema for predictions (churn_probability, at_risk_flag)
# - Add field validation (e.g., tenure >= 0, contract types)
# - Add example data for API documentation
# - Ensure compatibility with FastAPI if used

from pydantic import BaseModel, Field
from typing import Literal

# Add your Pydantic models here
