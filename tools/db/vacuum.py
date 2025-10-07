#!/usr/bin/env python3
"""
PostgreSQL VACUUM script for stockie databases.
Designed for cron execution - logs all output and handles errors gracefully.
"""

import psycopg2
import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from stockie.loaders.config_loader import ConfigLoader
from stockie.log.custom_logger import CustomLogger

class VacuumRunner:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.setup_config()
        self.setup_logging()
        self.setup_database_connection()
        
    def setup_config(self):
        """Load configuration from settings file"""
        self.config_loader = ConfigLoader(self.config_dir)
        self.full_config = self.config_loader.get()
        self.db_config = self.full_config['db']
        
        # Add password from environment variable (following daily.py pattern)
        self.db_config['password'] = os.getenv('DB_PASSWORD')
        
        # Get environment from ConfigLoader (which reads from .env file)
        self.environment = self.config_loader.get_environment()
        
    def setup_logging(self):
        """Setup logging using CustomLogger like daily.py"""
        vacuum_config = self.full_config.get('vacuum', {})
        
        # Create log filename based on environment and date
        log_filename = f"vacuum_{datetime.now().strftime('%Y%m%d')}.log"
        
        self.logger = CustomLogger(
            name=__file__,
            log_to_console=vacuum_config.get('console', True),
            log_level='INFO',
            log_dir=f"{vacuum_config.get('log_dir', '/mnt/log/stockie')}/{self.environment}",
            log_filename=log_filename
        ).get_logger()
        
    def setup_database_connection(self):
        """Setup database connection parameters from config"""
        self.database = self.db_config['dbname']
        self.user = self.db_config['user']
        self.password = self.db_config['password']
        self.host = self.db_config.get('host', 'localhost')
        self.port = self.db_config.get('port', 5432)
            
        self.conn_params = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }
    
    def connect(self):
        """Create database connection"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
            self.logger.info(f"Connected to {self.environment} database: {self.database}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False
    
    def get_table_stats(self):
        """Get current table statistics before vacuum"""
        try:
            cursor = self.conn.cursor()
            
            # Get table sizes
            cursor.execute("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as total_size,
                    pg_total_relation_size('public.'||tablename) as total_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size('public.'||tablename) DESC
                LIMIT 5;
            """)
            
            table_sizes = cursor.fetchall()
            
            # Get vacuum statistics
            cursor.execute("""
                SELECT 
                    relname,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY n_dead_tup DESC;
            """)
            
            vacuum_stats = cursor.fetchall()
            
            return {
                'table_sizes': table_sizes,
                'vacuum_stats': vacuum_stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get table statistics: {e}")
            return None
    
    def log_table_stats(self, stats, prefix=""):
        """Log table statistics"""
        if not stats:
            return
            
        self.logger.info(f"{prefix}Table Sizes:")
        for table, size, bytes_size in stats['table_sizes']:
            self.logger.info(f"  {table}: {size}")
            
        self.logger.info(f"{prefix}Dead Tuples:")
        for relname, inserts, updates, deletes, dead_tuples, last_vacuum, last_autovacuum in stats['vacuum_stats']:
            if dead_tuples > 0:
                dead_pct = (dead_tuples / max(inserts, 1)) * 100 if inserts > 0 else 0
                self.logger.info(f"  {relname}: {dead_tuples} dead tuples ({dead_pct:.1f}%)")
    
    def vacuum_table(self, table_name, vacuum_type='regular'):
        """Vacuum a specific table"""
        try:
            cursor = self.conn.cursor()
            
            if vacuum_type == 'full':
                sql = f"VACUUM FULL {table_name};"
                self.logger.info(f"Starting VACUUM FULL on {table_name}...")
            elif vacuum_type == 'analyze':
                sql = f"VACUUM ANALYZE {table_name};"
                self.logger.info(f"Starting VACUUM ANALYZE on {table_name}...")
            else:
                sql = f"VACUUM {table_name};"
                self.logger.info(f"Starting VACUUM on {table_name}...")
            
            start_time = datetime.now()
            cursor.execute(sql)
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"{vacuum_type.upper()} VACUUM completed on {table_name} in {duration:.1f} seconds")
            return True
        except Exception as e:
            self.logger.error(f"Failed to vacuum {table_name}: {e}")
            return False
    
    def run_automated_vacuum(self, vacuum_type='regular'):
        """Run automated vacuum on main tables"""
        if not self.connect():
            return False
        
        self.logger.info(f"Starting automated {vacuum_type} vacuum on {self.environment} database")
        self.logger.info(f"Database: {self.database} | User: {self.user}")
        
        # Get pre-vacuum statistics
        pre_stats = self.get_table_stats()
        if pre_stats:
            self.log_table_stats(pre_stats, "BEFORE VACUUM - ")
        
        # Define tables to vacuum - focusing on technical_indicators for TOAST bloat
        tables_to_vacuum = [
            'technical_indicators'
        ]
        
        success_count = 0
        total_start_time = datetime.now()
        
        for table in tables_to_vacuum:
            if self.vacuum_table(table, vacuum_type):
                success_count += 1
            else:
                self.logger.warning(f"Continuing with remaining tables after {table} failure")
        
        total_end_time = datetime.now()
        total_duration = (total_end_time - total_start_time).total_seconds()
        
        # Get post-vacuum statistics
        post_stats = self.get_table_stats()
        if post_stats:
            self.log_table_stats(post_stats, "AFTER VACUUM - ")
            
            # Calculate space differences if we have both sets of stats
            if pre_stats and post_stats:
                self.log_space_differences(pre_stats, post_stats)
        
        # Summary
        self.logger.info(f"Vacuum Summary:")
        self.logger.info(f"Tables vacuumed: {success_count}")
        self.logger.info(f"Total vacuum runtime: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        
        self.conn.close()
        return success_count == len(tables_to_vacuum)
    
    def log_space_differences(self, pre_stats, post_stats):
        """Log space reclaimed during vacuum"""
        pre_sizes = {table: bytes_size for table, _, bytes_size in pre_stats['table_sizes']}
        post_sizes = {table: bytes_size for table, _, bytes_size in post_stats['table_sizes']}
        
        self.logger.info("Space Changes:")
        for table in pre_sizes:
            if table in post_sizes:
                pre_size = pre_sizes[table]
                post_size = post_sizes[table]
                diff = pre_size - post_size
                
                if diff > 0:
                    diff_gb = diff / (1024**3)
                    pct_change = (diff / pre_size) * 100
                    self.logger.info(f"  {table}: Reclaimed {diff_gb:.2f} GB ({pct_change:.1f}%)")
                elif diff < 0:
                    self.logger.info(f"  {table}: Size increased (expected during VACUUM FULL)")
                else:
                    self.logger.info(f"  {table}: No significant size change")


def run_vacuum_job(config_dir: str, vacuum_type: str = 'regular') -> None:
    """Run the vacuum job with configuration from config_dir"""
    try:
        vacuum_runner = VacuumRunner(config_dir)
        success = vacuum_runner.run_automated_vacuum(vacuum_type)
        
        if success:
            vacuum_runner.logger.info(f"Vacuum completed successfully for {vacuum_runner.environment}")
        else:
            vacuum_runner.logger.error(f"Vacuum completed with errors for {vacuum_runner.environment}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Vacuum failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main function for command line execution"""
    parser = argparse.ArgumentParser(description="Run PostgreSQL VACUUM for stockie databases.")
    parser.add_argument("--config-dir", required=True, help="Directory containing settings.yaml and .env")
    parser.add_argument('--type', choices=['regular', 'analyze', 'full'], 
                       default='regular', help='Type of vacuum to perform')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.config_dir):
        print(f"Error: Configuration directory '{args.config_dir}' does not exist")
        sys.exit(1)
        
    run_vacuum_job(args.config_dir, args.type)


if __name__ == "__main__":
    main()