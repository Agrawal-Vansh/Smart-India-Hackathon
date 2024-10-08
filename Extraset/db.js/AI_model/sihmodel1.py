
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Load the crew dataset
# crew_data = pd.read_csv(r"\Backend\AI_model\MOCK_DATA.csv")
try:
    # crew_data = pd.read_csv(r"./MOCK_DATA.csv")
    crew_data = pd.read_csv(r"Backend\AI_model\MOCK_DATA.csv")
    print("Crew data loaded successfully.")
except Exception as e:
    print(f"Error loading crew data: {e}")

# Load the route dataset
# route_data = pd.read_csv(r'\delhi_bus_routes2.csv')
try:
    # route_data = pd.read_csv(r"delhi_bus_routes2.csv")
    route_data = pd.read_csv(r"Backend\AI_model\MOCK_DATA.csv")
    print("Route data loaded successfully.")
except Exception as e:
    print(f"Error loading route data: {e}")

# Explore the datasets
#print(crew_data.head())
#print(route_data.head())

from geopy.geocoders import OpenCage
import pandas as pd
import time
from geopy.exc import GeocoderTimedOut, GeocoderQuotaExceeded

# Initialize the OpenCage geocoder with your API key
geolocator = OpenCage(api_key='387271a4e08743fe95360c86817f5e10')

def get_lat_long_opencage(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderQuotaExceeded:
        print(f"Quota exceeded. Waiting before retrying...")
        time.sleep(60)  # Wait for a minute before retrying
        return get_lat_long_opencage(address)
    except Exception as e:
        print(f"Error geocoding address '{address}': {e}")
        return None, None

# Sample data loading (replace with your actual data loading process)
# crew_data = pd.read_csv('cleaned_crew_data.csv')
# route_data = pd.read_csv('route_data.csv')
# Apply the function using OpenCage with rate limiting
crew_data['Crew_Lat'], crew_data['Crew_Long'] = zip(*crew_data['Address'].apply(get_lat_long_opencage))
route_data['Start_Lat'], route_data['Start_Long'] = zip(*route_data['Start Point'].apply(get_lat_long_opencage))

# Save the updated data to CSV files (optional)
# crew_data.to_csv('updated_crew_data.csv', index=False)
# route_data.to_csv('updated_route_data.csv', index=False)

# Display some of the updated data
#print(crew_data.head())
#print(route_data.head())

#pip install opencage
from opencage.geocoder import OpenCageGeocode
from opencage.geocoder import RateLimitExceededError, UnknownError
import time

# Replace 'YOUR_API_KEY' with your actual OpenCage API key
api_key = '387271a4e08743fe95360c86817f5e10'
geocoder = OpenCageGeocode(api_key)

def get_lat_long_with_retry(address, retries=3, delay=1):
    """
    Geocode an address with retries using OpenCage.

    Parameters:
    address (str): The address to geocode.
    retries (int): Number of retries if geocoding fails.
    delay (int): Delay between retries in seconds.

    Returns:
    tuple: Latitude and longitude if successful, otherwise (None, None).
    """
    for attempt in range(retries):
        try:
            result = geocoder.geocode(address)
            if result and len(result):
                return result[0]['geometry']['lat'], result[0]['geometry']['lng']
        except RateLimitExceededError: 
            print(f"Rate limit exceeded for address '{address}'. Retrying after delay...")
            time.sleep(delay * 2)  # wait longer in case of rate limits
        except UnknownError as e:
            print(f"Unknown error for address '{address}': {e}")
            time.sleep(delay)
    return None, None

# Fill missing addresses with a default value (e.g., Kashmere Gate)
crew_data['Address'] = crew_data['Address'].fillna('Kashmere Gate')

# Identify rows with missing latitude/longitude
missing_coords_index = crew_data[crew_data['Crew_Lat'].isnull()].index

# Remove rows where latitude or longitude is missing
cleaned_crew_data = crew_data.dropna(subset=['Crew_Lat', 'Crew_Long'])

# Verify the shape of the cleaned DataFrame
print(f"Original DataFrame shape: {crew_data.shape}")
print(f"Cleaned DataFrame shape: {cleaned_crew_data.shape}")

# Optionally, save the cleaned DataFrame to a new CSV file
cleaned_crew_data.to_csv('cleaned_crew_data.csv', index=False)

print(cleaned_crew_data[['Address', 'Crew_Lat', 'Crew_Long']].isnull().sum())

from geopy.distance import great_circle
import pandas as pd

# Load cleaned crew data and route data
# cleaned_crew_data = pd.read_csv('cleaned_crew_data.csv')  # Uncomment if needed
# route_data = pd.read_csv('route_data.csv')  # Load your route data

# Calculate the distance between each crew member and each route start point
def calculate_distances(crew_row, route_data):
    crew_coords = (crew_row['Crew_Lat'], crew_row['Crew_Long'])
    distances = route_data.apply(lambda route_row: great_circle(
        crew_coords,
        (route_row['Start_Lat'], route_row['Start_Long'])
    ).km, axis=1)
    return distances

# Assign each crew member to the closest route
def assign_routes(crew_data, route_data):
    assignments = []
    for _, crew_row in crew_data.iterrows():
        distances = calculate_distances(crew_row, route_data)
        closest_route_index = distances.idxmin()
        closest_route_id = route_data.loc[closest_route_index, 'Route ID']
        assignments.append(closest_route_id)
    return assignments

# Calculate assignments
cleaned_crew_data['Assigned_Route'] = assign_routes(cleaned_crew_data, route_data)

# Print out the updated DataFrame with assigned routes
print(cleaned_crew_data[['CrewID', 'Address', 'Assigned_Route']])

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

# Example: Assume route_data and cleaned_crew_data are your datasets
# Split the data (without merging)
X_train, X_test, y_train, y_test = train_test_split(cleaned_crew_data, cleaned_crew_data['Assigned_Route'], test_size=0.2, random_state=42)

def get_route_features(route_id):
    route_info = route_data[route_data['Route ID'] == route_id].iloc[0]
    return {
        'Route_Difficulty': route_info['Route Difficulty'],
        'Distance_km': route_info['Distance (km)'],
        'Start_Lat': route_info['Start_Lat'],
        'Start_Long': route_info['Start_Long'],
    }

def prepare_features(crew_row):
    # Extract crew features
    crew_features = {
        'ExperienceYears': crew_row['ExperienceYears'],
        'Gender': crew_row['Gender'],
        # Add more crew features as needed
    }

    # Fetch route features using Route ID
    route_features = get_route_features(crew_row['Route ID'])

    # Combine both
    return {**crew_features, **route_features}

# Prepare training data
X_train_prepared = X_train.apply(prepare_features, axis=1)
X_train_prepared = pd.DataFrame(X_train_prepared.tolist())  # Convert to DataFrame

# Define categorical and numerical features
categorical_features = ['Gender']
numerical_features = ['ExperienceYears', 'Route_Difficulty', 'Distance_km', 'Start_Lat', 'Start_Long']

# Preprocessing pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numerical_features),
        ('cat', OneHotEncoder(), categorical_features)
    ])

# Combine preprocessor with the model
model_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier())
])

# Train the model
model_pipeline.fit(X_train_prepared, y_train)

# Prepare test data similarly and evaluate the model
X_test_prepared = X_test.apply(prepare_features, axis=1)
X_test_prepared = pd.DataFrame(X_test_prepared.tolist())
y_pred = model_pipeline.predict(X_test_prepared)

# Evaluate the model (optional)
from sklearn.metrics import accuracy_score, classification_report
print(f"Accuracy: {accuracy_score(y_test, y_pred)}")

report = classification_report(y_test, y_pred)
print(f'Classification Report:\n{report}')

# Generate predictions in the required format
def format_predictions(crew_data, model_pipeline):
    predictions = []
    for _, crew_row in crew_data.iterrows():
        features = prepare_features(crew_row)
        features_df = pd.DataFrame([features])
        assigned_route = model_pipeline.predict(features_df)[0]
        predictions.append({
            "id": crew_row['CrewID'],
            "preferredRoute": assigned_route,
            "shift": crew_row['timing_preferences']
        })
    return predictions

# Apply formatting to the entire dataset
formatted_predictions = format_predictions(cleaned_crew_data, model_pipeline)
print(formatted_predictions)

