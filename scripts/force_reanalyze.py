#!/usr/bin/env python3
"""
Force re-analysis of all tracks by clearing waveform data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from src.database.connection import get_engine

def clear_waveform_data():
    """Clear all waveform data to force re-analysis"""
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            # Clear waveform data
            result = conn.execute(text("UPDATE track SET waveform_data = NULL"))
            conn.commit()
            
            count = result.rowcount
            print(f"✅ Cleared waveform data for {count} tracks")
            print("📊 Tracks will be re-analyzed when loaded")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(clear_waveform_data())
