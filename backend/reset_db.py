from database import engine, Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_db():
    logger.info("🔄 Resetting database...")
    try:
        # Drop all tables
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS verification_codes CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS accounts CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            conn.commit()
        logger.info("✅ Tables dropped.")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created.")
        
    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_db()