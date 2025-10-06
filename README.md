
# CS:GO Case Price Prediction

## Project Overview

The Steam market is one of the most underrated markets right now. Most people outside of the gaming environment don't even know about it. Counter Strike becomes more popular every day, thanks to the growing e-sport ecosystem and gambling promotions. As a result, Counter Strike skins and case prices are fluctuating all the time.

This project uses past price history, daily player count, and e-sport event data to predict tomorrow's case prices using machine learning. The model can predict prices for 50 different weapon cases.


## Dataset

There is no up-to-date dataset available, so I collected my own by scraping multiple sources:

**Data Sources:**
- Daily Case Prices (50 different cases) - scraped from Steam
- Daily Counter Strike Event Data - scraped from Liquipedia  
- Daily Player Count Data - scraped from SteamDB

You can find the scraping scripts inside each data folder. You can update the dataset daily or weekly using these scripts.

**Data Folders:**
- `case-prices-steam-data/` - Steam weapon case prices
- `event-data/` - S-Tier tournament events
- `player-count-data/` - Daily CS:GO player counts

## Project Structure

**Notebooks:**
1. `1_eda.ipynb` - Exploratory data analysis
2. `2_process-data.ipynb` - Process and merge datasets
3. `3_xgboost-training.ipynb` - XGBoost model training
4. `4_lightgbm-training.ipynb` - LightGBM model training

## Features

The models use 6 features to predict tomorrow's price:

- `item_encoded` - Weapon case ID (50 different cases)
- `price_lag_1` - Today's price
- `price_lag_2` - Yesterday's price
- `price_lag_3` - Price from 2 days ago
- `Average_Players` - Daily average player count
- `has_tournament` - S-Tier tournament indicator (0 or 1)

## Models

Two gradient boosting models were trained:

### XGBoost Model
- Test MAE: ~$0.03
- Test R² Score: ~0.99
- Relies heavily on lag features (price momentum)

### LightGBM Model  
- Test MAE: ~$0.03
- Test R² Score: ~0.99
- More balanced feature importance

Both models achieve similar performance, but LightGBM gives more weight to player count and tournament events.

## Usage

To predict tomorrow's price, you need to provide:
1. Item name (e.g., "Kilowatt Case")
2. Today's price
3. Yesterday's price
4. Price from 2 days ago
5. Average players today
6. Tournament today (0 or 1)

Example prediction code is included in the training notebooks.

## Files

**Models:**
- `csgo_price_prediction_model_xgboost.pkl` - Trained XGBoost model
- `csgo_price_prediction_model_lightgbm.pkl` - Trained LightGBM model

**Data:**
- `csv-files/csgo_item_level_dataset.csv` - Merged dataset
- `csv-files/item_mapping.pkl` - Item name to ID mapping








































