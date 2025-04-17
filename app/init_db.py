import os
import logging
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.database import SessionLocal, engine
from app.security import get_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_default_admin():
    """Creates a default admin user if no admin user exists in the database."""
    
    # Get default admin credentials from environment variables
    default_admin_email = os.getenv("DEFAULT_ADMIN_EMAIL")
    default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    default_admin_name = os.getenv("DEFAULT_ADMIN_NAME")
    
    # Check if environment variables are set
    if not all([default_admin_email, default_admin_password, default_admin_name]):
        logger.warning("Default admin credentials not fully configured in .env file")
        return
    
    # Create a database session
    db = SessionLocal()
    try:
        # Check if any admin exists
        existing_admin = db.query(models.Admin).first()
        
        if not existing_admin:
            logger.info("No admin found. Creating default admin user...")
            
            # Check if user with this email already exists
            if default_admin_email:  # Make sure it's not None
                existing_user = crud.get_user_by_email(db, email=default_admin_email)
                
                if existing_user:
                    logger.info(f"User with email {default_admin_email} already exists. Not creating default admin.")
                    return
            else:
                logger.warning("Default admin email is None. Skipping default admin creation.")
                return
            
            # Create admin registration data with proper type handling
            # Cast environment variables to string to satisfy type checking
            admin_email = str(default_admin_email) if default_admin_email else ""
            admin_password = str(default_admin_password) if default_admin_password else ""
            admin_name = str(default_admin_name) if default_admin_name else "System Administrator"
            
            admin_data = schemas.AdminRegistration(
                email=admin_email,
                password=admin_password,
                name=admin_name,
                contact="Not provided"
            )
            
            # Register admin
            admin = crud.register_admin(db, admin_data)
            
            logger.info(f"Default admin created successfully with email: {default_admin_email}")
        else:
            logger.info("Admin user(s) already exist. Skipping default admin creation.")
    
    except Exception as e:
        logger.error(f"Error creating default admin: {str(e)}")
    finally:
        db.close()

def init_db():
    """Initialize the database with default data if needed."""
    
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or verified")
    
    # Create default admin
    create_default_admin()
    
    logger.info("Database initialization completed")

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialization completed")