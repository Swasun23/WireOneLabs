import falcon
from routes import app  # Import the Falcon app from the routes file
from database import create_tables


# Create tables in the database
create_tables()
print("Tables created!")


