#!/usr/bin/env python3
"""
Database initialization script for DeepSeaGuard
Creates tables and populates with sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import engine, Base, ISAZone, SessionLocal
from utils.sample_data import create_sample_isa_zones
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with tables and sample data"""
    try:
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Check if sample data already exists
        db = SessionLocal()
        existing_zones = db.query(ISAZone).count()
        
        if existing_zones == 0:
            logger.info("Populating database with sample ISA zones...")
            
            # Create sample zones
            sample_zones = create_sample_isa_zones()
            
            for zone_data in sample_zones:
                zone = ISAZone(
                    zone_id=zone_data["zone_id"],
                    zone_name=zone_data["zone_name"],
                    zone_type=zone_data["zone_type"],
                    max_duration_hours=zone_data["max_duration_hours"],
                    geojson_data=zone_data["geojson_data"]
                )
                db.add(zone)
            
            db.commit()
            logger.info(f"Added {len(sample_zones)} sample ISA zones")
        else:
            logger.info(f"Database already contains {existing_zones} zones, skipping sample data")
        
        db.close()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def reset_database():
    """Reset the database (drop all tables and recreate)"""
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
        
        # Reinitialize
        init_database()
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize DeepSeaGuard database")
    parser.add_argument("--reset", action="store_true", help="Reset database (drop all tables)")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    else:
        init_database() 