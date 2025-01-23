import psycopg2
from io import BytesIO
import joblib

# Database connection parameters
db_params = {
    "dbname": "water-quality-db",
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

def deserialize_model(binary_data):
    buffer = BytesIO(binary_data)
    return joblib.load(buffer)

def test_ml_model_storage():
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()

        # Fetch the latest MachineLearningModel instance
        cur.execute("SELECT id, model_file, scaler_file FROM machine_learning_model ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()

        if row:
            model_id, model_binary, scaler_binary = row

            print(f"Testing MachineLearningModel with ID: {model_id}")

            # Test model deserialization
            if model_binary:
                try:
                    model = deserialize_model(model_binary)
                    print("Model deserialized successfully.")
                    print(f"Model type: {type(model)}")
                except Exception as e:
                    print(f"Error deserializing model: {str(e)}")
            else:
                print("Model file is empty.")

            # Test scaler deserialization
            if scaler_binary:
                try:
                    scaler = deserialize_model(scaler_binary)
                    print("Scaler deserialized successfully.")
                    print(f"Scaler type: {type(scaler)}")
                except Exception as e:
                    print(f"Error deserializing scaler: {str(e)}")
            else:
                print("Scaler file is empty.")

        else:
            print("No MachineLearningModel instances found in the database.")

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    test_ml_model_storage()