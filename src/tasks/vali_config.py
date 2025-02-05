

class DeltaValiConfig:
  
    CHALLENGE_PERIOD_MAX_POSITIONAL_RETURNS_RATIO = 0.02  # one position shouldn't be more than 2% of the total realized returns
    CHALLENGE_PERIOD_MAX_REALIZED_RETURNS_RATIO_ONE_DAY = 0.30  # one day shouldn't be more than 30% of the total realized returns
    REALIZED_RETURNS_WINDOW = 1 # in days
    CHALLENGE_PERIOD_MAX_REALIZED_RETURNS_RATIO = 0.02
    CHALLENGE_PERIOD_MAX_DRAWDOWN = 5
    

class DeltaDevConstants:
  
  DEV_ACCOUNTS = ["dev@delta-mining.com"]