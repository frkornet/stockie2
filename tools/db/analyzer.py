#!/usr/bin/env python3
"""
PostgreSQL Database Analyzer Tool
Comprehensive analysis of database space, performance configuration, TOAST usage, 
and table statistics for PostgreSQL databases.
"""

import psycopg2
import os
import argparse
import sys
from datetime import datetime
from stockie.loaders.config_loader import ConfigLoader

class PostgreSQLSpaceAnalyzer:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.setup_config()
        self.setup_database_connection()
        self.conn = None
    
    def setup_config(self):
        """Load configuration from settings file"""
        self.config_loader = ConfigLoader(self.config_dir)
        self.full_config = self.config_loader.get()
        self.db_config = self.full_config['db']
        
        # Add password from environment variable (following daily.py pattern)
        self.db_config['password'] = os.getenv('DB_PASSWORD')
        
        # Get environment from ConfigLoader (which reads from .env file)
        self.environment = self.config_loader.get_environment()
    
    def setup_database_connection(self):
        """Setup database connection parameters from config"""
        self.database = self.db_config['dbname']
        self.user = self.db_config['user']
        self.password = self.db_config['password']
        self.host = self.db_config.get('host', 'localhost')
        self.port = self.db_config.get('port', 5432)
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            print(f"Connected to {self.environment.upper()} database: {self.database}")
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
        return True
    
    def analyze_database_sizes(self):
        """Get size of current database"""
        print("\n🗄️  DATABASE SIZES")
        print("=" * 50)
        
        query = f"""
        SELECT 
            datname as database_name,
            pg_size_pretty(pg_database_size(datname)) as size_pretty,
            pg_database_size(datname) as size_bytes
        FROM pg_database 
        WHERE datname = '{self.database}';
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'database_name':<15} {'size_pretty':<12} {'size_bytes':<15}")
            print("-" * 45)
            for row in results:
                print(f"{row[0]:<15} {row[1]:<12} {row[2]:<15}")
            
            cursor.close()
            return results
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def analyze_tablespace_sizes(self):
        """Get size of tablespaces relevant to current database"""
        print("\nTABLESPACE SIZES (Current Database Context)")
        print("=" * 60)
        
        # Determine environment-specific tablespace pattern
        env_prefix = f"stockie_{self.environment}_" if self.environment != 'prod' else "stockie_"
        
        query = f"""
        SELECT 
            ts.spcname as tablespace_name,
            pg_size_pretty(pg_tablespace_size(ts.spcname)) as size_pretty,
            pg_tablespace_size(ts.spcname) as size_bytes,
            CASE 
                WHEN ts.spcname LIKE '{env_prefix}%' THEN 'Environment Tablespace'
                WHEN ts.spcname IN ('pg_default', 'pg_global') THEN 'System Tablespace'
                ELSE 'Other Environment'
            END as tablespace_type
        FROM pg_tablespace ts
        WHERE ts.spcname LIKE '{env_prefix}%'
           OR ts.spcname IN ('pg_default', 'pg_global')
        ORDER BY 
            CASE WHEN ts.spcname LIKE '{env_prefix}%' THEN 1
                 WHEN ts.spcname = 'pg_default' THEN 2
                 ELSE 3 END,
            pg_tablespace_size(ts.spcname) DESC;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'tablespace_name':<20} {'size_pretty':<12} {'size_bytes':<15} {'type':<20}")
            print("-" * 70)
            for row in results:
                print(f"{row[0]:<20} {row[1]:<12} {row[2]:<15} {row[3]:<20}")
                
            cursor.close()
            return results
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def analyze_table_sizes(self):
        """Get size of all tables in current database"""
        print("\nTABLE SIZES (Current Database)")
        print("=" * 50)
        
        query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
            pg_total_relation_size(schemaname||'.'||tablename) as total_bytes
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'schema':<8} {'tablename':<20} {'total_size':<12} {'table_size':<12} {'index_size':<12} {'total_bytes':<15}")
            print("-" * 85)
            for row in results:
                print(f"{row[0]:<8} {row[1]:<20} {row[2]:<12} {row[3]:<12} {row[4]:<12} {row[5]:<15}")
            
            cursor.close()
            return results
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def analyze_index_sizes(self):
        """Get size of all indexes"""
        print("\nINDEX SIZES")
        print("=" * 40)
        
        query = """
        SELECT 
            schemaname,
            relname as tablename,
            indexrelname as indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
            pg_relation_size(indexrelid) as index_bytes
        FROM pg_stat_user_indexes 
        ORDER BY pg_relation_size(indexrelid) DESC
        LIMIT 20;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'schema':<8} {'tablename':<20} {'indexname':<25} {'index_size':<12} {'index_bytes':<15}")
            print("-" * 85)
            for row in results:
                print(f"{row[0]:<8} {row[1]:<20} {row[2]:<25} {row[3]:<12} {row[4]:<15}")
            
            cursor.close()
            return results
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def analyze_stockie_tables_detailed(self):
        """Detailed analysis of stockie-specific tables"""
        print("\nSTOCKIE TABLES DETAILED ANALYSIS")
        print("=" * 50)
        
        # Get row counts and sizes for main tables
        query = """
        SELECT 
            'stock_prices' as table_name,
            COUNT(*) as row_count,
            pg_size_pretty(pg_total_relation_size('stock_prices')) as total_size,
            pg_size_pretty(pg_relation_size('stock_prices')) as table_size,
            pg_total_relation_size('stock_prices') as total_bytes
        FROM stock_prices
        
        UNION ALL
        
        SELECT 
            'technical_indicators' as table_name,
            COUNT(*) as row_count,
            pg_size_pretty(pg_total_relation_size('technical_indicators')) as total_size,
            pg_size_pretty(pg_relation_size('technical_indicators')) as table_size,
            pg_total_relation_size('technical_indicators') as total_bytes
        FROM technical_indicators
        
        ORDER BY total_bytes DESC;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'table_name':<20} {'row_count':<12} {'total_size':<12} {'table_size':<12} {'total_bytes':<15}")
            print("-" * 75)
            for row in results:
                print(f"{row[0]:<20} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<15}")
            
            # Additional stats
            print(f"\nADDITIONAL STATS:")
            
            # Stock prices stats
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM stock_prices;")
            unique_tickers = cursor.fetchone()[0]
            print(f"Unique tickers in stock_prices: {unique_tickers:,}")
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM stock_prices;")
            date_range = cursor.fetchone()
            print(f"Date range: {date_range[0]} to {date_range[1]}")
            
            # Technical Indicators stats  
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM technical_indicators;")
            indicator_tickers = cursor.fetchone()[0]
            print(f"Unique tickers in technical_indicators: {indicator_tickers:,}")
            
            # Note: technical_indicators table uses JSONB format for efficient storage
            print("Technical indicators table uses JSONB format")
            
            cursor.close()
            return results
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def analyze_disk_usage_by_type(self):
        """Analyze disk usage by different PostgreSQL object types with TOAST breakdown"""
        print("\n💿 DISK USAGE BY DATA TYPE")
        print("=" * 50)
        
        query = """
        SELECT 
            'Tables' as data_type,
            pg_size_pretty(SUM(pg_relation_size(oid))) as size_pretty,
            SUM(pg_relation_size(oid)) as size_bytes
        FROM pg_class 
        WHERE relkind = 'r' AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        
        UNION ALL
        
        SELECT 
            'Indexes' as data_type,
            pg_size_pretty(SUM(pg_relation_size(oid))) as size_pretty,
            SUM(pg_relation_size(oid)) as size_bytes
        FROM pg_class 
        WHERE relkind = 'i' AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        
        UNION ALL
        
        SELECT 
            'TOAST Tables' as data_type,
            pg_size_pretty(SUM(pg_relation_size(oid))) as size_pretty,
            SUM(pg_relation_size(oid)) as size_bytes
        FROM pg_class 
        WHERE relkind = 't'
        
        ORDER BY size_bytes DESC;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'data_type':<12} {'size_pretty':<12} {'size_bytes':<15}")
            print("-" * 40)
            for row in results:
                print(f"{row[0]:<12} {row[1]:<12} {row[2]:<15}")
            
            cursor.close()
            
            # Add detailed TOAST analysis
            self.analyze_toast_tables()
            
            return results
        except Exception as e:
            print(f"Error analyzing disk usage: {e}")
            return None
    
    def analyze_toast_tables(self):
        """Detailed analysis of TOAST tables (especially for technical_indicators)"""
        print(f"\nDETAILED TOAST ANALYSIS:")
        print("=" * 50)
        
        # Get top 10 largest objects including TOAST
        query = """
        SELECT 
            relname as object_name,
            CASE relkind 
                WHEN 'r' THEN 'Table'
                WHEN 'i' THEN 'Index' 
                WHEN 't' THEN 'TOAST Table'
                WHEN 'S' THEN 'Sequence'
                ELSE relkind::text
            END as object_type,
            pg_size_pretty(pg_relation_size(oid)) as size_pretty,
            pg_relation_size(oid) as size_bytes
        FROM pg_class 
        ORDER BY pg_relation_size(oid) DESC
        LIMIT 10;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            print(f"{'object_name':<25} {'type':<12} {'size':<12} {'size_bytes':<15}")
            print("-" * 70)
            for row in results:
                print(f"{row[0]:<25} {row[1]:<12} {row[2]:<12} {row[3]:<15}")
                
            # Check for technical_indicators update statistics if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'technical_indicators' AND table_schema = 'public'
                );
            """)
            
            if cursor.fetchone()[0]:
                print(f"\nTable Update Statistics (technical_indicators):")
                cursor.execute("""
                    SELECT 
                        relname,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_dead_tup as dead_tuples,
                        CASE WHEN n_tup_ins > 0 
                             THEN ROUND(n_tup_upd::numeric / n_tup_ins::numeric, 1) 
                             ELSE 0 
                        END as avg_updates_per_row,
                        last_autovacuum
                    FROM pg_stat_user_tables 
                    WHERE relname = 'technical_indicators';
                """)
                
                stats = cursor.fetchone()
                if stats:
                    print(f"Table: {stats[0]}")
                    print(f"Inserts: {stats[1]:,}")
                    print(f"Updates: {stats[2]:,}")
                    print(f"Deletes: {stats[3]:,}")
                    print(f"Dead tuples: {stats[4]:,}")
                    print(f"Avg updates per row: {stats[5]}x")
                    print(f"Last autovacuum: {stats[6]}")
                    
                    if stats[5] and float(stats[5]) > 1.5:
                        print(f"\nTOAST Analysis:")
                        print("High update frequency detected - this explains large TOAST table size.")
                        print("JSONB updates create new TOAST entries, causing table bloat.")
                        print("Consider VACUUM FULL during maintenance windows.")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error analyzing TOAST tables: {e}")
    
    def get_performance_config(self):
        """Get key PostgreSQL performance configuration parameters"""
        print("\nPOSTGRESQL PERFORMANCE CONFIGURATION")
        print("=" * 60)
        
        # Key performance parameters to display
        query = """
        SELECT 
            name,
            setting,
            unit,
            context,
            short_desc
        FROM pg_settings 
        WHERE name IN (
            'shared_buffers',           -- Memory for shared buffer cache
            'effective_cache_size',     -- OS cache estimate
            'work_mem',                 -- Memory for sorts/hashes
            'maintenance_work_mem',     -- Memory for maintenance operations
            'wal_buffers',             -- WAL buffer size
            'checkpoint_timeout',       -- Checkpoint frequency
            'checkpoint_completion_target',  -- Checkpoint spreading
            'max_wal_size',            -- WAL size before checkpoint
            'min_wal_size',            -- Minimum WAL size
            'random_page_cost',        -- Cost of random page access
            'seq_page_cost',           -- Cost of sequential page access
            'effective_io_concurrency', -- I/O concurrency
            'max_worker_processes',     -- Max background processes
            'max_parallel_workers',     -- Max parallel workers
            'max_parallel_workers_per_gather',  -- Max parallel workers per query
            'max_connections',          -- Maximum connections
            'autovacuum',              -- Autovacuum enabled
            'autovacuum_max_workers',  -- Max autovacuum workers
            'default_statistics_target' -- Statistics target
        )
        ORDER BY 
            CASE 
                WHEN name LIKE '%mem%' OR name = 'shared_buffers' OR name = 'effective_cache_size' THEN 1
                WHEN name LIKE '%wal%' OR name LIKE '%checkpoint%' THEN 2
                WHEN name LIKE '%parallel%' OR name LIKE '%worker%' OR name = 'max_connections' THEN 3
                WHEN name LIKE '%vacuum%' THEN 4
                ELSE 5
            END,
            name;
        """
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Group parameters by category
            memory_params = []
            wal_checkpoint_params = []
            parallelism_params = []
            maintenance_params = []
            other_params = []
            
            for row in results:
                name, setting, unit, context, desc = row
                param_info = (name, setting, unit or '', context, desc)
                
                if any(keyword in name for keyword in ['mem', 'shared_buffers', 'effective_cache_size']):
                    memory_params.append(param_info)
                elif any(keyword in name for keyword in ['wal', 'checkpoint']):
                    wal_checkpoint_params.append(param_info)
                elif any(keyword in name for keyword in ['parallel', 'worker', 'max_connections']):
                    parallelism_params.append(param_info)
                elif 'vacuum' in name:
                    maintenance_params.append(param_info)
                else:
                    other_params.append(param_info)
            
            # Display grouped parameters
            categories = [
                ("Memory Settings", memory_params),
                ("WAL & Checkpoints", wal_checkpoint_params), 
                ("Parallelism & Connections", parallelism_params),
                ("Maintenance", maintenance_params),
                ("Other Performance", other_params)
            ]
            
            for category_name, params in categories:
                if params:
                    print(f"\n{category_name}")
                    print("-" * len(category_name))
                    for name, setting, unit, context, desc in params:
                        # Format the output nicely
                        value_with_unit = f"{setting} {unit}".strip()
                        print(f"  {name:<30} {value_with_unit:<15} ({context})")
            
            cursor.close()
            return results
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        print(f"\nPOSTGRESQL DATABASE ANALYSIS REPORT ({self.environment.upper()})")
        print(f"Database: {self.database} | User: {self.user}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Run all analyses
        db_sizes = self.analyze_database_sizes()
        tablespace_sizes = self.analyze_tablespace_sizes()
        table_sizes = self.analyze_table_sizes()
        index_sizes = self.analyze_index_sizes()
        stockie_details = self.analyze_stockie_tables_detailed()
        disk_usage = self.analyze_disk_usage_by_type()
        perf_config = self.get_performance_config()
        
        # Summary insights
        print(f"\nKEY INSIGHTS:")
        print("-" * 30)
        
        try:
            if table_sizes is not None and len(table_sizes) > 0:
                largest_table = table_sizes[0]  # First row is largest
                print(f"Largest table: {largest_table[1]} ({largest_table[2]})")  # tablename, total_size
                
            if stockie_details is not None and len(stockie_details) > 0:
                total_stockie_bytes = sum(row[4] for row in stockie_details)  # total_bytes column
                print(f"Total stockie data: {total_stockie_bytes / (1024**3):.2f} GB")
        except Exception as e:
            print(f"Summary calculation skipped: {e}")
        
        print(f"\nRECOMMENDATIONS:")
        print("-" * 30)
        print("1. Check if old data can be archived or partitioned")
        print("2. Analyze index usage - unused indexes waste space")
        print("3. Consider VACUUM FULL for heavily updated tables")
        print("4. Monitor WAL file accumulation")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("\nDatabase connection closed")


def run_analysis(config_dir: str) -> None:
    """Run comprehensive database analysis with configuration from config_dir"""
    try:
        analyzer = PostgreSQLSpaceAnalyzer(config_dir)
        print(f"Analyzing {analyzer.environment.upper()} database...")
        
        if not analyzer.connect():
            return
        
        try:
            analyzer.generate_summary_report()
        except Exception as e:
            print(f"Error during analysis: {e}")
        finally:
            analyzer.close()
            
    except Exception as e:
        print(f"Analysis failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main function for command line execution"""
    parser = argparse.ArgumentParser(description="Run comprehensive PostgreSQL database analysis including space, performance, and configuration.")
    parser.add_argument("--config-dir", required=True, help="Directory containing settings.yaml and .env")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.config_dir):
        print(f"Error: Configuration directory '{args.config_dir}' does not exist")
        sys.exit(1)
        
    run_analysis(args.config_dir)


if __name__ == "__main__":
    main()